#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import builtins
import gc
import math
import os
import sys
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, mock_open

import pytest

import pygpt_net.utils as utils
from pygpt_net.utils import parse_args


def test_parse_args_string():
    assert parse_args([{"name": "test_str", "value": "string", "type": "str"}])["test_str"] == "string"


def test_parse_args_int():
    assert parse_args([{"name": "test_int", "value": "123", "type": "int"}])["test_int"] == 123


def test_parse_args_float():
    assert parse_args([{"name": "test_float", "value": "123.50", "type": "float"}])["test_float"] == 123.50


def test_parse_args_bool_true_int():
    assert parse_args([{"name": "test_bool", "value": "1", "type": "bool"}])["test_bool"] is True


def test_parse_args_bool_false_int():
    assert parse_args([{"name": "test_bool", "value": "0", "type": "bool"}])["test_bool"] is False


def test_parse_args_bool_true_string():
    assert parse_args([{"name": "test_bool", "value": "true", "type": "bool"}])["test_bool"] is True


def test_parse_args_bool_false_string():
    assert parse_args([{"name": "test_bool", "value": "false", "type": "bool"}])["test_bool"] is False


def test_parse_args_dict():
    args = parse_args([{"name": "test_dict", "value": '{"key1": "value1", "key2": "value2"}', "type": "dict"}])
    assert args["test_dict"] == {"key1": "value1", "key2": "value2"}


def test_parse_args_list():
    args = parse_args([{"name": "test_list", "value": "item1,item2, item3,   item4", "type": "list"}])
    assert args["test_list"] == ["item1", "item2", "item3", "item4"]


def test_parse_args_none():
    assert parse_args([{"name": "test_none", "value": "any", "type": "None"}])["test_none"] is None


def test_parse_args_default():
    assert parse_args([{"name": "test_str", "value": "string", "type": ""}])["test_str"] == "string"


def test_translation_alias_delegates_to_trans(monkeypatch):
    trans = MagicMock(return_value="translated")
    monkeypatch.setattr(utils, "trans", trans)
    assert utils._("key", True, "domain") == "translated"
    trans.assert_called_once_with("key", True, "domain")


def test_trans_reload_initializes_locale_once(monkeypatch):
    locale = MagicMock()
    factory = MagicMock(return_value=locale)
    monkeypatch.setattr(utils, "Locale", factory)
    monkeypatch.setattr(utils, "locale", None)

    utils.trans_reload()
    utils.trans_reload()

    factory.assert_called_once_with()
    assert locale.reload_config.call_count == 2


def test_trans_initializes_domain_reloads_and_gets_value(monkeypatch):
    locale = MagicMock()
    locale.get.return_value = "value"
    factory = MagicMock(return_value=locale)
    monkeypatch.setattr(utils, "Locale", factory)
    monkeypatch.setattr(utils, "locale", None)

    assert utils.trans("key", reload=True, domain="plugin") == "value"
    factory.assert_called_once_with("plugin")
    locale.reload.assert_called_once_with("plugin")
    locale.get.assert_called_once_with("key", "plugin")


def test_sizeof_fmt_invalid_small_and_large_values():
    assert utils.sizeof_fmt("bad") == "-"
    assert utils.sizeof_fmt(512) == "512,0 B"
    assert utils.sizeof_fmt(1536) == "1,5 KB"
    assert utils.sizeof_fmt(1024 ** 8) == "1,0 YiB"


def test_environment_helpers_use_local_environment_proxy(monkeypatch):
    local_env = {}
    monkeypatch.setattr(utils, "os", SimpleNamespace(environ=local_env))

    utils.set_env("PYGPT_TEST_ENV", "one")
    assert utils.has_env("PYGPT_TEST_ENV") is True
    assert utils.get_env("PYGPT_TEST_ENV") == "one"

    utils.set_env("PYGPT_TEST_ENV", "two", append=True)
    assert local_env["PYGPT_TEST_ENV"] == "one two"

    # allow_overwrite means preserve an already-set value in this helper.
    utils.set_env("PYGPT_TEST_ENV", "ignored", allow_overwrite=True)
    assert local_env["PYGPT_TEST_ENV"] == "one two"

    local_env["PYGPT_TEST_ENV"] = ""
    assert utils.has_env("PYGPT_TEST_ENV") is False
    assert utils.get_env("PYGPT_TEST_ENV", "fallback") == "fallback"


def test_freeze_updates_restores_widget_after_exception():
    widget = MagicMock()
    with pytest.raises(RuntimeError):
        with utils.freeze_updates(widget):
            raise RuntimeError("boom")
    assert widget.setUpdatesEnabled.call_args_list == [((False,), {}), ((True,), {})]


def test_get_init_value_reads_once_and_caches_metadata(monkeypatch):
    reader = mock_open(read_data='__version__ = "9.9.9"\n__author__ = "Tester"\n')
    monkeypatch.setattr(builtins, "open", reader)
    monkeypatch.setattr(utils, "init_file_meta", None)

    assert utils.get_init_value("__version__") == "9.9.9"
    assert utils.get_init_value("__author__") == "Tester"
    assert reader.call_count == 1


