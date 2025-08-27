#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.28 00:00:00                  #
# ================================================== #

import pytest

from pygpt_net.controller.agent.llama import Llama
import pygpt_net.controller.agent.llama as llama_module


class FakeCheckBox:
    def __init__(self):
        self.checked = None
        self.calls = []

    def setChecked(self, val):
        self.checked = bool(val)
        self.calls.append(val)


class FakeTray:
    def __init__(self):
        self.msg_calls = []

    def show_msg(self, title, content):
        self.msg_calls.append((title, content))


class FakeUI:
    def __init__(self):
        self.hooks = []
        self.config = {'global': {'agent.llama.loop.enabled': FakeCheckBox()}}
        self.tray = FakeTray()

    def add_hook(self, name, cb):
        self.hooks.append((name, cb))


class FakeCoreConfig:
    def __init__(self, store=None):
        self.store = store or {}
        self.set_calls = []
        self.save_calls = 0

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.set_calls.append((key, value))
        self.store[key] = value

    def save(self):
        self.save_calls += 1


class FakeCtxStore:
    def __init__(self, all_return=None):
        self.all_return = all_return if all_return is not None else []
        self.all_calls = []

    def all(self, meta_id):
        self.all_calls.append(meta_id)
        return self.all_return


class FakeCore:
    def __init__(self, config=None, ctx=None):
        self.config = config or FakeCoreConfig()
        self.ctx = ctx or FakeCtxStore()


class FakeControllerConfig:
    def __init__(self):
        self.apply_calls = []

    def apply_value(self, parent_id, key, option, value):
        self.apply_calls.append((parent_id, key, option, value))


class FakePresets:
    def __init__(self, is_bot=False):
        self._is_bot = is_bot

    def is_bot(self):
        return self._is_bot


class FakeKernel:
    def __init__(self, stopped=False):
        self._stopped = stopped

    def stopped(self):
        return self._stopped


class FakeController:
    def __init__(self):
        self.config = FakeControllerConfig()
        self.presets = FakePresets()
        self.kernel = FakeKernel()


class FakeWindow:
    def __init__(self, store=None):
        self.ui = FakeUI()
        self.core = FakeCore(FakeCoreConfig(store or {}), FakeCtxStore())
        self.controller = FakeController()
        self.dispatched = []
        self.status = []

    def update_status(self, msg):
        self.status.append(msg)

    def dispatch(self, event):
        self.dispatched.append(event)


class DummyMeta:
    def __init__(self, id_):
        self.id = id_


class DummyCtx:
    def __init__(self, id_):
        self.meta = DummyMeta(id_)


class FakeKernelEvent:
    STATE_IDLE = "STATE_IDLE"
    REQUEST_NEXT = "REQUEST_NEXT"

    def __init__(self, name, data):
        self.name = name
        self.data = data


def fake_trans(key):
    return f"tr:{key}"


@pytest.mark.parametrize("enabled", [True, False])
def test_reload_applies_values_and_checkbox(enabled):
    store = {
        'agent.llama.loop.enabled': enabled,
        'agent.llama.loop.score': 83,
        'agent.llama.loop.mode': 'score',
    }
    w = FakeWindow(store=store)
    llama = Llama(w)
    llama.reload()
    assert w.ui.config['global']['agent.llama.loop.enabled'].checked == enabled
    assert len(w.controller.config.apply_calls) == 2
    keys = {call[1] for call in w.controller.config.apply_calls}
    assert 'agent.llama.loop.score' in keys
    assert 'agent.llama.loop.mode' in keys
    for call in w.controller.config.apply_calls:
        if call[1] == 'agent.llama.loop.score':
            assert call[3] == 83
            assert call[2] == llama.options['agent.llama.loop.score']
        if call[1] == 'agent.llama.loop.mode':
            assert call[3] == 'score'
            assert call[2] == llama.options['agent.llama.loop.mode']


def test_setup_registers_hooks_and_calls_reload(monkeypatch):
    w = FakeWindow()
    llama = Llama(w)
    called = {'n': 0}

    def fake_reload():
        called['n'] += 1

    monkeypatch.setattr(llama, 'reload', fake_reload)
    llama.setup()
    assert called['n'] == 1
    assert len(w.ui.hooks) == 2
    assert w.ui.hooks[0][0] == "update.global.agent.llama.loop.score"
    assert w.ui.hooks[1][0] == "update.global.agent.llama.loop.mode"
    assert w.ui.hooks[0][1] == llama.hook_update
    assert w.ui.hooks[1][1] == llama.hook_update


def test_init_defaults():
    llama = Llama()
    assert llama.get_eval_step() == 0
    assert 'agent.llama.loop.score' in llama.options
    assert 'agent.llama.loop.mode' in llama.options
    assert llama.options['agent.llama.loop.score']['type'] == 'int'
    keys = llama.options['agent.llama.loop.mode']['keys']
    all_keys = set()
    for d in keys:
        all_keys.update(d.keys())
    assert 'complete' in all_keys
    assert 'score' in all_keys


def test_reset_eval_step_and_next_and_get():
    llama = Llama()
    assert llama.get_eval_step() == 0
    llama.eval_step_next()
    assert llama.get_eval_step() == 1
    llama.reset_eval_step()
    assert llama.get_eval_step() == 0


def test_on_user_send_resets_eval_step():
    w = FakeWindow()
    llama = Llama(w)
    llama.eval_step = 5
    llama.on_user_send("x")
    assert llama.get_eval_step() == 0


