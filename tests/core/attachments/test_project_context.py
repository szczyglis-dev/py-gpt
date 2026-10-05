from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pygpt_net.core.attachments.context import Context
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.summarizer import Summarizer
from pygpt_net.item.ctx import CtxGroup, CtxMeta, CtxItem
from pygpt_net.item.model import ModelItem


def project_fixture(tmp_path):
    values = {"context.extra_summary.enabled": False,
              "max_output_tokens": 128}
    config = SimpleNamespace(get=lambda key, default=None: values.get(key, default),
                             get_user_dir=lambda name: str(tmp_path))
    group = CtxGroup()
    group.id, group.uuid = 7, "project-seven"
    group.extra["attachment_share"] = True
    group.extra["attachment_share_cached"] = True
    owner, current, foreign = CtxMeta(), CtxMeta(), CtxMeta()
    owner.id, owner.uuid, owner.group = 1, "conversation-one", group
    current.id, current.uuid, current.group = 2, "conversation-two", group
    foreign.id, foreign.uuid, foreign.group = 3, "foreign", CtxGroup()
    foreign.group.id = 99
    # Deliberately hide owner from the sidebar and return unfiltered mock data;
    # both project isolation and independence of sidebar filters are exercised.
    provider = SimpleNamespace(get_meta=Mock(return_value={1: owner, 3: foreign}), save=Mock())
    ctx_core = SimpleNamespace(get_group_by_id=lambda key: group if key == 7 else foreign.group,
                               get_meta=lambda: {2: current}, provider=provider, update_group=Mock(), save=Mock())
    model = ModelItem("model")
    model.ctx, model.tokens = 4096, 256
    core = SimpleNamespace(config=config, ctx=ctx_core, tokens=SimpleNamespace(from_str=lambda text, model: len(text)),
                           models=SimpleNamespace(get_num_ctx=lambda key: 4096), debug=SimpleNamespace(log=Mock()))
    window = SimpleNamespace(core=core)
    attachment = Context(window)
    core.attachments = SimpleNamespace(context=attachment)
    core.summarizer = Summarizer(window)
    core.summarizer.complete = Mock(return_value="Helios budget EUR")
    ctx = CtxItem()
    ctx.meta, ctx.meta_id, ctx.input = current, current.id, "What is the Helios budget?"
    bridge = BridgeContext(ctx=ctx, model=model, prompt=ctx.input, max_tokens=128)
    return attachment, bridge, owner, foreign, group, values


def put_text(root, scope, uid, text):
    folder = root / scope / uid
    folder.mkdir(parents=True)
    (folder / (uid + ".txt")).write_text(text, encoding="utf-8")
    return {"uuid": uid, "type": "local_file", "name": uid + ".txt", "path": uid + ".txt", "active": True}


