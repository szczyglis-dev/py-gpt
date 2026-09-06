from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.code_interpreter.tool import CodeInterpreter


def _sig():
    return SimpleNamespace(emit=MagicMock())


def _tool():
    tool = CodeInterpreter()
    tool.signals = SimpleNamespace(
        focus_input=_sig(),
        append_input=_sig(),
        set_checkbox_auto_clear=_sig(),
        set_checkbox_ipython=_sig(),
        set_checkbox_all=_sig(),
        toggle_all_visible=_sig(),
    )
    tabs = MagicMock(); tabs.column_idx = 0
    window = SimpleNamespace(
        controller=SimpleNamespace(
            kernel=MagicMock(),
            command=MagicMock(),
            ui=SimpleNamespace(tabs=tabs),
        ),
        core=SimpleNamespace(config=MagicMock()),
        ui=SimpleNamespace(dialogs=MagicMock(), nodes={"icon.interpreter": MagicMock()}),
        dispatch=MagicMock(),
    )
    tool.window = window
    tool.dialog = SimpleNamespace(widget=SimpleNamespace(
        input=MagicMock(), history=MagicMock(), output=MagicMock(), checkbox_all=MagicMock(), on_open=MagicMock()
    ))
    return tool


def _assert_execute_event(tool, expected_cmd, expected_code, auto_init=None):
    event = tool.window.controller.command.dispatch_only.call_args.args[0]
    command = event.data["commands"][0]
    assert command["cmd"] == expected_cmd
    assert command["params"]["code"] == expected_code
    assert command["params"]["path"] == tool.file_current
    if auto_init is not None:
        assert command["params"].get("auto_init") is auto_init
    assert command["silent"] is True
    assert command["force"] is True
    assert event.data["silent"] is True
    assert event.ctx is not None


def test_code_interpreter_send_input_normalizes_tabs_dispatches_ipython_and_clears_input():
    tool = _tool()
    tool.store_history = MagicMock()
    tool.is_all = MagicMock(return_value=False)
    widget = SimpleNamespace(input=MagicMock(), history=MagicMock())
    widget.input.toPlainText.return_value = "\tprint(1)\n"

    tool.send_input(widget)

    tool.window.controller.kernel.resume.assert_called_once_with()
    tool.store_history.assert_called_once_with(widget)
    _assert_execute_event(tool, "ipython_execute", "print(1)", auto_init=True)
    widget.input.clear.assert_called_once_with()
    widget.input.setFocus.assert_called_once_with()


def test_code_interpreter_send_input_respects_auto_clear_and_execute_all():
    tool = _tool()
    tool.ipython = False
    tool.auto_clear = True
    tool.clear_output = MagicMock()
    tool.store_history = MagicMock()
    tool.is_all = MagicMock(return_value=True)
    widget = SimpleNamespace(input=MagicMock(), history=MagicMock())
    widget.input.toPlainText.return_value = "x = 1"

    tool.send_input(widget)

    tool.clear_output.assert_called_once_with()
    _assert_execute_event(tool, "code_execute_all", "x = 1", auto_init=True)


def test_code_interpreter_send_input_empty_non_ipython_does_not_dispatch():
    tool = _tool()
    tool.ipython = False
    tool.store_history = MagicMock()
    tool.is_all = MagicMock(return_value=False)
    widget = SimpleNamespace(input=MagicMock(), history=MagicMock())
    widget.input.toPlainText.return_value = "   "

    tool.send_input(widget)
    tool.window.controller.command.dispatch_only.assert_not_called()


def test_code_interpreter_send_input_restart_and_clear_commands_short_circuit():
    tool = _tool()
    tool.store_history = MagicMock()
    tool.restart_kernel = MagicMock()
    tool.clear = MagicMock()
    widget = SimpleNamespace(input=MagicMock(), history=MagicMock())

    widget.input.toPlainText.return_value = "/restart now"
    tool.send_input(widget)
    tool.restart_kernel.assert_called_once_with()
    tool.window.controller.command.dispatch_only.assert_not_called()
    widget.input.clear.assert_called_once_with()
    widget.input.setFocus.assert_called_once_with()

    widget.input.reset_mock()
    widget.input.toPlainText.return_value = "/clear please"
    tool.send_input(widget)
    tool.clear.assert_called_once_with(force=True)
    assert tool.window.controller.command.dispatch_only.call_count == 0


def test_code_interpreter_run_input_dispatches_native_and_ipython_modes():
    tool = _tool()
    tool.ipython = False
    tool.is_all = MagicMock(return_value=False)
    tool.run_input("print(2)")
    _assert_execute_event(tool, "code_execute", "print(2)")

    tool.window.controller.command.dispatch_only.reset_mock()
    tool.ipython = True
    tool.run_input("print(3)")
    _assert_execute_event(tool, "ipython_execute", "print(3)")


def test_code_interpreter_run_input_execute_all_empty_and_control_commands():
    tool = _tool()
    tool.ipython = False
    tool.is_all = MagicMock(return_value=True)
    tool.run_input("x")
    _assert_execute_event(tool, "code_execute_all", "x")

    tool.window.controller.command.dispatch_only.reset_mock()
    tool.is_all.return_value = False
    tool.run_input("")
    tool.window.controller.command.dispatch_only.assert_not_called()

    tool.restart_kernel = MagicMock(); tool.clear = MagicMock()
    tool.run_input("/restart"); tool.restart_kernel.assert_called_once_with()
    tool.run_input("/clear"); tool.clear.assert_called_once_with(force=True)


