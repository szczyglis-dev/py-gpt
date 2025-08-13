#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 01:00:00                  #
# ================================================== #

import importlib
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock
import pytest

chat_mod = importlib.import_module("pygpt_net.core.idx.chat")
Chat = chat_mod.Chat

class FakeModelItem:
    def __init__(self, id="fake-model"):
        self.id = id

class FakeCtx:
    def __init__(self, input_text="hi"):
        self.input = input_text
        self.stream = None
        self.input_tokens = None
        self.output_tokens = None
        self.agent_call = False
        self.use_agent_final_response = False
        self._meta = None
        self._output = None
    def add_doc_meta(self, meta):
        self._meta = meta
    def set_output(self, *args):
        self._output = args

class FakeResponseObj:
    def __init__(self, response=None, response_gen=None, source_nodes=None, message=None):
        self.response = response
        self.response_gen = response_gen
        self.source_nodes = source_nodes or []
        self.message = message

class FakeNode:
    def __init__(self, id_, text, score, metadata=None):
        self.id_ = id_
        self.text = text
        self.score = score
        self.metadata = metadata or {}
    def get_score(self):
        return self.score

class FakeContextClass:
    def __init__(self, window):
        self._window = window
    def get_messages(self, *args, **kwargs):
        return []
    def append_images(self, ctx):
        pass
    def add_system(self, prompt):
        return SimpleNamespace(role="system", content=prompt)
    def add_user(self, query, attachments=None):
        return SimpleNamespace(role="user", content=query)

class FakeResponseClass:
    def __init__(self, window):
        self.from_react = Mock()
        self.from_index_stream = Mock()
        self.from_llm_stream = Mock()
        self.from_index = Mock()
        self.from_llm = Mock()

def make_window(config_map=None):
    cfg = config_map or {}
    class Config:
        def __init__(self, m):
            self._m = dict(m)
        def get(self, key, default=None):
            return self._m.get(key, default)
        def has(self, key):
            return key in self._m
        def get_user_dir(self, name):
            return "/tmp/userdir"
    tokens = SimpleNamespace(from_llama_messages=Mock(return_value="TOKENS"))
    debug = SimpleNamespace(info=Mock())
    idx = SimpleNamespace(
        llm=SimpleNamespace(
            get=Mock(),
            get_service_context=Mock()
        ),
        indexing=SimpleNamespace(
            index_files=Mock(),
            index_urls=Mock()
        )
    )
    models = SimpleNamespace(is_tool_call_allowed=lambda mode, model: True, from_defaults=lambda: FakeModelItem())
    plugins = SimpleNamespace(get_option=lambda a,b: False)
    agents = SimpleNamespace(provider=SimpleNamespace(get=Mock()), tools=SimpleNamespace(prepare=Mock()), runner=SimpleNamespace(llama_workflow=SimpleNamespace(run=Mock())))
    return SimpleNamespace(core=SimpleNamespace(config=Config(cfg), tokens=tokens, debug=debug, idx=idx, models=models, plugins=plugins, agents=agents), idx_logger_message=Mock())

def make_chat(monkeypatch, config_map=None, storage=None):
    monkeypatch.setattr(chat_mod, "Context", FakeContextClass)
    monkeypatch.setattr(chat_mod, "Response", FakeResponseClass)
    win = make_window(config_map=config_map)
    storage = storage or Mock()
    return Chat(window=win, storage=storage)

def test_init_creates_components(monkeypatch):
    monkeypatch.setattr(chat_mod, "Context", FakeContextClass)
    monkeypatch.setattr(chat_mod, "Response", FakeResponseClass)
    win = make_window()
    storage = Mock()
    c = Chat(window=win, storage=storage)
    assert c.window is win
    assert c.storage is storage
    assert c.context is not None
    assert c.response is not None
    assert c.prev_message is None

def test_call_raises_when_model_missing(monkeypatch):
    chat = make_chat(monkeypatch)
    context = SimpleNamespace(model=None, idx_mode="chat")
    with pytest.raises(Exception) as exc:
        chat.call(context)
    assert "Model config not provided" in str(exc.value)

def test_call_routes_to_raw_and_retrieval(monkeypatch):
    chat = make_chat(monkeypatch)
    monkeypatch.setattr(chat_mod, "ModelItem", FakeModelItem)
    ctx = SimpleNamespace(model=FakeModelItem(), idx_mode="query")
    chat.raw_query = Mock(return_value=True)
    chat.retrieval = Mock(return_value=True)
    chat.chat = Mock(return_value=True)
    r = chat.call(ctx)
    assert r is True
    chat.raw_query.assert_called_once_with(context=ctx, extra=None)
    ctx.idx_mode = "retrieval"
    r2 = chat.call(ctx)
    assert r2 is True
    chat.retrieval.assert_called()

def test_raw_query_calls_query(monkeypatch):
    chat = make_chat(monkeypatch)
    chat.query = Mock(return_value=True)
    ctx = SimpleNamespace()
    assert chat.raw_query(ctx) is True
    chat.query.assert_called_once_with(context=ctx, extra=None)