@pytest.mark.parametrize(
    "notify,mode,expect_show",
    [
        (True, "not-llama", True),
        (True, "llama-mode", False),
        (False, "whatever", False),
    ],
)
def test_on_end_dispatch_and_notify(monkeypatch, notify, mode, expect_show):
    monkeypatch.setattr(llama_module, "KernelEvent", FakeKernelEvent)
    monkeypatch.setattr(llama_module, "MODE_LLAMA_INDEX", "llama-mode")
    monkeypatch.setattr(llama_module, "trans", fake_trans)
    w = FakeWindow(store={'agent.goal.notify': notify, 'mode': mode})
    llama = Llama(w)
    llama.eval_step = 3
    llama.on_end()
    assert llama.get_eval_step() == 0
    assert len(w.dispatched) == 1
    ev = w.dispatched[0]
    assert isinstance(ev, FakeKernelEvent)
    assert ev.name == FakeKernelEvent.STATE_IDLE
    assert ev.data == {"id": "agent"}
    if expect_show:
        assert len(w.ui.tray.msg_calls) == 1
        title, content = w.ui.tray.msg_calls[0]
        assert title == "tr:notify.agent.goal.title"
        assert content == "tr:notify.agent.goal.content"
    else:
        assert len(w.ui.tray.msg_calls) == 0


@pytest.mark.parametrize("case", ["loop_disabled", "is_bot", "stopped"])
def test_on_finish_aborts_paths(monkeypatch, case):
    store = {
        'agent.llama.loop.enabled': case != "loop_disabled",
        'agent.llama.max_eval': 10,
    }
    w = FakeWindow(store=store)
    w.controller.presets._is_bot = case == "is_bot"
    w.controller.kernel._stopped = case == "stopped"
    llama = Llama(w)
    called = {'n': 0}

    def fake_on_end():
        called['n'] += 1

    monkeypatch.setattr(llama, 'on_end', fake_on_end)
    ctx = DummyCtx("mid")
    llama.on_finish(ctx)
    assert called['n'] == 1
    assert len(w.dispatched) == 0


def test_on_finish_max_steps_reached(monkeypatch):
    store = {
        'agent.llama.loop.enabled': True,
        'agent.llama.max_eval': 2,
    }
    w = FakeWindow(store=store)
    llama = Llama(w)
    llama.eval_step = 2
    called = {'n': 0}

    def fake_on_end():
        called['n'] += 1

    monkeypatch.setattr(llama, 'on_end', fake_on_end)
    ctx = DummyCtx("m1")
    llama.on_finish(ctx)
    assert called['n'] == 1
    assert w.status[-1] == "Stopped. Limit of max steps: 2"
    assert len(w.dispatched) == 0


def test_on_finish_success_flow_dispatches_request_next(monkeypatch):
    monkeypatch.setattr(llama_module, "KernelEvent", FakeKernelEvent)
    monkeypatch.setattr(llama_module, "trans", fake_trans)
    store = {
        'agent.llama.loop.enabled': True,
        'agent.llama.max_eval': 0,
    }
    w = FakeWindow(store=store)
    w.core.ctx.all_return = ["h1", "h2"]
    llama = Llama(w)
    ctx = DummyCtx("meta123")
    llama.on_finish(ctx)
    assert llama.get_eval_step() == 1
    assert w.status[-1] == "tr:status.evaluating"
    assert len(w.dispatched) == 1
    ev = w.dispatched[0]
    assert isinstance(ev, FakeKernelEvent)
    assert ev.name == FakeKernelEvent.REQUEST_NEXT
    assert 'context' in ev.data and 'extra' in ev.data
    br_ctx = ev.data['context']
    assert getattr(br_ctx, 'ctx') is ctx
    assert getattr(br_ctx, 'history') == ["h1", "h2"]
    assert ev.data['extra'] == {}
    assert w.core.ctx.all_calls == ["meta123"]


def test_hook_update_no_change_score(monkeypatch):
    w = FakeWindow(store={'agent.llama.loop.score': 77})
    llama = Llama(w)
    called = {'n': 0}

    def fake_update():
        called['n'] += 1

    monkeypatch.setattr(llama, 'update', fake_update)
    llama.hook_update('agent.llama.loop.score', 77, 'caller')
    assert w.core.config.save_calls == 0
    assert len(w.core.config.set_calls) == 0
    assert called['n'] == 0


def test_hook_update_no_change_mode(monkeypatch):
    w = FakeWindow(store={'agent.llama.loop.mode': 'score'})
    llama = Llama(w)
    called = {'n': 0}

    def fake_update():
        called['n'] += 1

    monkeypatch.setattr(llama, 'update', fake_update)
    llama.hook_update('agent.llama.loop.mode', 'score', 'caller')
    assert w.core.config.save_calls == 0
    assert len(w.core.config.set_calls) == 0
    assert called['n'] == 0


def test_hook_update_score_changes(monkeypatch):
    w = FakeWindow(store={'agent.llama.loop.score': 10})
    llama = Llama(w)
    called = {'n': 0}

    def fake_update():
        called['n'] += 1

    monkeypatch.setattr(llama, 'update', fake_update)
    llama.hook_update('agent.llama.loop.score', '88', 'caller')
    assert w.core.config.set_calls == [('agent.llama.loop.score', 88)]
    assert w.core.config.save_calls == 1
    assert called['n'] == 1


def test_hook_update_mode_changes(monkeypatch):
    w = FakeWindow(store={'agent.llama.loop.mode': 'complete'})
    llama = Llama(w)
    called = {'n': 0}

    def fake_update():
        called['n'] += 1

    monkeypatch.setattr(llama, 'update', fake_update)
    llama.hook_update('agent.llama.loop.mode', 'score', 'caller')
    assert w.core.config.set_calls == [('agent.llama.loop.mode', 'score')]
    assert w.core.config.save_calls == 1
    assert called['n'] == 1


def test_noop_methods():
    w = FakeWindow()
    llama = Llama(w)
    llama.on_stop()
    llama.update()