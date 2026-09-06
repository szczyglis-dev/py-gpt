#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from unittest.mock import patch

from pygpt_net.item.ctx import (
    CtxGroup,
    CtxItem,
    CtxMeta,
    _additional_ctx_archive_key,
    get_additional_ctx_display_names,
    group_additional_ctx_items,
)


def test_additional_ctx_archive_key_supports_current_and_legacy_formats():
    assert _additional_ctx_archive_key("not-a-dict") is None
    assert _additional_ctx_archive_key({}) is None
    assert _additional_ctx_archive_key({"archive_id": 12}) == ("archive_id", "12")

    legacy = {
        "stored_name": "inside.txt",
        "real_path": os.path.join("tmp", "archive.zip"),
        "path": os.path.join("tmp", "unpacked", "inside.txt"),
    }
    assert _additional_ctx_archive_key(legacy) == (
        "archive_path",
        os.path.normcase(os.path.normpath(legacy["real_path"])),
    )
    assert _additional_ctx_archive_key({
        "stored_name": "archive.zip",
        "real_path": "archive.zip",
        "path": "archive.zip",
    }) is None


def test_group_additional_ctx_items_keeps_order_and_groups_archive_members():
    plain_a = {"name": "a.txt"}
    zip_a = {"name": "one.txt", "archive_id": "z1"}
    plain_b = {"name": "b.txt"}
    zip_b = {"name": "two.txt", "archive_id": "z1"}
    other_zip = {"name": "x.txt", "archive_id": "z2"}

    groups = group_additional_ctx_items([plain_a, zip_a, plain_b, zip_b, other_zip])
    assert groups == [
        {"archive": False, "items": [plain_a]},
        {"archive": True, "items": [zip_a, zip_b]},
        {"archive": False, "items": [plain_b]},
        {"archive": True, "items": [other_zip]},
    ]
    assert group_additional_ctx_items(None) == []


def test_get_additional_ctx_display_names_handles_native_and_archives():
    items = [
        {"name": "plain.txt"},
        {"name": "native.pdf", "native": True},
        {
            "name": "a.txt",
            "archive_id": "z1",
            "archive_name": "bundle.zip",
            "native": True,
        },
        {
            "name": "b.txt",
            "archive_id": "z1",
            "archive_name": "bundle.zip",
            "native": False,
        },
        {
            "name": "c.txt",
            "archive_id": "z2",
            "real_path": "/tmp/all-native.tar",
            "native": True,
        },
    ]
    assert get_additional_ctx_display_names(items) == [
        "plain.txt",
        "native.pdf (Native)",
        "bundle.zip (2 files) (1 Native)",
        "all-native.tar (1 file) (Native)",
    ]


def test_ctx_item_integrity_and_mode():
    item = CtxItem(mode="chat")
    assert item.id is None
    assert item.meta_id is None
    assert item.external_id is None
    assert item.stream is None
    assert item.cmds == []
    assert item.results == []
    assert item.urls == []
    assert item.images == []
    assert item.files == []
    assert item.attachments == []
    assert item.reply is False
    assert item.input is None
    assert item.output is None
    assert item.mode == "chat"
    assert item.model is None
    assert item.input_timestamp is None
    assert item.output_timestamp is None
    assert item.input_tokens == 0
    assert item.output_tokens == 0
    assert item.total_tokens == 0
    assert item.extra == {}
    assert item.current is False
    assert item.internal is False
    assert item.is_vision is False
    assert item.stream_agent_output is True
    assert item.ai_name is None


def test_ctx_item_final_input_and_output_include_hidden_content_only_when_present():
    item = CtxItem()
    assert item.final_input is None
    assert item.final_output is None

    item.input = "visible input"
    item.output = "visible output"
    assert item.final_input == "visible input"
    assert item.final_output == "visible output"

    item.hidden_input = "hidden input"
    item.hidden_output = "hidden output"
    assert item.final_input == "visible input\n\nhidden input"
    assert item.final_output == "visible output\n\nhidden output"


def test_ctx_item_get_display_output_prefers_response_over_reasoning():
    item = CtxItem()
    item.output = "answer"
    item.extra = {"reasoning": {"visible": True, "text": "thought"}}
    assert item.get_display_output() == "answer"
    assert item.get_display_output("selected") == "selected"


