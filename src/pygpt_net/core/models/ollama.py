#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.02.01 11:00:00                  #
# ================================================== #

import requests

class Ollama:
    def __init__(self, window=None):
        """
        Ollama core

        :param window: Window instance
        """
        self.window = window

    def get_status(self) -> dict:
        """
        Check Ollama status

        :return: dict
        """
        url = "http://localhost:11434/api/tags"
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': True,
                    'models': data.get('models', [])
                }
            else:
                return {
                    'status': False,
                    'models': []
                }
        except requests.exceptions.RequestException:
            return {
                'status': False,
                'models': []
            }