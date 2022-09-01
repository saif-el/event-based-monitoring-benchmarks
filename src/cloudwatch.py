import json
import os
import time
from logging import Logger
from typing import List

import boto3
from botocore.exceptions import ClientError

from src.helpers import (
    create_batches_from_list,
    get_unix_timestamp,
    get_timestamp_with_offset, timed_operation
)

log = Logger(name="cloudwatch")
cw_logs = boto3.client('logs')
log_group = os.getenv("CLOUDWATCH_LOG_GROUP")
batch_size = 500


def _put_log_events(kwargs, this_batch_size):
    with timed_operation("cloudwatch_logs", "basic_write", num_records=this_batch_size):
        try:
            return cw_logs.put_log_events(**kwargs)
        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidSequenceTokenException":
                log_stream_name = kwargs.get("logStreamName")
                response = cw_logs.describe_log_streams(
                    logGroupName=kwargs.get("logGroupName"),
                    logStreamNamePrefix=log_stream_name
                )
                if "logStreams" in response and len(response.get("logStreams")) > 0:
                    log_stream = response.get("logStreams")[0]
                    if log_stream.get("logStreamName") == log_stream_name:
                        kwargs["sequenceToken"] = log_stream.get("uploadSequenceToken")
                        return cw_logs.put_log_events(**kwargs)
            raise e


def write_many(log_stream: str, items: List[dict]):
    if len(items) == 0:
        return

    sequence_token = None
    batches = create_batches_from_list(items, batch_size)
    for batch in batches:
        this_batch_size = len(batch)
        kwargs = {
            "logGroupName": log_group,
            "logStreamName": log_stream,
            "logEvents": [
                {
                    "timestamp": item.pop("time"),
                    "message": json.dumps(item),
                }
                for item in batch
            ]
        }
        if sequence_token is not None:
            kwargs["sequenceToken"] = sequence_token
        try:
            response = _put_log_events(kwargs, this_batch_size)
            sequence_token = response.get("nextSequenceToken")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                log.info(
                    {
                        "message": "Creating new log stream",
                        "log_group": log_group,
                        "log_stream": log_stream
                    }
                )
                try:
                    cw_logs.create_log_stream(
                        logGroupName=log_group,
                        logStreamName=log_stream
                    )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                        pass
                    else:
                        raise e
                response = _put_log_events(kwargs, this_batch_size)
                sequence_token = response.get("nextSequenceToken")
            elif e.response["Error"]["Code"] == "InvalidSequenceTokenException":
                log.info(
                    {
                        "message": "Attempted putting events with "
                                   "invalid sequence token",
                        "log_group": log_group,
                        "log_stream": log_stream
                    }
                )
                sequence_token = e.response.get("expectedSequenceToken")
                kwargs["sequenceToken"] = sequence_token
                response = _put_log_events(kwargs, this_batch_size)
                sequence_token = response.get("nextSequenceToken")
            else:
                log.exception(e)
                raise e


def get_many(
    log_stream,
    page_size=100,
    page_cursor: str = None,
    page_direction='next'
):
    kwargs = {
        "logGroupName": log_group,
        "logStreamName": log_stream,
        "limit": page_size,
    }
    if page_cursor is not None:
        kwargs["nextToken"] = page_cursor
    if page_direction == 'next':
        kwargs["startFromHead"] = True
    else:
        kwargs["startFromHead"] = False

    try:
        response = cw_logs.get_log_events(**kwargs)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            log.info(
                {
                    "message": f"No logs found",
                    "log_group": log_group,
                    "log_stream": log_stream
                }
            )
            return [], None, None
        raise e

    items = [
        json.loads(item.get("message"))
        for item in response.get("events")
    ]
    next_page_cursor = response.get("nextForwardToken")
    prev_page_cursor = response.get("nextBackwardToken")

    if page_direction == 'next' and page_cursor == next_page_cursor:
        next_page_cursor = None
    if page_direction == 'prev' and page_cursor == prev_page_cursor:
        prev_page_cursor = None

    return items, prev_page_cursor, next_page_cursor


def search(
    log_stream,
    search_term,
    page_size=10,
    page_cursor: str = None
):
    kwargs = {
        "logGroupName": log_group,
        "logStreamNames": [log_stream],
        "filterPattern": search_term,
        "limit": page_size,
    }
    if page_cursor is not None:
        kwargs["nextToken"] = page_cursor,

    try:
        response = cw_logs.filter_log_events(**kwargs)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            log.info(
                {
                    "message": f"No logs found",
                    "search_term": search_term,
                    "log_group": log_group,
                    "log_stream": log_stream
                }
            )
            return [], None
        raise e

    items = [
        json.loads(item.get("message"))
        for item in response.get("events")
    ]
    next_page_cursor = response.get("nextToken")

    return items, next_page_cursor


def query(query_string):
    start_time = get_unix_timestamp()
    kwargs = {
        "logGroupName": log_group,
        "startTime": start_time,
        "endTime": get_timestamp_with_offset(start_time, days=7),
        "queryString": query_string,
    }
    response = cw_logs.start_query(**kwargs)
    query_id = response.get("queryId")
    response = cw_logs.get_query_results(queryId=query_id)
    while response.get("status") in {"Scheduled", "Running"}:
        time.sleep(1)
        response = cw_logs.get_query_results(queryId=query_id)

    return response.get("results")
