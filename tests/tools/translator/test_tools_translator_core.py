import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.translator.tool import Translator
from pygpt_net.item.model import ModelItem


def _sig():
    return SimpleNamespace(emit=MagicMock(), connect=MagicMock())


def _signals():
    return SimpleNamespace(
        save_config=_sig(), translate=_sig(), append=_sig(), replace=_sig(), set_status=_sig(),
        reload=_sig(), update=_sig(), load_config=_sig(), on_load=_sig(),
    )


def _tool(tmp_path):
    tool = Translator()
    tool.signals = _signals()
    config = MagicMock(); config.get_user_dir.return_value = str(tmp_path)
    models = MagicMock(); text = MagicMock()
    window = SimpleNamespace(
        core=SimpleNamespace(config=config, models=models, text=text, idx=SimpleNamespace(indexing=MagicMock()), logger=MagicMock()),
        controller=SimpleNamespace(chat=SimpleNamespace(common=MagicMock())),
        ui=SimpleNamespace(dialogs=MagicMock(), nodes={"icon.translator": MagicMock()}),
        threadpool=MagicMock(), dispatch=MagicMock(),
    )
    tool.window = window
    return tool


def test_translator_defaults_setup_and_content_signals(tmp_path):
    tool = _tool(tmp_path)
    tool.update = MagicMock()
    tool.setup()
    tool.signals.save_config.connect.assert_called_once_with(tool.save_config)
    tool.signals.translate.connect.assert_called_once_with(tool.translate)
    tool.update.assert_called_once_with()
    assert tool.id == "translator"
    assert tool.config_file == ".translator.json"

    tool.append_content("left", "a")
    tool.replace_content("right", "b")
    tool.signals.append.emit.assert_called_once_with("left", "a")
    tool.signals.replace.emit.assert_called_once_with("right", "b")


def test_translator_update_delegates_update_menu(tmp_path):
    tool = _tool(tmp_path)
    tool.update_menu = MagicMock()
    tool.update()
    tool.update_menu.assert_called_once_with()
    assert tool.on_reload() is None


def test_translator_translate_reports_missing_model_without_worker(tmp_path):
    tool = _tool(tmp_path)
    tool.set_status = MagicMock()
    tool.window.core.text.get_language_name.side_effect = lambda code: {"en": "English", "pl": "Polish"}[code]
    tool.window.core.models.get.return_value = None

    with patch("pygpt_net.tools.translator.tool.trans", return_value="sending"):
        tool.translate("left", "missing", "hello", "en", "pl")

    tool.set_status.assert_any_call("sending")
    tool.set_status.assert_called_with("Translation model 'missing' not found.")
    tool.window.threadpool.start.assert_not_called()


def test_translator_translate_builds_mocked_worker_and_clears_opposite_column(tmp_path):
    tool = _tool(tmp_path)
    tool.set_status = MagicMock(); tool.clear_right = MagicMock(); tool.clear_left = MagicMock()
    tool.window.core.text.get_language_name.side_effect = lambda code: {"en": "English", "pl": "Polish"}[code]
    model = object(); tool.window.core.models.get.return_value = model
    worker = SimpleNamespace(signals=None, kwargs={})
    worker_signal = _sig()
    signal_bundle = SimpleNamespace(updated=worker_signal)

    with patch("pygpt_net.tools.translator.tool.Worker", return_value=worker) as worker_cls, \
            patch("pygpt_net.tools.translator.tool.WorkerSignals", return_value=signal_bundle), \
            patch("pygpt_net.tools.translator.tool.trans", return_value="sending"):
        tool.translate("left", "model", "hello", "en", "pl")

    tool.clear_right.assert_called_once_with(force=True)
    worker_cls.assert_called_once_with(tool.translate_execute)
    worker_signal.connect.assert_called_once_with(tool.handle_update)
    assert worker.kwargs == {
        "id": "left",
        "model": model,
        "text": "hello",
        "from_lang_code": "en",
        "from_lang": "English",
        "to_lang": "Polish",
        "to_lang_code": "pl",
        "window": tool.window,
        "updated_signal": worker_signal,
    }
    tool.window.threadpool.start.assert_called_once_with(worker)


def test_translator_translate_right_clears_left(tmp_path):
    tool = _tool(tmp_path)
    tool.set_status = MagicMock(); tool.clear_right = MagicMock(); tool.clear_left = MagicMock()
    tool.window.core.text.get_language_name.return_value = "Lang"
    tool.window.core.models.get.return_value = object()
    worker = SimpleNamespace(signals=None, kwargs={})
    with patch("pygpt_net.tools.translator.tool.Worker", return_value=worker), \
            patch("pygpt_net.tools.translator.tool.WorkerSignals", return_value=SimpleNamespace(updated=_sig())), \
            patch("pygpt_net.tools.translator.tool.trans", return_value="sending"):
        tool.translate("right", "model", "hello", "en", "pl")
    tool.clear_left.assert_called_once_with(force=True)


