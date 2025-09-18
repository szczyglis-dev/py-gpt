#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

import json
from dataclasses import dataclass, field
from typing import Optional



@dataclass(slots=True)
class BuilderLayoutItem:
    id: Optional[object] = None
    name: Optional[object] = None
    data: Optional[object] = None

    def __init__(self):
        """Custom agent item"""
        self.id = None
        self.name = None
        self.data = None

    def reset(self):
        """Reset"""
        self.id = None
        self.name = None
        self.data = None

    def to_dict(self) -> dict:
        """
        Return as dictionary

        :return: dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "data": self.data,
        }

    def dump(self) -> str:
        """
        Dump item to string

        :return: serialized item
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()