def test_ctx_item_get_display_output_reasoning_fallback_and_escaping():
    item = CtxItem()
    item.output = ""
    item.extra = {"reasoning": {"visible": True, "text": "  a <think>b</think>  "}}
    assert item.get_display_output() == "<think>a &lt;think&gt;b&lt;/think&gt;</think>"

    item.extra = {"reasoning": {"visible": False, "text": "hidden"}}
    assert item.get_display_output() == ""
    item.extra = {"reasoning": {"visible": True, "text": "   "}}
    assert item.get_display_output() == ""
    item.extra = []
    assert item.get_display_output() == ""


def test_ctx_item_clear_reply_only_clears_url_state_for_replies():
    item = CtxItem()
    item.urls = ["now"]
    item.urls_before = ["before"]
    item.clear_reply()
    assert item.urls == ["now"]
    assert item.urls_before == ["before"]

    item.reply = True
    item.clear_reply()
    assert item.urls == []
    assert item.urls_before == []


def test_ctx_item_from_previous_prefers_before_values_and_deep_copies():
    previous = CtxItem()
    previous.urls = ["url-current"]
    previous.urls_before = ["url-before"]
    previous.images = [{"id": 1}]
    previous.files = ["file"]
    previous.attachments_before = [{"name": "att"}]

    item = CtxItem()
    item.prev_ctx = previous
    item.from_previous()

    assert item.urls == ["url-before"]
    assert item.images == [{"id": 1}]
    assert item.files == ["file"]
    assert item.attachments == [{"name": "att"}]
    assert item.urls is not previous.urls_before
    assert item.images is not previous.images

    item.images[0]["id"] = 2
    assert previous.images[0]["id"] == 1


def test_ctx_item_from_previous_without_previous_context_is_noop():
    item = CtxItem()
    item.urls = ["keep"]
    item.from_previous()
    assert item.urls == ["keep"]


def test_ctx_item_agent_name_uses_extra_metadata():
    item = CtxItem()
    item.extra = None
    item.set_agent_name("Worker")
    assert item.ai_name == "Worker"
    assert item.extra == {"agent_name": "Worker"}
    assert item.get_agent_name() == "Worker"

    item.set_agent_name(None)
    assert item.ai_name is None
    assert item.get_agent_name() == "Worker"

    item.extra = "invalid"
    assert item.get_agent_name() is None


def test_ctx_item_empty_commands_and_audio_read_rules():
    item = CtxItem()
    assert item.is_empty() is True
    item.live_output = "partial"
    assert item.is_empty() is False
    item.live_output = ""
    item.stream = object()
    assert item.is_empty() is False
    item.stream = None
    item.output = "answer"
    assert item.is_empty() is False

    item.output = "plain"
    assert item.has_commands() is False
    assert item.audio_read_allowed() is True

    item.cmds = [{"cmd": "x"}]
    assert item.has_commands() is True
    assert item.audio_read_allowed() is False

    item.cmds = []
    item.tool_calls = [{"name": "x"}]
    assert item.has_commands() is True
    item.tool_calls = []
    item.output = 'prefix <tool>{"other":"x"}</tool>'
    assert item.audio_read_allowed() is True
    item.output = 'prefix <tool>{"cmd": "x"}</tool>'
    assert item.audio_read_allowed() is False


def test_ctx_item_document_metadata_and_setters_use_timestamps():
    item = CtxItem()
    meta = {"doc_id": "d1"}
    item.add_doc_meta(meta)
    assert item.index_meta is meta
    assert item.doc_ids == [meta]

    with patch("pygpt_net.item.ctx.time.time", side_effect=[1_700_000_001, 1_700_000_002]):
        item.set_input("hello", "User")
        item.set_output("world", "AI")

    assert item.input == "hello"
    assert item.input_name == "User"
    assert item.input_timestamp == 1_700_000_001
    assert item.output == "world"
    assert item.output_name == "AI"
    assert item.output_timestamp == 1_700_000_002

    item.set_agent_final_response("final")
    assert item.agent_final_response == "final"
    item.set_tokens(12, 8)
    assert (item.input_tokens, item.output_tokens, item.total_tokens) == (12, 8, 20)
    assert item.get_pid() == 0