def test_query_stream_true_and_false(monkeypatch):
    chat = make_chat(monkeypatch)
    monkeypatch.setattr(chat_mod, "ModelItem", FakeModelItem)
    chat.get_custom_prompt = Mock(return_value=None)
    chat.get_metadata = Mock(return_value={"m":"v"})
    ctx_item = FakeCtx("hello")
    context = SimpleNamespace(idx="idx", model=FakeModelItem(), system_prompt_raw="sys", stream=True, ctx=ctx_item)
    index = Mock()
    engine = Mock()
    resp = FakeResponseObj(response=None, response_gen="GEN", source_nodes=[FakeNode("id1","t",0.9,{"k":"v"})])
    engine.query = Mock(return_value=resp)
    index.as_query_engine = Mock(return_value=engine)
    llm = Mock()
    chat.get_index = Mock(return_value=(index, llm))
    chat.window.core.tokens.from_llama_messages = Mock(return_value=123)
    r = chat.query(context)
    assert r is True
    assert ctx_item._meta == {"m":"v"}
    assert ctx_item.stream == "GEN"
    assert ctx_item.input_tokens == 123
    ctx_item2 = FakeCtx("hey")
    context2 = SimpleNamespace(idx="idx", model=FakeModelItem(), system_prompt_raw="sys", stream=False, ctx=ctx_item2)
    resp2 = FakeResponseObj(response="ANSWER", response_gen=None, source_nodes=[FakeNode("id2","tx",0.8,{"k":"v"})])
    engine.query = Mock(return_value=resp2)
    r2 = chat.query(context2)
    assert r2 is True
    assert ctx_item2._meta == {"m":"v"}
    assert ctx_item2.input_tokens == 123
    assert ctx_item2._output == ("ANSWER", "")

def test_query_returns_false_when_no_response(monkeypatch):
    chat = make_chat(monkeypatch)
    monkeypatch.setattr(chat_mod, "ModelItem", FakeModelItem)
    ctx_item = FakeCtx("x")
    context = SimpleNamespace(idx="idx", model=FakeModelItem(), system_prompt_raw="", stream=False, ctx=ctx_item)
    index = Mock()
    engine = Mock()
    engine.query = Mock(return_value=None)
    index.as_query_engine = Mock(return_value=engine)
    chat.get_index = Mock(return_value=(index, Mock()))
    r = chat.query(context)
    assert r is False

def test_retrieval_builds_output_and_metadata(monkeypatch):
    chat = make_chat(monkeypatch)
    ctx_item = FakeCtx("q")
    context = SimpleNamespace(idx="idx", model=FakeModelItem(), stream=False, ctx=ctx_item)
    node1 = SimpleNamespace(text="T1", score=0.9)
    node2 = SimpleNamespace(text="T2", score=0.5)
    retriever = SimpleNamespace(retrieve=Mock(return_value=[node1, node2]))
    index = SimpleNamespace(as_retriever=Mock(return_value=retriever))
    llm = Mock()
    chat.get_index = Mock(return_value=(index, llm))
    chat.get_metadata = Mock(return_value={"m": "v"})
    res = chat.retrieval(context)
    assert res is True
    assert "**Score: 0.9**" in ctx_item._output[0]
    assert ctx_item._meta == {"m": "v"}

def test_is_stream_allowed_behavior(monkeypatch):
    chat = make_chat(monkeypatch)
    win = chat.window
    win.core.config._m.update({"cmd": True, "llama.idx.react": True})
    assert chat.is_stream_allowed() is False
    win.core.config._m.update({"cmd": False, "llama.idx.react": True})
    assert chat.is_stream_allowed() is True

def test_query_file_indexes_and_cleans_tmp(monkeypatch):
    storage = Mock()
    tmp_id = "tmp123"
    index = Mock()
    storage.get_tmp = Mock(return_value=(tmp_id, index))
    storage.clean_tmp = Mock()
    chat = make_chat(monkeypatch, storage=storage)
    monkeypatch.setattr(chat_mod, "ModelItem", FakeModelItem)
    win = chat.window
    llm = Mock()
    embed = Mock()
    win.core.idx.llm.get_service_context = Mock(return_value=(llm, embed))
    win.core.idx.indexing.index_files = Mock(return_value=(["f1"], []))
    engine = Mock()
    engine.query = Mock(return_value=FakeResponseObj(response="OUT", source_nodes=[FakeNode("id","t",0.9,{"k":"v"})]))
    index.as_query_engine = Mock(return_value=engine)
    chat.get_metadata = Mock(return_value={"m":"v"})
    ctx = FakeCtx()
    out = chat.query_file(ctx=ctx, path="p", query="q", model=FakeModelItem())
    assert out == "OUT"
    storage.clean_tmp.assert_called_once_with(tmp_id)

