#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 05:00:00                  #
# ================================================== #

import os
import sys
import traceback
import logging


class ErrorHandler:
    def __init__(self, window=None):
        """
        Error handler

        :param window: Window instance
        """
        self.window = window

    def get_platform_info(self):
        """
        Return platform info

        :return: platform info
        :rtype: str
        """
        data = ""
        data += "{}, {}, Snap: {}".\
            format(self.window.platform.get_os(), self.window.platform.get_architecture(), self.window.platform.is_snap())
        return data

    def log(self, error):
        """
        Handle error

        :param error: error object
        """
        path = os.path.join(self.window.config.path, 'error.log')
        logging.basicConfig(
            filename=path,
            filemode='a',
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=logging.ERROR
        )

        # if error is only string then convert it to Exception
        if not isinstance(error, Exception):
            trace = traceback.format_exc()
            print("*** Error: {}".format(str(error)))
            data = f"Message: {error}\n" \
                f"Traceback:\n{trace}" \
                f"Platform: {self.get_platform_info()}"
            print(data)
            logging.error(data)
            return

        etype, value, tb = sys.exc_info()
        traceback_details = traceback.extract_tb(tb)
        if len(traceback_details) >= 4:
            last_calls = traceback_details[-4:]
        else:
            last_calls = traceback_details
        formatted_traceback = ''.join(traceback.format_list(last_calls))
        data = f"Type: {etype.__name__}\n" \
            f"Message: {value}\n" \
            f"Traceback:\n{formatted_traceback}" \
            f"Platform: {self.get_platform_info()}"

        logging.error(data)
        print("*** Error: {}".format(str(error)))
        print(data)
