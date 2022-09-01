import time
from copy import deepcopy
from datetime import datetime
from logging import Logger
from typing import List

from src.events import IngestionEvent
from src import cloudwatch as cw
from src import es
from src import postgres as rds
from src import timestream as ts
from src.helpers import DataType

log = Logger(name="write_helper")


def _write_to_cw(events: List[dict]):
    now = time.localtime()
    log_stream = f"{now.tm_year}/{now.tm_mon}/{now.tm_mday}/{now.tm_hour}/{now.tm_min}"
    cw.write_many(log_stream, events)


def _write_to_es(events: List[dict]):
    field_types = IngestionEvent.get_types_for_event_fields()
    es_type_for_data = {
        DataType.STRING: "keyword",
        DataType.INTEGER: "integer",
        DataType.BOOLEAN: "boolean",
        DataType.TIMESTAMP: "date"
    }
    index_settings = {
        "mappings": {
            "properties": {
                field: {"type": es_type_for_data.get(field_type)}
                for field, field_type in field_types.items()
            }
        }
    }
    index = "monitoring_events"
    es.create_index_if_not_exists(index, index_settings)
    es.index_documents_in_bulk(index, events)


def _write_to_rds(events: List[dict]):
    field_types = IngestionEvent.get_types_for_event_fields()
    postgres_type_for_data = {
        DataType.STRING: "text",
        DataType.INTEGER: "integer",
        DataType.BOOLEAN: "boolean",
        DataType.TIMESTAMP: "timestamp"
    }
    table = "monitoring_events"
    col_name_and_types = {
        field: postgres_type_for_data.get(field_type)
        for field, field_type in field_types.items()
    }
    col_name_and_types["id"] = "serial"
    for event in events:
        for field, value in event.items():
            if field_types.get(field) == DataType.TIMESTAMP:
                event[field] = datetime.fromtimestamp(value / 1000)
    with rds.PSQLConnection() as connection:
        connection.create_table(table, "id", col_name_and_types)
        connection.create_index(table, "ingestion_batch_id")
        connection.create_index(table, "user_id")
        connection.create_index(table, "repo_id")
        connection.create_index(table, "job_id")
        connection.create_index(table, "created_at")
        connection.create_index(table, "time")
        connection.insert_rows(table, events)


def _write_to_ts(events: List[dict]):
    field_types = IngestionEvent.get_types_for_event_fields()
    field_types["created_at"] = DataType.STRING
    field_types["num_stages"] = DataType.STRING
    for event in events:
        for field, value in event.items():
            event[field] = str(value)

    ts_client = ts.Timestream()
    ts_client.write(
        events,
        field_types,
        "time",
        ["stage", "stage_progress", "errored", "finished"],
        [
            "ingestion_batch_id",
            "org_id",
            "user_id",
            "repo_id",
            "repo_version",
            "priority",
            "job_id",
            "job_type",
            "created_at",
            "dataset_id",
            "num_stages",
        ]
    )


def write_events(events: List[dict]):
    print(f"Writing {len(events)} events...")

    print("-> cloudwatch")
    _write_to_cw(deepcopy(events))

    print("-> elasticsearch")
    _write_to_es(deepcopy(events))

    print("-> rds")
    _write_to_rds(deepcopy(events))

    print("-> timestream")
    _write_to_ts(deepcopy(events))