def test_query_file_returns_none_when_no_files(monkeypatch):
    storage = Mock()
    tmp_id = "tmpX"
    index = Mock()
    storage.get_tmp = Mock(return_value=(tmp_id, index))
    storage.clean_tmp = Mock()
    chat = make_chat(monkeypatch, storage=storage)
    win = chat.window
    win.core.idx.llm.get_service_context = Mock(return_value=(Mock(), Mock()))
    win.core.idx.indexing.index_files = Mock(return_value=([], []))
    ctx = FakeCtx()
    out = chat.query_file(ctx=ctx, path="p", query="q", model=FakeModelItem())
    assert out is None
    storage.clean_tmp.assert_called_once_with(tmp_id)

def test_query_web_indexes_and_cleans_tmp(monkeypatch):
    storage = Mock()
    tmp_id = "tmpw"
    index = Mock()
    storage.get_tmp = Mock(return_value=(tmp_id, index))
    storage.clean_tmp = Mock()
    chat = make_chat(monkeypatch, storage=storage)
    win = chat.window
    llm = Mock()
    embed = Mock()
    win.core.idx.llm.get_service_context = Mock(return_value=(llm, embed))
    win.core.idx.indexing.index_urls = Mock(return_value=(1, []))
    engine = Mock()
    engine.query = Mock(return_value=FakeResponseObj(response="WOUT", source_nodes=[FakeNode("id","t",0.9,{"k":"v"})]))
    index.as_query_engine = Mock(return_value=engine)
    ctx = FakeCtx()
    out = chat.query_web(ctx=ctx, type="html", url="u", args={}, query="q", model=FakeModelItem())
    assert out == "WOUT"
    storage.clean_tmp.assert_called_once_with(tmp_id)

def test_query_retrieval_returns_text_when_found(monkeypatch):
    chat = make_chat(monkeypatch)
    monkeypatch.setattr(chat_mod, "ModelItem", FakeModelItem)
    index = Mock()
    retriever = SimpleNamespace(retrieve=Mock(return_value=[FakeNode("nid","TXT",0.9)]))
    index.as_retriever = Mock(return_value=retriever)
    chat.get_index = Mock(return_value=(index, Mock()))
    out = chat.query_retrieval(query="q", idx="i", model=FakeModelItem())
    assert out == "TXT"

def test_get_memory_buffer_uses_chat_memory(monkeypatch):
    chat = make_chat(monkeypatch)
    monkeypatch.setattr(chat_mod, "ChatMemoryBuffer", SimpleNamespace(from_defaults=Mock(return_value="MEMBUF")))
    res = chat.get_memory_buffer(history=["a"], llm="LLM")
    assert res == "MEMBUF"

def test_get_custom_prompt_none_and_nonempty(monkeypatch):
    chat = make_chat(monkeypatch)
    monkeypatch.setattr(chat_mod, "ChatPromptTemplate", lambda msgs: {"msgs": msgs})
    monkeypatch.setattr(chat_mod, "ChatMessage", lambda role, content: {"role": role, "content": content})
    monkeypatch.setattr(chat_mod, "MessageRole", SimpleNamespace(SYSTEM="system", USER="user"))
    assert chat.get_custom_prompt(None) is None
    res = chat.get_custom_prompt("SYS_PROMPT")
    assert isinstance(res, dict)
    assert "msgs" in res

def test_get_index_creates_empty_and_returns_existing(monkeypatch):
    storage = Mock()
    storage.exists = Mock(return_value=False)
    storage.index_from_empty = Mock(return_value="EMPTY_IDX")
    chat = make_chat(monkeypatch, storage=storage)
    monkeypatch.setattr(chat_mod, "ModelItem", FakeModelItem)
    win = chat.window
    win.core.idx.llm.get_service_context = Mock(return_value=("LLM", "EMBED"))
    idx, llm = chat.get_index(None, FakeModelItem(), stream=False)
    assert idx == "EMPTY_IDX"
    storage.exists = Mock(return_value=True)
    storage.get = Mock(return_value="IDX")
    idx2, llm2 = chat.get_index("name", FakeModelItem(), stream=True)
    assert idx2 == "IDX"

def test_get_metadata_filters_and_limits():
    chat = make_chat(lambda m: None) if False else make_chat
    # create instance directly without monkeypatch for this utility method
    chat = make_chat(__import__("pytest").MonkeyPatch().context()) if False else make_chat
    # Use a Chat instance created by monkeypatch fixture for method access
    mp = pytest.MonkeyPatch()
    mp.setattr(chat_mod, "Context", FakeContextClass)
    mp.setattr(chat_mod, "Response", FakeResponseClass)
    win = make_window()
    storage = Mock()
    c = Chat(window=win, storage=storage)
    nodes = [FakeNode(f"id{i}", f"t{i}", 0.9, {"k": i}) for i in range(5)]
    meta = c.get_metadata(nodes)
    assert len(meta) == 3
    assert all("score" in v for v in meta.values())
    mp.undo()
