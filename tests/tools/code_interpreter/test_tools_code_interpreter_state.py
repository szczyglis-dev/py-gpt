import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.code_interpreter.tool import CodeInterpreter


def _sig():
    return SimpleNamespace(emit=MagicMock())


def _signals():
    return SimpleNamespace(
        update_input=_sig(),
        update_history=_sig(),
        set_checkbox_all=_sig(),
        set_checkbox_auto_clear=_sig(),
        set_checkbox_ipython=_sig(),
        toggle_all_visible=_sig(),
        reload_view=_sig(),
        begin_output=_sig(),
        end_output=_sig(),
        update=_sig(),
        focus_input=_sig(),
        restore_nodes=_sig(),
        clear_history=_sig(),
        clear_output=_sig(),
        append_input=_sig(),
    )


def _tool(tmp_path):
    tool = CodeInterpreter()
    tool.signals = _signals()
    data_dir = tmp_path / "data"
    tmp_dir = tmp_path / "tmp"
    data_dir.mkdir(exist_ok=True)
    tmp_dir.mkdir(exist_ok=True)
    config = MagicMock()
    config.get_user_dir.side_effect = lambda kind: str(data_dir if kind == "data" else tmp_dir)
    plugin = MagicMock()
    plugins = MagicMock()
    plugins.get.return_value = plugin
    parser = MagicMock()
    window = SimpleNamespace(
        core=SimpleNamespace(
            config=config,
            plugins=plugins,
            filesystem=SimpleNamespace(parser=parser),
        ),
        ui=SimpleNamespace(
            dialogs=MagicMock(),
            nodes={"icon.interpreter": MagicMock()},
            splitters={},
        ),
        controller=SimpleNamespace(
            kernel=MagicMock(),
            command=MagicMock(),
            ui=SimpleNamespace(tabs=MagicMock()),
        ),
        dispatch=MagicMock(),
    )
    window.controller.ui.tabs.column_idx = 0
    tool.window = window
    tool.dialog = SimpleNamespace(widget=SimpleNamespace(
        history=MagicMock(),
        output=MagicMock(),
        input=MagicMock(),
        checkbox_all=MagicMock(),
        on_open=MagicMock(),
    ))
    return tool, data_dir, tmp_dir, plugin


def test_code_interpreter_defaults_and_paths(tmp_path):
    tool, _, tmp_dir, _ = _tool(tmp_path)
    assert tool.id == "interpreter"
    assert tool.has_tab is True
    assert tool.ipython is True
    assert tool.max_history_size == 1000
    assert tool.get_path_input() == str(tmp_dir / ".interpreter.input.py")
    assert tool.get_path_output() == str(tmp_dir / ".interpreter.output.py")
    assert tool.get_path_output_json() == str(tmp_dir / ".interpreter.output.json")
    assert tool.get_widget() is tool.dialog.widget
    assert tool.get_widget_history() is tool.dialog.widget.history
    assert tool.get_widget_output() is tool.dialog.widget.output
    assert tool.get_widget_input() is tool.dialog.widget.input


