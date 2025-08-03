#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

import pytest
from unittest.mock import MagicMock
from pygpt_net.core.types import MODE_AGENT, MODE_AGENT_LLAMA, MODE_AGENT_OPENAI
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.controller.agent.legacy import Legacy


# Dummy context for testing
class DummyCtx:
    def __init__(self, sub_reply=False, cmds=None, extra_ctx=""):
        self.sub_reply = sub_reply
        self.cmds = cmds if cmds is not None else []
        self.extra_ctx = extra_ctx
        self.input_name = "input"
        self.output_name = "output"
        self.first = False


@pytest.fixture
def dummy_window():
    win = MagicMock()
    # UI setup
    ui = MagicMock()
    ui.add_hook = MagicMock()
    ui.config = {
        "global": {
            "agent.auto_stop": MagicMock(),
            "agent.continue": MagicMock(),
        }
    }
    ui.nodes = {'status.agent': MagicMock()}
    ui.tray = MagicMock()
    win.ui = ui

    # Core setup
    core = MagicMock()
    # We'll override get() for each test via side_effect
    core.config.get = MagicMock()
    core.config.set = MagicMock()
    core.config.save = MagicMock()
    core.prompt.get = MagicMock()
    core.command.is_native_enabled = MagicMock()
    core.plugins.get_option = MagicMock()
    core.debug.error = MagicMock()
    win.core = core

    # Controller setup
    controller = MagicMock()
    agent = MagicMock()
    agent.legacy = MagicMock()
    agent.common = MagicMock()
    controller.agent = agent
    controller.config = MagicMock()
    controller.plugins = MagicMock()
    controller.chat = MagicMock()
    controller.chat.common = MagicMock()
    controller.kernel = MagicMock()
    controller.kernel.stack = MagicMock()
    controller.idx = MagicMock()
    win.controller = controller

    # Additional window methods
    win.update_status = MagicMock()
    win.dispatch = MagicMock()
    return win


@pytest.fixture
def legacy_instance(dummy_window):
    return Legacy(window=dummy_window)


def test_setup(legacy_instance, dummy_window, monkeypatch):
    # Replace reload to test hook registration
    called = False

    def fake_reload():
        nonlocal called
        called = True
    monkeypatch.setattr(legacy_instance, "reload", fake_reload)
    legacy_instance.setup()
    dummy_window.ui.add_hook.assert_called_with("update.global.agent.iterations", legacy_instance.hook_update)
    assert called is True


def test_reload(legacy_instance, dummy_window):
    # Setup config values
    conf = {
        "agent.auto_stop": True,
        "agent.continue.always": False,
        "agent.iterations": 5
    }
    dummy_window.core.config.get.side_effect = lambda key: conf.get(key, None)
    legacy_instance.reload()
    dummy_window.ui.config["global"]["agent.auto_stop"].setChecked.assert_called_with(True)
    dummy_window.ui.config["global"]["agent.continue"].setChecked.assert_called_with(False)
    dummy_window.controller.config.apply_value.assert_called_with(
        parent_id="global",
        key="agent.iterations",
        option=legacy_instance.options["agent.iterations"],
        value=5,
    )


def test_update_agent_mode(legacy_instance, dummy_window):
    # Mode is agent and iterations is 0
    conf = {"mode": MODE_AGENT, "agent.iterations": 0}
    dummy_window.core.config.get.side_effect = lambda key: conf.get(key, None)
    legacy_instance.iteration = 0
    legacy_instance.update()
    expected_status = "0 / " + "∞"
    dummy_window.ui.nodes['status.agent'].setText.assert_called_with(expected_status)
    dummy_window.controller.agent.common.toggle_status.assert_called()


def test_get_functions(legacy_instance):
    funcs = legacy_instance.get_functions()
    assert isinstance(funcs, list)
    assert len(funcs) == 1
    assert funcs[0].get("cmd") == "goal_update"


def test_on_system_prompt_non_native(legacy_instance, dummy_window):
    # Simulate non-native command mode
    dummy_window.core.command.is_native_enabled.return_value = False
    dummy_window.core.prompt.get.side_effect = lambda key: "native_goal_text" if key == "agent.goal" else ""
    res = legacy_instance.on_system_prompt("base prompt", "append", auto_stop=True)
    assert res == "base prompt\nappend\n\nnative_goal_text"

    # auto_stop false: no stop command appended
    res2 = legacy_instance.on_system_prompt("base prompt", "append", auto_stop=False)
    assert res2 == "base prompt\nappend"


