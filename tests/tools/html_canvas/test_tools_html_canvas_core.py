from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.html_canvas.tool import HtmlCanvas


def _tool(tmp_path):
    tool = HtmlCanvas()
    config = MagicMock()
    config.get_user_dir.side_effect = lambda kind: str(tmp_path / kind)
    (tmp_path / "tmp").mkdir(exist_ok=True)
    (tmp_path / "data").mkdir(exist_ok=True)
    tabs = MagicMock()
    tabs.column_idx = 0
    window = SimpleNamespace(
        core=SimpleNamespace(config=config),
        controller=SimpleNamespace(
            ui=SimpleNamespace(tabs=tabs),
            chat=SimpleNamespace(common=MagicMock()),
        ),
        ui=SimpleNamespace(dialogs=MagicMock(), nodes={"icon.html_canvas": MagicMock()}),
    )
    tool.window = window
    tool.dialog = SimpleNamespace(widget=MagicMock())
    tool.signals = SimpleNamespace(
        reload=SimpleNamespace(emit=MagicMock()),
        update=SimpleNamespace(emit=MagicMock()),
        url=SimpleNamespace(emit=MagicMock()),
        closed=SimpleNamespace(emit=MagicMock()),
    )
    return tool


def test_html_canvas_defaults_setup_and_reload(tmp_path):
    tool = _tool(tmp_path)
    tool.migrate_legacy_output = MagicMock()
    tool.load_output = MagicMock()
    tool.update = MagicMock()

    tool.setup()
    tool.migrate_legacy_output.assert_called_once_with()
    tool.load_output.assert_called_once_with()
    tool.update.assert_called_once_with()

    tool.setup.reset_mock() if isinstance(tool.setup, MagicMock) else None
    with patch.object(tool, "setup") as setup:
        tool.on_reload()
    setup.assert_called_once_with()

    assert tool.id == "html_canvas"
    assert tool.has_tab is True
    assert tool.file_output == ".canvas.html"


def test_html_canvas_migrate_legacy_output_moves_or_removes_file(tmp_path):
    tool = _tool(tmp_path)
    legacy = tmp_path / "data" / tool.file_output
    current = tmp_path / "tmp" / tool.file_output
    legacy.write_text("legacy", encoding="utf-8")

    tool.migrate_legacy_output()
    assert current.read_text(encoding="utf-8") == "legacy"
    assert not legacy.exists()

    legacy.write_text("stale", encoding="utf-8")
    current.write_text("current", encoding="utf-8")
    tool.migrate_legacy_output()
    assert current.read_text(encoding="utf-8") == "current"
    assert not legacy.exists()


def test_html_canvas_migrate_legacy_output_ignores_oserror(tmp_path):
    tool = _tool(tmp_path)
    legacy = tmp_path / "data" / tool.file_output
    legacy.write_text("legacy", encoding="utf-8")
    with patch("pygpt_net.tools.html_canvas.tool.os.replace", side_effect=OSError("locked")):
        assert tool.migrate_legacy_output() is None


def test_html_canvas_toggle_edit_switches_visibility_and_saves_when_leaving_edit(tmp_path):
    tool = _tool(tmp_path)
    widget = SimpleNamespace(edit=MagicMock(), output=MagicMock())
    widget.edit.toPlainText.return_value = "<b>x</b>"
    tool.set_output = MagicMock()
    tool.save_output = MagicMock()

    tool.is_edit = False
    tool.toggle_edit(widget)
    assert tool.is_edit is True
    widget.edit.setVisible.assert_called_with(True)
    widget.output.setVisible.assert_called_with(False)
    tool.set_output.assert_not_called()

    tool.toggle_edit(widget)
    assert tool.is_edit is False
    tool.set_output.assert_called_once_with("<b>x</b>")
    tool.save_output.assert_called_once_with()


def test_html_canvas_paths_dialog_id_and_url_signal(tmp_path):
    tool = _tool(tmp_path)
    assert tool.get_current_path() == str(tmp_path / "tmp" / ".canvas.html")
    assert tool.get_dialog_id() == "html_canvas"
    tool.set_url("https://example.com")
    tool.signals.url.emit.assert_called_once_with("https://example.com")


