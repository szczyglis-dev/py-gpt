#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.26 23:00:00                  #
# ================================================== #

from unittest.mock import MagicMock, patch

from tests.mocks import mock_window_conf
from pygpt_net.item.assistant import AssistantItem
from pygpt_net.core.assistants import Assistants


def test_install():
    """
    Test install
    """
    assistants = Assistants()
    assistants.provider = MagicMock()
    assistants.provider.install = MagicMock()
    assistants.install()
    assistants.provider.install.assert_called_once_with()


def test_patch():
    """
    Test patch
    """
    assistants = Assistants()
    assistants.provider = MagicMock()
    assistants.provider.patch = MagicMock()
    version = '1.0.0'
    assistants.patch(version)
    assistants.provider.patch.assert_called_once_with(version)


def test_get_by_idx():
    """
    Test get by index
    """
    assistants = Assistants()
    items = {
        'assistant1': AssistantItem(),
        'assistant2': AssistantItem(),
    }
    assistants.items = items
    assert assistants.get_by_idx(0) == 'assistant1'
    assert assistants.get_by_idx(1) == 'assistant2'


def test_get_by_id():
    """
    Test get by id
    """
    assistants = Assistants()
    a1 = AssistantItem()
    a2 = AssistantItem()
    items = {
        'assistant1': a1,
        'assistant2': a2,
    }
    assistants.items = items
    assert assistants.get_by_id('assistant1') == a1
    assert assistants.get_by_id('assistant2') == a2


def test_get_by_id_not_found():
    """
    Test get by id not found
    """
    assistants = Assistants()
    items = {
        'assistant1': AssistantItem(),
        'assistant2': AssistantItem(),
    }
    assistants.items = items
    assert assistants.get_by_id('assistant3') is None


def test_get_all():
    """
    Test get all
    """
    assistants = Assistants()
    items = {
        'assistant1': AssistantItem(),
        'assistant2': AssistantItem(),
    }
    assistants.items = items
    assert assistants.get_all() == items


def test_has():
    """
    Test has
    """
    assistants = Assistants()
    items = {
        'assistant1': AssistantItem(),
        'assistant2': AssistantItem(),
    }
    assistants.items = items
    assert assistants.has('assistant1') is True
    assert assistants.has('assistant3') is False


def test_create():
    """
    Test create
    """
    assistants = Assistants()
    assistant = assistants.create()
    assert isinstance(assistant, AssistantItem)


def test_add():
    """
    Test add
    """
    assistant = MagicMock()
    assistant.id = "id1"

    with patch('pygpt_net.core.assistants.assistants.Assistants.save') as mock_save:
        assistants = Assistants()
        assistants.add(assistant)

        mock_save.assert_called_once_with()
        assert assistants.items['id1'] == assistant


def test_delete():
    """
    Test delete
    """
    a1 = AssistantItem()
    a2 = AssistantItem()
    items = {
        'assistant1': a1,
        'assistant2': a2,
    }

    with patch('pygpt_net.core.assistants.assistants.Assistants.save') as mock_save:
        assistants = Assistants()
        assistants.items = items
        assistants.delete('assistant1')

        mock_save.assert_called_once_with()
        assert assistants.items == {'assistant2': a2}


def test_replace_attachment():
    """
    Test replace attachment
    """
    assistant = MagicMock()
    assistant.attachments = {
        'id_old': MagicMock(),
        'id_other': MagicMock(),
    }

    with patch('pygpt_net.core.assistants.assistants.Assistants.save') as mock_save:
        assistants = Assistants()
        assistants.replace_attachment(assistant, MagicMock(), 'id_old', 'id_new')

        mock_save.assert_called_once_with()
        assert 'id_old' not in assistant.attachments
        assert 'id_new' in assistant.attachments
        assert 'id_other' in assistant.attachments


def test_get_default_assistant_empty():
    """
    Test get default assistant empty
    """
    assistants = Assistants()
    assert assistants.get_default_assistant() is None


def test_get_default_assistant():
    """
    Test get default assistant
    """
    assistants = Assistants()
    a1 = AssistantItem()
    a2 = AssistantItem()
    items = {
        'assistant1': a1,
        'assistant2': a2,
    }
    assistants.items = items
    assert assistants.get_default_assistant() == 'assistant1'


def test_load(mock_window_conf):
    """
    Test load
    """
    asst1 = AssistantItem()
    asst1.name = 'Assistant 1'

    asst2 = AssistantItem()
    asst2.name = 'Assistant 2'
    fake_data = {
            'id1': asst1,
            'id2': asst2,
    }
    assistants = Assistants(window=mock_window_conf)
    assistants.provider = {}
    assistants.provider = MagicMock()
    assistants.provider.load.return_value = fake_data
    assistants.load()

    assistants.provider.load.assert_called_once_with()
    assert assistants.items['id1'].name == 'Assistant 1'
    assert assistants.items['id2'].name == 'Assistant 2'


def test_save():
    """
    Test save
    """
    a1 = AssistantItem()
    a2 = AssistantItem()
    items = {
        'assistant1': a1,
        'assistant2': a2,
    }
    assistants = Assistants()
    assistants.items = items
    assistants.provider = MagicMock()
    assistants.provider.patch = MagicMock()
    assistants.save()
    assistants.provider.save.assert_called_once_with(items)
