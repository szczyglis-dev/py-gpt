#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from pygpt_net.core.ctx.bag import Bag


def test_init_defaults():
    bag = Bag()
    assert bag.window is None
    assert bag.meta is None
    assert bag.tab_id == 0
    assert isinstance(bag.items, list)
    assert bag.get_items() == []
    assert bag.count_items() == 0


def test_init_with_window():
    win = object()
    bag = Bag(window=win)
    assert bag.window is win
    assert bag.meta is None
    assert bag.tab_id == 0
    assert bag.get_items() == []
    assert bag.count_items() == 0


def test_get_items_returns_reference_and_mutation_reflects():
    bag = Bag()
    ref = bag.get_items()
    m = MagicMock()
    ref.append(m)
    assert bag.items is ref
    assert bag.count_items() == 1
    assert bag.get_items()[0] is m


def test_clear_items_empties_existing_items_and_is_idempotent():
    bag = Bag()
    a = MagicMock()
    b = MagicMock()
    bag.items = [a, b]
    assert bag.count_items() == 2
    bag.clear_items()
    assert bag.items == []
    assert bag.count_items() == 0
    bag.clear_items()
    assert bag.items == []
    assert bag.count_items() == 0


def test_set_items_calls_clear_items_and_sets_reference():
    bag = Bag()
    bag.items = [MagicMock()]
    new_items = [MagicMock(), MagicMock()]
    with patch.object(Bag, "clear_items") as mocked_clear:
        bag.set_items(new_items)
    mocked_clear.assert_called_once()
    assert bag.items is new_items
    assert bag.count_items() == 2


def test_set_items_replaces_previous_items_when_not_mocked():
    bag = Bag()
    old = [MagicMock(), MagicMock()]
    bag.items = old
    new_items = [MagicMock()]
    bag.set_items(new_items)
    assert bag.items is new_items
    assert bag.count_items() == 1