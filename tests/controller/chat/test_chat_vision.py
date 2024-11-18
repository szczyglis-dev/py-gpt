#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.03 08:00:00                  #
# ================================================== #

from unittest.mock import MagicMock

from tests.mocks import mock_window
from pygpt_net.controller.chat.vision import Vision


def test_show_inline(mock_window):
    """Test show inline vision"""
    vision = Vision(mock_window)
    vision.window.ui.nodes['inline.vision'].setVisible = MagicMock()
    vision.show_inline()
    vision.window.ui.nodes['inline.vision'].setVisible.assert_called_once_with(True)


def test_hide_inline(mock_window):
    """Test hide inline vision"""
    vision = Vision(mock_window)
    vision.window.ui.nodes['inline.vision'].setVisible = MagicMock()
    vision.hide_inline()
    vision.window.ui.nodes['inline.vision'].setVisible.assert_called_once_with(False)

def test_available(mock_window):
    """Test available vision"""
    vision = Vision(mock_window)
    vision.is_available = False
    vision.available()
    assert vision.is_available


def test_unavailable(mock_window):
    """Test unavailable vision"""
    vision = Vision(mock_window)
    vision.is_available = True
    vision.unavailable()
    assert not vision.is_available
