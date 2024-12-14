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

import datetime
import os.path
from typing import List, Dict, Any

from llama_index.core.schema import Document


class Metadata:
    def __init__(self, window=None):
        """
        Metadata core

        :param window: Window instance
        """
        self.window = window

    def append_file_metadata(
            self,
            docs: List[Document],
            path: str
    ):
        """
        Append custom meta to documents (file)

        :param docs: list of documents
        :param path: path to file
        """
        metas = self.window.core.config.get("llama.idx.custom_meta")
        ext = str(os.path.splitext(path)[1][1:]).lower()
        data_dir = self.window.core.config.get_user_dir("data")
        if (len(docs) > 0
                and metas is not None
                and isinstance(metas, list)
                and len(metas) > 0):

            for doc in docs:
                meta = doc.metadata
                for item in metas:
                    extensions = item["extensions"].replace(" ", "").lower().split(",")

                    # * means all extensions
                    if ext in extensions or "*" in extensions:
                        key = item["key"]
                        value = item["value"]

                        # remove key if value is empty
                        if str(value).strip() == "" and key in meta:
                            del meta[key]
                            continue

                        # append or replace custom meta
                        try:
                            relative_path = os.path.relpath(path, data_dir)
                            relative_dir = os.path.relpath(os.path.dirname(path), data_dir)
                            # if file is outside of data directory, strip relative path, and use absolute path
                            if relative_path.startswith(".."):
                                relative_path = os.path.basename(path)
                                relative_dir = os.path.dirname(path)
                            meta[key] = value.format(
                                path=path,
                                relative_path=relative_path,
                                relative_dir=relative_dir,
                                filename=os.path.basename(path),
                                dirname=os.path.dirname(path),
                                ext=ext,
                                size=os.path.getsize(path),
                                mtime=os.path.getmtime(path),
                                timestamp=int(datetime.datetime.now().timestamp()),
                                date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                time=datetime.datetime.now().strftime("%H:%M:%S"),
                                date_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            )
                        except Exception as e:
                            print("Error while appending custom meta: " + str(e))
                            self.window.core.debug.log(e)
                doc.metadata = meta

    def append_web_metadata(
            self,
            docs: List[Document],
            type: str,
            args: Dict[str, Any]
    ):
        """
        Append custom meta to documents (web)

        :param docs: list of documents
        :param type: type of URL (webpage, feed, etc.)
        :param args: loader arguments
        """
        metas = self.window.core.config.get("llama.idx.custom_meta.web")
        if (len(docs) > 0
                and metas is not None
                and isinstance(metas, list)
                and len(metas) > 0):

            for doc in docs:
                meta = doc.metadata
                for item in metas:
                    item_type = item["loader"].replace("web_", "")
                    if item_type != type:
                        continue

                    key = item["key"]
                    value = item["value"]

                    # remove key if value is empty
                    if str(value).strip() == "" and key in meta:
                        del meta[key]
                        continue

                    # append or replace custom meta
                    try:
                        meta[key] = value.format(
                            timestamp=int(datetime.datetime.now().timestamp()),
                            date=datetime.datetime.now().strftime("%Y-%m-%d"),
                            time=datetime.datetime.now().strftime("%H:%M:%S"),
                            date_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            **args
                        )
                    except Exception as e:
                        print("Error while appending custom meta (web): " + str(e))
                        self.window.core.debug.log(e)
                doc.metadata = meta