def test_get_app_meta_queries_expected_keys(monkeypatch):
    getter = MagicMock(side_effect=lambda key: f"value:{key}")
    monkeypatch.setattr(utils, "get_init_value", getter)

    meta = utils.get_app_meta()

    assert meta["version"] == "value:__version__"
    assert meta["github"] == "value:__github__"
    assert meta["report"] == "value:__report__"
    assert getter.call_count == 16


def test_parse_args_invalid_values_and_native_collections():
    class NoSplit:
        pass

    result = utils.parse_args([
        {"name": "bad_int", "value": "x", "type": "int"},
        {"name": "bad_float", "value": "x", "type": "float"},
        {"name": "bad_bool", "value": "x", "type": "bool"},
        {"name": "bad_dict", "value": "{", "type": "dict"},
        {"name": "native_dict", "value": {"a": 1}, "type": "dict"},
        {"name": "bad_list", "value": NoSplit(), "type": "list"},
        {"name": "native_list", "value": ["a", "b"], "type": "list"},
        {"name": "default", "value": 123},
    ])

    assert result == {
        "bad_int": 0,
        "bad_float": 0.0,
        "bad_bool": False,
        "bad_dict": {},
        "native_dict": {"a": 1},
        "bad_list": [],
        "native_list": ["a", "b"],
        "default": "123",
    }


def test_unpack_var_supported_invalid_and_passthrough():
    class BadBool:
        def __bool__(self):
            raise RuntimeError("bad bool")

    assert utils.unpack_var("12", "int") == 12
    assert utils.unpack_var("bad", "int") == 0
    assert utils.unpack_var("1.5", "float") == 1.5
    assert utils.unpack_var("bad", "float") == 0.0
    assert utils.unpack_var(1, "bool") is True
    assert utils.unpack_var(BadBool(), "bool") is False
    marker = object()
    assert utils.unpack_var(marker, "str") is marker


def test_pack_arg_supported_types_and_serialization_failures():
    assert utils.pack_arg(None, "str") == ""
    assert utils.pack_arg("", "str") == ""
    assert utils.pack_arg(["a", "b"], "list") == "a,b"
    assert utils.pack_arg(123, "list") == ""
    assert utils.pack_arg({"a": 1}, "dict") == '{"a": 1}'
    assert utils.pack_arg({1, 2}, "dict") == ""
    assert utils.pack_arg(True, "bool") == "True"
    assert utils.pack_arg("value", "str") == "value"


def test_image_helpers_supported_and_unsupported_extensions():
    assert utils.get_image_extensions() == ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"]
    assert utils.is_image("PHOTO.JPEG") is True
    assert utils.is_image("archive.tar.gz") is False


def test_get_tz_offset_uses_mocked_timestamp_difference(monkeypatch):
    class Moment:
        def __init__(self, timestamp):
            self._timestamp = timestamp

        def timestamp(self):
            return self._timestamp

    class FakeDateTime:
        @classmethod
        def utcnow(cls):
            return Moment(1000)

        @classmethod
        def now(cls):
            return Moment(4600)

    monkeypatch.setattr(utils, "datetime", FakeDateTime)
    assert utils.get_tz_offset() == 3600


def test_natsort_orders_numeric_fragments_naturally():
    assert utils.natsort(["item10", "Item2", "item1"]) == ["item1", "Item2", "item10"]


def test_mem_clean_disabled_and_forced_non_platform_path(monkeypatch):
    assert utils.mem_clean(force=False) is False

    collect = MagicMock()
    monkeypatch.setattr(gc, "collect", collect)
    qapp = SimpleNamespace(sendPostedEvents=MagicMock(), processEvents=MagicMock())
    qtcore = SimpleNamespace(
        QEvent=SimpleNamespace(DeferredDelete="deferred"),
        QEventLoop=SimpleNamespace(AllEvents="all"),
    )
    qtgui = SimpleNamespace(QPixmapCache=SimpleNamespace(clear=MagicMock()))
    monkeypatch.setattr(utils, "QApplication", qapp)
    monkeypatch.setattr(utils, "QtCore", qtcore)
    monkeypatch.setattr(utils, "QtGui", qtgui)
    monkeypatch.setattr(sys, "platform", "test-platform")

    assert utils.mem_clean(force=True) is False
    collect.assert_called_once_with()
    qapp.sendPostedEvents.assert_called_once_with(None, "deferred")
    qapp.processEvents.assert_called_once_with("all", 50)
    qtgui.QPixmapCache.clear.assert_called_once_with()


def test_short_num_boundaries_custom_options_and_special_values():
    assert utils.short_num(999) == "999"
    assert utils.short_num(1500) == "1,5k"
    assert utils.short_num(-1500) == "-1,5k"
    assert utils.short_num(999_950) == "1M"
    assert utils.short_num(1536, base=1024, suffixes=("", "Ki", "Mi"), decimal_sep=".") == "1.5Ki"
    assert utils.short_num(Decimal("12.34"), max_decimals=0) == "12,34"
    assert utils.short_num(float("inf")) == "inf"
    assert utils.short_num(float("-inf")) == "-inf"
    assert math.isnan(float(utils.short_num(float("nan"))))
    with pytest.raises(TypeError):
        utils.short_num(object())