def test_translator_set_status_dispatches_kernel_event_and_signal(tmp_path):
    tool = _tool(tmp_path)
    with patch("pygpt_net.tools.translator.tool.QApplication.processEvents") as process:
        tool.set_status("Working")
    event = tool.window.dispatch.call_args.args[0]
    assert event.data["status"] == "Working"
    tool.signals.set_status.emit.assert_called_once_with("Working")
    process.assert_called_once_with()


def test_translator_translate_execute_dispatches_force_call_with_tools_disabled(tmp_path):
    tool = _tool(tmp_path)
    updated = MagicMock()

    def dispatch(event):
        event.data["response"] = "Cześć"

    tool.window.dispatch.side_effect = dispatch
    model = ModelItem()
    tool.translate_execute(tool.window, "left", model, "en", "English", "pl", "Polish", "Hello", updated)

    event = tool.window.dispatch.call_args.args[0]
    assert event.data["extra"] == {"disable_tools": True}
    ctx = event.data["context"]
    assert ctx.prompt == "Hello"
    assert ctx.model is model
    assert ctx.force is True
    assert "from English to Polish" in ctx.system_prompt
    updated.emit.assert_called_once_with("left", "Cześć")


def test_translator_translate_execute_auto_detect_prompt(tmp_path):
    tool = _tool(tmp_path)
    updated = MagicMock()
    tool.window.dispatch.side_effect = lambda event: event.data.__setitem__("response", "Hola")
    tool.translate_execute(tool.window, "right", ModelItem(), "-", "Auto", "es", "Spanish", "Hi", updated)
    ctx = tool.window.dispatch.call_args.args[0].data["context"]
    assert "Translate provided text to Spanish" in ctx.system_prompt
    assert "from Auto" not in ctx.system_prompt


def test_translator_handle_update_success_failure_and_direction(tmp_path):
    tool = _tool(tmp_path)
    tool.set_status = MagicMock(); tool.replace_content = MagicMock()

    tool.handle_update("left", "translated")
    tool.set_status.assert_called_with("Translation completed successfully.")
    tool.replace_content.assert_called_once_with("right", "translated")

    tool.set_status.reset_mock(); tool.replace_content.reset_mock()
    tool.handle_update("right", "translated")
    tool.replace_content.assert_called_once_with("left", "translated")

    tool.set_status.reset_mock(); tool.replace_content.reset_mock()
    tool.handle_update("left", "")
    tool.set_status.assert_called_once_with("Translation failed, no response received.")
    tool.replace_content.assert_not_called()


def test_translator_paths_dialog_id_and_open_file(tmp_path):
    tool = _tool(tmp_path)
    assert tool.get_current_path() == str(tmp_path / ".translator.json")
    assert tool.get_dialog_id() == "translator"
    tool.window.core.config.get_last_used_dir.return_value = str(tmp_path)
    dialog = MagicMock(); dialog.exec.return_value = True; dialog.selectedFiles.return_value = ["/tmp/a.txt"]
    tool.window.core.idx.indexing.read_text_content.return_value = ("content", {})
    tool.replace_content = MagicMock()

    with patch("pygpt_net.tools.translator.tool.QFileDialog", return_value=dialog):
        tool.open_file()
    tool.window.core.idx.indexing.read_text_content.assert_called_once_with("/tmp/a.txt")
    tool.replace_content.assert_called_once_with("left", "content")


def test_translator_open_file_logs_read_errors(tmp_path):
    tool = _tool(tmp_path)
    dialog = MagicMock(); dialog.exec.return_value = True; dialog.selectedFiles.return_value = ["/tmp/a.txt"]
    tool.window.core.idx.indexing.read_text_content.side_effect = RuntimeError("bad")
    with patch("pygpt_net.tools.translator.tool.QFileDialog", return_value=dialog):
        tool.open_file()
    assert "Error reading file /tmp/a.txt: bad" in tool.window.core.logger.error.call_args.args[0]


def test_translator_set_output_get_output_and_reload(tmp_path):
    tool = _tool(tmp_path)
    tool.set_output("raw")
    path = tmp_path / ".translator.json"
    assert path.read_text(encoding="utf-8") == "raw"
    tool.signals.reload.emit.assert_called_once_with(str(path))
    tool.signals.update.emit.assert_called_once_with("raw")
    assert tool.get_output() == "raw"

    tool.load_config = MagicMock(); tool.update = MagicMock()
    tool.reload_output()
    tool.load_config.assert_called_once_with(); tool.update.assert_called_once_with()