def test_on_input_before(legacy_instance):
    # When is_user True, adds prefix
    legacy_instance.is_user = True
    res = legacy_instance.on_input_before("hello")
    assert res == "user: hello"
    # When is_user False, returns prompt unchanged
    legacy_instance.is_user = False
    res2 = legacy_instance.on_input_before("hello")
    assert res2 == "hello"


def test_on_user_send(legacy_instance, dummy_window):
    legacy_instance.iteration = 10
    legacy_instance.prev_output = "something"
    legacy_instance.finished = True
    legacy_instance.stop = True
    # Ensure update is called on window.controller.agent.legacy
    dummy_window.controller.agent.legacy.update = MagicMock()
    legacy_instance.on_user_send("test")
    assert legacy_instance.iteration == 0
    assert legacy_instance.prev_output is None
    assert legacy_instance.finished is False
    assert legacy_instance.stop is False
    dummy_window.controller.agent.legacy.update.assert_called()


def test_on_ctx_end_stop_branch(legacy_instance):
    legacy_instance.stop = True
    dummy_ctx = DummyCtx()
    legacy_instance.iteration = 5
    legacy_instance.prev_output = "prev"
    legacy_instance.on_ctx_end(dummy_ctx)
    assert legacy_instance.stop is False
    assert legacy_instance.iteration == 0
    assert legacy_instance.prev_output is None


def test_on_ctx_end_sub_reply(legacy_instance, dummy_window):
    dummy_ctx = DummyCtx(sub_reply=True)
    legacy_instance.on_ctx_end(dummy_ctx)
    # No dispatch expected
    dummy_window.dispatch.assert_not_called()


def test_on_ctx_end_dispatch(legacy_instance, dummy_window):
    # Setup branch: no stop, no sub_reply, no cmds --> reply dispatch
    dummy_ctx = DummyCtx()
    legacy_instance.stop = False
    legacy_instance.prev_output = "continue text"
    legacy_instance.iteration = 0
    # Ensure no command in ctx
    dummy_ctx.cmds = []
    # iteration < iterations (pass iterations=3)
    dummy_window.controller.kernel.stack.waiting.return_value = False
    # Replace update to spy
    orig_update = legacy_instance.update
    legacy_instance.update = MagicMock()
    legacy_instance.on_ctx_end(dummy_ctx, iterations=3)
    assert legacy_instance.iteration == 1
    dummy_window.dispatch.assert_called()
    # Restore update if needed
    legacy_instance.update = orig_update


def test_on_ctx_end_over_iterations(legacy_instance, dummy_window):
    dummy_ctx = DummyCtx()
    legacy_instance.iteration = 1
    # Simulate notify enabled
    dummy_window.core.config.get.side_effect = lambda key: True if key == "agent.goal.notify" else None
    legacy_instance.on_stop = MagicMock()
    legacy_instance.on_ctx_end(dummy_ctx, iterations=1)
    legacy_instance.on_stop.assert_called_with(auto=True)
    dummy_window.ui.tray.show_msg.assert_called()


def test_on_ctx_before(legacy_instance):
    # For iteration 0
    dummy_ctx = DummyCtx()
    legacy_instance.iteration = 0
    legacy_instance.is_user = True
    legacy_instance.on_ctx_before(dummy_ctx, reverse_roles=False)
    assert dummy_ctx.internal is True
    assert dummy_ctx.first is True
    assert legacy_instance.is_user is False
    # Test role swap when iteration is odd and reverse_roles True
    dummy_ctx2 = DummyCtx()
    dummy_ctx2.input_name = "first"
    dummy_ctx2.output_name = "second"
    legacy_instance.iteration = 1
    legacy_instance.on_ctx_before(dummy_ctx2, reverse_roles=True)
    assert dummy_ctx2.input_name == "second"
    assert dummy_ctx2.output_name == "first"


def test_on_ctx_after(legacy_instance, dummy_window):
    # Default mode branch
    conf = {"mode": MODE_AGENT, "agent.continue.always": False}
    dummy_window.core.config.get.side_effect = lambda key: conf.get(key, None)
    dummy_window.core.prompt.get.side_effect = lambda key: "always cont" if key == "agent.continue.always" else "cont"
    # ctx.extra_ctx empty
    dummy_ctx = DummyCtx(extra_ctx="")
    legacy_instance.on_ctx_after(dummy_ctx)
    assert legacy_instance.prev_output == "cont"

    # When always continue is enabled
    conf["agent.continue.always"] = True
    legacy_instance.on_ctx_after(dummy_ctx)
    assert legacy_instance.prev_output == "always cont"

    # Inline branch override via extra_ctx
    dummy_ctx.extra_ctx = "extra"
    legacy_instance.on_ctx_after(dummy_ctx)
    assert legacy_instance.prev_output == "extra"


