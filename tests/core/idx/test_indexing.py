#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.22 11:00:00                  #
# ================================================== #

import os
import platform
from unittest.mock import MagicMock, patch
from llama_index.readers.schema.base import Document

from tests.mocks import mock_window
from pygpt_net.core.idx import Indexing


def test_get_online_loader(mock_window):
    """Test get online loader"""
    idx = Indexing(mock_window)
    loader = MagicMock()
    loaders = [
        {
            "ext": "pdf",
            "loader": loader,
        },
    ]
    mock_window.core.config.set("llama.hub.loaders", loaders)
    assert idx.get_online_loader("pdf") == loader


def test_get_documents(mock_window):
    """Test get documents"""
    idx = Indexing(mock_window)
    idx.get_online_loader = MagicMock(return_value=None)
    doc = Document()
    docs = [doc]
    reader = MagicMock()
    reader.load_data = MagicMock(return_value=docs)
    loaders = {
        "pdf": reader,
    }
    idx.loaders = loaders
    with patch("os.path.isdir") as mock_isdir:
        mock_isdir.return_value = False
        documents = idx.get_documents("file.pdf")
    assert documents == docs

