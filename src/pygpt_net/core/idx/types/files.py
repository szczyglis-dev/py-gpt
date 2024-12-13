#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 00:00:00                  #
# ================================================== #

import datetime
import os.path
from typing import Optional


class Files:
    def __init__(self, window=None, provider=None):
        """
        Indexed files core

        :param window: Window instance
        :param provider: provider name
        """
        self.window = window
        self.provider = provider

    def append(
            self,
            store_id: str,
            idx: str,
            file_id: str,
            path: str,
            doc_id: str
    ) -> int:
        """
        Append file to index

        :param store_id: store id
        :param idx: index name
        :param file_id: file id
        :param path: file path
        :param doc_id: document id
        :return: ID of appended file
        """
        data = {
            "name": file_id,  # use file id as name
            "path": path,
            "indexed_ts": datetime.datetime.now().timestamp(),
            "id": doc_id,
        }
        return self.provider.append_file(
            store_id=store_id,
            idx=idx,
            data=data,
        )

    def get_id(self, path: str) -> str:
        """
        Prepare file id

        :param path: file path
        :return: file id
        """
        path = os.path.normpath(path)
        root_path = os.path.normpath(self.window.core.config.get_user_dir('data'))
        path = path.replace(root_path, '')
        path = path.replace("\\", "/").strip(r'\/')
        return path

    def get_doc_id(
            self,
            store_id: str,
            idx: str,
            file_id: str
    ) -> str:
        """
        Get indexed document id by file

        :param store_id: store id
        :param idx: index name
        :param file_id: file id
        :return: document id
        """
        return self.provider.get_file_doc_id(
            store_id=store_id,
            idx=idx,
            file_id=file_id,
        )

    def exists(
            self,
            store_id: str,
            idx: str,
            file_id: str
    ) -> bool:
        """
        Check if file is indexed

        :param store_id: store id
        :param idx: index name
        :param file_id: file id
        :return: True if file is indexed
        """
        return self.provider.is_file_indexed(
            store_id=store_id,
            idx=idx,
            file_id=file_id,
        )

    def update(
            self,
            id: int,
            doc_id: str,
            ts: int
    ) -> bool:
        """
        Update timestamp of indexed file

        :param id: database record ID
        :param doc_id: document ID
        :param ts: timestamp
        :return: True if file was updated
        """
        return self.provider.update_file(
            id=id,
            doc_id=doc_id,
            ts=ts,
        )

    def remove(
            self,
            store_id: str,
            idx: str,
            doc_id: str
    ):
        """
        Remove document from index

        :param store_id: store id
        :param idx: index name
        :param doc_id: document id
        """
        self.provider.remove_file(
            store_id=store_id,
            idx=idx,
            doc_id=doc_id,
        )

    def truncate(
            self,
            store_id: Optional[str] = None,
            idx: Optional[str] = None
    ):
        """
        Truncate files from index

        :param store_id: store id
        :param idx: index name
        """
        self.provider.truncate_files(
            store_id=store_id,
            idx=idx,
        )
