from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.agent_builder.tool import AgentBuilder


class _FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 6, 21, 22, 33)


def _builder():
    tool = AgentBuilder()
    custom = MagicMock()
    window = SimpleNamespace(
        ui=SimpleNamespace(editor={}, dialog={}, dialogs=MagicMock(), nodes={}, models={}),
        core=SimpleNamespace(agents=SimpleNamespace(custom=custom)),
        controller=SimpleNamespace(presets=SimpleNamespace(editor=MagicMock())),
        update_status=MagicMock(),
    )
    tool.window = window
    return tool, custom


def test_agent_builder_defaults_and_editing_allowed_state_machine():
    tool, _ = _builder()
    assert tool.id == "agent_builder"
    assert tool.opened is False
    assert tool.current_agent is None
    assert tool.editing_allowed() is False

    tool.opened = True
    tool.current_agent = "a"
    assert tool.editing_allowed() is True
    tool._restoring = True
    assert tool.editing_allowed() is False
    tool._restoring = False
    tool._closing = True
    assert tool.editing_allowed() is False


def test_agent_builder_save_requires_stable_open_editor_unless_forced():
    tool, custom = _builder()
    editor = MagicMock()
    editor._alive = True
    editor._closing = False
    editor.save_layout.return_value = {"nodes": [1]}
    editor.export_schema.return_value = [{"kind": "agent"}]
    tool.window.ui.editor["agent.builder"] = editor

    tool.save()
    custom.save.assert_not_called()

    tool.opened = True
    tool._restoring = True
    tool.save()
    custom.save.assert_not_called()

    tool.save(force=True)
    custom.update_layout.assert_called_once_with({"nodes": [1]})
    custom.save.assert_called_once_with()


def test_agent_builder_save_deep_copies_layout_and_schema_and_updates_current_agent():
    tool, custom = _builder()
    tool.opened = True
    tool.current_agent = "agent-1"
    data = {"nodes": [{"id": 1}]}
    schema = [{"name": "worker"}]
    editor = MagicMock(_alive=True, _closing=False)
    editor.save_layout.return_value = data
    editor.export_schema.return_value = schema
    tool.window.ui.editor["agent.builder"] = editor

    with patch("pygpt_net.tools.agent_builder.tool.datetime", _FixedDateTime):
        tool.save()

    stored_layout = custom.update_layout.call_args.args[0]
    stored_agent_layout, stored_schema = custom.update_agent.call_args.args[1:]
    assert stored_layout == data and stored_layout is not data
    assert stored_agent_layout == data and stored_agent_layout is not data
    assert stored_schema == schema and stored_schema is not schema
    custom.update_agent.assert_called_once()
    custom.save.assert_called_once_with()
    tool.window.update_status.assert_called_once_with("Saved at: 21:22:33")
    tool.window.controller.presets.editor.reload_all.assert_called_once_with(all=True)


def test_agent_builder_save_skips_dead_closing_and_invalid_snapshots():
    tool, custom = _builder()
    tool.opened = True

    for editor in (
        SimpleNamespace(_alive=False, _closing=False),
        SimpleNamespace(_alive=True, _closing=True),
    ):
        tool.window.ui.editor["agent.builder"] = editor
        tool.save()
    custom.save.assert_not_called()

    editor = MagicMock(_alive=True, _closing=False)
    editor.save_layout.return_value = ["invalid"]
    tool.window.ui.editor["agent.builder"] = editor
    tool.save()
    custom.save.assert_not_called()


def test_agent_builder_load_delegates_to_restore():
    tool, _ = _builder()
    tool.restore = MagicMock()
    tool.load()
    tool.restore.assert_called_once_with()


def test_agent_builder_open_close_toggle_and_show_hide():
    tool, _ = _builder()
    fake_dialog = MagicMock()

    with patch("pygpt_net.tools.agent_builder.tool.Builder", return_value=fake_dialog), \
            patch("pygpt_net.tools.agent_builder.tool.QtCore.QTimer.singleShot") as single_shot:
        tool.open()

    fake_dialog.setup.assert_called_once_with()
    single_shot.assert_called_once()
    assert single_shot.call_args.args[0] == 0
    tool.window.ui.dialogs.open.assert_called_once_with("agent.builder", width=900, height=600)
    assert tool.opened is True

    tool.close()
    tool.window.ui.dialogs.close.assert_called_with("agent.builder")
    assert tool.opened is False

    tool.open = MagicMock()
    tool.close = MagicMock()
    tool.opened = False
    tool.toggle()
    tool.open.assert_called_once_with()
    tool.opened = True
    tool.toggle()
    tool.close.assert_called_once_with()

    tool.open.reset_mock(); tool.close.reset_mock()
    tool.show_hide(True); tool.show_hide(False)
    tool.open.assert_called_once_with()
    tool.close.assert_called_once_with()


