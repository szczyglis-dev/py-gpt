#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.22 18:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget
from datetime import datetime, timedelta

from ...widget.lists.context import ContextList
from ...widget.vision.camera import VideoContainer
from ....utils import trans


class CtxList:
    def __init__(self, window=None):
        """
        Context list UI

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """
        Setup layout

        :return: QWidget
        :rtype: QWidget
        """
        ctx = self.setup_ctx()
        video = self.setup_video()

        layout = QVBoxLayout()
        layout.addWidget(ctx)
        layout.addWidget(video)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def setup_ctx(self):
        """
        Setup list

        :return: QWidget
        :rtype: QWidget
        """
        id = 'ctx.list'
        self.window.ui.nodes['ctx.new'] = QPushButton(trans('ctx.new'))
        self.window.ui.nodes['ctx.new'].clicked.connect(
            lambda: self.window.controller.context.new())

        self.window.ui.nodes[id] = ContextList(self.window, id)
        self.window.ui.nodes[id].selection_locked = self.window.controller.context.context_change_locked
        self.window.ui.nodes['ctx.label'] = QLabel(trans("ctx.list.label"))
        self.window.ui.nodes['ctx.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['ctx.new'])
        layout.addWidget(self.window.ui.nodes[id])
        layout.setContentsMargins(0, 0, 0, 0)

        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])
        self.window.ui.nodes[id].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.context.selection_change())

        widget = QWidget()
        widget.setLayout(layout)
        widget.setContentsMargins(0, 0, 0, 0)

        return widget

    def setup_video(self):
        """
        Setup video preview
        :return: VideoContainer
        :rtype: VideoContainer
        """
        self.window.ui.nodes['video.preview'] = VideoContainer(self.window)
        self.window.ui.nodes['video.preview'].setVisible(False)

        return self.window.ui.nodes['video.preview']

    def create_model(self, parent):
        """
        Create model

        :param parent: parent widget
        :return: QStandardItemModel
        :rtype: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update_list(self, id, data):
        """
        Update list

        :param id: ID of the list
        :param data: Data to update
        """
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())
        i = 0
        for n in data:
            if 'name' in data[n] and 'date' in data[n]:
                self.window.ui.models[id].insertRow(i)
                dt = self.convert_date(data[n]['date'])
                name = data[n]['name'] + ' (' + dt + ')'
                self.window.ui.models[id].setData(self.window.ui.models[id].index(i, 0), name)
                i += 1

        self.window.ui.nodes[id].restore_selection()

    def convert_date(self, date_str):
        """
        Convert date to human readable format

        :param date_str: date string in format YYYY-MM-DD
        :return: string
        :rtype: str
        """
        today = datetime.today().date()
        yesterday = today - timedelta(days=1)
        one_week_ago = today - timedelta(weeks=1)
        two_weeks_ago = today - timedelta(weeks=2)
        three_weeks_ago = today - timedelta(weeks=3)
        one_month_ago = today - timedelta(days=30)

        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        if date == today:
            return trans('dt.today')
        elif date == yesterday:
            return trans('dt.yesterday')
        elif date > one_week_ago:
            days_ago = (today - date).days
            return f"{days_ago} " + trans('dt.days_ago')
        elif date == one_week_ago:
            return trans('dt.week')
        elif date == two_weeks_ago:
            return "2 " + trans('dt.weeks')
        elif date == three_weeks_ago:
            return "3 " + trans('dt.weeks')
        elif date >= one_month_ago:
            return trans('dt.month')
        else:
            return date.strftime("%Y-%m-%d")
