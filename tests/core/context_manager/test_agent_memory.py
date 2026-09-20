#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from llama_index.core.base.llms.types import (
    AudioBlock,
    CachePoint,
    ChatMessage,
    DocumentBlock,
    ImageBlock,
    TextBlock,
    ToolCallBlock,
    VideoBlock,
)

from pygpt_net.core.context_manager.agent_memory import ContinuationSummaryBlock, SafeAgentMemory
from pygpt_net.core.context_manager.constants import SOURCE_ITEM_KWARG


def test_continuation_aget_returns_runtime_wrapper_and_refreshes_persistent_notes():
    manager = MagicMock()
    manager.get_notes.return_value = "latest notes"
    block = SimpleNamespace(
        persistent=True,
        ctx=object(),
        manager=manager,
        summary="stale",
        _limit=lambda value: value,
        _log=MagicMock(),
    )

    result = asyncio.run(ContinuationSummaryBlock._aget(block))

    assert "<context_continuation_runtime>" in result
    assert "latest notes" in result
    assert block.summary == "latest notes"


def test_continuation_aget_returns_empty_when_no_summary():
    block = SimpleNamespace(
        persistent=False,
        ctx=None,
        manager=MagicMock(),
        summary="",
        _limit=lambda value: value,
        _log=MagicMock(),
    )

    assert asyncio.run(ContinuationSummaryBlock._aget(block)) == ""


def test_continuation_aput_updates_nonpersistent_summary():
    message = ChatMessage(role="user", content="hello")
    block = SimpleNamespace(
        persistent=False,
        ctx=None,
        summary="old",
        _messages_text=lambda messages: "snapshot",
        _merge=AsyncMock(return_value="merged"),
        _limit=lambda value: value,
        _log=MagicMock(),
    )

    asyncio.run(ContinuationSummaryBlock._aput(block, [message]))

    assert block.summary == "merged"
    block._merge.assert_awaited_once_with("old", "snapshot")


def test_continuation_aput_persistent_retries_revision_race_then_saves():
    manager = MagicMock()
    manager.get.side_effect = [
        {"content": "one", "revision": 1},
        {"content": "two", "revision": 2},
    ]
    manager.commit_runtime_summary.side_effect = [None, {"content": "saved"}]
    block = SimpleNamespace(
        persistent=True,
        ctx=object(),
        summary="",
        manager=manager,
        _messages_text=lambda messages: "snapshot",
        _source_floor=lambda messages: 12,
        _merge=AsyncMock(side_effect=["merged one", "merged two"]),
        _limit=lambda value: value,
        _log=MagicMock(),
    )

    asyncio.run(ContinuationSummaryBlock._aput(block, [ChatMessage(role="user", content="x")]))

    assert block.summary == "saved"
    assert manager.commit_runtime_summary.call_count == 2
    assert manager.commit_runtime_summary.call_args_list[0].kwargs == {
        "expected_revision": 1,
        "last_item_id": 12,
    }
    assert manager.commit_runtime_summary.call_args_list[1].kwargs == {
        "expected_revision": 2,
        "last_item_id": 12,
    }


def test_continuation_aput_keeps_canonical_value_after_two_revision_races():
    manager = MagicMock()
    manager.get.side_effect = [
        {"content": "one", "revision": 1},
        {"content": "two", "revision": 2},
    ]
    manager.commit_runtime_summary.return_value = None
    manager.get_notes.return_value = "winner"
    block = SimpleNamespace(
        persistent=True,
        ctx=object(),
        summary="",
        manager=manager,
        _messages_text=lambda messages: "snapshot",
        _source_floor=lambda messages: 1,
        _merge=AsyncMock(return_value="merged"),
        _limit=lambda value: value,
        _log=MagicMock(),
    )

    asyncio.run(ContinuationSummaryBlock._aput(block, [ChatMessage(role="user", content="x")]))

    assert block.summary == "winner"


def test_atruncate_keeps_defensive_prefix():
    block = SimpleNamespace(summary="fallback")

    assert asyncio.run(ContinuationSummaryBlock.atruncate(block, "", 5)) == "fallback"
    long_value = "x" * 2000
    assert len(asyncio.run(ContinuationSummaryBlock.atruncate(block, long_value, 5))) == 1300


def test_merge_uses_llm_response_and_falls_back_on_error():
    manager = MagicMock()
    manager.build_checkpoint_input.side_effect = lambda state, chunk: f"{state}|{chunk}"
    manager.clean_checkpoint_output.side_effect = lambda text: text.strip()
    llm = SimpleNamespace(achat=AsyncMock(side_effect=[
        SimpleNamespace(message=SimpleNamespace(content=" first ")),
        RuntimeError("provider"),
    ]))
    block = SimpleNamespace(
        manager=manager,
        llm=llm,
        max_chars=12000,
        _split_snapshot=lambda snapshot: ["a", "b"],
        _response_text=ContinuationSummaryBlock._response_text,
        _limit=lambda text, keep_latest=False: text,
        _fallback_merge=lambda current, chunk: f"{current}+fallback:{chunk}",
        _log=MagicMock(),
    )

    result = asyncio.run(ContinuationSummaryBlock._merge(block, "old", "snapshot"))

    assert result == "first+fallback:b"
    block._log.assert_called_once()