def test_html_canvas_set_get_load_save_clear_output_use_tmp_file(tmp_path):
    tool = _tool(tmp_path)
    tool.set_output("<p>Hello</p>")
    path = tmp_path / "tmp" / ".canvas.html"
    assert path.read_text(encoding="utf-8") == "<p>Hello</p>"
    tool.signals.reload.emit.assert_called_once_with(str(path))
    tool.signals.update.emit.assert_called_once_with("<p>Hello</p>")
    assert tool.get_output() == "<p>Hello</p>"

    path.write_text("changed", encoding="utf-8")
    tool.set_output = MagicMock()
    tool.load_output()
    tool.set_output.assert_called_once_with("changed")

    tool.set_output = MagicMock()
    tool.get_output = MagicMock(return_value="snapshot")
    tool.save_output()
    assert path.read_text(encoding="utf-8") == "snapshot"

    tool.set_output = MagicMock()
    tool.clear_output()
    assert not path.exists()
    tool.set_output.assert_called_once_with("")


def test_html_canvas_clear_requires_confirmation_and_clear_all_delegates(tmp_path):
    tool = _tool(tmp_path)
    tool.clear_output = MagicMock()
    with patch("pygpt_net.tools.html_canvas.tool.trans", return_value="confirm"):
        tool.clear()
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="html_canvas.clear", id=0, msg="confirm")
    tool.clear_output.assert_not_called()

    tool.clear(force=True)
    tool.clear_output.assert_called_once_with()
    tool.clear_output.reset_mock()
    tool.clear_all()
    tool.clear_output.assert_called_once_with()


def test_html_canvas_open_only_once_and_optional_load(tmp_path):
    tool = _tool(tmp_path)
    tool.load_output = MagicMock()
    tool.update = MagicMock()

    tool.open(load=True)
    assert tool.opened is True
    assert tool.auto_opened is False
    tool.load_output.assert_called_once_with()
    tool.window.ui.dialogs.open.assert_called_once_with("html_canvas", width=800, height=600)
    tool.dialog.widget.on_open.assert_called_once_with()
    tool.update.assert_called_once_with()

    tool.open(load=True)
    assert tool.window.ui.dialogs.open.call_count == 1


def test_html_canvas_auto_open_handles_current_tab_split_screen(tmp_path):
    tool = _tool(tmp_path)
    tabs = tool.window.controller.ui.tabs
    tabs.is_current_tool.return_value = True
    tabs.get_tool_column.return_value = 1
    tabs.column_idx = 0
    tool.open = MagicMock()

    tool.auto_open()

    tabs.enable_split_screen.assert_called_once_with(True)
    tool.open.assert_not_called()


def test_html_canvas_auto_open_switches_existing_tool_tab(tmp_path):
    tool = _tool(tmp_path)
    tabs = tool.window.controller.ui.tabs
    tabs.is_current_tool.return_value = False
    tabs.is_tool.return_value = True
    tabs.get_first_tab_by_tool.return_value = SimpleNamespace(idx=4, column_idx=1)
    tabs.column_idx = 0
    tool.open = MagicMock()

    tool.auto_open(load=False)

    tabs.switch_tab_by_idx.assert_called_once_with(4, 1)
    tabs.enable_split_screen.assert_called_once_with(True)
    tool.open.assert_not_called()


def test_html_canvas_auto_open_opens_once_when_not_present_in_tabs(tmp_path):
    tool = _tool(tmp_path)
    tabs = tool.window.controller.ui.tabs
    tabs.is_current_tool.return_value = False
    tabs.is_tool.return_value = False
    tool.open = MagicMock()

    tool.auto_open(load=False)
    assert tool.auto_opened is True
    tool.open.assert_called_once_with(load=False)

    tool.auto_open(load=False)
    assert tool.open.call_count == 1


