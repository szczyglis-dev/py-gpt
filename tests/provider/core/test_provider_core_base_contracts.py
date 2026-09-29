#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

import pytest

from pygpt_net.provider.core.agent.base import BaseProvider as AgentBaseProvider
from pygpt_net.provider.core.assistant.base import BaseProvider as AssistantBaseProvider
from pygpt_net.provider.core.attachment.base import BaseProvider as AttachmentBaseProvider
from pygpt_net.provider.core.calendar.base import BaseProvider as CalendarBaseProvider
from pygpt_net.provider.core.config.base import BaseProvider as ConfigBaseProvider
from pygpt_net.provider.core.ctx.base import BaseProvider as CtxBaseProvider
from pygpt_net.provider.core.history.base import BaseProvider as HistoryBaseProvider
from pygpt_net.provider.core.index.base import BaseProvider as IndexBaseProvider
from pygpt_net.provider.core.mode.base import BaseProvider as ModeBaseProvider
from pygpt_net.provider.core.model.base import BaseProvider as ModelBaseProvider
from pygpt_net.provider.core.notepad.base import BaseProvider as NotepadBaseProvider
from pygpt_net.provider.core.plugin_preset.base import BaseProvider as PluginPresetBaseProvider
from pygpt_net.provider.core.preset.base import BaseProvider as PresetBaseProvider
from pygpt_net.provider.core.prompt.base import BaseProvider as PromptBaseProvider
from pygpt_net.provider.core.remote_file.base import BaseProvider as RemoteFileBaseProvider
from pygpt_net.provider.core.remote_store.base import BaseProvider as RemoteStoreBaseProvider


@pytest.mark.parametrize(("provider_cls", "provider_type"), [
    (AgentBaseProvider, "agent"),
    (AssistantBaseProvider, "assistant"),
    (AttachmentBaseProvider, "attachment"),
    (CalendarBaseProvider, "calendar_note"),
    (ConfigBaseProvider, "config"),
    (CtxBaseProvider, "ctx"),
    (HistoryBaseProvider, "history"),
    (IndexBaseProvider, "index"),
    (ModeBaseProvider, "mode"),
    (ModelBaseProvider, "model"),
    (NotepadBaseProvider, "notepad"),
    (PluginPresetBaseProvider, "plugin_presets"),
    (PresetBaseProvider, "preset"),
    (PromptBaseProvider, "prompt"),
    (RemoteFileBaseProvider, "remote_file"),
    (RemoteStoreBaseProvider, "remote_store"),
])
def test_base_provider_initialization_and_attach(provider_cls, provider_type):
    first_window = object()
    second_window = object()
    provider = provider_cls(first_window)

    assert provider.window is first_window
    assert provider.id == ""
    assert provider.type == provider_type

    provider.attach(second_window)
    assert provider.window is second_window


def test_config_base_provider_initializes_paths_and_meta():
    provider = ConfigBaseProvider()
    assert provider.path is None
    assert provider.path_app is None
    assert provider.meta is None


def test_ctx_base_load_default_is_empty_list():
    provider = CtxBaseProvider()
    assert provider.load(123) == []


def test_ctx_base_count_meta_uses_extended_get_meta_signature():
    provider = CtxBaseProvider()
    provider.get_meta = MagicMock(return_value={1: object(), 2: object()})

    result = provider.count_meta(
        search_string="hello",
        filters={"important": True},
        search_content=True,
    )

    assert result == 2
    provider.get_meta.assert_called_once_with(
        search_string="hello",
        limit=0,
        offset=0,
        filters={"important": True},
        search_content=True,
    )


def test_ctx_base_count_meta_falls_back_to_legacy_signature():
    provider = CtxBaseProvider()

    def legacy_get_meta(search_string=None):
        return {1: object()}

    provider.get_meta = MagicMock(side_effect=legacy_get_meta)
    assert provider.count_meta(search_string="legacy", filters={"x": 1}) == 1
    assert provider.get_meta.call_count == 2
    assert provider.get_meta.call_args_list[-1].kwargs == {"search_string": "legacy"}
