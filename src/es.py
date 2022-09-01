import concurrent.futures
import json
import os
import time
from http import HTTPStatus
from logging import Logger
from typing import Callable, List

import requests

from src.helpers import get_awsauth, timed_operation

ES_CONTENT_HEADERS = {'Content-Type': 'application/json'}
DEFAULT_PAGE_SIZE = 1000
log = Logger(name="elasticsearch")
elastic_url = "https://" + os.getenv("ES_DOMAIN_URL") + "/"
auth = get_awsauth(os.getenv("AWS_REGION"), "es")


def _check_response(response, operation_name, ignored_errors=None, err_title=None):
    response_data = response.json()

    if response.status_code == HTTPStatus.GATEWAY_TIMEOUT:
        # Since the last request ended in a timeout, we will make the process
        # sleep for 10s and give Elasticsearch a break from processing requests
        time.sleep(10)

    has_error = (
        response_data is not None
        and "error" in response_data
        and isinstance(response_data.get("error"), dict)
    )
    has_multiple_errors = (
        response_data is not None
        and "errors" in response_data
        and response_data.get("errors") is True
    )
    if response.status_code not in [200, 201] or has_error or has_multiple_errors:
        if ignored_errors is None:
            ignored_errors = set()

        error_data = None
        if has_error:
            error_data = response_data.get("error")
            if error_data.get("type") in ignored_errors:
                error_data = None
        if has_multiple_errors:
            error_data = []
            for item in response_data.get("items"):
                item_error = item.get("error")
                if item_error.get("type") in ignored_errors:
                    continue
                if item_error:
                    error_data.append(item_error)

        if error_data:
            log.warning(
                {
                    "message": "Operation failed",
                    "operation": operation_name,
                    "error_title": err_title,
                    "error_data": error_data
                }
            )
            raise Exception(error_data)

    return response_data


def create_index_if_not_exists(index: str, index_settings: dict):
    index_url = elastic_url + index
    resp = requests.head(index_url, auth=auth)
    index_not_present = resp.status_code == 404
    if index_not_present:
        log.info("Creating new index: " + index)
        resp = requests.put(index_url, auth=auth, json=index_settings)
        _check_response(resp, "create_index_if_not_exists")


def index_document(index: str, document: dict, doc_id: str):
    resp = requests.post(
        f"{elastic_url}{index}/_doc/{doc_id}",
        auth=auth,
        json=document
    )
    _check_response(resp, "index_document")
    return resp


def index_documents_in_bulk(
    index: str,
    documents: List[dict],
    doc_ids: List[str] = None,
    batch_size=500,
):
    def action_item(idx: int):
        if doc_ids is not None and len(doc_ids) == len(documents):
            return {
                "index": {"_index": index, "_type": "_doc", "_id": doc_ids[idx]}
            }
        return {"index": {"_index": index, "_type": "_doc"}}

    batches_of_actions = []
    actions = []
    for i, document in enumerate(documents):
        actions.append(json.dumps(action_item(i)))
        actions.append(json.dumps(document))

        is_full_batch = (i + 1) % batch_size == 0
        is_last_batch = i == len(documents) - 1
        if is_full_batch or is_last_batch:
            batches_of_actions.append(actions.copy())
            actions = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_batch_write = {
            executor.submit(_bulk_index, actions)
            for actions in batches_of_actions
        }
        with timed_operation(
            "elasticsearch",
            "basic_write",
            num_records=len(documents)
        ):
            for future in concurrent.futures.as_completed(future_to_batch_write):
                try:
                    future.result()
                except Exception as exc:
                    raise exc


def get_document(index: str, doc_id: str) -> dict:
    resp = requests.get(
        f"{elastic_url}{index}/_doc/{doc_id}",
        auth=auth,
    )
    result = _check_response(resp, "get_document")
    return result


def get_documents_in_bulk(index: str, doc_ids: List[str]) -> List[dict]:
    json_payload = {
        "ids": doc_ids
    }
    resp = requests.get(
        f"{elastic_url}{index}/_mget",
        auth=auth,
        headers=ES_CONTENT_HEADERS,
        json=json_payload
    )
    result = _check_response(resp, "get_documents_in_bulk")
    return result.get("docs")


def query(index: str, query: dict) -> List[dict]:
    request_url = f"{elastic_url}{index}/_search"
    resp = requests.get(request_url, auth=auth, json=query)
    return _check_response(resp, "query")