def test_response_text_supports_message_content_blocks_text_and_fallback():
    assert ContinuationSummaryBlock._response_text(SimpleNamespace(message=SimpleNamespace(content="a"))) == "a"
    response = SimpleNamespace(message=SimpleNamespace(content=None, blocks=[SimpleNamespace(text="b")]))
    assert ContinuationSummaryBlock._response_text(response) == "b"
    assert ContinuationSummaryBlock._response_text(SimpleNamespace(message=None, text="c")) == "c"


def test_message_text_keeps_useful_blocks_and_strips_transport_metadata():
    message = ChatMessage(
        role="assistant",
        blocks=[TextBlock(text="hello"), ImageBlock.model_construct(), CachePoint.model_construct()],
        additional_kwargs={
            "session_id": "internal",
            SOURCE_ITEM_KWARG: 7,
            "provider": "keep",
        },
    )

    value = ContinuationSummaryBlock._message_text(message)

    assert "hello" in value
    assert "<ImageBlock>" in value
    assert "<CachePoint>" in value
    assert "session_id" not in value
    assert SOURCE_ITEM_KWARG not in value
    assert '"provider": "keep"' in value


def test_source_floor_uses_highest_valid_source_item_marker():
    messages = [
        ChatMessage(role="assistant", content="a", additional_kwargs={SOURCE_ITEM_KWARG: "3"}),
        ChatMessage(role="assistant", content="b", additional_kwargs={SOURCE_ITEM_KWARG: 9}),
        ChatMessage(role="assistant", content="c", additional_kwargs={SOURCE_ITEM_KWARG: "bad"}),
    ]

    assert ContinuationSummaryBlock._source_floor(messages) == 9


def test_safe_memory_estimator_counts_text_media_and_serialized_blocks():
    fake = SimpleNamespace(
        tokenizer_fn=lambda text: range(len(str(text))),
        image_token_size_estimate=100,
        audio_token_size_estimate=200,
        video_token_size_estimate=300,
        document_token_size_estimate=400,
    )

    assert SafeAgentMemory._estimate_block(fake, TextBlock(text="abc")) == 3
    assert SafeAgentMemory._estimate_block(fake, ImageBlock.model_construct()) == 100
    assert SafeAgentMemory._estimate_block(fake, AudioBlock.model_construct()) == 200
    assert SafeAgentMemory._estimate_block(fake, VideoBlock.model_construct()) == 300
    assert SafeAgentMemory._estimate_block(fake, DocumentBlock.model_construct()) == 400
    assert SafeAgentMemory._estimate_block(fake, CachePoint.model_construct()) == 0


def test_safe_memory_estimate_message_counts_additional_kwargs_and_framing():
    fake = SimpleNamespace(tokenizer_fn=lambda text: range(len(str(text))))
    fake._estimate_block = lambda block: SafeAgentMemory._estimate_block(fake, block)
    fake.image_token_size_estimate = 100
    fake.audio_token_size_estimate = 200
    fake.video_token_size_estimate = 300
    fake.document_token_size_estimate = 400
    message = ChatMessage(role="user", content="abc", additional_kwargs={"x": 1})

    result = SafeAgentMemory._estimate_message(fake, message)

    assert result >= 8 + 3
    assert result > 11


def test_safe_memory_estimate_token_count_handles_message_and_message_list():
    fake = SimpleNamespace()
    fake._estimate_message = lambda message: 10
    fake._estimate_block = lambda block: 2
    one = ChatMessage(role="user", content="a")
    two = ChatMessage(role="assistant", content="b")

    assert SafeAgentMemory._estimate_token_count(fake, one) == 10
    assert SafeAgentMemory._estimate_token_count(fake, [one, two]) == 20
    assert SafeAgentMemory._estimate_token_count(fake, [TextBlock(text="a"), TextBlock(text="b")]) == 4


def test_split_snapshot_delegates_to_manager_with_minimum_input_budget():
    manager = MagicMock()
    manager.split_checkpoint_snapshot.return_value = ["a"]
    block = SimpleNamespace(manager=manager, model_id="m", summary_input_tokens=10)

    assert ContinuationSummaryBlock._split_snapshot(block, "snapshot") == ["a"]
    manager.split_checkpoint_snapshot.assert_called_once_with("snapshot", "m", 1024)


