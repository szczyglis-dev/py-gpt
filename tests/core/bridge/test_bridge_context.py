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

import importlib
import json
import pytest
from unittest.mock import Mock

def get_mod():
    return importlib.import_module("pygpt_net.core.bridge.context")

def test_multimodal_to_dict_defaults():
    mod = get_mod()
    mc = mod.MultimodalContext()
    assert mc.to_dict() == {
        "is_audio_input": False,
        "is_audio_output": False,
        "audio_format": "wav",
    }

def test_multimodal_to_dict_custom_values():
    mod = get_mod()
    mc = mod.MultimodalContext(is_audio_input=True, is_audio_output=True, audio_format="mp3")
    assert mc.to_dict() == {
        "audio_format": "mp3",
        "is_audio_input": True,
        "is_audio_output": True,
    }

def test_bridgecontext_init_raises_for_invalid_ctx():
    mod = get_mod()
    with pytest.raises(ValueError) as exc:
        mod.BridgeContext(ctx=object())
    assert "Invalid context instance" in str(exc.value)

def test_bridgecontext_init_raises_for_invalid_model():
    mod = get_mod()
    with pytest.raises(ValueError) as exc:
        mod.BridgeContext(model=object())
    assert "Invalid model instance" in str(exc.value)

def test_bridgecontext_accepts_valid_ctx_model(monkeypatch):
    mod = get_mod()
    class DummyCtx:
        pass
    class DummyModel:
        pass
    monkeypatch.setattr(mod, "CtxItem", DummyCtx, raising=False)
    monkeypatch.setattr(mod, "ModelItem", DummyModel, raising=False)
    mod.BridgeContext(ctx=DummyCtx(), model=DummyModel())

def test_bridgecontext_to_dict_with_ctx_model_and_reply_ctx(monkeypatch):
    mod = get_mod()
    class DummyCtx:
        def __init__(self):
            self._arg = None
        def to_dict(self, arg=False):
            self._arg = arg
            return {"ctx": "ok", "arg": arg}
    class DummyModel:
        def to_dict(self):
            return {"model": "ok"}
    monkeypatch.setattr(mod, "CtxItem", DummyCtx, raising=False)
    monkeypatch.setattr(mod, "ModelItem", DummyModel, raising=False)
    reply = Mock()
    reply.to_dict.return_value = {"reply": True}
    ctx_inst = DummyCtx()
    model_inst = DummyModel()
    bc = mod.BridgeContext(ctx=ctx_inst, model=model_inst, reply_ctx=reply, history=[1, 2, 3], temperature=0.25, stream=True)
    data = bc.to_dict()
    assert data["ctx"] == {"ctx": "ok", "arg": True}
    assert ctx_inst._arg is True
    assert data["model"] == {"model": "ok"}
    assert data["reply_context"] == {"reply": True}
    assert data["history"] == 3
    assert data["temperature"] == 0.25
    assert data["stream"] is True

def test_bridgecontext_to_dict_reply_context_none_by_default():
    mod = get_mod()
    bc = mod.BridgeContext()
    data = bc.to_dict()
    assert data["reply_context"] is None

def test_dump_returns_json_and_handles_exceptions(monkeypatch):
    mod = get_mod()
    bc = mod.BridgeContext(prompt="hello")
    dumped = bc.dump()
    assert isinstance(dumped, str)
    assert json.loads(dumped)["prompt"] == "hello"
    def bad_to_dict(self):
        raise RuntimeError("boom")
    monkeypatch.setattr(mod.BridgeContext, "to_dict", bad_to_dict, raising=True)
    bc2 = mod.BridgeContext()
    assert bc2.dump() == ""
    monkeypatch.setattr(mod.BridgeContext, "dump", lambda self: "DUMPED", raising=True)
    bc3 = mod.BridgeContext()
    assert str(bc3) == "DUMPED"