def test_html_canvas_open_file_reads_selected_html_and_opens_canvas(tmp_path):
    tool = _tool(tmp_path)
    src = tmp_path / "sample.html"
    src.write_text("<h1>x</h1>", encoding="utf-8")
    tool.window.core.config.get_last_used_dir.return_value = str(tmp_path)
    dialog = MagicMock()
    dialog.exec.return_value = True
    dialog.selectedFiles.return_value = [str(src)]
    tool.set_output = MagicMock()
    tool.open = MagicMock()

    with patch("pygpt_net.tools.html_canvas.tool.QFileDialog", return_value=dialog):
        tool.open_file()

    dialog.setDirectory.assert_called_once_with(str(tmp_path))
    tool.set_output.assert_called_once_with("<h1>x</h1>")
    tool.open.assert_called_once_with()


def test_html_canvas_close_toggle_show_hide_and_toolbar_icon(tmp_path):
    tool = _tool(tmp_path)
    tool.update = MagicMock()
    tool.opened = True
    tool.close()
    assert tool.opened is False
    tool.window.ui.dialogs.close.assert_called_once_with("html_canvas")

    tool.open = MagicMock(); tool.close = MagicMock(); tool.opened = False
    tool.toggle(); tool.open.assert_called_once_with()
    tool.opened = True; tool.toggle(); tool.close.assert_called_once_with()
    tool.open.reset_mock(); tool.close.reset_mock()
    tool.show_hide(True); tool.show_hide(False)
    tool.open.assert_called_once_with(); tool.close.assert_called_once_with()

    icon = tool.get_toolbar_icon()
    assert icon is tool.window.ui.nodes["icon.html_canvas"]
    tool.toggle_icon(True)
    icon.setVisible.assert_called_once_with(True)


def test_html_canvas_get_current_output_delegates_get_output(tmp_path):
    tool = _tool(tmp_path)
    tool.get_output = MagicMock(return_value="html")
    assert tool.get_current_output() == "html"


def test_html_canvas_handle_save_as_cleans_by_type_and_defers_save(tmp_path):
    tool = _tool(tmp_path)

    def run_now(_delay, callback):
        callback()

    with patch("pygpt_net.tools.html_canvas.tool.output_clean_html", return_value="clean-html") as clean_html, \
            patch("pygpt_net.tools.html_canvas.tool.output_html2text", return_value="plain") as html2text, \
            patch("pygpt_net.tools.html_canvas.tool.QTimer.singleShot", side_effect=run_now):
        tool.handle_save_as("<b>x</b>", "html")
        clean_html.assert_called_once_with("<b>x</b>")
        tool.window.controller.chat.common.save_text.assert_called_with("clean-html", "html")

        tool.handle_save_as("<b>x</b>", "txt")
        html2text.assert_called_once_with("<b>x</b>")
        tool.window.controller.chat.common.save_text.assert_called_with("plain", "txt")


def test_html_canvas_as_tab_wires_tool_widget_and_loads_output(tmp_path):
    tool = _tool(tmp_path)
    tab = object()
    dialog_tool = MagicMock()
    inner = MagicMock()
    dialog_tool.as_tab.return_value = inner
    tab_widget = MagicMock()
    tool.load_output = MagicMock()

    with patch("pygpt_net.tools.html_canvas.tool.Tool", return_value=dialog_tool), \
            patch("pygpt_net.tools.html_canvas.tool.TabWidget", return_value=tab_widget):
        result = tool.as_tab(tab)

    assert result is tab_widget
    tab_widget.from_tool.assert_called_once_with(inner)
    tab_widget.setup.assert_called_once_with()
    tool.load_output.assert_called_once_with()
    dialog_tool.set_tab.assert_called_once_with(tab)


def test_html_canvas_setup_dialogs_and_lang_mappings(tmp_path):
    tool = _tool(tmp_path)
    dialog = MagicMock()
    with patch("pygpt_net.tools.html_canvas.tool.Tool", return_value=dialog):
        tool.setup_dialogs()
    dialog.setup.assert_called_once_with()
    assert tool.dialog is dialog
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.html_canvas": "menu.tools.html_canvas"}
    }
