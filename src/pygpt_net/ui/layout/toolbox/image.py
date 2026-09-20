#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.03 14:25:00                  #
# ================================================== #

from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QSizePolicy

from pygpt_net.ui.widget.option.combo import OptionCombo
from pygpt_net.ui.widget.option.input import OptionInput
from pygpt_net.ui.widget.option.toggle_label import ToggleLabel
from pygpt_net.utils import trans


class Image:
    def __init__(self, window=None):
        """
        Toolbox UI

        :param window: Window instance
        """
        self.window = window

    def setup(self) -> QWidget:
        """
        Setup image

        :return: QWidget
        :rtype: QWidget
        """
        option = {
            "type": "int",
            "label": "img_variants",
            "min": 1,
            "max": 4,
            "value": 1,
        }

        ui = self.window.ui
        conf_global = ui.config['global']

        container = QWidget(parent=self.window)
        container.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        container.setMinimumWidth(0)
        ui.nodes['image.options'] = container

        conf_global['img_variants'] = OptionInput(self.window, 'global', 'img_variants', option)
        conf_global['img_variants'].setToolTip(trans("toolbox.img_variants.label"))

        option_resolutions = self.window.core.image.get_resolution_option()
        conf_global['img_resolution'] = OptionCombo(self.window, 'global', 'img_resolution', option_resolutions)
        conf_global['img_resolution'].setToolTip(trans("settings.img_resolution.desc"))

        option_aspect_ratio = self.window.core.image.get_xai_aspect_ratio_option()
        conf_global['img.aspect_ratio'] = OptionCombo(
            self.window, 'global', 'img.aspect_ratio', option_aspect_ratio
        )
        conf_global['img.aspect_ratio'].setToolTip(trans("settings.video.aspect_ratio"))
        # The xAI-only field starts hidden; Mode.update() toggles it for xAI image models.
        conf_global['img.aspect_ratio'].setVisible(False)
        ui.nodes['image.aspect_ratio'] = conf_global['img.aspect_ratio']

        # Keep media options shrinkable inside the fixed-minimum toolbox.
        conf_global['img_resolution'].setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        conf_global['img_resolution'].setMinimumWidth(0)
        conf_global['img.aspect_ratio'].setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        conf_global['img.aspect_ratio'].setMinimumWidth(0)
        conf_global['img_variants'].setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        conf_global['img_variants'].setMinimumWidth(0)

        conf_global['img.remix'] = ToggleLabel(trans("img.remix"), parent=self.window)
        conf_global['img.remix'].box.setToolTip(trans("img.remix.tooltip"))
        conf_global['img.remix'].box.toggled.connect(self.window.controller.media.toggle_remix_image)

        cols = QHBoxLayout()
        cols.addWidget(conf_global['img_resolution'], 3)
        cols.addWidget(conf_global['img.aspect_ratio'], 3)
        cols.addWidget(conf_global['img_variants'], 1)
        cols.setContentsMargins(2, 5, 5, 5)

        rows = QVBoxLayout()
        rows.addLayout(cols)
        rows.addWidget(conf_global['img.remix'])
        rows.setContentsMargins(2, 5, 5, 5)

        container.setLayout(rows)
        container.setContentsMargins(2, 0, 0, 10)
        container.setFixedHeight(100)

        return container