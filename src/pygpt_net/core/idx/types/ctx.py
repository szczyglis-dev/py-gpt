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

from typing import Optional


class Ctx:
    def __init__(self, window=None, provider=None):
        """
        Indexed ctx meta core

        :param window: Window instance
        :param provider: provider name
        """
        self.window = window
        self.provider = provider

    def append(
            self,
            store_id: str,
            idx: str,
            meta_id: int,
            doc_id: str
    ) -> int:
        """
        Append ctx meta to index db

        :param store_id: store id
        :param idx: index name
        :param meta_id: meta id
        :param doc_id: document id
        :return: ID of appended ctx meta
        """
        return self.provider.append_ctx_meta(
            store_id=store_id,
            idx=idx,
            meta_id=meta_id,
            doc_id=doc_id,
        )

    def exists(
            self,
            store_id: str,
            idx: str,
            meta_id: int
    ) -> bool:
        """
        Check if ctx meta is indexed

        :param store_id: store id
        :param idx: index name
        :param meta_id: meta id
        :return: True if ctx meta is indexed
        """
        return self.provider.is_meta_indexed(
            store_id=store_id,
            idx=idx,
            meta_id=meta_id,
        )

    def get_doc_id(
            self,
            store_id: str,
            idx: str,
            meta_id: int
    ) -> str:
        """
        Get indexed document id by meta id

        :param store_id: store id
        :param idx: index name
        :param meta_id: meta id
        :return: document id
        """
        return self.provider.get_meta_doc_id(
            store_id=store_id,
            idx=idx,
            meta_id=meta_id,
        )

    def update(
            self,
            meta_id: int,
            doc_id: str
    ) -> bool:
        """
        Update timestamp of indexed ctx meta

        :param meta_id: ctx meta id
        :param doc_id: document id
        :return: True if ctx meta was updated
        """
        return self.provider.update_ctx_meta(
            meta_id=meta_id,
            doc_id=doc_id,
        )

    def remove(
            self,
            store_id: str,
            idx: str,
            meta_id: str
    ):
        """
        Remove document from index db

        :param store_id: store id
        :param idx: index name
        :param meta_id: ctx meta id
        """
        self.provider.remove_ctx_meta(
            store_id=store_id,
            idx=idx,
            meta_id=meta_id,
        )

    def truncate(
            self,
            store_id: Optional[str] = None,
            idx: Optional[str] = None
    ):
        """
        Truncate ctx meta from index db

        :param store_id: store id
        :param idx: index name
        """
        self.provider.truncate_ctx(
            store_id=store_id,
            idx=idx,
        )
