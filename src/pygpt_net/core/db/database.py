#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

import os
import shutil
import time
from typing import Optional, Any, Dict

from sqlalchemy import create_engine, text

from pygpt_net.migrations import Migrations
from .viewer import Viewer


class Database:
    def __init__(self, window=None):
        """Database provider core"""
        self.window = window
        self.db_path = None
        self.db_name = 'db.sqlite'
        self.engine = None
        self.initialized = False
        self.echo = True

        # Tables configuration
        columns = {}
        columns["calendar_note"] = [
            'id',
            'idx',
            'status',
            'year',
            'month',
            'day',
            'created_ts',
            'updated_ts',
            'title',
            'content',
            'is_important',
            'is_deleted',
            'uuid',
        ]
        columns["config"] = [
            'config_key',
            'config_value',
            'created_ts',
            'updated_ts',
        ]
        columns["ctx_item"] = [
            'id',
            'meta_id',
            'input',
            'output',
            'input_name',
            'output_name',
            'input_ts',
            'output_ts',
            'mode',
            'model',
            'thread_id',
            'msg_id',
            'run_id',
            'cmds_json',
            'results_json',
            'urls_json',
            'images_json',
            'files_json',
            'attachments_json',
            'additional_ctx_json',
            'extra',
            'hidden_input',
            'hidden_output',
            'input_tokens',
            'output_tokens',
            'total_tokens',
            'is_internal',
            'docs_json',
            'external_id',
            'audio_id',
            'audio_expires_ts',
        ]
        columns["ctx_meta"] = [
            'id',
            'name',
            'updated_ts',
            'mode',
            'model',
            'created_ts',
            'indexed_ts',
            'last_mode',
            'last_model',
            'thread_id',
            'assistant_id',
            'preset_id',
            'run_id',
            'status',
            'extra',
            'is_initialized',
            'is_deleted',
            'is_important',
            'is_archived',
            'label',
            'indexes_json',
            'additional_ctx_json',
            'external_id',
            'group_id',
            'root_id',
            'parent_id',
            'owner_uuid',
            'uuid',
        ]
        columns["ctx_group"] = [
            'id',
            'name',
            'updated_ts',
            'created_ts',
            'uuid',
            'additional_ctx_json',
        ]
        columns["idx_ctx"] = [
            'id',
            'meta_id',
            'updated_ts',
            'item_id',
            'doc_id',
            'created_ts',
            'store',
            'idx',
            'uuid',
        ]
        columns["idx_external"] = [
            'id',
            'content',
            'type',
            'doc_id',
            'created_ts',
            'updated_ts',
            'store',
            'idx',
            'uuid',
        ]
        columns["idx_file"] = [
            'id',
            'name',
            'path',
            'doc_id',
            'created_ts',
            'updated_ts',
            'store',
            'idx',
            'uuid',
        ]
        columns["notepad"] = [
            'id',
            'idx',
            'title',
            'content',
            'created_ts',
            'updated_ts',
            'is_deleted',
            'is_initialized',
            'uuid',
        ]
        columns["remote_file"] = [
            'id',
            'file_id',
            'store_id',
            'thread_id',
            'name',
            'path',
            'size',
            'created_ts',
            'updated_ts',
            'uuid',
        ]
        columns["remote_store"] = [
            'id',
            'store_id',
            'name',
            'usage_bytes',
            'num_files',
            'expire_days',
            'status',
            'status_json',
            'last_active_ts',
            'last_sync_ts',
            'is_thread',
            'description',
            'uuid',
            'created_ts',
            'updated_ts',
        ]
        self.tables = {
            'calendar_note': {
                'columns': columns["calendar_note"],
                'sort_by': columns["calendar_note"],
                'search_fields': ['id', 'title', 'content'],
                'timestamp_columns': ['created_ts', 'updated_ts'],
                'json_columns': [],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'config': {
                'columns': columns["config"],
                'sort_by': columns["config"],
                'search_fields': ['config_key', 'config_value'],
                'timestamp_columns': ['created_ts', 'updated_ts'],
                'json_columns': [],
                'default_sort': 'config_key',
                'default_order': 'ASC',
                'primary_key': 'config_key',
            },
            'ctx_item': {
                'columns': columns["ctx_item"],
                'sort_by': columns["ctx_item"],
                'search_fields': ['id', 'input', 'output', 'input_name', 'output_name', 'meta_id', 'hidden_input',
                                  'hidden_output'],
                'timestamp_columns': ['input_ts', 'output_ts', 'audio_expires_ts'],
                'json_columns': ['cmds_json', 'results_json', 'urls_json', 'images_json', 'files_json',
                                 'attachments_json', 'docs_json', 'additional_ctx_json'],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'ctx_meta': {
                'columns': columns["ctx_meta"],
                'sort_by': columns["ctx_meta"],
                'search_fields': ['id', 'name'],
                'timestamp_columns': ['created_ts', 'updated_ts', 'indexed_ts'],
                'json_columns': ['indexes_json', 'additional_ctx_json'],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'ctx_group': {
                'columns': columns["ctx_group"],
                'sort_by': columns["ctx_group"],
                'search_fields': ['id', 'name'],
                'timestamp_columns': ['created_ts', 'updated_ts'],
                'json_columns': ['additional_ctx_json'],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'idx_ctx': {
                'columns': columns["idx_ctx"],
                'sort_by': columns["idx_ctx"],
                'search_fields': ['id', 'doc_id', 'meta_id', 'store', 'idx'],
                'timestamp_columns': ['created_ts', 'updated_ts'],
                'json_columns': [],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'idx_file': {
                'columns': columns["idx_file"],
                'sort_by': columns["idx_file"],
                'search_fields': ['id', 'doc_id', 'name', 'path', 'store', 'idx'],
                'timestamp_columns': ['created_ts', 'updated_ts'],
                'json_columns': [],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'idx_external': {
                'columns': columns["idx_external"],
                'sort_by': columns["idx_external"],
                'search_fields': ['id', 'doc_id', 'content', 'type', 'store', 'idx'],
                'timestamp_columns': ['created_ts', 'updated_ts'],
                'json_columns': [],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'notepad': {
                'columns': columns["notepad"],
                'sort_by': columns["notepad"],
                'search_fields': ['id', 'title', 'content'],
                'timestamp_columns': ['created_ts', 'updated_ts'],
                'json_columns': [],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'remote_file': {
                'columns': columns["remote_file"],
                'sort_by': columns["remote_file"],
                'search_fields': ['id', 'file_id', 'store_id', 'thread_id', 'name', 'path'],
                'timestamp_columns': ['created_ts', 'updated_ts'],
                'json_columns': [],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
            'remote_store': {
                'columns': columns["remote_store"],
                'sort_by': columns["remote_store"],
                'search_fields': ['id', 'store_id', 'uuid', 'name', 'description', 'status', 'status_json'],
                'timestamp_columns': ['created_ts', 'updated_ts', 'last_sync_ts', 'last_active_ts'],
                'json_columns': ['status_json'],
                'default_sort': 'id',
                'default_order': 'DESC',
                'primary_key': 'id',
            },
        }
        self.migrations = Migrations()
        self.viewer = Viewer(self)

    def init(self, force: bool = False):
        """
        Initialize database

        :param force: force initialization
        """
        if not self.initialized or force:
            self.db_path = os.path.join(self.window.core.config.path, self.db_name)
            self.prepare()

    def get_tables(self) -> Dict[str, Dict[str, Any]]:
        """
        Get tables configuration

        :return: tables
        """
        return self.tables

    def prepare(self):
        """Prepare database"""
        self.engine = create_engine(
            'sqlite:///{}'.format(self.db_path),
            echo=self.echo,
            future=True
        )
        if not self.is_installed():
            self.install()
        self.initialized = True

    def close(self):
        """Close database connection"""
        self.engine.dispose()
        self.initialized = False

    def install(self):
        """Install database schema"""
        with self.engine.begin() as conn:
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS config (
                config_key TEXT PRIMARY KEY,
                config_value TEXT,
                created_ts INTEGER,
                updated_ts INTEGER
            );"""))
            print("[DB] Installed database: {}".format(self.db_path))

    def get_version(self) -> int:
        """
        Get database migration version

        :return: version string
        """
        return int(self.get_param("db_version") or 0)

    def get_db(self):
        """
        Get database engine

        :return: database engine
        """
        return self.engine

    def is_installed(self) -> bool:
        """
        Check if database is installed

        :return: True if installed
        """
        if not os.path.exists(self.db_path):
            return False

        with self.engine.connect() as conn:
            result = conn.execute(text("""
            SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='config';
            """)).fetchone()
            return result[0] == 1

    def apply_migration(self, migration, conn, db_version: int):
        """
        Apply DB migration

        :param migration: migration object
        :param conn: database connection
        :param db_version: database version
        """
        migration.window = self.window
        migration_version = int(migration.__class__.__name__.replace('Version', ''))
        if migration_version > db_version:
            migration.up(conn)
            self.set_param_exec("db_version", migration_version, conn)
            print("[DB] Executed DB migration: {}".format(migration.__class__.__name__).replace('Version', ''))

    def has_migrations_to_apply(self, migrations: list) -> bool:
        """
        Check if there are any migrations to apply

        :param migrations: list of migrations
        """
        has_migrations = False
        for migration in migrations:
            migration.window = self.window
            migration_version = int(migration.__class__.__name__.replace('Version', ''))
            if migration_version > self.get_version():
                has_migrations = True
                break
        return has_migrations

    def make_backup(self) -> Optional[str]:
        """
        Make backup of database before migration

        :return: backup path
        """
        try:
            backup_path = os.path.join(self.window.core.config.path, 'db.sqlite.backup')
            if os.path.exists(backup_path):
                os.remove(backup_path)
            shutil.copyfile(self.db_path, backup_path)
            return backup_path
        except Exception as e:
            print("[DB] Error while making backup of database: {}".format(e))
        return None

    def migrate(self):
        """Apply all DB migrations"""
        db_version = self.get_version()
        migrations = Migrations().get_versions()
        sorted_migrations = sorted(migrations, key=lambda m: m.__class__.__name__)
        self.init()
        if self.has_migrations_to_apply(sorted_migrations):
            print("[DB] Migrating database...")
            self.make_backup()  # make backup of current database
            with self.engine.begin() as conn:
                for migration in sorted_migrations:
                    self.apply_migration(migration, conn, db_version)

    def get_param(self, key: str) -> Optional[str]:
        """
        Get parameter from database

        :param key: parameter key
        :return: parameter value
        """
        self.init()

        with self.engine.connect() as conn:
            sel_stmt = text("SELECT config_value FROM config WHERE config_key = :key").bindparams(key=key)
            result = conn.execute(sel_stmt).fetchone()
            return result[0] if result else None

    def set_param(self, key: str, value: Any):
        """
        Insert or update parameter in database

        :param key: parameter key
        :param value: parameter value
        """
        self.init()
        with self.engine.begin() as conn:
            self.set_param_exec(key, value, conn)

    def set_param_exec(self, key: str, value: Any, conn):
        """
        Insert or update parameter in database

        :param key: parameter key
        :param value: parameter value
        :param conn: database connection
        """
        ts = int(time.time())
        stmt = text("SELECT 1 FROM config WHERE config_key = :key").bindparams(key=key)
        result = conn.execute(stmt).fetchone()

        if result:
            stmt = text("""
                UPDATE config
                SET config_value = :value, updated_ts = :updated_ts
                WHERE config_key = :key
            """).bindparams(key=key, value=value, updated_ts=ts)
        else:
            stmt = text("""
                INSERT INTO config (config_key, config_value, created_ts, updated_ts) 
                VALUES (:key, :value, :created_ts, :updated_ts)
            """).bindparams(key=key, value=value, created_ts=ts, updated_ts=ts)

        conn.execute(stmt)

    def reload(self):
        """Reload database connection"""
        self.close()  # close current database
        self.init(force=True)  # re-init database with new path
