#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #

from packaging.version import parse as parse_version, Version
from unittest.mock import MagicMock, patch

from pygpt_net.item.preset import PresetItem
from tests.mocks import mock_window
from pygpt_net.core.presets import Presets


def test_install(mock_window):
    """Test install"""
    presets = Presets(mock_window)
    presets.provider = MagicMock()
    presets.install()
    presets.provider.install.assert_called_once()


def test_patch(mock_window):
    """Test patch"""
    presets = Presets(mock_window)
    presets.provider = MagicMock()
    presets.patch(parse_version("1.0.0"))
    presets.provider.patch.assert_called_once()


def test_build(mock_window):
    """Test get"""
    presets = Presets(mock_window)
    assert type(presets.build()) == PresetItem


def test_append_current(mock_window):
    """Test append_current"""
    presets = Presets(mock_window)
    presets.build = MagicMock(return_value=PresetItem())
    presets.append_current()
    assert len(presets.items) == 13
    assert presets.items['current.chat'].chat is True
    assert presets.items['current.completion'].completion is True
    assert presets.items['current.img'].img is True
    assert presets.items['current.vision'].vision is True
    assert presets.items['current.langchain'].langchain is True
    assert presets.items['current.assistant'].assistant is True


def test_has(mock_window):
    """Test has"""
    presets = Presets(mock_window)
    itm = PresetItem()
    itm.chat = True
    items = {
        'test': itm,
    }
    presets.items = items
    assert presets.has('chat', 'test') is True
    assert presets.has('chat', 'aaa') is False


def test_get_by_idx(mock_window):
    """Test get_by_idx"""
    presets = Presets(mock_window)
    itm = PresetItem()
    itm.chat = True
    items = {
        'test': itm,
    }
    presets.items = items
    assert presets.get_by_idx(0, 'chat') == 'test'


def test_get_by_mode(mock_window):
    """Test get_by_mode"""
    presets = Presets(mock_window)
    preset1 = PresetItem()
    preset1.chat = True
    preset2 = PresetItem()
    preset2.completion = True
    preset3 = PresetItem()
    preset3.img = True
    presets.items = {
        'test1': preset1,
        'test2': preset2,
        'test3': preset3,
    }
    assert presets.get_by_mode('chat') == {'test1': preset1}
    assert presets.get_by_mode('completion') == {'test2': preset2}
    assert presets.get_by_mode('img') == {'test3': preset3}


def test_get_idx_by_id(mock_window):
    """Test get_idx_by_id"""
    presets = Presets(mock_window)
    preset1 = PresetItem()
    preset1.chat = True
    preset2 = PresetItem()
    preset2.completion = True
    preset3 = PresetItem()
    preset3.img = True
    preset4 = PresetItem()
    preset4.img = True
    presets.items = {
        'test1': preset1,
        'test2': preset2,
        'test3': preset3,
        'test4': preset4,
    }
    assert presets.get_idx_by_id('chat', 'test1') == 0
    assert presets.get_idx_by_id('completion', 'test2') == 0
    assert presets.get_idx_by_id('img', 'test3') == 0
    assert presets.get_idx_by_id('img', 'test4') == 1


def test_get_default(mock_window):
    """Test get_default"""
    presets = Presets(mock_window)
    preset1 = PresetItem()
    preset1.chat = True
    preset2 = PresetItem()
    preset2.completion = True
    preset3 = PresetItem()
    preset3.img = True
    presets.items = {
        'test1': preset1,
        'test2': preset2,
        'test3': preset3,
    }
    assert presets.get_default('chat') == 'test1'
    assert presets.get_default('completion') == 'test2'
    assert presets.get_default('img') == 'test3'
    assert presets.get_default('vision') is None
    assert presets.get_default('langchain') is None
    assert presets.get_default('assistant') is None


def test_get_duplicate_name(mock_window):
    """Test get_duplicate_name"""
    presets = Presets(mock_window)
    preset1 = PresetItem()
    preset1.name = 'test'
    presets.items = {
        'test': preset1,
    }
    assert presets.get_duplicate_name('test') == ('test_copy', 'test copy')
    preset2 = PresetItem()
    preset2.name = 'test (1)'
    presets.items = {
        'test': preset1,
        'test_1': preset2,
    }
    assert presets.get_duplicate_name('test') == ('test_copy', 'test copy')
    preset3 = PresetItem()
    preset3.name = 'test (2)'
    presets.items = {
        'test': preset1,
        'test_1': preset2,
        'test_2': preset3,
    }
    assert presets.get_duplicate_name('test') == ('test_copy', 'test copy')


def test_duplicate(mock_window):
    """Test duplicate"""
    presets = Presets(mock_window)
    preset1 = PresetItem()
    preset1.name = 'test'
    presets.items = {
        'test': preset1,
    }
    presets.get_duplicate_name = MagicMock(return_value=('test_1', 'test (1)'))
    presets.duplicate('test')
    assert len(presets.items) == 2
    assert presets.items['test_1'].name == 'test (1)'
    assert presets.items['test_1'].chat is False
    assert presets.items['test_1'].completion is False
    assert presets.items['test_1'].img is False
    assert presets.items['test_1'].vision is False
    assert presets.items['test_1'].langchain is False
    assert presets.items['test_1'].assistant is False


def test_remove(mock_window):
    """Test remove"""
    presets = Presets(mock_window)
    preset1 = PresetItem()
    preset1.name = 'test'
    presets.items = {
        'test': preset1,
    }
    presets.provider = MagicMock()
    presets.remove('test')
    assert len(presets.items) == 0
    presets.provider.remove.assert_called_once_with('test')


def test_sort_by_name(mock_window):
    """Test sort_by_name"""
    presets = Presets(mock_window)
    preset1 = PresetItem()
    preset1.name = 'test2'
    preset2 = PresetItem()
    preset2.name = 'test1'
    presets.items = {
        'test1': preset1,
        'test2': preset2,
    }
    presets.sort_by_name()
    assert list(presets.items.keys()) == ['test2', 'test1']


def test_load(mock_window):
    """Test load"""
    presets = Presets(mock_window)
    presets.provider = MagicMock()
    presets.provider.load = MagicMock(return_value={
        'test1': PresetItem(),
        'test2': PresetItem(),
        'test3': PresetItem(),
    })
    presets.load()
    assert len(presets.items) == 16  # 10 current. presets + 3 loaded presets
    presets.provider.load.assert_called_once_with()


def test_save(mock_window):
    """Test save"""
    presets = Presets(mock_window)
    preset1 = PresetItem()
    preset1.name = 'test'
    presets.items = {
        'test': preset1,
    }
    presets.provider = MagicMock()
    presets.save('test')
    presets.provider.save.assert_called_once_with('test', preset1)


def test_save_all(mock_window):
    """Test save_all"""
    presets = Presets(mock_window)
    preset1 = PresetItem()
    preset1.name = 'test'
    presets.items = {
        'test': preset1,
    }
    presets.provider = MagicMock()
    presets.save_all()
    presets.provider.save_all.assert_called_once_with(presets.items)
