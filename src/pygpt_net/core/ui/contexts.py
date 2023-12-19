#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.19 17:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel, Qt
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget
from datetime import datetime, timedelta

from .widget.select import ContextSelectMenu
from .widget.camera import VideoContainer
from ..utils import trans


class Contexts:
    def __init__(self, window=None):
        """
        Contexts UI

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """
        Setup contexts list

        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        # contexts
        contexts = self.setup_contexts()
        self.window.ui.models['ctx.contexts'] = self.create_model(self.window)
        self.window.ui.nodes['ctx.contexts'].setModel(self.window.ui.models['ctx.contexts'])
        self.window.ui.nodes['ctx.contexts'].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.context.selection_change())

        self.window.ui.nodes['video.preview'] = VideoContainer(self.window)
        self.window.ui.nodes['video.preview'].setVisible(False)

        ctx_widget = QWidget()
        ctx_widget.setLayout(contexts)
        ctx_widget.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.addWidget(ctx_widget)
        layout.addWidget(self.window.ui.nodes['video.preview'])

        return layout

    def setup_contexts(self):
        """
        Setup contexts list

        :return: QVBoxLayout
        :rtype: QVBoxLayout
        """
        id = 'ctx.contexts'
        self.window.ui.nodes['contexts.new'] = QPushButton(trans('context.new'))
        self.window.ui.nodes['contexts.new'].clicked.connect(
            lambda: self.window.controller.context.new())

        self.window.ui.nodes[id] = ContextSelectMenu(self.window, id)
        self.window.ui.nodes[id].setStyleSheet(self.window.controller.theme.get_style('text_small'))
        self.window.ui.nodes[id].selection_locked = self.window.controller.context.context_change_locked
        self.window.ui.nodes['contexts.label'] = QLabel(trans("ctx.contexts.label"))
        self.window.ui.nodes['contexts.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        layout = QVBoxLayout()
        # layout.addWidget(self.window.ui.nodes['contexts.label'])
        layout.addWidget(self.window.ui.nodes['contexts.new'])
        layout.addWidget(self.window.ui.nodes[id])
        layout.setContentsMargins(0, 0, 0, 0)

        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])

        # prevent focus out selection leave
        self.window.ui.nodes[id].selectionModel().selectionChanged.connect(self.window.ui.nodes[id].lockSelection)
        return layout

    def create_model(self, parent):
        """
        Create list model

        :param parent: parent widget
        :return: QStandardItemModel
        :rtype: QStandardItemModel
        """
        model = QStandardItemModel(0, 1, parent)
        return model

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
