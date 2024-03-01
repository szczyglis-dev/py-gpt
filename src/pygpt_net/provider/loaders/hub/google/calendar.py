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

import os
from typing import Any

from llama_index.readers.google.calendar.base import GoogleCalendarReader as Reader

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

class GoogleCalendarReader(Reader):
    """
    Wrapper for:

    llama_index.readers.google.calendar.base.GoogleCalendarReader

    Extending base reader with credentials configuration.
    """

    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
    ) -> None:
        """Initialize with parameters."""
        self.credentials_path = credentials_path
        self.token_path = token_path

    def _get_credentials(self) -> Any:
        """Get valid user credentials from storage.

        ** Based on base reader, extended with credentials configuration. **
        https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/readers/llama-index-readers-google/llama_index/readers/google/calendar/base.py

        The file token.json stores the user's access and refresh tokens, and is
        created automatically when the authorization flow completes for the first
        time.

        Returns:
            Credentials, the obtained credential.
        """
        from google_auth_oauthlib.flow import InstalledAppFlow

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())

        return creds