def test_code_interpreter_setup_restores_config_and_initializes_once(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.migrate_legacy_files = MagicMock()
    tool.load_history = MagicMock()
    tool.load_output = MagicMock()
    tool.update = MagicMock()
    tool.set_initial_size = MagicMock()
    values = {
        "interpreter.input": "print(1)",
        "interpreter.execute_all": True,
        "interpreter.auto_clear": True,
        "interpreter.ipython": False,
    }
    tool.window.core.config.has.side_effect = lambda key: key in values
    tool.window.core.config.get.side_effect = lambda key, *args: values[key]

    tool.setup()

    tool.migrate_legacy_files.assert_called_once_with()
    tool.load_history.assert_called_once_with()
    tool.load_output.assert_called_once_with()
    tool.update.assert_called_once_with()
    tool.signals.update_input.emit.assert_called_once_with("print(1)")
    tool.signals.set_checkbox_all.emit.assert_called_once_with(True)
    tool.signals.set_checkbox_auto_clear.emit.assert_called_once_with(True)
    tool.signals.set_checkbox_ipython.emit.assert_called_once_with(False)
    # self.ipython is still the tool's in-memory value until widget callback updates it.
    tool.signals.toggle_all_visible.emit.assert_called_once_with(False)
    tool.set_initial_size.assert_called_once_with()
    tool.window.core.config.set.assert_called_once_with("interpreter.dialog.initialized", True)


def test_code_interpreter_setup_does_not_reset_initialized_dialog_size(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.migrate_legacy_files = MagicMock()
    tool.load_history = MagicMock()
    tool.load_output = MagicMock()
    tool.update = MagicMock()
    tool.set_initial_size = MagicMock()
    tool.window.core.config.has.side_effect = lambda key: key == "interpreter.dialog.initialized"

    tool.setup()
    tool.set_initial_size.assert_not_called()


def test_code_interpreter_migrate_legacy_files_moves_or_deletes_stale_files(tmp_path):
    tool, data_dir, tmp_dir, _ = _tool(tmp_path)
    names = [
        tool.file_current,
        tool.file_input,
        tool.file_output,
        tool.file_output_json,
        ".interpreter.kernel.json",
    ]
    for name in names:
        (data_dir / name).write_text("legacy", encoding="utf-8")

    tool.migrate_legacy_files()
    for name in names:
        assert not (data_dir / name).exists()
        assert (tmp_dir / name).read_text(encoding="utf-8") == "legacy"

    # Existing current files win; stale legacy copies are removed.
    (data_dir / tool.file_input).write_text("stale", encoding="utf-8")
    (tmp_dir / tool.file_input).write_text("current", encoding="utf-8")
    tool.migrate_legacy_files()
    assert not (data_dir / tool.file_input).exists()
    assert (tmp_dir / tool.file_input).read_text(encoding="utf-8") == "current"


def test_code_interpreter_migrate_legacy_files_ignores_oserror(tmp_path):
    tool, data_dir, _, _ = _tool(tmp_path)
    (data_dir / tool.file_output).write_text("legacy", encoding="utf-8")
    with patch("pygpt_net.tools.code_interpreter.tool.os.replace", side_effect=OSError("locked")):
        assert tool.migrate_legacy_files() is None


def test_code_interpreter_theme_event_reload_and_ipython_output(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.reload_view = MagicMock()
    from pygpt_net.core.events import RenderEvent

    tool.handle(SimpleNamespace(name=RenderEvent.ON_THEME_CHANGE))
    tool.reload_view.assert_called_once_with()

    tool.append_output = MagicMock()
    tool.handle_ipython_output("line")
    tool.append_output.assert_called_once_with("line")

    tool.on_reload()
    assert tool.reload_view.call_count == 2


def test_code_interpreter_reload_view_emits_signal(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.reload_view()
    tool.signals.reload_view.emit.assert_called_once_with()


def test_code_interpreter_get_output_max_entries_defaults_and_sanitizes(tmp_path):
    tool, _, _, plugin = _tool(tmp_path)
    tool.window.core.plugins.get.return_value = None
    assert tool.get_output_max_entries() == 30

    tool.window.core.plugins.get.return_value = plugin
    plugin.get_option_value.return_value = "12"
    assert tool.get_output_max_entries() == 12
    plugin.get_option_value.return_value = -5
    assert tool.get_output_max_entries() == 0
    plugin.get_option_value.return_value = "invalid"
    assert tool.get_output_max_entries() == 30


def test_code_interpreter_output_begin_resets_matching_buffer_and_emits(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.output_buffer = "old"
    tool.input_buffer = "old-input"

    tool.output_begin("stdout")
    assert tool.output_buffer == ""
    assert tool.input_buffer == "old-input"
    tool.signals.begin_output.emit.assert_called_with("stdout")

    tool.output_begin("stdin")
    assert tool.input_buffer == ""
    tool.signals.begin_output.emit.assert_called_with("stdin")


def test_code_interpreter_output_end_extracts_files_and_saves_nodes(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.output_buffer = "data"
    tool.save_output_nodes = MagicMock()

    def extract(ctx, text):
        assert text == "data"
        ctx.images = ["img.png"]
        ctx.files = ["out.csv"]

    tool.window.core.filesystem.parser.extract_data_files.side_effect = extract
    tool.output_end("stdout")

    assert tool.output_buffer == ""
    tool.window.core.filesystem.parser.extract_data_files.assert_called_once()
    tool.signals.end_output.emit.assert_called_once()
    emitted_type, emitted_ctx = tool.signals.end_output.emit.call_args.args
    assert emitted_type == "stdout"
    assert emitted_ctx.images == ["img.png"]
    assert emitted_ctx.files == ["out.csv"]
    tool.save_output_nodes.assert_called_once_with()


def test_code_interpreter_output_end_stdin_clears_input_without_parsing(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.input_buffer = "input"
    tool.output_end("stdin")
    assert tool.input_buffer == ""
    tool.window.core.filesystem.parser.extract_data_files.assert_not_called()


def test_code_interpreter_append_output_updates_buffers_and_persistence(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.save_output = MagicMock()
    tool.load_history = MagicMock()

    tool.append_output("A", "stdout")
    tool.append_output("B", "stderr")
    tool.append_output("C", "stdin")

    assert tool.output_buffer == "AB"
    assert tool.input_buffer == "C"
    assert tool.signals.update.emit.call_args_list[0].args == ("A", "stdout", True)
    assert tool.save_output.call_count == 3
    assert tool.load_history.call_count == 3


def test_code_interpreter_history_file_roundtrip_and_line_limit(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.max_history_size = 2
    tool.save_history("one\ntwo\nthree\n")
    assert tool.get_history() == "two\nthree\n"

    tool.max_history_size = 0
    tool.save_history("a\nb\nc")
    assert tool.get_history() == "a\nb\nc"

    tool.load_history()
    tool.signals.update_history.emit.assert_called_once_with("a\nb\nc")

def test_code_interpreter_load_output_restores_nodes_and_trims_persisted_state(tmp_path):
    tool, _, tmp_dir, plugin = _tool(tmp_path)
    plugin.get_option_value.return_value = 2
    json_path = tmp_dir / tool.file_output_json
    out_path = tmp_dir / tool.file_output
    json_path.write_text(json.dumps([
        {"content": "", "type": "text", "images": [], "files": []},
        {"content": "one", "type": "stdout", "images": [], "files": []},
        {"content": "two", "type": "stderr", "images": ["i.png"], "files": []},
        {"content": "three", "type": "stdout", "images": [], "files": ["f.txt"]},
    ]), encoding="utf-8")
    out_path.write_text("old", encoding="utf-8")

    tool.load_output()

    tool.signals.focus_input.emit.assert_called_once_with()
    nodes = tool.signals.restore_nodes.emit.call_args.args[0]
    assert [n.content for n in nodes] == ["two", "three"]
    persisted = json.loads(json_path.read_text(encoding="utf-8"))
    assert [item["content"] for item in persisted] == ["two", "three"]
    assert out_path.read_text(encoding="utf-8") == "twothree"


def test_code_interpreter_load_output_keeps_all_when_limit_zero(tmp_path):
    tool, _, tmp_dir, plugin = _tool(tmp_path)
    plugin.get_option_value.return_value = 0
    (tmp_dir / tool.file_output_json).write_text(json.dumps([
        {"content": "a", "type": "stdout", "images": [], "files": []},
        {"content": "b", "type": "stdout", "images": [], "files": []},
    ]), encoding="utf-8")
    tool.save_output_nodes = MagicMock()

    tool.load_output()

    nodes = tool.signals.restore_nodes.emit.call_args.args[0]
    assert [n.content for n in nodes] == ["a", "b"]
    tool.save_output_nodes.assert_not_called()


def test_code_interpreter_load_output_tolerates_invalid_json(tmp_path):
    tool, _, tmp_dir, _ = _tool(tmp_path)
    (tmp_dir / tool.file_output_json).write_text("{broken", encoding="utf-8")
    tool.load_output()
    tool.signals.restore_nodes.emit.assert_called_once_with([])


def test_code_interpreter_save_output_writes_plaintext_and_json_nodes(tmp_path):
    tool, _, tmp_dir, _ = _tool(tmp_path)
    tool.dialog.widget.output.get_plaintext.return_value = "plain"
    n1 = SimpleNamespace(content="x", type="stdout", images=["i"], files=[])
    n2 = SimpleNamespace(content="y", type="stderr", images=[], files=["f"])
    tool.dialog.widget.output.get_nodes.return_value = [n1, n2]

    tool.save_output()

    assert (tmp_dir / tool.file_output).read_text(encoding="utf-8") == "plain"
    data = json.loads((tmp_dir / tool.file_output_json).read_text(encoding="utf-8"))
    assert data == [
        {"content": "x", "type": "stdout", "images": ["i"], "files": []},
        {"content": "y", "type": "stderr", "images": [], "files": ["f"]},
    ]


def test_code_interpreter_save_output_nodes_accepts_explicit_nodes(tmp_path):
    tool, _, tmp_dir, _ = _tool(tmp_path)
    node = SimpleNamespace(content="x", type="stdout", images=[], files=[])
    tool.save_output_nodes([node])
    assert json.loads((tmp_dir / tool.file_output_json).read_text(encoding="utf-8"))[0]["content"] == "x"
    tool.dialog.widget.output.get_nodes.assert_not_called()


def test_code_interpreter_clear_history_output_and_all_remove_both_state_files(tmp_path):
    tool, _, tmp_dir, _ = _tool(tmp_path)
    input_path = tmp_dir / tool.file_input
    output_path = tmp_dir / tool.file_output
    json_path = tmp_dir / tool.file_output_json
    for path in (input_path, output_path, json_path):
        path.write_text("x", encoding="utf-8")

    tool.clear_history()
    assert not input_path.exists()
    tool.signals.clear_history.emit.assert_called_once_with()

    tool.clear_output()
    assert not output_path.exists()
    assert not json_path.exists()
    tool.signals.clear_output.emit.assert_called_once_with()

    input_path.write_text("x", encoding="utf-8")
    output_path.write_text("x", encoding="utf-8")
    json_path.write_text("x", encoding="utf-8")
    tool.clear_all()
    assert not input_path.exists() and not output_path.exists() and not json_path.exists()


def test_code_interpreter_clear_requires_confirmation_unless_forced(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.clear_output = MagicMock()
    with patch("pygpt_net.tools.code_interpreter.tool.trans", return_value="confirm"):
        tool.clear()
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="interpreter.clear", id=0, msg="confirm")
    tool.clear_output.assert_not_called()
    tool.clear(force=True)
    tool.clear_output.assert_called_once_with()


def test_code_interpreter_append_to_edit_preserves_existing_history(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.get_history = MagicMock(return_value="old")
    tool.save_history = MagicMock()
    tool.load_history = MagicMock()
    tool.append_to_edit("new")
    tool.save_history.assert_called_once_with("old\nnew")
    tool.load_history.assert_called_once_with()

    tool.get_history.return_value = ""
    tool.save_history.reset_mock()
    tool.append_to_edit("first")
    tool.save_history.assert_called_once_with("first")


def test_code_interpreter_store_history_skips_missing_history_widget(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.save_history = MagicMock()
    widget = SimpleNamespace(history=None)
    tool.store_history(widget)
    tool.save_history.assert_not_called()

    history = MagicMock()
    history.get_plaintext.return_value = "code"
    tool.store_history(SimpleNamespace(history=history))
    tool.save_history.assert_called_once_with("code")


def test_code_interpreter_simple_state_accessors_and_toolbar(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.ipython = False
    tool.opened = True
    assert tool.is_ipython() is False
    assert tool.is_opened() is True

    tool.get_output = MagicMock(return_value="out")
    tool.get_history = MagicMock(return_value="hist")
    assert tool.get_current_output() == "out"
    assert tool.get_current_history() == "hist"

    tool.dialog.widget.checkbox_all.isChecked.return_value = True
    assert tool.is_all() is True
    assert tool.get_toolbar_icon() is tool.window.ui.nodes["icon.interpreter"]
    tool.toggle_icon(True)
    tool.window.ui.nodes["icon.interpreter"].setVisible.assert_called_once_with(True)


def test_code_interpreter_toggle_settings_update_config_and_signals(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    widget = SimpleNamespace(
        checkbox_auto_clear=MagicMock(),
        checkbox_ipython=MagicMock(),
        checkbox_all=MagicMock(),
    )
    widget.checkbox_auto_clear.isChecked.return_value = True
    tool.toggle_auto_clear(widget)
    assert tool.auto_clear is True
    tool.window.core.config.set.assert_called_with("interpreter.auto_clear", True)
    tool.signals.set_checkbox_auto_clear.emit.assert_called_once_with(True)

    widget.checkbox_ipython.isChecked.return_value = False
    tool.toggle_ipython(widget)
    assert tool.ipython is False
    tool.window.core.config.set.assert_called_with("interpreter.ipython", False)
    tool.signals.toggle_all_visible.emit.assert_called_with(True)

    widget.checkbox_ipython.isChecked.return_value = True
    tool.toggle_ipython(widget)
    tool.signals.toggle_all_visible.emit.assert_called_with(False)

    widget.checkbox_all.isChecked.return_value = True
    tool.toggle_all(widget)
    tool.window.core.config.set.assert_called_with("interpreter.execute_all", True)
    tool.signals.set_checkbox_all.emit.assert_called_once_with(True)


def test_code_interpreter_setup_theme_uses_current_font_size(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    tool.window.core.config.get.return_value = 17
    tool.setup_theme()
    assert tool.dialog.widget.output.value == 17


def test_code_interpreter_lang_mappings(tmp_path):
    tool, _, _, _ = _tool(tmp_path)
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.interpreter": "menu.tools.interpreter"}
    }
