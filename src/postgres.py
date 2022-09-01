import os
from typing import Any, Dict, List
from uuid import uuid4

import psycopg2
from psycopg2.extras import execute_values

from src.helpers import create_batches_from_list, timed_operation

batch_size = 500


class PSQLClient:
    def __init__(self):
        self._connection = psycopg2.connect(
            host=os.getenv("RDS_DB_HOST"),
            port=os.getenv("RDS_DB_PORT"),
            dbname=os.getenv("RDS_DB_NAME"),
            user=os.getenv("RDS_DB_USER"),
            password=os.getenv("RDS_DB_PASSWORD"),
        )

    def create_table(
        self,
        table: str,
        primary_key: str,
        col_name_and_types: Dict[str, str]
    ):
        table_cols = []
        for col_name, col_type in col_name_and_types.items():
            if col_name == primary_key:
                table_cols.append(f"{col_name} {col_type} PRIMARY KEY")
            else:
                table_cols.append(f"{col_name} {col_type}")
        query = f"""
        CREATE TABLE IF NOT EXISTS {table} (
            {', '.join(table_cols)}
        )
        """

        with self._connection.cursor() as cursor:
            cursor.execute(query)

    def create_index(self, table: str, column: str):
        query = f"CREATE INDEX IF NOT EXISTS {table}__{column} ON {table} ({column})"
        with self._connection.cursor() as cursor:
            cursor.execute(query)
            self._connection.commit()

    def _insert_row_batch(self, table: str, rows: List[dict]):
        col_names = ()
        row_values_list = []
        for row_data in rows:
            col_names = list(row_data.keys())
            row_values = tuple(row_data.values())
            row_values_list.append(row_values)

        query = f"INSERT INTO {table} ({','.join(col_names)}) VALUES %s"
        with timed_operation("rds", "basic_write", num_records=len(rows)):
            with self._connection.cursor() as cursor:
                execute_values(cursor, query, row_values_list)
                self._connection.commit()

    def insert_rows(self, table: str, rows: List[dict]):
        batches_of_rows = create_batches_from_list(rows, batch_size)
        for batch in batches_of_rows:
            self._insert_row_batch(table, batch)

    def exec_query(self, query: str, args: tuple = None):
        with self._connection.cursor(name=f"rds_query_{uuid4()}") as cursor:
            cursor.itersize = 10000

            cursor.execute(query, args)
            for row in cursor:
                yield row

    def cleanup(self):
        self._connection.close()


class PSQLConnection:
    def __enter__(self):
        self.client = PSQLClient()
        return self.client

    def __exit__(self, exc_type, exc_value, traceback):
        self.client.cleanup()
