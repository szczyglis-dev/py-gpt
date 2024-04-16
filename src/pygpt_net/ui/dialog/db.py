#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QGridLayout, QScrollArea, QSplitter, QComboBox, QLineEdit, QPushButton, \
    QHBoxLayout, QVBoxLayout, QLabel, QWidget, QSizePolicy, QCheckBox, QMenuBar

from pygpt_net.ui.widget.dialog.db import DatabaseDialog
from pygpt_net.ui.widget.lists.db import DatabaseList, DatabaseTableModel
from pygpt_net.ui.widget.textarea.editor import CodeEditor

import pygpt_net.icons_rc
from pygpt_net.utils import trans


class Database:
    def __init__(self, window=None):
        """
        Database viewer setup

        :param window: Window instance
        """
        self.window = window
        self.viewer = None

    def setup(self, id: str = "db"):
        """
        Setup DB debug dialog

        :param id: debug id
        """
        self.viewer = DataBrowser(self.window)

        scroll = QScrollArea()
        scroll.setWidget(self.viewer)
        scroll.setWidgetResizable(True)

        # data viewer
        text_viewer = CodeEditor(self.window)
        text_viewer.setReadOnly(False)

        self.window.ui.debug[id].browser = self.viewer
        self.window.ui.debug[id].viewer = text_viewer

        editor_save_button = QPushButton("Save/update")
        editor_save_button.clicked.connect(self.viewer.save_data)

        editor_layout = QVBoxLayout()
        editor_layout.addWidget(text_viewer)
        editor_layout.addWidget(editor_save_button)
        editor_widget = QWidget()
        editor_widget.setLayout(editor_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(scroll)  # DataBrowser
        splitter.addWidget(editor_widget)  # Value viewer
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        self.menu_bar = QMenuBar()
        self.batch_actions_menu = self.menu_bar.addMenu("Actions")
        self.delete_all_action = QAction(QIcon(":/icons/delete.svg"), "Delete all records")
        self.delete_all_action.triggered.connect(self.viewer.delete_all)
        self.truncate_action = QAction(QIcon(":/icons/delete.svg"), "Truncate table")
        self.truncate_action.triggered.connect(self.viewer.truncate_table)
        self.batch_actions_menu.addAction(self.delete_all_action)
        self.batch_actions_menu.addAction(self.truncate_action)

        layout = QGridLayout()
        layout.addWidget(splitter, 1, 0)
        layout.setMenuBar(self.menu_bar)

        self.window.ui.dialog['debug.db'] = DatabaseDialog(self.window, id)
        self.window.ui.dialog['debug.db'].setLayout(layout)
        self.window.ui.dialog['debug.db'].setWindowTitle("Debug: Database (SQLite)")

class DataBrowser(QWidget):
    def __init__(self, window=None):
        super().__init__()
        self.window = window

        # append list widget
        self.set_list_widget()  # TableView

        # db path
        if self.is_editable():
            self.db_path_label = QLabel(self.window.core.db.db_path)
            self.db_path_label.setAlignment(Qt.AlignRight)

        # combo boxes
        self.table_select = QComboBox()
        self.sort_by_select = QComboBox()
        self.sort_order_select = QComboBox()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(trans("db.search.placeholder"))
        self.search_column_select = QComboBox()
        self.search_column_select.addItem("*", None)

        self.table_select.view().setMinimumWidth(200)
        self.sort_by_select.view().setMinimumWidth(200)
        self.sort_order_select.view().setMinimumWidth(200)
        self.search_column_select.view().setMinimumWidth(200)

        # buttons
        self.refresh_button = QPushButton(trans("db.refresh"))
        self.refresh_button.clicked.connect(self.update_table_view)
        self.prev_button = QPushButton(trans("db.prev"))
        self.next_button = QPushButton(trans("db.next"))
        self.limit_input = QLineEdit("100")
        self.limit_input.setFixedWidth(80)
        self.limit_input.editingFinished.connect(self.on_limit_change)
        self.limit_label = QLabel(trans("db.limit") + ":")
        self.limit_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # pagination
        self.page_input = QLineEdit("1")
        self.page_input.setFixedWidth(80)
        self.page_input_label = QLabel(trans("db.page") + ":")
        self.page_input_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.page_input.editingFinished.connect(self.on_page_input_change)
        self.page_info_label = QLabel(" / 1")  # total pages
        self.page_info_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # checkboxes
        if not self.is_inline():
            self.convert_timestamps_checkbox = QCheckBox(trans("db.time_convert"))
            self.convert_timestamps_checkbox.setChecked(True)
            self.convert_timestamps_checkbox.stateChanged.connect(self.update_table_view)
            self.convert_timestamps_checkbox.setToolTip(trans("db.time_convert.tip"))

        if self.is_editable():
            self.auto_backup_checkbox = QCheckBox(trans("db.backup"))
            self.auto_backup_checkbox.setChecked(True)
            self.auto_backup_checkbox.setToolTip(trans("db.backup.tip"))

        # offset
        self.current_offset = 0

        # layouts
        top_layout = QHBoxLayout()
        bottom_layout = QHBoxLayout()
        bottom_layout_left = QHBoxLayout()
        bottom_layout_right = QHBoxLayout()
        main_layout = QVBoxLayout()

        # fill combo boxes
        self.table_select.addItems(self.get_table_names())
        self.sort_order_select.addItems(['ASC', 'DESC'])

        # signals
        self.table_select.currentIndexChanged.connect(self.on_table_select_changed)
        self.sort_by_select.currentIndexChanged.connect(self.update_table_view)
        self.sort_order_select.currentIndexChanged.connect(self.update_table_view)
        self.search_input.textChanged.connect(self.update_table_view)
        self.search_column_select.currentIndexChanged.connect(self.update_table_view)

        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)

        self.table_select.setCurrentText(self.get_default_table())
        self.on_table_select_changed()  # load data

        # setup layouts
        if not self.is_inline():
            top_layout.addWidget(QLabel(trans("db.table")))
        top_layout.addWidget(self.table_select)
        top_layout.addWidget(QLabel(trans("db.sort") + ":"))
        top_layout.addWidget(self.sort_by_select)

        if not self.is_inline():
            top_layout.addWidget(QLabel(trans("db.order") + ":"))
        top_layout.addWidget(self.sort_order_select)

        if not self.is_inline():
            top_layout.addWidget(QLabel(trans("db.search") + ":"))
        top_layout.addWidget(self.search_input)

        if not self.is_inline():
            top_layout.addWidget(QLabel(trans("db.search_in") + ":"))
        top_layout.addWidget(self.search_column_select)
        #top_layout.addWidget(self.refresh_button)

        bottom_layout_left.addWidget(self.prev_button)
        bottom_layout_left.addWidget(self.next_button)
        bottom_layout_left.addWidget(self.refresh_button)

        if not self.is_inline():
            bottom_layout_right.addWidget(self.convert_timestamps_checkbox)

        if self.is_editable():
            bottom_layout_right.addWidget(self.auto_backup_checkbox)

        if not self.is_inline():
            # separator
            bottom_layout_right.addWidget(QLabel("|"))

        bottom_layout_right.addWidget(self.page_input_label)
        bottom_layout_right.addWidget(self.page_input)
        bottom_layout_right.addWidget(self.page_info_label)
        bottom_layout_right.addWidget(self.limit_label)
        bottom_layout_right.addWidget(self.limit_input)

        bottom_layout.addLayout(bottom_layout_left)
        bottom_layout.addStretch()
        bottom_layout.addLayout(bottom_layout_right)

        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.get_list_widget())  # TableView
        main_layout.addLayout(bottom_layout)

        if self.is_editable():
            main_layout.addWidget(self.db_path_label)  # db path

        self.setLayout(main_layout)

    def is_inline(self) -> bool:
        return False

    def is_editable(self) -> bool:
        return True

    def set_list_widget(self):
        self.window.ui.debug["db"] = DatabaseList(self.window)

    def get_list_widget(self):
        return self.window.ui.debug["db"]

    def get_default_table(self):
        """
        Get default table

        :return: Default table name
        """
        return "ctx_item"

    def get_filters(self):
        return {}

    def get_table_name(self, selected_text):
        return selected_text

    def get_table_names(self):
        return self.get_tables().keys()

    def save_data(self):
        """Save data to the database"""
        id = self.get_list_widget().viewer_current_id
        field = self.get_list_widget().viewer_current_field
        data = {
            'table': self.get_table_name(self.table_select.currentText()),
            'id': id,
            'field': field,
            'value': self.get_list_widget().viewer.toPlainText(),
        }
        self.window.ui.dialogs.confirm(
            type='db.update_row',
            id=data,
            msg="Update [{}] field in record ID: {}?".format(field, id),
        )

    def is_auto_backup(self) -> bool:
        """
        Get auto backup status.

        :return: Auto backup status
        """
        return self.auto_backup_checkbox.isChecked()

    def delete_row(self, id: int):
        """
        Delete row from the database

        :param id: Row id
        """
        data = {
            'table': self.get_table_name(self.table_select.currentText()),
            'row_id': id,
        }
        self.window.ui.dialogs.confirm(
            type='db.delete_row',
            id=data,
            msg="Delete record ID: {} from database?".format(id),
        )

    def truncate_table(self):
        """Truncate table"""
        data = {
            'table': self.get_table_name(self.table_select.currentText()),
        }
        self.window.ui.dialogs.confirm(
            type='db.truncate_table',
            id=data,
            msg="Truncate table: {}?".format(self.table_select.currentText()),
        )

    def delete_all(self):
        """Delete all from table"""
        data = {
            'table': self.get_table_name(self.table_select.currentText()),
        }
        self.window.ui.dialogs.confirm(
            type='db.delete_all',
            id=data,
            msg="Delete all records from table: {}?".format(self.table_select.currentText()),
        )

    def get_tables(self) -> dict:
        """
        Get tables configuration

        :return: Tables dictionary
        """
        return self.window.core.db.get_tables()

    def get_viewer(self):
        """
        Get database viewer instance

        :return: Database viewer
        """
        return self.window.core.db.viewer

    def on_limit_change(self):
        """Limit input change event"""
        try:
            limit = int(self.limit_input.text())
            if limit <= 0:
                raise ValueError("Limit must be > 0.")
        except ValueError:
            current_limit = max(1, self.current_offset // self.get_page_size() + 1)
            self.limit_input.setText(str(current_limit))
            return
        self.current_offset = 0
        self.update_table_view()

    def get_page_size(self) -> int:
        """
        Get page size from input

        :return: Number of rows per page
        """
        try:
            return int(self.limit_input.text())
        except ValueError:
            return 100

    def on_page_input_change(self, update: bool = True):
        """
        Page input change event

        :param update: Update table view
        """
        page = int(self.page_input.text()) - 1
        limit = int(self.limit_input.text())
        search_query = self.search_input.text()
        search_column = self.search_column_select.currentText()
        if search_column == "*":
            search_column = None
        current_table = self.get_table_name(self.table_select.currentText())
        total_rows = self.get_viewer().count_rows(
            current_table,
            search_query=search_query,
            search_column=search_column,
            filters=self.get_filters(),
        )

        # check if page is in range
        if page * limit < total_rows and page >= 0:
            if update:
                self.current_offset = page * limit
                self.update_table_view()
        else:
            # reset page
            current_page = self.current_offset // limit + 1
            self.page_input.setText(str(current_page))

    def update_sort_by(self):
        """Update sort by combo box"""
        current_table = self.get_table_name(self.table_select.currentText())
        self.sort_by_select.clear()
        tables = self.get_tables()
        if current_table in tables:
            self.sort_by_select.addItems(tables[current_table]['sort_by'])
            self.sort_by_select.setCurrentText(tables[current_table]['default_sort'])

    def on_table_select_changed(self):
        """Table select change event"""
        tables = self.get_tables()
        current_table = self.get_table_name(self.table_select.currentText())
        self.sort_by_select.clear()
        if current_table in tables:
            self.sort_by_select.addItems(tables[current_table]['sort_by'])
            self.sort_by_select.setCurrentText(tables[current_table]['default_sort'])
            self.sort_order_select.setCurrentText(tables[current_table]['default_order'])
            self.page_input.setText("1")  # reset page
            self.on_page_input_change()
            self.update_table_view()  # update view
            self.update_search_columns()  # update search columns

    def update_search_columns(self):
        """Update search columns"""
        tables = self.get_tables()
        current_table = self.get_table_name(self.table_select.currentText())
        self.search_column_select.clear()
        self.search_column_select.addItem("*", None)
        self.search_column_select.addItems(tables[current_table]['columns'])

    def update_pagination_info(self):
        """Update pagination info"""
        limit = int(self.limit_input.text())
        search_query = self.search_input.text()
        search_column = self.search_column_select.currentText()
        if search_column == "*":
            search_column = None
        current_table = self.get_table_name(self.table_select.currentText())
        total_rows = self.get_viewer().count_rows(
            current_table,
            search_query=search_query,
            search_column=search_column,
            filters=self.get_filters(),
        )
        total_pages = (total_rows - 1) // limit + 1
        self.page_info_label.setText(f" / {total_pages}  ({total_rows} rows)")

        current_page = self.current_offset // limit + 1
        self.page_input.setText(str(current_page))
        self.prev_button.setEnabled(self.current_offset > 0)
        self.next_button.setEnabled(self.current_offset + limit < total_rows)

    def update_table_view(self):
        """Update table view"""
        tables = self.get_tables()
        current_table = self.get_table_name(self.table_select.currentText())
        sort_by = self.sort_by_select.currentText()
        sort_order = self.sort_order_select.currentText()
        search_query = self.search_input.text()
        search_column = self.search_column_select.currentText()
        if search_column == "*":
            search_column = None
        limit = int(self.limit_input.text())

        if current_table not in tables or sort_by == '' or sort_order == '' or limit <= 0:
            return

        data = self.get_viewer().fetch_data(
            table=current_table,
            columns=tables[current_table]['columns'],
            sort_by=sort_by,
            order=sort_order,
            search_query=search_query,
            search_column=search_column,
            offset=self.current_offset,
            limit=limit,
            filters=self.get_filters(),
        )
        self.load_data(data, tables[current_table])
        self.update_pagination_info()

    def prev_page(self):
        """Previous page event"""
        limit = int(self.limit_input.text())
        if self.current_offset - limit >= 0:
            self.current_offset -= limit
        else:
            self.current_offset = 0
        self.update_table_view()

    def next_page(self):
        """Next page event"""
        limit = int(self.limit_input.text())
        current_table = self.get_table_name(self.table_select.currentText())
        total_rows = self.get_viewer().count_rows(current_table)

        if self.current_offset + limit < total_rows:
            self.current_offset += limit
        self.update_table_view()

    def get_current_table(self):
        return self.get_table_name(self.table_select.currentText())

    def load_data(self, data: list, table: dict):
        """
        Load data into the table view

        :param data: rows
        :param table: table configuration
        """
        convert_timestamps = True
        if self.is_editable():
            self.db_path_label.setText(self.window.core.db.db_path)
        if not self.is_inline():
            convert_timestamps = self.convert_timestamps_checkbox.isChecked()
        model = DatabaseTableModel(
            data,
            table['columns'],
            timestamp_columns=table.get('timestamp_columns', []),
            convert_timestamps=convert_timestamps,
        )
        self.get_list_widget().setModel(model)
        self.get_list_widget().adjustColumns()
