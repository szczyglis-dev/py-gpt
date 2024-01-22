#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.22 10:00:00                  #
# ================================================== #

from pygpt_net.utils import parse_args


def test_parse_args_string():
    items = [
        {
            "name": "test_str",
            "value": "string",
            "type": "str",
        }
    ]
    args = parse_args(items)
    assert args["test_str"] == "string"


def test_parse_args_int():
    items = [
        {
            "name": "test_int",
            "value": "123",
            "type": "int",
        }
    ]
    args = parse_args(items)
    assert args["test_int"] == 123


def test_parse_args_float():
    items = [
        {
            "name": "test_float",
            "value": "123.50",
            "type": "float",
        }
    ]
    args = parse_args(items)
    assert args["test_float"] == 123.50


def test_parse_args_bool_true_int():
    items = [
        {
            "name": "test_bool",
            "value": "1",
            "type": "bool",
        }
    ]
    args = parse_args(items)
    assert args["test_bool"] is True


def test_parse_args_bool_false_int():
    items = [
        {
            "name": "test_bool",
            "value": "0",
            "type": "bool",
        }
    ]
    args = parse_args(items)
    assert args["test_bool"] is False


def test_parse_args_bool_true_string():
    items = [
        {
            "name": "test_bool",
            "value": "true",
            "type": "bool",
        }
    ]
    args = parse_args(items)
    assert args["test_bool"] is True


def test_parse_args_bool_false_string():
    items = [
        {
            "name": "test_bool",
            "value": "false",
            "type": "bool",
        }
    ]
    args = parse_args(items)
    assert args["test_bool"] is False


def test_parse_args_dict():
    items = [
        {
            "name": "test_dict",
            "value": '{"key1": "value1", "key2": "value2"}',
            "type": "dict",
        }
    ]
    args = parse_args(items)
    assert args["test_dict"] == {"key1": "value1", "key2": "value2"}


def test_parse_args_list():
    items = [
        {
            "name": "test_list",
            "value": "item1,item2, item3,   item4",
            "type": "list",
        }
    ]
    args = parse_args(items)
    assert args["test_list"] == ["item1", "item2", "item3", "item4"]


def test_parse_args_none():
    items = [
        {
            "name": "test_none",
            "value": "any",
            "type": "None",
        }
    ]
    args = parse_args(items)
    assert args["test_none"] is None


def test_parse_args_default():
    items = [
        {
            "name": "test_str",
            "value": "string",
            "type": "",
        }
    ]
    args = parse_args(items)
    assert args["test_str"] == "string"
