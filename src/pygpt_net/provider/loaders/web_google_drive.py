#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.19 20:00:00                  #
# ================================================== #

import json

from llama_index.core.readers.base import BaseReader

from llama_index.readers.google.drive.base import GoogleDriveReader
from .base import BaseLoader


class Loader(BaseLoader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = "google_drive"
        self.name = "Google Drive"
        self.type = ["web"]
        self.instructions = [
            {
                "google_drive": {
                    "description": "read and index files from Google Drive",
                    "args": {
                        "folder_id": {
                            "type": "str",
                        },
                        "file_ids": {
                            "type": "list",
                        },
                        "mime_types": {
                            "type": "list",
                        },
                    },
                }
            }
        ]
        self.init_args = {
            "client_config": {},
            "credentials_path" : "credentials.json",
            "token_path": "token.json",
            "pydrive_creds_path": "creds.txt",
        }
        self.init_args_types = {
            "client_config": "dict",
            "credentials_path": "str",
            "token_path": "str",
            "pydrive_creds_path": "str",
        }

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        args = self.get_args()
        return GoogleDriveReader(**args)

    def get_external_id(self, args: dict = None) -> str:
        """
        Get unique web content identifier

        :param args: load_data args
        :return: unique content identifier
        """
        unique = {}
        if "folder_id" in args and args.get("folder_id"):
            unique["folder_id"] = args.get("folder_id")
        if "file_ids" in args and args.get("file_ids"):
            unique["file_ids"] = args.get("file_ids")
        if "mime_types" in args and args.get("mime_types"):
            unique["mime_types"] = args.get("mime_types")
        return json.dumps(unique)

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for load_data() method

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        args = {}
        if "url" in kwargs and kwargs.get("url"):
            if isinstance(kwargs.get("url"), str):
                args["folder_id"] = kwargs.get("url")  # default folder id

        if "folder_id" in kwargs and kwargs.get("folder_id"):
            if isinstance(kwargs.get("folder_id"), str):
                args["folder_id"] = kwargs.get("folder_id")  # folder id

        if "file_ids" in kwargs and kwargs.get("file_ids"):
            if isinstance(kwargs.get("file_ids"), list):
                args["file_ids"] = kwargs.get("file_ids")  # list of file ids

        if "mime_types" in kwargs and kwargs.get("mime_types"):
            if isinstance(kwargs.get("mime_types"), list):
                args["mime_types"] = kwargs.get("mime_types")  # list of mime types
        return args