def test_agent_builder_store_current_guards_and_force_during_close():
    tool, _ = _builder()
    tool.save = MagicMock()
    tool.opened = True

    tool.store_current()
    tool.save.assert_called_once_with(force=False)

    tool.save.reset_mock(); tool._restoring = True
    tool.store_current()
    tool.save.assert_not_called()

    tool._restoring = False; tool._closing = True
    tool.store_current()
    tool.save.assert_not_called()
    tool.store_current(force=True)
    tool.save.assert_called_once_with(force=True)


def test_agent_builder_restore_is_timezone_independent_and_resets_guard():
    tool, custom = _builder()
    editor = MagicMock()
    tool.window.ui.editor["agent.builder"] = editor
    custom.get_layout.return_value = SimpleNamespace(data={"nodes": [1]})
    custom.get_agents.return_value = {"first": object(), "second": object()}
    tool.update_list = MagicMock()
    tool.edit_agent = MagicMock()

    with patch("pygpt_net.tools.agent_builder.tool.datetime", _FixedDateTime):
        tool.restore()

    editor.load_layout.assert_called_once_with({"nodes": [1]})
    tool.window.update_status.assert_called_once_with("Loaded layout at: 21:22:33")
    tool.update_list.assert_called_once_with()
    tool.edit_agent.assert_called_once_with("first")
    assert tool._restoring is False


def test_agent_builder_restore_does_nothing_when_closing():
    tool, custom = _builder()
    tool._closing = True
    tool.update_list = MagicMock()
    tool.restore()
    custom.get_layout.assert_not_called()
    tool.update_list.assert_not_called()


def test_agent_builder_on_close_and_exit_preserve_teardown_guards():
    tool, _ = _builder()
    tool.opened = True
    seen = []

    def store(force=False):
        seen.append((force, tool._closing))

    tool.store_current = store
    tool.on_close()
    assert seen == [(True, True)]
    assert tool.opened is False
    assert tool._closing is False

    tool.on_close = MagicMock()
    tool.opened = False
    tool.on_exit()
    tool.on_close.assert_not_called()
    tool.opened = True
    tool.on_exit()
    tool.on_close.assert_called_once_with()


def test_agent_builder_clear_confirm_and_forced_clear_save():
    tool, _ = _builder()
    editor = MagicMock()
    editor.clear.return_value = True
    tool.window.ui.editor["agent.builder"] = editor
    tool.save = MagicMock()

    with patch("pygpt_net.tools.agent_builder.tool.trans", return_value="confirm"):
        tool.clear()
    tool.window.ui.dialogs.confirm.assert_called_once_with(
        type="agent.builder.agent.clear", id=0, msg="confirm"
    )
    editor.clear.assert_not_called()

    tool.clear(force=True)
    editor.clear.assert_called_once_with(ask_user=False)
    tool.save.assert_called_once_with()


def test_agent_builder_add_agent_dialog_and_creation_flow():
    tool, custom = _builder()
    create = MagicMock()
    tool.window.ui.dialog["create"] = create

    tool.add_agent()
    assert create.id == "agent.builder.agent"
    create.input.setText.assert_called_once_with("")
    assert create.current == ""
    create.show.assert_called_once_with()
    create.input.setFocus.assert_called_once_with()

    tool.current_agent = "old"
    tool.save = MagicMock()
    tool.update_list = MagicMock()
    tool.edit_agent = MagicMock()
    tool.update_presets = MagicMock()
    editor = MagicMock()
    tool.window.ui.editor["agent.builder"] = editor
    custom.new_agent.return_value = "new-id"

    tool.add_agent("New")

    tool.save.assert_called_once_with()
    custom.new_agent.assert_called_once_with("New")
    editor.clear.assert_called_once_with(ask_user=False)
    tool.window.ui.dialogs.close.assert_called_with("create")
    tool.edit_agent.assert_called_once_with("new-id")
    tool.update_presets.assert_called_once_with()


