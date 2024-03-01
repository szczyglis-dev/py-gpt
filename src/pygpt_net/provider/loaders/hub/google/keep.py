#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.01 02:00:00                  #
# ================================================== #

import json
import os
from typing import Any

from llama_index.readers.google.keep.base import GoogleKeepReader as Reader

class GoogleKeepReader(Reader):
    """
    Wrapper for:

    llama_index.readers.google.keep.base.GoogleKeepReader

    Extending base reader with credentials configuration.
    """

    def __init__(
        self,
        credentials_path: str = "keep_credentials.json",
    ) -> None:
        """Initialize with parameters."""
        self.credentials_path = credentials_path

    def _get_keep(self) -> Any:
        import gkeepapi

        """Get a Google Keep object with login."""
        # Read username and password from keep_credentials.json
        if os.path.exists(self.credentials_path):
            with open(self.credentials_path) as f:
                credentials = json.load(f)
        else:
            raise RuntimeError("Failed to load " + str(self.credentials_path) + " file.")

        keep = gkeepapi.Keep()
        success = keep.login(credentials["username"], credentials["password"])
        if not success:
            raise RuntimeError("Failed to login to Google Keep.")

        return keep