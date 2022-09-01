from enum import Enum

from src import cloudwatch as cw
from src import es
from src import postgres as rds
from src import timestream as ts
from src.helpers import timed_operation
from src.queries.type1 import queries as type1_queries
from src.queries.type2 import queries as type2_queries
from src.queries.type3 import queries as type3_queries
from src.queries.type4 import queries as type4_queries
from src.queries.type5 import queries as type5_queries


class QueryType(Enum):
    TYPE_I = 1
    TYPE_II = 2
    TYPE_III = 3
    TYPE_IV = 4
    TYPE_V = 5

    def get_query(self, service: str):
        if self == QueryType.TYPE_I:
            return type1_queries.get(service)
        elif self == QueryType.TYPE_II:
            return type2_queries.get(service)
        elif self == QueryType.TYPE_III:
            return type3_queries.get(service)
        elif self == QueryType.TYPE_IV:
            return type4_queries.get(service)
        else:
            return type5_queries.get(service)

    def __str__(self):
        return f"query_type_{self.value}"


def _query_from_cw(query_type: QueryType, scale: str):
    query = query_type.get_query("cw")
    operation = f"{query_type}__{scale}"
    for i in range(10):
        with timed_operation("cloudwatch_logs", operation, is_first_query=(i == 0)):
            res = cw.query(query)
        for _ in res:
            pass


def _query_from_es(query_type: QueryType, scale: str):
    query = query_type.get_query("es")
    operation = f"{query_type}__{scale}"
    for i in range(10):
        with timed_operation("elasticsearch", operation, is_first_query=(i == 0)):
            es.query("monitoring_events", query)


def _query_from_rds(query_type: QueryType, scale: str):
    query = query_type.get_query("rds")
    operation = f"{query_type}__{scale}"
    with rds.PSQLConnection() as connection:
        for i in range(10):
            with timed_operation("rds", operation, is_first_query=(i == 0)):
                res = connection.exec_query(query)
                for _ in res:
                    pass


def _query_from_ts(query_type: QueryType, scale: str):
    query = query_type.get_query("ts")
    operation = f"{query_type}__{scale}"
    ts_client = ts.Timestream()
    for i in range(10):
        with timed_operation("ts", operation, is_first_query=(i == 0)):
            ts_client.query(query)


def perform_queries(scale):
    print(f"Querying data stores for scale {scale}...")

    query_types = [
        QueryType.TYPE_I,
        QueryType.TYPE_II,
        QueryType.TYPE_III,
        QueryType.TYPE_IV,
        QueryType.TYPE_V,
    ]
    for query_type in query_types:
        print(f"-> cloudwatch, {query_type}")
        _query_from_cw(query_type, scale)

        print(f"-> elasticsearch, {query_type}")
        _query_from_es(query_type, scale)

        print(f"-> rds, {query_type}")
        _query_from_rds(query_type, scale)

        print(f"-> timestream, {query_type}")
        _query_from_ts(query_type, scale)
