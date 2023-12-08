#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 22:00:00                  #
# ================================================== #

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget
from datetime import datetime, timedelta

from .widget.select import ContextSelectMenu
from ..utils import trans


class Contexts:
    def __init__(self, window=None):
        """
        Contexts UI

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """
        Setups contexts list

        :return: QVBoxLayout
        """
        # contexts
        contexts = self.setup_contexts()
        self.window.models['ctx.contexts'] = self.create_model(self.window)
        self.window.data['ctx.contexts'].setModel(self.window.models['ctx.contexts'])
        self.window.data['ctx.contexts'].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.context.selection_change())

        ctx_widget = QWidget()
        ctx_widget.setLayout(contexts)
        ctx_widget.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout()
        layout.addWidget(ctx_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        return layout

    def setup_contexts(self):
        """
        Setups contexts list

        :return: QVBoxLayout
        """
        id = 'ctx.contexts'
        self.window.data['contexts.new'] = QPushButton(trans('context.new'))
        self.window.data['contexts.new'].clicked.connect(
            lambda: self.window.controller.context.new())

        self.window.data[id] = ContextSelectMenu(self.window, id) # TODO: smaller font size
        self.window.data[id].setStyleSheet(self.window.controller.theme.get_style('text_small'))
        self.window.data['contexts.label'] = QLabel(trans("ctx.contexts.label"))
        self.window.data['contexts.label'].setStyleSheet(self.window.controller.theme.get_style('text_bold'))

        layout = QVBoxLayout()
        layout.addWidget(self.window.data['contexts.label'])
        layout.addWidget(self.window.data['contexts.new'])
        layout.addWidget(self.window.data[id])

        self.window.models[id] = self.create_model(self.window)
        self.window.data[id].setModel(self.window.models[id])
        return layout

    def create_model(self, parent):
        """
        Creates list model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        model = QStandardItemModel(0, 1, parent)
        return model

    def update_list(self, id, data):
        """
        Updates list

        :param id: ID of the list
        :param data: Data to update
        """
        self.window.models[id].removeRows(0, self.window.models[id].rowCount())
        i = 0
        for n in data:
            if 'name' in data[n] and 'date' in data[n]:
                self.window.models[id].insertRow(i)
                dt = self.convert_date(data[n]['date'])
                name = data[n]['name'] + ' (' + dt + ')'
                self.window.models[id].setData(self.window.models[id].index(i, 0), name)
                i += 1

    def convert_date(self, date_str):
        """
        Converts date to human readable format

        :param date_str: date string in format YYYY-MM-DD
        :return: string
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