def test_fallback_merge_preserves_old_state_and_newest_chunk_under_limits():
    manager = MagicMock()
    manager.clip_text_to_tokens.side_effect = lambda value, *args, **kwargs: value
    block = SimpleNamespace(
        max_chars=2000,
        max_tokens=1000,
        model_id="m",
        manager=manager,
    )
    block._limit = lambda text, keep_latest=False: ContinuationSummaryBlock._limit(block, text, keep_latest)

    result = ContinuationSummaryBlock._fallback_merge(block, "old-state", "x" * 3000)

    assert result.startswith("old-state")
    assert "automatic fallback" in result
    assert result.endswith("x" * 100)
    manager.clip_text_to_tokens.assert_called_once()


def test_messages_text_wraps_each_message_with_role_and_index():
    messages = [
        ChatMessage(role="user", content="one"),
        ChatMessage(role="assistant", content="two"),
    ]
    block = SimpleNamespace(_message_text=ContinuationSummaryBlock._message_text)

    value = ContinuationSummaryBlock._messages_text(block, messages)

    assert '<message index="1" role="MessageRole.USER">' in value
    assert '<message index="2" role="MessageRole.ASSISTANT">' in value
    assert "one" in value and "two" in value


def test_object_text_serializes_pydantic_like_objects_and_plain_fallback():
    obj = SimpleNamespace(model_dump=lambda **kwargs: {"x": 1})
    assert ContinuationSummaryBlock._object_text(obj) == '{"x": 1}'

    class Bad:
        def model_dump(self, **kwargs):
            raise RuntimeError("bad")

        def __str__(self):
            return "fallback"

    assert ContinuationSummaryBlock._object_text(Bad()) == "fallback"


def test_safe_memory_aget_strips_internal_transport_metadata_from_copy(monkeypatch):
    from llama_index.core.memory import Memory as BaseMemory

    original = ChatMessage(
        role="assistant",
        content="hello",
        additional_kwargs={"session_id": "s", SOURCE_ITEM_KWARG: 7, "keep": "yes"},
    )

    async def fake_aget(self, input=None, **kwargs):
        return [original]

    monkeypatch.setattr(BaseMemory, "aget", fake_aget)
    memory = SafeAgentMemory.model_construct()

    result = asyncio.run(SafeAgentMemory.aget(memory))

    assert result[0] is not original
    assert result[0].additional_kwargs == {"keep": "yes"}
    assert original.additional_kwargs["session_id"] == "s"
    assert original.additional_kwargs[SOURCE_ITEM_KWARG] == 7


def test_safe_memory_aput_spills_oversized_message_to_long_term_block(monkeypatch):
    from llama_index.core.memory import Memory as BaseMemory

    stored = []

    async def fake_base_aput(self, message):
        stored.append(message)

    monkeypatch.setattr(BaseMemory, "aput", fake_base_aput)
    monkeypatch.setattr(SafeAgentMemory, "_estimate_token_count", lambda self, message: 900)
    long_term = SimpleNamespace(accept_short_term_memory=True, aput=AsyncMock())
    memory = SafeAgentMemory.model_construct(
        token_limit=1000,
        single_message_ratio=0.45,
        memory_blocks=[long_term],
        session_id="session",
    )
    message = ChatMessage(
        role="assistant",
        content="large",
        additional_kwargs={"session_id": "internal", "keep": "yes"},
    )

    asyncio.run(SafeAgentMemory.aput(memory, message))

    long_term.aput.assert_awaited_once()
    assert len(stored) == 1
    marker = stored[0]
    assert "compacted one oversized message" in marker.content
    assert marker.additional_kwargs == {"keep": "yes"}


def test_safe_memory_aput_delegates_normally_when_message_fits(monkeypatch):
    from llama_index.core.memory import Memory as BaseMemory

    stored = []

    async def fake_base_aput(self, message):
        stored.append(message)

    monkeypatch.setattr(BaseMemory, "aput", fake_base_aput)
    monkeypatch.setattr(SafeAgentMemory, "_estimate_token_count", lambda self, message: 10)
    memory = SafeAgentMemory.model_construct(
        token_limit=1000,
        single_message_ratio=0.45,
        memory_blocks=[],
        session_id="session",
    )
    message = ChatMessage(role="user", content="small")

    asyncio.run(SafeAgentMemory.aput(memory, message))

    assert stored == [message]


def test_safe_memory_aput_messages_routes_every_seed_message_through_safe_path():
    fake = SimpleNamespace(aput=AsyncMock())
    messages = [ChatMessage(role="user", content="a"), ChatMessage(role="assistant", content="b")]

    asyncio.run(SafeAgentMemory.aput_messages(fake, messages))

    assert fake.aput.await_count == 2
    assert [call.args[0] for call in fake.aput.await_args_list] == messages
