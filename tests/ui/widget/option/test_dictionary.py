#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.05 12:30:00                  #
# ================================================== #

from PySide6.QtCore import Qt

from pygpt_net.ui.widget.option.dictionary import OptionDictModel


def test_header_labels_can_override_raw_dictionary_keys():
    model = OptionDictModel(
        items=[{"name": "Provider", "api_key": "SECRET"}],
        headers=["name", "api_key"],
        header_labels={"name": "Provider name", "api_key": "API key"},
    )

    assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Provider name"
    assert model.headerData(1, Qt.Horizontal, Qt.DisplayRole) == "API key"


def test_secret_dictionary_field_is_masked_only_for_display():
    model = OptionDictModel(
        items=[{"name": "Provider", "api_key": "SECRET"}],
        headers=["name", "api_key"],
        secret_headers={"api_key"},
    )
    index = model.index(0, 1)

    assert model.data(index, Qt.DisplayRole) == "••••••••"
    assert model.data(index, Qt.EditRole) == "SECRET"


def test_empty_secret_dictionary_field_is_not_replaced_with_mask():
    model = OptionDictModel(
        items=[{"api_key": ""}],
        headers=["api_key"],
        secret_headers={"api_key"},
    )
    index = model.index(0, 0)

    assert model.data(index, Qt.DisplayRole) == ""
    assert model.data(index, Qt.EditRole) == ""


def test_model_counts_and_invalid_parent_indexes():
    from PySide6.QtCore import QModelIndex

    model = OptionDictModel(
        items=[{"id": 1}, {"id": 2}],
        headers=["id", "name"],
    )

    assert model.rowCount() == 2
    assert model.columnCount() == 2
    assert model.rowCount(model.index(0, 0)) == 0
    assert model.columnCount(model.index(0, 0)) == 0
    assert model.index(99, 0) == QModelIndex()
    assert model.index(0, 99) == QModelIndex()


def test_enabled_column_exposes_check_state_and_edit_value():
    model = OptionDictModel(
        items=[{"enabled": True}, {"enabled": False}],
        headers=["enabled"],
    )

    enabled = model.index(0, 0)
    disabled = model.index(1, 0)

    assert model.data(enabled, Qt.CheckStateRole) == Qt.Checked
    assert model.data(disabled, Qt.CheckStateRole) == Qt.Unchecked
    assert model.data(enabled, Qt.EditRole) is True
    assert model.data(disabled, Qt.EditRole) is False


def test_set_data_updates_check_state_and_regular_fields():
    model = OptionDictModel(
        items=[{"enabled": False, "name": "Old"}],
        headers=["enabled", "name"],
    )

    assert model.setData(model.index(0, 0), Qt.Checked, Qt.CheckStateRole) is True
    assert model.items[0]["enabled"] is True
    assert model.setData(model.index(0, 1), "New", Qt.EditRole) is True
    assert model.items[0]["name"] == "New"
    assert model.setData(model.index(0, 1), "Ignored", Qt.DisplayRole) is False


def test_enabled_flags_are_checkable_and_editable():
    model = OptionDictModel(items=[{"enabled": True}], headers=["enabled"])
    flags = model.flags(model.index(0, 0))

    assert flags & Qt.ItemIsUserCheckable
    assert flags & Qt.ItemIsEditable


def test_update_data_replaces_items():
    model = OptionDictModel(items=[{"id": 1}], headers=["id"])
    replacement = [{"id": 2}, {"id": 3}]

    model.updateData(replacement)

    assert model.items is replacement
    assert model.rowCount() == 2
