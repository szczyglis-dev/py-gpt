#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 02:00:00                  #
# ================================================== #

from packaging.version import Version

from pygpt_net.item.index import IndexItem


class BaseProvider:
    def __init__(self, window=None):
        self.window = window
        self.id = ""
        self.type = "index"

    def attach(self, window):
        self.window = window

    def install(self):
        pass

    def patch(self, version: Version) -> bool:
        pass

    def load(self, store_id: str) -> dict:
        pass

    def append_file(self, store_id: str, idx: str, data: dict) -> int:
        pass

    def append_ctx_meta(self, store_id: str, idx: str, meta_id: int, doc_id: str) -> int:
        pass

    def append_external(self, store_id: str, idx: str, data: dict) -> int:
        pass

    def update_file(self, id: int, doc_id: str, ts: int) -> bool:
        pass

    def update_ctx_meta(self, id: int, doc_id: str) -> bool:
        pass

    def update_external(self, content: str, type: str, doc_id: str, ts: int) -> bool:
        pass

    def is_meta_indexed(self, store_id: str, idx: str, meta_id: int) -> bool:
        pass

    def is_file_indexed(self, store_id: str, idx: str, file_id: str) -> bool:
        pass

    def is_external_indexed(self, store_id: str, idx: str, content: str, type: str) -> bool:
        pass

    def get_meta_doc_id(self, store_id: str, idx: str, meta_id: int) -> str:
        pass

    def get_file_doc_id(self, store_id: str, idx: str, file_id: str) -> str:
        pass

    def get_external_doc_id(self, store_id: str, idx: str, content: str, type: str) -> str:
        pass

    def remove_file(self, store_id: str, idx: str, doc_id: str):
        pass

    def remove_external(self, store_id: str, idx: str, doc_id: str):
        pass

    def remove_ctx_meta(self, store_id: str, idx: str, meta_id: str):
        pass

    def truncate(self, store_id: str, idx: str):
        pass

    def truncate_all(self, store_id: str = None, idx: str = None) -> bool:
        pass

    def truncate_files(self, store_id: str = None, idx: str = None) -> bool:
        pass

    def truncate_ctx(self, store_id: str = None, idx: str = None) -> bool:
        pass

    def truncate_external(self, store_id: str = None, idx: str = None) -> bool:
        pass

    def get_counters(self, type: str) -> dict:
        pass

    def dump(self, index: IndexItem) -> str:
        pass

    def get_version(self) -> str:
        pass