def test_ctx_item_to_dict_sanitizes_runtime_flags_unless_dump_requested():
    item = CtxItem("chat")
    item.hidden = True
    item.live_output = "streamed"
    item.sub_call = True
    item.sub_calls = 3
    item.sub_reply = True
    item.sub_tool_call = True
    item.meta = CtxMeta(id=4)

    normal = item.to_dict()
    assert normal["hidden"] is False
    assert "live_output" not in normal
    assert normal["sub_call"] is False
    assert normal["sub_calls"] == 0
    assert normal["sub_reply"] is False
    assert normal["sub_tool_call"] is False
    assert normal["meta"]["id"] == 4
    assert list(normal) == sorted(normal)

    dumped = item.to_dict(dump=True)
    assert dumped["hidden"] is True
    assert dumped["live_output"] == "streamed"
    assert dumped["sub_call"] is True
    assert dumped["sub_calls"] == 3
    assert dumped["sub_reply"] is True
    assert dumped["sub_tool_call"] is True


def test_ctx_item_to_dict_leaves_non_ctx_meta_value_unchanged():
    item = CtxItem()
    item.meta = {"id": "raw"}
    assert item.to_dict()["meta"] == {"id": "raw"}


def test_ctx_item_from_dict_loads_supported_fields_and_defaults():
    item = CtxItem()
    item.from_dict({
        "agent_call": True,
        "attachments": ["a"],
        "attachments_before": ["old-a"],
        "audio_expires_ts": 99,
        "audio_id": "audio",
        "cmds": ["cmd"],
        "current": True,
        "doc_ids": ["d"],
        "external_id": "e",
        "extra": {"x": 1},
        "extra_ctx": "extra",
        "files": ["f"],
        "files_before": ["old-f"],
        "first": True,
        "hidden": True,
        "hidden_input": "hi",
        "hidden_output": "ho",
        "id": 1,
        "idx": 2,
        "images": ["i"],
        "images_before": ["old-i"],
        "index_meta": {"m": 1},
        "input": "in",
        "input_name": "U",
        "input_timestamp": 10,
        "input_tokens": 11,
        "internal": True,
        "is_vision": True,
        "meta": {"id": 4},
        "meta_id": 4,
        "model": "m",
        "mode": "chat",
        "msg_id": "msg",
        "output": "out",
        "output_name": "A",
        "output_timestamp": 20,
        "output_tokens": 12,
        "results": ["r"],
        "reply": True,
        "run_id": "run",
        "stream": "s",
        "sub_call": True,
        "sub_calls": 2,
        "sub_reply": True,
        "sub_tool_call": True,
        "thread": "t",
        "tool_calls": ["tc"],
        "total_tokens": 23,
        "urls": ["u"],
        "urls_before": ["old-u"],
    })
    assert item.agent_call is True
    assert item.audio_expires_ts == 99
    assert item.extra_ctx == "extra"
    assert item.is_vision is True
    assert item.meta == {"id": 4}
    assert item.sub_calls == 2
    assert item.tool_calls == ["tc"]
    assert item.total_tokens == 23
    assert item.urls_before == ["old-u"]

    fresh = CtxItem()
    fresh.from_dict({})
    assert fresh.attachments == []
    assert fresh.audio_expires_ts is None
    assert fresh.extra is None
    assert fresh.extra_ctx is False
    assert fresh.total_tokens == 0


def test_ctx_item_debug_dump_print_and_str(capsys):
    item = CtxItem()
    item.id = 7
    item.input = "hello"
    item.output = "world"
    item.extra = {"ą": "ę"}

    debug = json.loads(item.to_debug())
    assert debug["id"] == 7
    assert json.loads(item.dump())["id"] == 7
    assert str(item) == item.dump(True)

    item.print()
    captured = capsys.readouterr().out
    assert "[7]" in captured
    assert "Input: hello" in captured
    assert "Output: world" in captured


def test_ctx_item_dump_returns_empty_string_on_serialization_error():
    item = CtxItem()
    with patch("pygpt_net.item.ctx.json.dumps", side_effect=TypeError):
        assert item.dump() == ""


def test_ctx_meta_integrity_uses_timestamp_values():
    with patch("pygpt_net.item.ctx.time.time", return_value=1_700_000_500):
        item = CtxMeta(id=5)

    assert item.id == 5
    assert item.external_id is None
    assert item.uuid is None
    assert item.name is None
    assert item.date is not None
    assert item.created == 1_700_000_500
    assert item.updated == 1_700_000_500
    assert item.mode is None
    assert item.model is None
    assert item.extra is None
    assert item.initialized is False
    assert item.deleted is False
    assert item.important is False
    assert item.archived is False


