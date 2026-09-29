import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pygpt_net


def load_reasoning_module():
    path = Path(pygpt_net.__file__).parent / "provider" / "api" / "reasoning.py"
    spec = importlib.util.spec_from_file_location("pygpt_reasoning_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load_reasoning_module()


def test_is_tagged_reasoning_model_detects_supported_backends():
    assert r.is_tagged_reasoning_model(None) is False
    assert r.is_tagged_reasoning_model(SimpleNamespace(is_ollama=lambda: True)) is True
    assert r.is_tagged_reasoning_model(SimpleNamespace(is_ollama=lambda: False, provider=" LOCAL_AI ")) is True
    assert r.is_tagged_reasoning_model(SimpleNamespace(is_ollama=lambda: False, provider="x", llama_index={"provider": "my_ollama"})) is True
    assert r.is_tagged_reasoning_model(SimpleNamespace(is_ollama=lambda: False, provider="x", llama_index={"provider": "remote"})) is False


def test_is_tagged_reasoning_model_tolerates_broken_probe():
    class Model:
        provider = "remote"
        llama_index = None
        def is_ollama(self):
            raise RuntimeError("probe failed")
    assert r.is_tagged_reasoning_model(Model()) is False


def test_extract_tagged_reasoning_handles_plain_complete_multiple_and_partial():
    assert r.extract_tagged_reasoning(None) == ("", "")
    assert r.extract_tagged_reasoning("answer") == ("answer", "")
    assert r.extract_tagged_reasoning("<think>reason</think>\n\nanswer") == ("answer", "reason")
    assert r.extract_tagged_reasoning("A<think>one</think>B<think>two</think>C") == ("ABC", "one\n\ntwo")
    assert r.extract_tagged_reasoning("before<think>unfinished") == ("before", "unfinished")
    assert r.extract_tagged_reasoning("orphan</think>") == ("orphan</think>", "")


def test_extract_tagged_reasoning_strips_only_leading_separator_variants():
    for sep in ("\n", "\r\n", "\n\n", "\r\n\r\n"):
        answer, reasoning = r.extract_tagged_reasoning(f"<think>x</think>{sep}answer")
        assert answer == "answer"
        assert reasoning == "x"
    answer, _ = r.extract_tagged_reasoning("prefix<think>x</think>\n\nanswer")
    assert answer == "prefix\n\nanswer"


def test_strip_and_store_tagged_reasoning_normalizes_extra():
    ctx = SimpleNamespace(extra=None)
    cleaned = r.strip_and_store_tagged_reasoning(ctx, "<think>hidden</think>\n\nvisible", provider="ollama")
    assert cleaned == "visible"
    assert ctx.extra["reasoning"] == {
        "provider": "ollama",
        "type": "thinking",
        "text": "hidden",
        "raw": True,
        "visible": True,
        "encrypted": False,
    }


def test_stream_reasoning_lifecycle_and_stripping():
    state = SimpleNamespace()
    assert r.stream_reasoning_delta(state, None, "p") is None
    assert r.stream_reasoning_delta(state, "", "p") is None
    assert r.stream_reasoning_delta(state, "one", "p", kind="thinking", raw=True) == "<think>one"
    assert r.stream_reasoning_delta(state, " two", "p", kind="thinking", raw=True) == " two"
    assert r.close_stream_reasoning(state) == "</think>\n\n"
    first_block = state.reasoning_display_blocks[0]
    assert first_block == "<think>one two</think>\n\n"

    assert r.stream_reasoning_delta(state, "three", "p") == "<think>three"
    assert state.reasoning_buffer.getvalue() == "one two\n\nthree"
    text = r.stream_text_delta(state, "answer")
    assert text == "</think>\n\nanswer"
    rendered = first_block + "answer " + state.reasoning_display_blocks[1]
    assert r.strip_stream_reasoning(rendered, state) == "answer "


def test_close_and_stream_text_noop_paths():
    state = SimpleNamespace(reasoning_open=False)
    assert r.close_stream_reasoning(state) == ""
    assert r.stream_text_delta(state, None) is None
    assert r.stream_text_delta(state, "") is None
    assert r.stream_text_delta(state, "x") == "x"
    assert r.strip_stream_reasoning("", state) == ""


def test_close_reasoning_without_display_buffer():
    state = SimpleNamespace(reasoning_open=True, reasoning_display_buffer=None)
    assert r.close_stream_reasoning(state) == ""
    assert state.reasoning_open is False


def test_store_reasoning_preserves_existing_dict_and_coerces_tokens():
    ctx = SimpleNamespace(extra={"other": 1, "reasoning": {"old": True}})
    r.store_reasoning(ctx, "anthropic", "  summary  ", kind="summary", reasoning_tokens="12")
    assert ctx.extra["other"] == 1
    data = ctx.extra["reasoning"]
    assert data["old"] is True
    assert data["text"] == "summary"
    assert data["tokens"] == 12
    assert data["visible"] is True

    r.store_reasoning(ctx, None, "", kind="", visible=True, reasoning_tokens="bad")
    assert data["provider"] == ""
    assert data["type"] == "summary"
    assert data["visible"] is False
    assert data["tokens"] == 12


def test_ensure_reasoning_metadata_updates_text_reasoning_or_creates_hidden():
    ctx = SimpleNamespace(extra={"reasoning": {"text": "summary"}})
    r.ensure_reasoning_metadata(ctx, "openai", "7")
    assert ctx.extra["reasoning"]["tokens"] == 7

    hidden = SimpleNamespace(extra={})
    r.ensure_reasoning_metadata(hidden, "openai", 9)
    assert hidden.extra["reasoning"]["type"] == "hidden"
    assert hidden.extra["reasoning"]["tokens"] == 9
    assert hidden.extra["reasoning"]["visible"] is False


def test_ensure_reasoning_metadata_ignores_non_positive_and_invalid():
    for value in (None, 0, -1, "bad"):
        ctx = SimpleNamespace(extra={})
        r.ensure_reasoning_metadata(ctx, "x", value)
        assert ctx.extra == {}


def test_persist_stream_reasoning_uses_timestamp_free_usage_metadata():
    ctx = SimpleNamespace(extra={})
    state = SimpleNamespace(
        reasoning_buffer=r.io.StringIO("summary"),
        reasoning_provider="google",
        reasoning_kind="summary",
        reasoning_raw=False,
        usage_payload={"reasoning": 13},
    )
    r.persist_stream_reasoning(ctx, state)
    assert ctx.extra["reasoning"]["text"] == "summary"
    assert ctx.extra["reasoning"]["tokens"] == 13


def test_persist_stream_reasoning_ignores_missing_empty_or_broken_buffer():
    ctx = SimpleNamespace(extra={})
    r.persist_stream_reasoning(ctx, SimpleNamespace())
    assert ctx.extra == {}
    r.persist_stream_reasoning(ctx, SimpleNamespace(reasoning_buffer=r.io.StringIO("  ")))
    assert ctx.extra == {}
    broken = SimpleNamespace(reasoning_buffer=SimpleNamespace(getvalue=lambda: (_ for _ in ()).throw(RuntimeError())))
    r.persist_stream_reasoning(ctx, broken)
    assert ctx.extra == {}


def test_cleanup_stream_reasoning_closes_buffers_and_clears_blocks():
    a, b = r.io.StringIO("a"), r.io.StringIO("b")
    state = SimpleNamespace(reasoning_buffer=a, reasoning_display_buffer=b, reasoning_display_blocks=["x"])
    r.cleanup_stream_reasoning(state)
    assert a.closed and b.closed
    assert state.reasoning_buffer is None
    assert state.reasoning_display_buffer is None
    assert state.reasoning_display_blocks == []
