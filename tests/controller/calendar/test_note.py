#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 03:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from pygpt_net.item.calendar_note import CalendarNoteItem
from tests.mocks import mock_window
from pygpt_net.controller.calendar.note import Note


def test_update(mock_window):
    """Test update"""
    mock_window.core.calendar.add = MagicMock()
    mock_window.core.calendar.update = MagicMock()
    mock_window.core.calendar.get_by_date = MagicMock(return_value=None)
    note = Note(mock_window)
    item = CalendarNoteItem()
    note.create = MagicMock(return_value=item)
    note.refresh_num = MagicMock()
    note.update()
    mock_window.core.calendar.add.assert_called_once()


def test_update_content(mock_window):
    """Test update content"""
    item = CalendarNoteItem()
    item.content = "test"
    mock_window.core.calendar.get_by_date = MagicMock(return_value=item)
    mock_window.ui.calendar['note'].setPlainText = MagicMock()
    note = Note(mock_window)
    note.update_content(2024, 1, 1)
    mock_window.ui.calendar['note'].setPlainText.assert_called_once_with("test")


def test_update_label(mock_window):
    """Test update label"""
    mock_window.ui.calendar['note.label'].setText = MagicMock()
    note = Note(mock_window)
    note.update_label(2024, 1, 1)
    mock_window.ui.calendar['note.label'].setText.assert_called_once()


def test_update_current(mock_window):
    """Test update current"""
    note = Note(mock_window)
    note.update_label = MagicMock()
    note.update_current()
    note.update_label.assert_called_once()


def test_update_status(mock_window):
    """Test update status"""
    item = CalendarNoteItem()
    item.content = "test"
    mock_window.core.calendar.get_by_date = MagicMock(return_value=item)
    mock_window.core.calendar.update = MagicMock()
    note = Note(mock_window)
    note.refresh_num = MagicMock()
    note.update_status("red", 2024, 1, 1)
    mock_window.core.calendar.update.assert_called_once()


def test_refresh_ctx(mock_window):
    """Test refresh ctx"""
    mock_window.core.ctx.provider.get_ctx_count_by_day = MagicMock(return_value=1)
    mock_window.ui.calendar['select'].update_ctx = MagicMock()
    note = Note(mock_window)
    note.get_counts_around_month = MagicMock(return_value=1)
    note.refresh_ctx(2024, 1)
    mock_window.ui.calendar['select'].update_ctx.assert_called_once()


def test_create(mock_window):
    """Test create"""
    item = CalendarNoteItem()
    mock_window.core.calendar.build = MagicMock(return_value=item)
    note = Note(mock_window)
    item = note.create(2024, 1, 1)
    assert isinstance(item, CalendarNoteItem) is True
    assert item.year == 2024
    assert item.month == 1
    assert item.day == 1


def test_refresh_num(mock_window):
    """Test refresh num"""
    mock_window.ui.calendar['select'].update_notes = MagicMock()
    note = Note(mock_window)
    note.get_notes_existence_around_month = MagicMock(return_value=1)
    note.refresh_num(2024, 1)
    mock_window.ui.calendar['select'].update_notes.assert_called_once()

