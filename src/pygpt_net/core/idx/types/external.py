#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 04:00:00                  #
# ================================================== #

import datetime
import time


class External:
    def __init__(self, window=None, provider=None):
        """
        External data core

        :param window: Window instance
        :param provider: provider name
        """
        self.window = window
        self.provider = provider

    def append(
            self,
            store_id: str,
            idx: str,
            content: str,
            type: str,
            doc_id: str
    ) -> int:
        """
        Append file to index

        :param store_id: store id
        :param idx: index name
        :param content: content
        :param type: content type
        :param doc_id: document id
        :return: ID of appended external content
        """
        data = {
            "content": content,
            "type": type,
            "indexed_ts": datetime.datetime.now().timestamp(),
            "id": doc_id,
        }
        return self.provider.append_external(
            store_id=store_id,
            idx=idx,
            data=data,
        )

    def get_doc_id(self, store_id: str, idx: str, content: str, type: str) -> str:
        """
        Get indexed document id by content

        :param store_id: store id
        :param idx: index name
        :param content: content
        :param type: content type
        :return: document id
        """
        return self.provider.get_external_doc_id(
            store_id=store_id,
            idx=idx,
            content=content,
            type=type,
        )

    def exists(self, store_id: str, idx: str, content: str, type: str) -> bool:
        """
        Check if content is indexed

        :param store_id: store id
        :param idx: index name
        :param content: content
        :param type: content type
        :return: True if external content is indexed
        """
        return self.provider.is_external_indexed(
            store_id=store_id,
            idx=idx,
            content=content,
            type=type,
        )

    def update(self, content: str, type: str, doc_id: str, ts: int) -> bool:
        """
        Update timestamp of indexed external content

        :param content: content
        :param type: content type
        :param doc_id: document ID
        :param ts: timestamp
        :return: True if content was updated
        """
        return self.provider.update_external(
            content=content,
            type=type,
            doc_id=doc_id,
            ts=ts,
        )

    def remove(self, store_id: str, idx: str, doc_id: str):
        """
        Remove document from index

        :param store_id: store id
        :param idx: index name
        :param doc_id: document id
        """
        self.provider.remove_external(
            store_id=store_id,
            idx=idx,
            doc_id=doc_id,
        )

    def truncate(self, store_id: str = None, idx: str = None):
        """
        Truncate external data from index

        :param store_id: store id
        :param idx: index name
        """
        self.provider.truncate_external(
            store_id=store_id,
            idx=idx,
        )

    def set_indexed(self, content: str, type: str, idx: str, doc_id: str) -> bool:
        """
        Set external content as indexed

        :param content: content, e.g. url address
        :param type: content type, e.g. url
        :param idx: index name
        :param doc_id: document ID
        :return: True if updated
        """
        ts = int(time.time())
        store = self.window.core.idx.get_current_store()

        # add to index db
        if not self.exists(store, idx, content, type):
            self.append(
                store_id=store,  # current store
                idx=idx,  # index name
                content=content,  # content (e.g. url)
                type=type,  # content type
                doc_id=doc_id,  # document id
            )
        else:
            # update document id in index db if already indexed
            self.update(
                content=content,  # content (e.g. url)
                type=type,  # content type
                doc_id=doc_id,  # document id
                ts=ts,  # timestamp
            )
        return True