def test_agent_builder_rename_duplicate_and_delete_flows(capsys):
    tool, custom = _builder()
    tool.update_list = MagicMock()
    tool.update_presets = MagicMock()

    custom.get_agent.return_value = None
    tool.rename_agent("missing", "X")
    assert "Agent not found: missing" in capsys.readouterr().out

    agent = SimpleNamespace(name="A", layout={"x": 1})
    custom.get_agent.return_value = agent
    rename = MagicMock()
    tool.window.ui.dialog["rename"] = rename
    tool.rename_agent("a")
    rename.input.setText.assert_called_once_with("A")
    assert rename.current == "a"

    tool.rename_agent("a", "B")
    assert agent.name == "B"
    custom.save.assert_called_once_with()
    tool.update_presets.assert_called_once_with()

    tool.duplicate_agent("a")
    custom.duplicate_agent.assert_called_once_with("a", "B (copy)")

    with patch("pygpt_net.tools.agent_builder.tool.trans", return_value="confirm"):
        tool.delete_agent("a")
    tool.window.ui.dialogs.confirm.assert_called_with(
        type="agent.builder.agent.delete", id="a", msg="confirm"
    )


def test_agent_builder_forced_delete_current_clears_editor_and_selects_next():
    tool, custom = _builder()
    editor = MagicMock()
    tool.window.ui.editor["agent.builder"] = editor
    list_widget = MagicMock()
    idx = MagicMock()
    idx.isValid.return_value = True
    idx.data.return_value = "next"
    list_widget.list.currentIndex.return_value = idx
    tool.window.ui.nodes["agent.builder.list"] = list_widget
    tool.current_agent = "dead"
    tool.opened = True
    custom.get_agents.return_value = {"next": object()}
    tool.update_list = MagicMock()
    tool.edit_agent = MagicMock()

    tool.delete_agent("dead", force=True)

    custom.delete_agent.assert_called_once_with("dead")
    editor.clear.assert_called_once_with(ask_user=False)
    assert tool.current_agent is None
    tool.edit_agent.assert_called_once_with("next")


def test_agent_builder_edit_agent_saves_switch_then_loads_or_clears_layout():
    tool, custom = _builder()
    editor = MagicMock(_alive=True, _closing=False)
    tool.window.ui.editor["agent.builder"] = editor
    tool.window.ui.nodes["agent.builder.list"] = object()
    tool.current_agent = "old"
    tool.opened = True
    tool.save = MagicMock()
    tool.select_on_list = MagicMock()
    custom.get_agent.return_value = SimpleNamespace(layout={"nodes": []})

    tool.edit_agent("new")
    tool.save.assert_called_once_with()
    assert tool.current_agent == "new"
    editor.load_layout.assert_called_once_with({"nodes": []})
    tool.select_on_list.assert_called_once_with("new")

    custom.get_agent.return_value = SimpleNamespace(layout=None)
    tool.save.reset_mock()
    tool.edit_agent("new")
    tool.save.assert_not_called()
    editor.clear.assert_called_once_with(ask_user=False)


def test_agent_builder_update_list_and_select_on_list():
    tool, custom = _builder()
    tool.update_list()
    custom.get_agents.assert_not_called()

    list_node = MagicMock()
    list_view = list_node.list
    tool.window.ui.nodes["agent.builder.list"] = list_node
    custom.get_agents.return_value = {"a": object()}
    tool.update_list()
    list_node.update_list.assert_called_once_with(custom.get_agents.return_value)

    model = MagicMock()
    model.rowCount.return_value = 2
    idx0, idx1 = MagicMock(), MagicMock()
    model.index.side_effect = [idx0, idx1]
    model.data.side_effect = ["other", "target"]
    sm = MagicMock()
    list_view.selectionModel.return_value = sm
    tool.window.ui.models["agent.builder.list"] = model

    tool.select_on_list("target")
    list_view.setCurrentIndex.assert_called_once_with(idx1)
    sm.select.assert_called_once()
    list_view.scrollTo.assert_called_once_with(idx1)


def test_agent_builder_registry_contains_only_flow_node_types_and_expected_limits():
    tool, _ = _builder()
    with patch("pygpt_net.tools.agent_builder.tool.trans", side_effect=lambda key: key):
        registry = tool.get_registry()

    assert registry.types() == ["Flow/Start", "Flow/Agent", "Flow/Memory", "Flow/End"]
    assert registry.get("Flow/Start").max_num == 1
    assert registry.get("Flow/End").max_num == 1
    assert registry.get("Flow/Agent").export_kind == "agent"
    agent_props = {p.id: p for p in registry.get("Flow/Agent").properties}
    assert agent_props["remote_tools"].value is True
    assert agent_props["local_tools"].value is True
    assert agent_props["memory"].allowed_outputs == 1


def test_agent_builder_lang_mappings():
    tool, _ = _builder()
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.agent.builder": "menu.tools.agent.builder"}
    }
