#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.02 16:00:00                  #
# ================================================== #

import os
from typing import List


class Camera:
    def __init__(self, window=None):
        """
        Camera core

        :param window: Window instance
        """
        self.window = window
        self.capture = None
        self.current = None

    def install(self):
        """Install provider data"""
        img_dir = self.window.core.config.get_user_dir('capture')
        if not os.path.exists(img_dir):
            os.makedirs(img_dir, exist_ok=True)

    def get_devices_data(self) -> List[dict]:
        """
        Return a list of camera devices for UI selection.

        Format:
        [
            {'id': <int index>, 'name': <str description>},
            ...
        ]

        'id' is the ordinal index used by vision.capture.idx.
        """
        try:
            from PySide6.QtMultimedia import QMediaDevices
        except Exception as e:
            # Qt Multimedia not available
            self.window.core.debug.log(e)
            return []

        try:
            devices = list(QMediaDevices.videoInputs())
        except Exception as e:
            self.window.core.debug.log(e)
            return []

        result = []
        for idx, dev in enumerate(devices):
            try:
                name = dev.description()
            except Exception:
                name = f"Camera {idx}"
            result.append({'id': idx, 'name': name})
        return result

    def get_devices(self) -> List[dict]:
        """
        Get choices list of single-pair dicts {id: name}.

        Example:
        [
            {'0': 'Integrated Camera'},
            {'1': 'USB Camera'},
            ...
        ]
        """
        items = self.get_devices_data()
        return [{str(item['id']): item['name']} for item in items]