def test_code_interpreter_restart_kernel_dispatches_command_and_timezone_free_status():
    tool = _tool()
    with patch("pygpt_net.tools.code_interpreter.tool.strftime", return_value="12:34:56"):
        tool.restart_kernel()

    tool.window.controller.kernel.resume.assert_called_once_with()
    command_event = tool.window.controller.command.dispatch_only.call_args.args[0]
    command = command_event.data["commands"][0]
    assert command == {
        "cmd": "ipython_kernel_restart",
        "params": {},
        "silent": True,
        "force": True,
    }
    tool.signals.focus_input.emit.assert_called_once_with()
    status_event = tool.window.dispatch.call_args.args[0]
    assert status_event.data["status"] == "[OK] Kernel restarted at 12:34:56."


def test_code_interpreter_update_input_append_and_cursor_helpers():
    tool = _tool()
    tool.dialog.widget.input.toPlainText.return_value = "code"
    tool.update_input()
    tool.window.core.config.set.assert_called_once_with("interpreter.input", "code")

    tool.append_to_input("more")
    tool.signals.append_input.emit.assert_called_once_with("more")

    tool.cursor_to_end()
    tool.dialog.widget.history.scroll_to_bottom.assert_called_once_with()

    tool.scroll_to_bottom()
    assert tool.dialog.widget.history.scroll_to_bottom.call_count == 2
    tool.dialog.widget.output.scroll_to_bottom.assert_called_once_with()


def test_code_interpreter_open_close_toggle_and_show_hide():
    tool = _tool()
    tool.load_history = MagicMock(); tool.load_output = MagicMock(); tool.update = MagicMock()
    tool.cursor_to_end = MagicMock(); tool.scroll_to_bottom = MagicMock()

    tool.open()
    assert tool.opened is True and tool.auto_opened is False
    tool.window.ui.dialogs.open.assert_called_once_with("interpreter", width=800, height=600)
    tool.dialog.widget.input.setFocus.assert_called_once_with()
    tool.dialog.widget.on_open.assert_called_once_with()
    tool.cursor_to_end.assert_called_once_with()
    tool.scroll_to_bottom.assert_called_once_with()

    tool.close()
    assert tool.opened is False
    tool.window.ui.dialogs.close.assert_called_once_with("interpreter")

    tool.open = MagicMock(); tool.close = MagicMock(); tool.opened = False
    tool.toggle(); tool.open.assert_called_once_with()
    tool.opened = True; tool.toggle(); tool.close.assert_called_once_with()
    tool.open.reset_mock(); tool.close.reset_mock()
    tool.show_hide(True); tool.show_hide(False)
    tool.open.assert_called_once_with(); tool.close.assert_called_once_with()


def test_code_interpreter_auto_open_current_or_existing_tab_vs_dialog():
    tool = _tool()
    tabs = tool.window.controller.ui.tabs
    tool.open = MagicMock()

    tabs.is_current_tool.return_value = True
    tabs.get_tool_column.return_value = 1
    tabs.column_idx = 0
    tool.auto_open()
    tabs.enable_split_screen.assert_called_once_with(True)
    tool.open.assert_not_called()

    tabs.reset_mock(); tabs.column_idx = 0
    tabs.is_current_tool.return_value = False
    tabs.is_tool.return_value = True
    tabs.get_first_tab_by_tool.return_value = SimpleNamespace(idx=5, column_idx=1)
    tool.auto_open()
    tabs.switch_tab_by_idx.assert_called_once_with(5, 1)
    tabs.enable_split_screen.assert_called_once_with(True)
    tool.open.assert_not_called()

    tabs.reset_mock(); tabs.is_current_tool.return_value = False; tabs.is_tool.return_value = False
    tool.auto_opened = False
    tool.auto_open()
    assert tool.auto_opened is True
    tool.open.assert_called_once_with()


def test_code_interpreter_as_tab_setup_dialogs_and_theme_helpers():
    tool = _tool()
    tab = object()
    dialog_tool = MagicMock(); inner = MagicMock(); dialog_tool.as_tab.return_value = inner
    tab_widget = MagicMock()
    tool.load_history = MagicMock(); tool.load_output = MagicMock()

    with patch("pygpt_net.tools.code_interpreter.tool.Tool", return_value=dialog_tool), \
            patch("pygpt_net.tools.code_interpreter.tool.TabWidget", return_value=tab_widget):
        result = tool.as_tab(tab)
    assert result is tab_widget
    tab_widget.from_tool.assert_called_once_with(inner)
    tab_widget.setup.assert_called_once_with()
    tool.load_history.assert_called_once_with()
    tool.load_output.assert_called_once_with()
    dialog_tool.set_tab.assert_called_once_with(tab)

    dialog = MagicMock()
    with patch("pygpt_net.tools.code_interpreter.tool.Tool", return_value=dialog):
        tool.setup_dialogs()
    dialog.setup.assert_called_once_with()
    dialog.set_is_dialog.assert_called_once_with(True)
