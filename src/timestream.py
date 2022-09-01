import concurrent.futures
import os
from datetime import datetime
from logging import Logger
from typing import Any, Dict, Iterator, List, Optional, Union

import boto3
from botocore.config import Config

from src.helpers import create_batches_from_list, timed_operation

batch_size = 100


def _cast_value(value: str, data_type: str) -> Any:
    if data_type == "VARCHAR":
        return value
    if data_type in ("INTEGER", "BIGINT"):
        return int(value)
    if data_type == "DOUBLE":
        return float(value)
    if data_type == "BOOLEAN":
        return value.lower() == "true"
    if data_type == "TIMESTAMP":
        return datetime.strptime(value[:-3], "%Y-%m-%d %H:%M:%S.%f")
    if data_type == "DATE":
        return datetime.strptime(value, "%Y-%m-%d").date()
    if data_type == "TIME":
        return datetime.strptime(value[:-3], "%H:%M:%S.%f").time()
    if data_type == "ARRAY":
        return str(value)
    raise ValueError(f"Unsupported Amazon Timestream type: {data_type}")


def _process_row_data(schema: List[Dict[str, str]], row_data: Dict[str, Any]):
    row_processed = []
    for col_schema, col in zip(schema, row_data["Data"]):
        if col.get("NullValue", False):
            row_processed.append(None)
        elif "ScalarValue" in col:
            row_processed.append(
                _cast_value(
                    value=col["ScalarValue"],
                    data_type=col_schema["type"]
                )
            )
        elif "ArrayValue" in col:
            row_processed.append(
                _cast_value(value=col["ArrayValue"], data_type="ARRAY")
            )
        else:
            raise ValueError(
                f"Query with non ScalarType/ArrayColumnInfo/NullValue for "
                f"column {col_schema['name']}. "
                f"Expected {col_schema['type']} instead of {col}"
            )
    return row_processed


def _process_schema(page: Dict[str, Any]) -> List[Dict[str, str]]:
    schema: List[Dict[str, str]] = []
    for col in page["ColumnInfo"]:
        if "ScalarType" in col["Type"]:
            schema.append(
                {"name": col["Name"], "type": col["Type"]["ScalarType"]}
            )
        elif "ArrayColumnInfo" in col["Type"]:
            schema.append(
                {
                    "name": col["Name"],
                    "type": col["Type"]["ArrayColumnInfo"]
                }
            )
        else:
            raise ValueError(
                f"Query with non ScalarType or ArrayColumnInfo for column "
                f"{col['Name']}: {col['Type']}"
            )
    return schema


def _serialize_rows(
    row_list: List[List[Any]],
    schema: List[Dict[str, str]]
) -> List[Dict[str, Any]]:
    rows = []
    column_names = [c["name"] for c in schema]
    for row_data in row_list:
        row = {}
        for k, v in zip(column_names, row_data):
            row[k] = v
        rows.append(row)
    return rows


def wrap_in_pagination_query(
    select_statement: str,
    page_size: int,
    page_after: int,
    sort_by: str,
    sort_order: str,
):
    return f'''
    SELECT *
    FROM (
        SELECT
            ROW_NUMBER() OVER (
                ORDER BY row_of_interest.{sort_by} {sort_order}
            ) AS row_num,
            row_of_interest.*
        FROM (

            {select_statement}

        ) row_of_interest
    )
    WHERE row_num BETWEEN {page_after + 1} and {page_after + page_size}
    '''


