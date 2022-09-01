import os
import time
from contextlib import ContextDecorator
from datetime import datetime, timedelta
from enum import Enum

import boto3
from requests_aws4auth import AWS4Auth


def get_unix_timestamp():
    return int(time.time())


def get_unix_timestamp_ms():
    return int(round(time.time() * 1000))


def get_timestamp_with_offset(
    timestamp: int,
    days: float = 0,
    minutes: float = 0,
    ahead=True,
    ms=True
):
    dt = datetime.fromtimestamp(timestamp)
    td = timedelta(days=days, minutes=minutes)
    if ahead:
        datetime_with_offset = dt + td
    else:
        datetime_with_offset = dt - td
    if ms:
        return int(round(datetime_with_offset.timestamp() * 1000))
    return int(datetime_with_offset.timestamp())


def create_batches_from_list(list_of_items: list, batch_size: int = 100):
    return [
        list_of_items[i:(i + batch_size)]
        for i in range(0, len(list_of_items), batch_size)
    ]


def get_awsauth(region, service):
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        service,
        session_token=credentials.token,
    )
    return awsauth


class DataType(str, Enum):
    STRING = "VARCHAR"
    INTEGER = "BIGINT"
    DOUBLE = "DOUBLE"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"

    def __str__(self):
        return str(self.value)


class timed_operation(ContextDecorator):
    def __init__(self, data_store, operation, num_records=None, is_first_query=None):
        self.record_id = str(get_unix_timestamp_ms())
        self.data_store = data_store
        self.operation = operation
        self.num_records = num_records
        self.is_first_query = is_first_query
        self.start_time = -1
        self.end_time = -1
        self._table = boto3.resource("dynamodb").Table(
            os.getenv("BENCHMARK_DATA_TABLE_NAME")
        )

    def __enter__(self):
        self.start_time = get_unix_timestamp_ms()

    def __exit__(self, exc_type, exc, exc_tb):
        self.end_time = get_unix_timestamp_ms()
        if not exc:
            item = {
                "record_id": self.record_id,
                "data_store": self.data_store,
                "operation": self.operation,
                "exec_time": self.end_time - self.start_time,
            }
            if self.num_records is not None:
                item["num_records"] = self.num_records
            if self.is_first_query is not None:
                item["is_first_query"] = self.is_first_query
            self._table.put_item(Item=item)
