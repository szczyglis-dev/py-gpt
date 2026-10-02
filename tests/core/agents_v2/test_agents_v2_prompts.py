#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.agents_v2.prompts as prompts_module
from pygpt_net.core.agents_v2.prompts import (
    AGENTS_DIRECTORY_MEMORIES_PROMPT,
    AGENTS_DIRECTORY_SUPPORT_PROMPT,
    agents_directory_exists,
    append_agents_directory_support,
)


def _window(workdir):
    filesystem = SimpleNamespace(get_data_dir=MagicMock(return_value=str(workdir)))
    debug = SimpleNamespace(log=MagicMock())
    return SimpleNamespace(core=SimpleNamespace(filesystem=filesystem, debug=debug))


def test_agents_directory_exists_detects_directory_in_active_workdir(tmp_path):
    agents_dir = tmp_path / ".agents"
    agents_dir.mkdir()
    window = _window(tmp_path)
    ctx = object()

    assert agents_directory_exists(window, ctx=ctx) is True
    window.core.filesystem.get_data_dir.assert_called_once_with(ctx=ctx, create=False)


def test_agents_directory_exists_returns_false_when_directory_is_missing(tmp_path):
    window = _window(tmp_path)

    assert agents_directory_exists(window) is False
    window.core.filesystem.get_data_dir.assert_called_once_with(ctx=None, create=False)


def test_agents_directory_exists_rejects_path_resolving_outside_workdir(tmp_path, monkeypatch):
    window = _window(tmp_path)
    outside = str(tmp_path.parent / (tmp_path.name + "-outside") / ".agents")
    original_realpath = prompts_module.os.path.realpath

    monkeypatch.setattr(prompts_module.os.path, "isdir", lambda path: True)
    monkeypatch.setattr(
        prompts_module.os.path,
        "realpath",
        lambda path: outside if str(path).endswith(".agents") else original_realpath(path),
    )

    assert agents_directory_exists(window) is False


def test_append_agents_directory_support_uses_existing_directory_guidance_once():
    prompt = append_agents_directory_support("Base prompt", directory_exists=True)

    assert prompt.startswith("Base prompt\n\n")
    assert AGENTS_DIRECTORY_SUPPORT_PROMPT in prompt
    assert ".agents/memories/" in prompt
    assert append_agents_directory_support(prompt, directory_exists=True) == prompt


def test_append_agents_directory_support_uses_memory_hint_when_directory_missing():
    prompt = append_agents_directory_support("Base prompt", directory_exists=False)

    assert AGENTS_DIRECTORY_MEMORIES_PROMPT in prompt
    assert "No `%workdir%/.agents/` directory exists" in prompt
    assert ".agents/memories/" in prompt


def test_custom_main_prompt_and_unknown_default_preserve_user_policy():
    from pygpt_net.core.agents_v2.prompts import build_custom_main_prompt, get_default_custom_prompt, CUSTOM_PRIMARY_PROMPT_CONFIG_KEY
    assert build_custom_main_prompt(' custom ') == 'custom'
    assert build_custom_main_prompt(None) == ''
    assert get_default_custom_prompt('unknown') == ''
    assert 'Primary Agent' in get_default_custom_prompt(CUSTOM_PRIMARY_PROMPT_CONFIG_KEY)