def query_documents(
    index: str,
    query: dict,
    sort_by: List[dict] = None,
    source_fields_to_fetch: List[str] = None,
    filter_fn: Callable = None
) -> List[dict]:
    def _fetch_page(_scroll_id: str = None) -> dict:
        if _scroll_id is None:
            payload = {
                "size": DEFAULT_PAGE_SIZE,
                "query": query,
            }
            if sort_by is not None:
                payload["sort"] = sort_by
            if source_fields_to_fetch is not None:
                payload["_source"] = source_fields_to_fetch
            request_url = f"{elastic_url}{index}/_search?scroll=1m"
        else:
            payload = {
                "scroll": "5s",
                "scroll_id": _scroll_id
            }
            request_url = f"{elastic_url}_search/scroll"

        resp = requests.get(request_url, auth=auth, json=payload)
        return _check_response(resp, "query_documents:_fetch_page")

    def _hits_from_results(_results) -> List[dict]:
        return (_results.get("hits") or {}).get("hits", [])

    results = _fetch_page()
    hits = _hits_from_results(results)
    all_hits = []
    scroll_ids = []
    while len(hits) > 0:
        if filter_fn:
            hits = [document for document in hits if filter_fn(document)]
        all_hits.extend(hits)

        scroll_id = results.get("_scroll_id")
        if scroll_id:
            scroll_ids.append(scroll_id)

        results = _fetch_page(scroll_id)
        hits = _hits_from_results(results)

    # Clear scroll contexts
    requests.delete(
        f"{elastic_url}_search/scroll", json={
            "scroll_id": scroll_ids
        }
    )

    return all_hits


def _bulk_index(actions: List[str], start=0, end=None, backoff=1):
    """
    This function sends bulk_index request to Elasticsearch and also handles
    `RequestPayload` too large error.

    Args:
        actions (list): Elasticsearch bulk index documents
        start (int, optional): payload slice start. Defaults to 0.
        end (int, optional): payload slice end. Defaults to None.

    Returns:
        int: batch size to be used in next requests
    """
    end = end or len(actions)
    batch_size = end - start
    resp = requests.put(
        f"{elastic_url}_bulk",
        auth=auth,
        headers=ES_CONTENT_HEADERS,
        data=('\n'.join(actions[start:end]) + '\n').encode()
    )
    if resp.status_code == 413:
        mid = (start + end) // 2
        # ensure mid is always even, since actions are in batches of 2
        mid = mid + 1 if mid % 2 == 1 else mid
        batch_size = min(_bulk_index(actions, start, mid), batch_size)
        batch_size = max(_bulk_index(actions, mid, end), batch_size)
    elif (
        resp.status_code == HTTPStatus.TOO_MANY_REQUESTS
        or resp.status_code == HTTPStatus.GATEWAY_TIMEOUT
    ):
        if backoff > 60:
            _check_response(resp, "_bulk_index")
        else:
            time.sleep(backoff)
            _bulk_index(actions, start, end, backoff=(backoff * 2))
    else:
        _check_response(resp, "_bulk_index")
    return batch_size


def index_exists(index_name):
    index_url = elastic_url + index_name
    resp = requests.head(index_url, auth=auth)
    return not resp.status_code == HTTPStatus.NOT_FOUND


def delete_index(index_name):
    index_url = elastic_url + index_name
    resp = requests.delete(index_url, auth=auth)
    _check_response(resp, "delete_index", err_title=f"{index_name} deletion failed")
    return resp


def reindex(source_index, destination_index, fields_list=None):
    payload = {
        "source": {
            "index": source_index
        },
        "dest": {
            "index": destination_index
        },
    }
    if fields_list:
        payload["source"]["_source"] = fields_list
    index_url = elastic_url + "_reindex"
    resp = requests.post(index_url, auth=auth, json=payload)
    _check_response(
        resp,
        "reindex",
        err_title=f"{source_index} -> {destination_index} reindex failed"
    )
    return resp


def refresh_index(index_name):
    resp = requests.post(elastic_url + f"{index_name}/_refresh", auth=auth)
    _check_response(
        resp,
        "refresh_index",
        err_title=f"{index_name} refresh index failed"
    )
    return resp


def get_all_indices_request():
    resp = requests.get(
        f"{elastic_url}_cat/indices?bytes=b&s=index&format=json",
        auth=auth
    )
    return resp.json()
