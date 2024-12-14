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

from typing import Dict, Any

from pygpt_net.item.ctx import CtxItem


class AudioContext:
    def __init__(self, **kwargs):
        """
        Audio context

        :param kwargs: keyword arguments
        """
        self.data = kwargs.get("ctx", None)
        self.prev_id = kwargs.get("prev_id", None)

    def to_dict(self) -> Dict:
        """
        Return as dictionary

        :return: dictionary
        """
        data = {
            "data": self.data,
            "prev_id": self.prev_id
        }
        # sort by keys
        data = dict(sorted(data.items(), key=lambda item: item[0]))
        return data