def test_translator_save_and_load_config_roundtrip_unicode(tmp_path):
    tool = _tool(tmp_path)
    config = {"left": {"lang": "pl"}, "label": "żółć"}
    tool.save_config(config)
    raw = (tmp_path / ".translator.json").read_text(encoding="utf-8")
    assert "żółć" in raw
    tool.load_config()
    tool.signals.load_config.emit.assert_called_once_with(config)


def test_translator_load_config_ignores_missing_or_non_dict_json(tmp_path):
    tool = _tool(tmp_path)
    tool.load_config()
    tool.signals.load_config.emit.assert_not_called()
    (tmp_path / ".translator.json").write_text(json.dumps([1, 2]), encoding="utf-8")
    tool.load_config()
    tool.signals.load_config.emit.assert_not_called()


def test_translator_clear_variants_confirm_and_force(tmp_path):
    tool = _tool(tmp_path)
    tool.replace_content = MagicMock()
    with patch("pygpt_net.tools.translator.tool.trans", side_effect=lambda key: key):
        tool.clear_left(); tool.clear_right(); tool.clear()
    assert tool.window.ui.dialogs.confirm.call_count == 3
    tool.replace_content.assert_not_called()

    tool.clear_left(force=True); tool.clear_right(force=True)
    assert tool.replace_content.call_args_list[-2].args == ("left", "")
    assert tool.replace_content.call_args_list[-1].args == ("right", "")

    tool.clear_output = MagicMock()
    tool.clear(force=True); tool.clear_all()
    assert tool.clear_output.call_count == 2


def test_translator_open_close_toggle_show_hide_and_toolbar(tmp_path):
    tool = _tool(tmp_path)
    tool.load_config = MagicMock(); tool.update = MagicMock()
    tool.open()
    assert tool.opened is True and tool.auto_opened is False
    tool.load_config.assert_called_once_with()
    tool.window.ui.dialogs.open.assert_called_once_with("translator", width=800, height=600)
    tool.signals.on_load.emit.assert_called_once_with()

    tool.open()
    assert tool.window.ui.dialogs.open.call_count == 1
    tool.close()
    assert tool.opened is False
    tool.window.ui.dialogs.close.assert_called_once_with("translator")

    tool.open = MagicMock(); tool.close = MagicMock(); tool.opened = False
    tool.toggle(); tool.open.assert_called_once_with()
    tool.opened = True; tool.toggle(); tool.close.assert_called_once_with()
    tool.open.reset_mock(); tool.close.reset_mock()
    tool.show_hide(True); tool.show_hide(False)
    tool.open.assert_called_once_with(); tool.close.assert_called_once_with()

    assert tool.get_toolbar_icon() is tool.window.ui.nodes["icon.translator"]
    tool.toggle_icon(False)
    tool.window.ui.nodes["icon.translator"].setVisible.assert_called_once_with(False)


def test_translator_current_output_and_handle_save_as(tmp_path):
    tool = _tool(tmp_path)
    tool.get_output = MagicMock(return_value="value")
    assert tool.get_current_output() == "value"

    def immediately(_delay, callback): callback()
    with patch("pygpt_net.tools.translator.tool.output_clean_html", return_value="clean") as clean, \
            patch("pygpt_net.tools.translator.tool.output_html2text", return_value="plain") as plain, \
            patch("pygpt_net.tools.translator.tool.QTimer.singleShot", side_effect=immediately):
        tool.handle_save_as("<b>x</b>", "html")
        clean.assert_called_once_with("<b>x</b>")
        tool.window.controller.chat.common.save_text.assert_called_with("clean", "html")
        tool.handle_save_as("<b>x</b>", "txt")
        plain.assert_called_once_with("<b>x</b>")
        tool.window.controller.chat.common.save_text.assert_called_with("plain", "txt")


def test_translator_as_tab_setup_dialogs_and_lang_mappings(tmp_path):
    tool = _tool(tmp_path)
    tab = object(); dialog_tool = MagicMock(); inner = MagicMock(); dialog_tool.as_tab.return_value = inner
    tab_widget = MagicMock(); tool.load_config = MagicMock()
    with patch("pygpt_net.tools.translator.tool.Tool", return_value=dialog_tool), \
            patch("pygpt_net.tools.translator.tool.TabWidget", return_value=tab_widget):
        result = tool.as_tab(tab)
    assert result is tab_widget
    tab_widget.from_tool.assert_called_once_with(inner)
    tab_widget.setup.assert_called_once_with()
    tool.load_config.assert_called_once_with()
    dialog_tool.set_tab.assert_called_once_with(tab)

    dialog = MagicMock()
    with patch("pygpt_net.tools.translator.tool.Tool", return_value=dialog):
        tool.setup_dialogs()
    assert tool.dialog is dialog
    dialog.setup.assert_called_once_with()
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.translator": "menu.tools.translator"}
    }
