#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

import json

from sqlalchemy import text


class Viewer:
    def __init__(self, database):
        self.database = database
        self.tables = {}
        self.auto_backup = True

    def fetch_data(
            self,
            table: str,
            columns: list,
            sort_by: str,
            order: str,
            search_query: str = None,
            search_column: str = None,
            offset: int = 0,
            limit: int = 100,
            filters: dict = None
    ) -> list:
        """
        Fetch data from the database with the given parameters.

        :param table: Table name
        :param columns: List of columns to fetch
        :param sort_by: Column to sort by
        :param order: Sort order (ASC or DESC)
        :param search_query: Search query
        :param search_column: Search column
        :param offset: Offset
        :param limit: Limit
        :param filters: Filters
        :return: Fetched data
        """
        tables = self.database.get_tables()

        if search_column:
            search_fields = [search_column]
        else:
            search_fields = tables[table]['search_fields']

        base_query = f"SELECT {', '.join(columns)} FROM {table}"
        where_clause = ""
        order_clause = f" ORDER BY {sort_by} {order}"
        limit_clause = f" LIMIT {limit} OFFSET {offset}"

        params = {}
        if search_query:
            search_clauses = [f"{column} LIKE :search_query" for column in search_fields]
            where_clause = f" WHERE ({' OR '.join(search_clauses)})"
            params['search_query'] = f"%{search_query}%"

        # apply filters
        # filters = {
        #     "column1": "value1",
        #     "column2": "value2"  # AND condition
        # }
        if filters:
            filter_clauses = [f"{column} = :filter_{column}" for column in filters.keys()]
            if where_clause == "":
                where_clause = f" WHERE ({' AND '.join(filter_clauses)})"
            else:
                where_clause += f" AND ({' AND '.join(filter_clauses)})"
            for column, value in filters.items():
                params[f"filter_{column}"] = value  # filter placeholder prefixed with 'filter_'

        query = f"{base_query}{where_clause}{order_clause}{limit_clause}"
        stmt = text(query).bindparams(**params)
        with self.database.get_db().connect() as conn:
            result = conn.execute(stmt).fetchall()
            return result

    def count_rows(
            self,
            table: str,
            search_query: str = None,
            search_column: str = None,
            filters: dict = None
    ) -> int:
        """
        Count the number of rows in the table with an optional search query.

        :param table: Table name
        :param search_query: Search query
        :param search_column: Search column
        :param filters: Filters
        :return: Number of rows
        """
        base_query = f"SELECT COUNT(*) FROM {table}"
        where_clause = ""
        params = {}
        tables = self.database.get_tables()

        if search_column:
            search_fields = [search_column]
        else:
            search_fields = tables[table]['search_fields']

        if search_query:
            where_clause = f" WHERE {' OR '.join([f'{column} LIKE :search_query' for column in search_fields])}"
            params['search_query'] = f"%{search_query}%"

        # apply filters
        # filters = {
        #     "column1": "value1",
        #     "column2": "value2"  # AND condition
        # }
        if filters:
            filter_clauses = [f"{column} = :filter_{column}" for column in filters.keys()]
            if where_clause == "":
                where_clause = f" WHERE ({' AND '.join(filter_clauses)})"
            else:
                where_clause += f" AND ({' AND '.join(filter_clauses)})"
            for column, value in filters.items():
                params[f"filter_{column}"] = value  # filter placeholder prefixed with 'filter_'

        query = f"{base_query}{where_clause}"
        stmt = text(query).bindparams(**params)
        with self.database.get_db().connect() as conn:
            count = conn.execute(stmt).scalar()
            return count

    def is_auto_backup(self) -> bool:
        """
        Get auto backup status.

        :return: Auto backup status
        """
        return self.database.window.ui.debug["db"].browser.is_auto_backup()

    def delete_row(self, data: dict):
        """
        Delete row from the database.

        :param data: Dictionary with table and row_id keys
        """
        # create backup
        if self.is_auto_backup():
            backup_path = self.database.make_backup()
            if backup_path:
                msg = f"[DB] Created DB backup: {backup_path}"
                self.log(msg)

        # delete row
        with self.database.get_db().begin() as conn:
            conn.execute(
                text(f"DELETE FROM {data['table']} WHERE id = :row_id")
                .bindparams(row_id=data['row_id'])
            )
            msg = f"[DB] Deleted row ID {data['row_id']} from table {data['table']}"
            self.log(msg)
        self.database.window.ui.debug["db"].browser.update_table_view()

    def update_row(self, data: dict):
        """
        Update row in the database.

        :param data: Dictionary with table, id, field and value keys
        """
        field = data['field']
        value = data['value']
        tables = self.database.get_tables()
        json_columns = tables[data['table']]['json_columns']
        timestamp_columns = tables[data['table']]['timestamp_columns']
        primary_key = tables[data['table']]['primary_key']

        # check JSON
        if field in json_columns or field.endswith("_json"):
            try:
                value = json.dumps(json.loads(value))  # validate and pack JSON
            except:
                raise ValueError(f"Invalid JSON value for column {field}")

        # check timestamp
        if field in timestamp_columns or field.endswith("_ts"):
            try:
                value = int(value)
            except:
                raise ValueError(f"Invalid timestamp value for column {field}")

        # check foreign id field
        if field.endswith("_id"):
            try:
                value = int(value)
            except:
                raise ValueError(f"Invalid _id value for column {field}")

        # create backup
        if self.is_auto_backup():
            backup_path = self.database.make_backup()
            if backup_path:
                msg = f"[DB] Created DB backup: {backup_path}"
                self.log(msg)

        # update row
        with self.database.get_db().begin() as conn:
            conn.execute(
                text(f"UPDATE {data['table']} SET {data['field']} = :value WHERE {primary_key} = :id")
                .bindparams(id=data['id'], value=value)
            )
            msg = f"[DB] Updated row ID {data['id']} in table {data['table']}"
            self.log(msg)
        self.database.window.ui.debug["db"].browser.update_table_view()

    def truncate_table(self, data: dict, reset: bool = False):
        """
        Truncate table in the database.

        :param data: Dictionary with table key
        :param reset: Reset table sequence
        """
        # create backup
        if self.is_auto_backup():
            backup_path = self.database.make_backup()
            if backup_path:
                msg = f"[DB] Created DB backup: {backup_path}"
                self.log(msg)

        # truncate table
        with self.database.get_db().begin() as conn:
            conn.execute(text(f"DELETE FROM {data['table']}"))
            if reset:  # reset table sequence (autoincrement)
                conn.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{data['table']}'"))
                msg = f"[DB] Truncated table {data['table']}"
            else:
                msg = f"[DB] Deleted all rows from table {data['table']}"
            self.log(msg)
        self.database.window.ui.debug["db"].browser.update_table_view()

    def log(self, msg: str):
        """
        Log action to debug.

        :param msg: Message
        """
        self.database.window.core.debug.info(msg)
        print(msg)
        self.database.window.ui.status(msg)