def test_existing_peer_files_are_visible_across_filtered_conversations_and_stay_isolated(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    local = put_text(tmp_path, owner.uuid, "plans", "Helios budget is 4200 EUR.")
    secret = put_text(tmp_path, foreign.uuid, "secret", "Other project's confidential budget.")
    shared = put_text(tmp_path, group.uuid, "requirements", "Helios must use offline storage.")
    owner.additional_ctx = [local]
    foreign.additional_ctx = [secret]
    group.additional_ctx = [shared]
    assert attachment.get_meta_items(bridge.ctx.meta) == [shared, local]
    assert attachment.get_text_path(bridge.ctx.meta, local) == str(tmp_path / owner.uuid / "plans" / "plans.txt")
    text = attachment.project.retrieve(bridge)
    assert "4200 EUR" in text and "plans.txt" in text
    assert "secret" not in text and "confidential" not in text
    assert len(text) <= bridge.model.ctx * 15 // 100
    group.extra["attachment_share"] = False
    assert attachment.get_meta_items(bridge.ctx.meta) == []
    assert attachment.project.retrieve(bridge) == ""


def test_project_override_inactive_files_and_current_upload_exclusion(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    old = put_text(tmp_path, group.uuid, "old", "Helios budget obsolete: 1 EUR.")
    new = put_text(tmp_path, group.uuid, "new", "Helios budget current: 4200 EUR.")
    old["active"] = False
    group.additional_ctx = [old, new]
    bridge.ctx.meta.additional_ctx_current = [new]
    assert attachment.project.retrieve(bridge) == ""
    bridge.ctx.meta.additional_ctx_current = []
    assert "4200 EUR" in attachment.project.retrieve(bridge)
    assert "obsolete" not in attachment.project.retrieve(bridge)
    attachment.set_project_items_active(bridge.ctx.meta, False)
    assert not attachment.is_project_share_enabled(bridge.ctx.meta)
    group.extra["attachment_share"] = False
    attachment.set_project_items_active(bridge.ctx.meta, True)
    assert attachment.is_project_share_enabled(bridge.ctx.meta)
    assert group.extra["attachment_share"] is True
    attachment.window.core.ctx.update_group.assert_called_with(group)


def test_full_sources_reach_summary_gateway_without_retrieval_clipping(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    text = "irrelevant filler " * 170 + "Helios budget is 4200 EUR."
    item = put_text(tmp_path, group.uuid, "large", text)
    group.additional_ctx = [item]
    gateway = attachment.window.core.summarizer.process = Mock(return_value="Budget: 4200 EUR")
    assert attachment.project.retrieve(bridge) == "Budget: 4200 EUR"
    assert text in gateway.call_args.args[0]


def test_source_changes_and_summary_gateway_receives_full_text(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    item = put_text(tmp_path, group.uuid, "plan", "Helios budget 4200 EUR.")
    group.additional_ctx = [item]
    assert "4200 EUR" in attachment.project.retrieve(bridge)
    path = tmp_path / group.uuid / "plan" / "plan.txt"
    path.write_text("Helios budget updated to 55000 EUR.", encoding="utf-8")
    summary = attachment.window.core.summarizer
    summary.process = Mock(side_effect=lambda text, context, source: text)
    assert "55000 EUR" in attachment.project.retrieve(bridge)
    assert summary.process.call_args.args[1] is bridge
    assert summary.process.call_args.args[2] == "project attachments"


def test_shared_file_owner_retains_library_access_when_sharing_is_disabled(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    item = put_text(tmp_path, group.uuid, "my-file", "Helios budget 4200 EUR.")
    item["owner_meta_id"] = bridge.ctx.meta.id
    group.additional_ctx = [item]
    group.extra["attachment_share"] = False
    assert attachment.get_meta_items(bridge.ctx.meta) == [item]
    assert attachment._item_project_scope(bridge.ctx.meta, item)


def test_explicit_library_reference_reads_only_the_selected_duplicate_filename(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    first = put_text(tmp_path, group.uuid, "first", "First version budget 100 EUR.")
    second = put_text(tmp_path, group.uuid, "second", "Second version budget 200 EUR.")
    first["name"] = second["name"] = "plans.txt"
    group.additional_ctx = [first, second]
    bridge.ctx.input = "Read <attachment>project-attachment:second:plans.txt</attachment>"
    text = attachment.get_context_text(bridge.ctx, filename=True, only_current=True)
    assert "Second version" in text and "First version" not in text
    assert bridge.ctx.final_input == "Read plans.txt"
    assert attachment.project.retrieve(bridge).count("Second version") == 0


def test_referenced_project_file_is_bound_to_the_turn_metadata(tmp_path):
    from pygpt_net.controller.chat.attachment import Attachment
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    item = put_text(tmp_path, group.uuid, "selected", "Helios budget 4200 EUR.")
    group.additional_ctx = [item]
    bridge.ctx.input = "Read <attachment>project-attachment:selected:selected.txt</attachment>"
    controller = Attachment(attachment.window)
    controller.bind_current_to_ctx(bridge.ctx)
    assert bridge.ctx.additional_ctx == [item]
    assert "selected.txt" in bridge.ctx.files


def test_deleting_or_resetting_source_conversation_preserves_project_knowledge(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    item = put_text(tmp_path, owner.uuid, "plans", "Helios budget is 4200 EUR.")
    existing = put_text(tmp_path, group.uuid, "existing", "Helios requires offline support.")
    owner.additional_ctx = [item]
    group.additional_ctx = [existing]
    attachment.delete_by_meta(owner)
    assert not (tmp_path / owner.uuid).exists()
    assert (tmp_path / group.uuid / "plans" / "plans.txt").read_text() == "Helios budget is 4200 EUR."
    assert (tmp_path / group.uuid / "existing" / "existing.txt").exists()
    assert {source["uuid"] for source in group.additional_ctx} == {"plans", "existing"}
    attachment.window.core.ctx.provider.get_meta.return_value = {}
    assert "4200 EUR" in attachment.project.retrieve(bridge)
    attachment.reset_by_meta(bridge.ctx.meta, delete_files=True)
    assert (tmp_path / group.uuid / "plans" / "plans.txt").exists()
    assert group.additional_ctx


def test_clearing_shared_library_removes_all_visible_scopes(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    shared = put_text(tmp_path, group.uuid, "shared", "Helios budget is 4200 EUR.")
    local = put_text(tmp_path, owner.uuid, "local", "Helios planning notes.")
    group.additional_ctx = [shared]
    owner.additional_ctx = [local]
    attachment.clear(bridge.ctx.meta, delete_files=True)
    assert group.additional_ctx == []
    assert owner.additional_ctx == []
    assert not (tmp_path / group.uuid / "shared").exists()
    assert not (tmp_path / owner.uuid / "local").exists()
    attachment.window.core.ctx.provider.save.assert_called()


def new_turn(bridge, history):
    item = CtxItem()
    item.meta, item.meta_id, item.input = bridge.ctx.meta, bridge.ctx.meta.id, "Follow up"
    return BridgeContext(ctx=item, model=bridge.model, mode=bridge.mode, prompt=item.input,
                         max_tokens=128, history=history)


def test_stateful_delivery_once_retry_reset_and_new_files(tmp_path, monkeypatch):
    from pygpt_net.core.types import MODE_CHAT
    monkeypatch.setattr("pygpt_net.provider.api.openai.responses.Responses.is_enabled", lambda *args: True)
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    values["use_context"] = True
    bridge.mode = MODE_CHAT
    group.additional_ctx = [put_text(tmp_path, group.uuid, "plans", "Budget 4200 EUR")]
    delivery = attachment.project.prepare(bridge)
    assert delivery.retained and "4200" in delivery.text
    attachment.project.record(bridge.ctx, delivery)
    retry = new_turn(bridge, [bridge.ctx])
    assert "4200" in attachment.project.prepare(retry).text  # no response yet
    bridge.ctx.output, bridge.ctx.msg_id = "Answer", "server-response-id"
    followup = new_turn(bridge, [bridge.ctx])
    assert attachment.project.prepare(followup).text == ""
    group.additional_ctx.append(put_text(tmp_path, group.uuid, "new", "New requirements"))
    assert attachment.project.prepare(followup).text.endswith("New requirements")
    assert "4200" not in attachment.project.prepare(followup).text
    reset = new_turn(bridge, [])
    assert "4200" in attachment.project.prepare(reset).text


def test_stateless_context_is_runtime_only_on_every_turn(tmp_path):
    from pygpt_net.core.types import MODE_CHAT
    from pygpt_net.core.bridge.worker import BridgeWorker
    from pygpt_net.controller.chat.attachment import Attachment
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    bridge.mode = MODE_CHAT
    group.additional_ctx = [put_text(tmp_path, group.uuid, "plans", "Budget 4200 EUR")]
    controller = Attachment(attachment.window)
    attachment.window.controller = SimpleNamespace(chat=SimpleNamespace(attachment=controller))
    for context in [bridge, new_turn(bridge, [bridge.ctx])]:
        worker = BridgeWorker()
        worker.window, worker.context = attachment.window, context
        worker.handle_additional_context()
        assert "4200" in context.prompt
        assert not context.ctx.hidden_input
        assert "project_context" not in (context.ctx.extra or {})
        prompt = context.prompt
        worker.handle_additional_context()
        assert context.prompt == prompt


def test_agent_memory_policy_and_project_switch_off_strip_replay(tmp_path):
    from pygpt_net.core.types import MODE_AGENT_OPENAI, MODE_AGENT_V2
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    values["use_context"] = True
    bridge.mode = MODE_AGENT_OPENAI
    item = put_text(tmp_path, group.uuid, "plans", "Budget 4200 EUR")
    group.additional_ctx = [item]
    attachment.project.record(bridge.ctx, attachment.project.prepare(bridge))
    bridge.ctx.output = "Answer"
    followup = new_turn(bridge, [bridge.ctx])
    assert attachment.project.prepare(followup).text == ""
    attachment.set_display_item_active(bridge.ctx.meta, item, False)
    disabled = new_turn(bridge, [bridge.ctx])
    assert attachment.project.prepare(disabled).text == ""
    assert "4200" not in disabled.history[0].final_input
    assert "4200" in bridge.ctx.final_input  # saved source turn remains untouched
    assert disabled.ctx.extra["project_context_reset"] is True
    attachment.window.core.ctx.update_group.assert_called()
    attachment.set_display_item_active(bridge.ctx.meta, item, True)
    assert "4200" in attachment.project.prepare(new_turn(bridge, [bridge.ctx])).text
    values["use_context"] = False
    assert attachment.project.delivery_family(bridge) == "runtime"
    bridge.mode = MODE_AGENT_V2
    assert attachment.project.delivery_family(bridge) == "agent-memory"


def test_agent_restore_sanitizes_disabled_source_without_mutating_stored_turn(tmp_path):
    from pygpt_net.core.types import MODE_AGENT_V2
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    bridge.mode = MODE_AGENT_V2
    group.additional_ctx = [put_text(tmp_path, group.uuid, "plans", "Budget 4200 EUR")]
    attachment.project.record(bridge.ctx, attachment.project.prepare(bridge))
    attachment.set_project_items_active(bridge.ctx.meta, False)
    cleaned = attachment.project.sanitize_history([bridge.ctx], bridge.ctx.meta, "agent-memory")
    assert "4200" not in cleaned[0].final_input
    assert "4200" in bridge.ctx.final_input


def test_bulk_sharing_persists_each_owner_once_and_disabled_rows_remain_visible(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    group.additional_ctx = [put_text(tmp_path, group.uuid, "one", "One"),
                            put_text(tmp_path, group.uuid, "two", "Two")]
    owner.additional_ctx = [put_text(tmp_path, owner.uuid, "three", "Three"),
                            put_text(tmp_path, owner.uuid, "four", "Four")]
    assert attachment.set_project_items_active(bridge.ctx.meta, False)
    assert len(attachment.get_project_items(bridge.ctx.meta)) == 4
    assert all(not attachment.is_shared(item) for item in attachment.get_project_items(bridge.ctx.meta))
    assert attachment.window.core.ctx.update_group.call_count >= 1
    assert attachment.window.core.ctx.provider.save.call_count >= 1
    assert not attachment.set_project_items_active(bridge.ctx.meta, False)
    assert attachment.set_project_items_active(bridge.ctx.meta, True, "one")
    assert attachment.is_shared(group.additional_ctx[0])
    assert not attachment.is_shared(group.additional_ctx[1])


def test_source_deactivation_breaks_server_chain_only_once(tmp_path, monkeypatch):
    from pygpt_net.core.types import MODE_CHAT
    monkeypatch.setattr("pygpt_net.provider.api.openai.responses.Responses.is_enabled", lambda *args: True)
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    values["use_context"] = True
    bridge.mode = MODE_CHAT
    item = put_text(tmp_path, group.uuid, "plans", "Budget 4200 EUR")
    group.additional_ctx = [item]
    attachment.project.record(bridge.ctx, attachment.project.prepare(bridge))
    bridge.ctx.output, bridge.ctx.msg_id = "Answer", "resp-old"
    attachment.set_project_items_active(bridge.ctx.meta, False)
    next_context = new_turn(bridge, [bridge.ctx])
    attachment.project.record(next_context.ctx, attachment.project.prepare(next_context))
    assert next_context.ctx.extra["project_context_reset"] is True
    next_context.ctx.output, next_context.ctx.msg_id = "No shared sources", "resp-new"
    followup = new_turn(bridge, [bridge.ctx, next_context.ctx])
    attachment.project.prepare(followup)
    assert not followup.ctx.extra.get("project_context_reset")


def test_bridge_stateful_delivery_is_saved_once_and_stateless_switch_strips_old_copy(tmp_path, monkeypatch):
    from pygpt_net.core.types import MODE_CHAT
    from pygpt_net.core.bridge.worker import BridgeWorker
    from pygpt_net.controller.chat.attachment import Attachment
    responses = Mock(return_value=True)
    monkeypatch.setattr("pygpt_net.provider.api.openai.responses.Responses.is_enabled", responses)
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    values["use_context"] = True
    bridge.mode = MODE_CHAT
    group.additional_ctx = [put_text(tmp_path, group.uuid, "plans", "Budget 4200 EUR")]
    attachment.window.controller = SimpleNamespace(chat=SimpleNamespace(attachment=Attachment(attachment.window)))
    def prepare(context):
        worker = BridgeWorker()
        worker.window, worker.context = attachment.window, context
        worker.handle_additional_context()
    prepare(bridge)
    assert bridge.ctx.hidden_input.count("4200") == 1
    assert bridge.prompt.count("4200") == 1
    bridge.ctx.output, bridge.ctx.msg_id = "Answer", "response-one"
    next_context = new_turn(bridge, [bridge.ctx])
    prepare(next_context)
    assert "4200" not in next_context.prompt and not next_context.ctx.hidden_input
    responses.return_value = False
    stateless = new_turn(bridge, [bridge.ctx])
    prepare(stateless)
    assert "4200" in stateless.prompt
    assert "4200" not in stateless.history[0].final_input
    assert not stateless.ctx.hidden_input


def test_pending_upload_toggle_survives_extraction_and_source_reference(tmp_path):
    from pygpt_net.controller.chat.attachment import Attachment
    from pygpt_net.item.attachment import AttachmentItem
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    uploaded = AttachmentItem(id="pending-source", name="plans.txt", extra={"project_active": False})
    item = put_text(tmp_path, group.uuid, "stored-source", "Budget 4200 EUR")
    item["name"] = "plans.txt"
    Attachment(attachment.window).append_to_meta(bridge.ctx.meta, item, uploaded)
    assert item["attachment_id"] == "pending-source" and not item["project_active"]
    assert item["active"]
    assert item in attachment.get_all(bridge.ctx.meta)
    Attachment(attachment.window).bind_current_to_ctx(bridge.ctx)
    assert bridge.ctx.additional_ctx == [item]
    assert item not in attachment.get_all(owner)
    bridge.ctx.meta.additional_ctx_current = []
    bridge.ctx.input = "Read <attachment>project-attachment:pending-source:plans.txt</attachment>"
    assert attachment.current_ids(bridge.ctx) == {"stored-source"}


@pytest.mark.parametrize("meta_extra", [None, "legacy metadata"])
@pytest.mark.parametrize("shared", [False, True])
def test_real_group_save_reload_preserves_uploaded_pdf_for_input_and_library(tmp_path, meta_extra, shared):
    from sqlalchemy import create_engine, text
    from pygpt_net.controller.chat.attachment import Attachment
    from pygpt_net.core.attachments.attachments import Attachments
    from pygpt_net.core.bridge.worker import BridgeWorker
    from pygpt_net.core.types import MODE_CHAT
    from pygpt_net.item.attachment import AttachmentItem
    from pygpt_net.provider.core.ctx.db_sqlite.storage import Storage

    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    core = attachment.window.core
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE ctx_group (
            id INTEGER PRIMARY KEY, uuid TEXT, name TEXT, created_ts INTEGER,
            updated_ts INTEGER, extra_json TEXT, additional_ctx_json TEXT)"""))
        conn.execute(text("""CREATE TABLE ctx_meta (
            id INTEGER PRIMARY KEY, external_id TEXT, name TEXT, mode TEXT, model TEXT,
            last_mode TEXT, last_model TEXT, thread_id TEXT, assistant_id TEXT,
            preset_id TEXT, run_id TEXT, status TEXT, extra TEXT, is_initialized INTEGER,
            is_deleted INTEGER, is_important INTEGER, is_archived INTEGER, label INTEGER,
            root_id INTEGER, parent_id INTEGER, additional_ctx_json TEXT)"""))
        conn.execute(text("INSERT INTO ctx_meta (id, extra) VALUES (:id, :extra)"),
                     {"id": bridge.ctx.meta.id, "extra": meta_extra})
    bridge.ctx.meta.extra = meta_extra
    group.extra.pop("attachment_share_cached", None)
    core.db = SimpleNamespace(get_db=lambda: engine)
    storage = Storage(attachment.window)
    storage.insert_group(group)
    group.id = int(group.id)
    cache = storage.get_groups()
    core.ctx.get_group_by_id = lambda key: cache.get(key)
    def save_and_reload(project):
        storage.update_group(project)
        cache.clear()
        cache.update(storage.get_groups())
    core.ctx.update_group = save_and_reload
    core.ctx.save = lambda meta_id: storage.update_meta(bridge.ctx.meta)
    # Startup sharing initialization must preserve the legacy text/NULL extra
    # field and execute an actual ctx_meta UPDATE without binding a dict.
    assert not attachment.is_project_share_enabled(bridge.ctx.meta)
    assert bridge.ctx.meta.extra == meta_extra
    with engine.connect() as conn:
        assert conn.execute(text("SELECT extra FROM ctx_meta WHERE id=:id"),
                            {"id": bridge.ctx.meta.id}).scalar() == meta_extra
    # Actual upload/copy/extraction storage + SQL persistence/reload. Only the
    # PDF reader is substituted, so provider fixtures cannot hide lost metadata.
    pdf = tmp_path / "invoice.pdf"
    pdf.write_bytes(b"test PDF bytes")
    invoice = "Invoice total: 1234.56 PLN"
    core.idx = SimpleNamespace(indexing=SimpleNamespace(read_text_content=Mock(return_value=(invoice, []))))
    core.tokens.from_str = lambda value, model=None: len(value)
    core.filesystem = SimpleNamespace(packer=SimpleNamespace(is_archive=lambda path: False))
    core.attachments.native = SimpleNamespace(get_model=lambda: bridge.model)
    controller = Attachment(attachment.window)
    controller.is_allowed = Mock(return_value=True)
    controller._try_native_upload = Mock(return_value=None)
    uploaded = AttachmentItem(id="uploaded-pdf", name=pdf.name, path=str(pdf), extra={"project_active": shared})
    assert controller.upload_file(uploaded, bridge.ctx.meta, bridge.ctx.input, False, MODE_CHAT)
    assert bridge.ctx.meta.additional_ctx_current
    stored = attachment.get_project_items(bridge.ctx.meta)
    assert len(stored) == 1 and stored[0]["name"] == "invoice.pdf"
    assert cache[group.id].additional_ctx == stored
    library = Attachments(attachment.window)
    library.context = attachment
    assert [item.name for item in library.get_from_meta_ctx(MODE_CHAT, bridge.ctx.meta)] == ["invoice.pdf"]
    bridge.mode = MODE_CHAT
    attachment.window.controller = SimpleNamespace(chat=SimpleNamespace(attachment=controller))
    worker = BridgeWorker()
    worker.window, worker.context = attachment.window, bridge
    worker.handle_additional_context()
    assert invoice in bridge.prompt
    assert invoice in bridge.ctx.hidden_input
    assert bridge.ctx.additional_ctx[0]["uuid"] == stored[0]["uuid"]
    # A fresh model-library read and second conversation see the same persisted source.
    bridge.ctx.meta.additional_ctx_current = []
    bridge.ctx.meta.group = storage.get_groups()[group.id]
    next_context = new_turn(bridge, [])
    other = CtxMeta()
    other.id, other.uuid, other.group = 42, "another-conversation", storage.get_groups()[group.id]
    next_context.ctx.meta, next_context.ctx.meta_id = other, other.id
    assert (invoice in attachment.project.prepare(next_context).text) is shared
    assert [item.name for item in library.get_from_meta_ctx(MODE_CHAT, other)] == (["invoice.pdf"] if shared else [])
    engine.dispose()


def test_group_share_flag_updates_and_reads_do_not_scan_sources(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    owner.additional_ctx = [put_text(tmp_path, owner.uuid, "one", "One"),
                            put_text(tmp_path, owner.uuid, "two", "Two")]
    attachment.refresh_share_flags(bridge.ctx.meta)
    assert group.extra["attachment_share"] is True
    assert "attachment_share" not in (bridge.ctx.meta.extra or {})
    attachment.set_project_items_active(bridge.ctx.meta, False, "one")
    assert group.extra["attachment_share"] is True
    attachment.set_project_items_active(bridge.ctx.meta, False, "two")
    assert "attachment_share" not in (owner.extra or {})
    assert group.extra["attachment_share"] is False
    source_reader = attachment.get_project_items
    attachment.get_project_items = Mock(side_effect=AssertionError("normal reads must use flags"))
    assert not attachment.is_project_share_enabled(bridge.ctx.meta)
    assert not attachment.is_project_share_enabled(owner)
    attachment.get_project_items = source_reader
    attachment.set_project_items_active(bridge.ctx.meta, True, "two")
    assert group.extra["attachment_share"] is True
    assert attachment.is_project_share_enabled(bridge.ctx.meta)


def test_legacy_project_sharing_initializes_group_flag_once(tmp_path):
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    group.extra = {"attachment_share": False}  # removed global switch is ignored
    owner.additional_ctx = [put_text(tmp_path, owner.uuid, "plans", "Plans")]
    assert attachment.is_project_share_enabled(bridge.ctx.meta)
    assert group.extra["attachment_share"] is True
    assert group.extra["attachment_share_cached"] is True
    attachment.get_project_items = Mock(side_effect=AssertionError("migration must run once"))
    assert attachment.is_project_share_enabled(bridge.ctx.meta)


def test_library_actions_persist_group_flags_and_sync_bulk_state(tmp_path):
    from pygpt_net.ui.widget.textarea.input import ChatInput
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    group.additional_ctx = [put_text(tmp_path, group.uuid, "plans", "Plan")]
    group.extra["attachment_share_all"] = True
    core = attachment.window.core
    core.ctx.get_current_meta = lambda: bridge.ctx.meta
    core.attachments.get_all = lambda *args, **kwargs: {}
    attachment.window.controller = SimpleNamespace(
        ctx=SimpleNamespace(update_list=Mock()), chat=SimpleNamespace(attachment=SimpleNamespace(update=Mock())))
    popup = SimpleNamespace(_from_attachment_button=True, set_project_state=Mock(), set_entries=Mock())
    widget = SimpleNamespace(window=attachment.window, _mention_popup=popup,
                             _build_mention_entries=lambda **kwargs: [])
    ChatInput._set_library_shared(widget, False, "plans")
    assert group.extra["attachment_share"] is False
    assert group.extra["attachment_share_all"] is False
    assert "attachment_share" not in (bridge.ctx.meta.extra or {})
    popup.set_project_state.assert_called_with(True, False, False)
    ChatInput._set_library_shared(widget, True)
    assert group.extra["attachment_share"] is True
    assert group.extra["attachment_share_all"] is True
    assert group.additional_ctx[0]["active"] is True
    ChatInput._set_library_shared(widget, False)
    assert group.extra["attachment_share"] is False
    assert group.extra["attachment_share_all"] is False


@pytest.mark.parametrize('shared', [False, True])
def test_move_ungrouped_conversation_refreshes_cached_project_sharing(tmp_path, shared):
    from pygpt_net.core.ctx import Ctx
    attachment, bridge, owner, foreign, group, values = project_fixture(tmp_path)
    moved = bridge.ctx.meta
    moved.group = None
    moved.group_id = None
    moved.additional_ctx = [put_text(tmp_path, moved.uuid, 'moved', 'Conversation attachment')]
    moved.additional_ctx[0]['project_active'] = shared
    group.extra.update(attachment_share=False, attachment_share_cached=True)
    ctx_core = attachment.window.core.ctx
    ctx_core.window = attachment.window
    ctx_core.get_meta_by_id = lambda key: moved
    ctx_core.provider.update_meta_group_id = Mock()
    ctx_core.load_groups = Mock()
    Ctx.update_meta_group_id(ctx_core, moved.id, group.id)
    assert moved.group is group
    assert moved.group_id == group.id
    assert group.extra['attachment_share'] is shared
    assert attachment.is_project_share_enabled(moved) is shared
    assert moved.additional_ctx[0] in attachment.get_all(moved)
    assert (moved.additional_ctx[0] in attachment.get_all(owner)) is shared
    ctx_core.provider.update_meta_group_id.assert_called_once_with(moved.id, group.id)
    ctx_core.update_group.assert_called_with(group)