class Timestream:

    def __init__(self):
        ts_read_config = Config(read_timeout=60, retries={"max_attempts": 10})
        self._read_client = boto3.client(
            'timestream-query',
            config=ts_read_config,
            region_name="us-west-2"
        )
        ts_write_config = Config(
            read_timeout=20,
            max_pool_connections=5000,
            retries={"max_attempts": 10},
            region_name="us-west-2"
        )
        self._write_client = boto3.client('timestream-write', config=ts_write_config)

        table_id = os.getenv("TS_TABLE_ID")
        self._table, self._db = table_id.split(":")

        self._logger = Logger(name='timestream')

    def _paginate_query(
        self,
        sql: str,
        pagination_config: Optional[Dict[str, Any]],
        transform=False
    ) -> Iterator[List[Dict[str, Any]]]:
        paginator = self._read_client.get_paginator("query")
        row_list: List[List[Any]] = []
        schema: List[Dict[str, str]] = []
        page_iterator = paginator.paginate(
            QueryString=sql,
            PaginationConfig=pagination_config or {}
        )
        for page in page_iterator:
            if transform:
                if not schema:
                    schema = _process_schema(page=page)
                    self._logger.info("schema: %s", schema)
                for row_data in page["Rows"]:
                    row_list.append(_process_row_data(schema, row_data))
                if len(row_list) > 0:
                    yield _serialize_rows(row_list, schema)
                row_list = []
            else:
                yield page["Rows"]

    def query(self, sql: str, page_size: int = 100, chunked=False, transform=False):
        self._logger.info(
            {
                "message": "Running query",
                "query": sql.replace("\n", " ")
            }
        )
        result_iterator = self._paginate_query(
            sql,
            pagination_config={'PageSize': page_size},
            transform=transform
        )

        if chunked:
            return result_iterator

        rows = []
        for row_batch in result_iterator:
            rows.extend(row_batch)
        self._logger.info(
            {
                "message": "Query executed",
                "num_rows": len(rows)
            }
        )
        return rows

    @staticmethod
    def _prepare_records(
        rows: List[Dict[str, Any]],
        col_types: Dict[str, Any],
        time_col: str,
        measure_cols: List[str],
        dimension_cols: List[str]
    ):
        records = []
        for row in rows:
            dimensions = [
                {
                    'Name': col,
                    'Value': value,
                    'DimensionValueType': str(col_types.get(col))
                }
                for col, value in row.items()
                if col in dimension_cols
            ]
            timestamp = row.get(time_col)
            records.append(
                {
                    'Dimensions': dimensions,
                    'Time': timestamp,
                    'TimeUnit': 'MILLISECONDS',
                    'MeasureName': 'record',
                    'MeasureValueType': 'MULTI',
                    'MeasureValues': [
                        {
                            'Name': col,
                            'Value': value,
                            'Type': str(col_types.get(col))
                        }
                        for col, value in row.items()
                        if col in measure_cols
                    ]
                }
            )
        return records

    def _write_record_batch(self, record_batch):
        try:
            self._write_client.write_records(
                DatabaseName=self._db,
                TableName=self._table,
                Records=record_batch
            )
        except self._write_client.exceptions.RejectedRecordsException as e:
            self._logger.error({"RejectedRecords": e})
            for rr in e.response["RejectedRecords"]:
                self._logger.error(
                    f"Rejected index {rr['RecordIndex']}: {rr['Reason']}"
                )

    def _write_records(self, records):
        batches_of_records = create_batches_from_list(records, batch_size)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_batch_write = {
                executor.submit(self._write_record_batch, batch)
                for batch in batches_of_records
            }
            with timed_operation("timestream", "basic_write", num_records=len(records)):
                for future in concurrent.futures.as_completed(future_to_batch_write):
                    try:
                        future.result()
                    except Exception as exc:
                        raise exc

    def write(
        self,
        rows: List[Dict[str, Any]],
        col_types: Dict[str, Any],
        time_col: str,
        measure_col: Union[str, List[str]],
        dimensions_cols: List[str]
    ):
        if len(rows) == 0:
            return

        self._logger.info(
            {
                "message": "Writing records to Timestream",
                "db": self._db,
                "table": self._table,
                "num_records": len(rows)
            }
        )

        if isinstance(measure_col, str):
            measure_col = [measure_col]

        records = Timestream._prepare_records(
            rows,
            col_types,
            time_col,
            measure_col,
            dimensions_cols
        )
        self._write_records(records)