def test_on_cmd(legacy_instance, dummy_window):
    # If auto_stop is enabled, cmd() should be called.
    conf = {"agent.auto_stop": True}
    dummy_window.core.config.get.side_effect = lambda key: conf.get(key, None)
    legacy_instance.cmd = MagicMock()
    dummy_ctx = DummyCtx()
    legacy_instance.on_cmd(dummy_ctx, cmds=[])
    legacy_instance.cmd.assert_called_with(dummy_ctx, [], None)


def test_cmd_finished(legacy_instance, dummy_window):
    # Prepare a valid goal_update cmd with finished status
    dummy_ctx = DummyCtx()
    cmd_item = {
        "cmd": "goal_update",
        "params": {"status": "finished"}
    }
    conf = {"agent.goal.notify": True}
    dummy_window.core.config.get.side_effect = lambda key: conf.get(key, False)
    legacy_instance.on_stop = MagicMock()
    legacy_instance.finished = False
    legacy_instance.cmd(dummy_ctx, [cmd_item])
    legacy_instance.on_stop.assert_called_with(auto=True)
    dummy_window.update_status.assert_called()
    assert legacy_instance.finished is True
    dummy_window.ui.tray.show_msg.assert_called()


def test_cmd_pause(legacy_instance, dummy_window):
    # Test with pause status
    dummy_ctx = DummyCtx()
    cmd_item = {
        "cmd": "goal_update",
        "params": {"status": "pause"}
    }
    conf = {"agent.goal.notify": False}
    dummy_window.core.config.get.side_effect = lambda key: conf.get(key, False)
    legacy_instance.on_stop = MagicMock()
    legacy_instance.finished = False
    legacy_instance.cmd(dummy_ctx, [cmd_item])
    legacy_instance.on_stop.assert_called_with(auto=True)
    dummy_window.update_status.assert_called()
    assert legacy_instance.finished is True


def test_is_inline(legacy_instance, dummy_window):
    dummy_window.controller.plugins.is_type_enabled.return_value = True
    assert legacy_instance.is_inline() is True
    dummy_window.controller.plugins.is_type_enabled.return_value = False
    assert legacy_instance.is_inline() is False


def test_enabled(legacy_instance, dummy_window):
    # No inline: check mode equals MODE_AGENT
    dummy_window.core.config.get.side_effect = lambda key: MODE_AGENT if key == 'mode' else None
    assert legacy_instance.enabled(check_inline=False) is True
    # With inline: simulate inline enabled
    dummy_window.controller.plugins.is_type_enabled.return_value = True
    assert legacy_instance.enabled() is True
    # Neither agent mode nor inline enabled
    dummy_window.core.config.get.side_effect = lambda key: "other" if key == 'mode' else None
    dummy_window.controller.plugins.is_type_enabled.return_value = False
    assert legacy_instance.enabled() is False


def test_add_run(legacy_instance):
    legacy_instance.iteration = 5
    legacy_instance.add_run()
    assert legacy_instance.iteration == 6


def test_on_stop(legacy_instance, dummy_window):
    legacy_instance.iteration = 7
    legacy_instance.prev_output = "something"
    legacy_instance.stop = False
    legacy_instance.finished = True
    legacy_instance.on_stop(auto=True)
    dummy_window.controller.kernel.stack.lock.assert_called()
    dummy_window.controller.chat.common.unlock_input.assert_called()
    assert legacy_instance.iteration == 0
    assert legacy_instance.prev_output is None
    assert legacy_instance.stop is True
    assert legacy_instance.finished is False
    dummy_window.controller.idx.on_ctx_end.assert_called_with(ctx=None, mode="agent")


def test_hook_update(legacy_instance, dummy_window):
    # When value is unchanged nothing happens.
    dummy_window.core.config.get.side_effect = lambda key: 10 if key == "agent.iterations" else None
    legacy_instance.update = MagicMock()
    legacy_instance.hook_update("agent.iterations", 10, caller="test")
    # No update if equal
    legacy_instance.update.assert_not_called()
    # When different, update config and call update
    legacy_instance.hook_update("agent.iterations", "15", caller="test")
    dummy_window.core.config.set.assert_called_with("agent.iterations", 15)
    dummy_window.core.config.save.assert_called()
    legacy_instance.update.assert_called()