def test_ctx_meta_additional_ctx_prefers_group_and_can_reset_remove():
    meta = CtxMeta()
    local = {"name": "local.txt"}
    group_item = {"name": "group.txt"}
    meta.additional_ctx = [local]
    assert meta.has_additional_ctx() is True
    assert meta.get_additional_ctx() == [local]
    assert meta.get_attachment_names() == ["local.txt"]

    group = CtxGroup()
    group.additional_ctx = [group_item]
    meta.group = group
    assert meta.has_additional_ctx() is True
    assert meta.get_additional_ctx() is group.additional_ctx
    assert meta.get_attachment_names() == ["group.txt"]

    meta.remove_additional_ctx(group_item)
    assert group.additional_ctx == []
    meta.reset_additional_ctx()
    assert group.additional_ctx == []

    meta.group = None
    meta.additional_ctx = [local]
    meta.remove_additional_ctx(local)
    assert meta.additional_ctx == []
    meta.additional_ctx = [local]
    meta.reset_additional_ctx()
    assert meta.additional_ctx == []
    assert meta.has_additional_ctx() is False


def test_ctx_meta_to_from_dict_group_dump_and_str():
    meta = CtxMeta(id=3)
    meta.name = "Conversation"
    meta.uuid = "u"
    meta.indexes = {"idx": 1}
    meta.group_id = 9
    meta.group = CtxGroup(id=9, name="Group")

    data = meta.to_dict()
    assert data["id"] == 3
    assert data["name"] == "Conversation"
    assert data["__group__"]["id"] == 9
    assert json.loads(meta.dump())["id"] == 3
    assert str(meta) == meta.dump()
    assert meta.get_pid() == 0

    restored = CtxMeta()
    restored.from_dict({k: v for k, v in data.items() if k != "__group__"})
    assert restored.id == 3
    assert restored.name == "Conversation"
    assert restored.uuid == "u"
    assert restored.indexes == {"idx": 1}
    assert restored.group_id == 9


def test_ctx_meta_from_dict_defaults_and_dump_error():
    meta = CtxMeta()
    meta.from_dict({})
    assert meta.additional_ctx == []
    assert meta.archived is False
    assert meta.created is None
    assert meta.updated is None
    assert meta.label == 0

    with patch("pygpt_net.item.ctx.json.dumps", side_effect=TypeError):
        assert meta.dump() == ""


def test_ctx_group_integrity_helpers_serialization_and_from_dict():
    with patch("pygpt_net.item.ctx.time.time", return_value=1_700_000_700):
        group = CtxGroup(id=8, name="G")
    assert group.id == 8
    assert group.name == "G"
    assert group.created == 1_700_000_700
    assert group.updated == 1_700_000_700
    assert group.has_additional_ctx() is False
    assert group.get_additional_ctx() == []
    assert group.get_attachments_count() == 0

    group.additional_ctx = [
        {"name": "a.txt"},
        {"name": "b.txt", "native": True},
    ]
    group.items = [1, 2]
    group.count = 2
    group.uuid = "u"
    assert group.has_additional_ctx() is True
    assert group.get_additional_ctx() is group.additional_ctx
    assert group.get_attachments_count() == 2
    assert group.get_attachment_names() == ["a.txt", "b.txt (Native)"]

    data = group.to_dict()
    assert data["additional_ctx"] == group.additional_ctx
    assert json.loads(group.dump())["name"] == "G"
    assert str(group) == group.dump()

    restored = CtxGroup()
    restored.from_dict({
        "count": 4,
        "created": 10,
        "id": 3,
        "items": [9],
        "name": "Restored",
        "updated": 20,
        "uuid": "uuid",
    })
    assert restored.count == 4
    assert restored.created == 10
    assert restored.id == 3
    assert restored.items == [9]
    assert restored.name == "Restored"
    assert restored.updated == 20
    assert restored.uuid == "uuid"


def test_ctx_group_dump_returns_empty_string_on_serialization_error():
    group = CtxGroup()
    with patch("pygpt_net.item.ctx.json.dumps", side_effect=TypeError):
        assert group.dump() == ""
