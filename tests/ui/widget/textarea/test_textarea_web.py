from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.textarea.web import ChatWebOutput, CustomWebEnginePage, Bridge


def _window():
    config = SimpleNamespace(
        has=MagicMock(return_value=True),
        get=MagicMock(return_value=1.4),
        set=MagicMock(),
    )
    option = {"value": 1.0}
    controller = SimpleNamespace(
        finder=SimpleNamespace(open=MagicMock(), focus_in=MagicMock()),
        ui=SimpleNamespace(tabs=SimpleNamespace(on_column_focus=MagicMock())),
        chat=SimpleNamespace(render=SimpleNamespace(
            on_js_ready=MagicMock(),
            scroll=0,
            handle_save_as=MagicMock(),
            handle_audio_read=MagicMock(),
        )),
        settings=SimpleNamespace(editor=SimpleNamespace(get_option=MagicMock(return_value=option))),
        config=SimpleNamespace(apply=MagicMock()),
        ctx=SimpleNamespace(extra=SimpleNamespace(
            copy_code_text=MagicMock(), preview_code_text=MagicMock(), run_code_text=MagicMock()
        )),
    )
    return SimpleNamespace(
        core=SimpleNamespace(
            config=config,
            debug=SimpleNamespace(log=MagicMock()),
            filesystem=SimpleNamespace(url=SimpleNamespace(handle=MagicMock())),
        ),
        controller=controller,
        dispatch=MagicMock(),
    )


def test_web_tab_meta_and_content_accessors():
    widget = SimpleNamespace(tab=None, meta=None, plain="", html_content="")
    tab = object()
    meta = object()
    ChatWebOutput.set_tab(widget, tab)
    ChatWebOutput.set_meta(widget, meta)
    ChatWebOutput.set_plaintext(widget, "plain")
    ChatWebOutput.set_html_content(widget, "body")
    assert ChatWebOutput.get_tab(widget) is tab
    assert widget.meta is meta
    assert widget.plain == "plain"
    assert widget.html_content == "<html>body</html>"


def test_web_reset_content_clears_both_buffers():
    widget = SimpleNamespace(plain="x", html_content="y")
    ChatWebOutput.reset_current_content(widget)
    assert widget.plain == ""
    assert widget.html_content == ""


def test_web_zoom_change_persists_only_when_page_exists():
    window = _window()
    page = MagicMock()
    widget = SimpleNamespace(window=window, page=MagicMock(return_value=page), update_zoom=MagicMock())
    ChatWebOutput.on_zoom_changed(widget, 1.8)
    window.core.config.set.assert_called_once_with("zoom", 1.8)
    widget.update_zoom.assert_called_once_with()

    window.core.config.set.reset_mock()
    widget.page.return_value = None
    ChatWebOutput.on_zoom_changed(widget, 2.0)
    window.core.config.set.assert_not_called()


def test_web_update_zoom_uses_config_and_is_fail_safe():
    window = _window()
    page = MagicMock()
    widget = SimpleNamespace(window=window, page=MagicMock(return_value=page))
    ChatWebOutput.update_zoom(widget)
    page.setZoomFactor.assert_called_once_with(1.4)

    window.core.config.has.side_effect = RuntimeError("bad config")
    ChatWebOutput.update_zoom(widget)


def test_web_zoom_value_defaults_when_page_missing():
    page = MagicMock()
    page.zoomFactor.return_value = 1.7
    widget = SimpleNamespace(page=MagicMock(return_value=page))
    assert ChatWebOutput.get_zoom_value(widget) == 1.7
    widget.page.return_value = None
    assert ChatWebOutput.get_zoom_value(widget) == 1.0


def test_web_selection_actions_are_safe_when_page_missing():
    page = MagicMock()
    page.selectedText.return_value = "selected"
    widget = SimpleNamespace(page=MagicMock(return_value=page))
    assert ChatWebOutput.get_selected_text(widget) == "selected"
    ChatWebOutput.copy_selected_text(widget)
    ChatWebOutput.select_all_text(widget)
    ChatWebOutput.unselect_text(widget)
    assert page.triggerAction.call_count == 3

    widget.page.return_value = None
    assert ChatWebOutput.get_selected_text(widget) == ""
    ChatWebOutput.copy_selected_text(widget)
    ChatWebOutput.select_all_text(widget)
    ChatWebOutput.unselect_text(widget)


def test_web_selected_audio_ignores_empty_text():
    signals = SimpleNamespace(audio_read=SimpleNamespace(emit=MagicMock()))
    widget = SimpleNamespace(get_selected_text=MagicMock(return_value="hello"), signals=signals)
    ChatWebOutput._read_selected_text(widget)
    signals.audio_read.emit.assert_called_once_with("hello")

    signals.audio_read.emit.reset_mock()
    widget.get_selected_text.return_value = ""
    ChatWebOutput._read_selected_text(widget)
    signals.audio_read.emit.assert_not_called()


def test_web_save_selected_emits_current_selection():
    signals = SimpleNamespace(save_as=SimpleNamespace(emit=MagicMock()))
    widget = SimpleNamespace(get_selected_text=MagicMock(return_value="hello"), signals=signals)
    ChatWebOutput._save_selected_txt(widget)
    signals.save_as.emit.assert_called_once_with("hello", "txt")


def test_web_save_all_uses_page_callbacks():
    page = MagicMock()
    signals = SimpleNamespace(save_as=SimpleNamespace(emit=MagicMock()))
    widget = SimpleNamespace(page=MagicMock(return_value=page), signals=signals)
    ChatWebOutput._save_as_text(widget)
    cb = page.toPlainText.call_args.args[0]
    cb("plain")
    signals.save_as.emit.assert_called_once_with("plain", "txt")

    signals.save_as.emit.reset_mock()
    ChatWebOutput._save_as_html(widget)
    cb = page.toHtml.call_args.args[0]
    cb("<html>x</html>")
    signals.save_as.emit.assert_called_once_with("<html>x</html>", "html")


def test_web_focus_helpers_route_column_focus():
    window = _window()
    tab = SimpleNamespace(column_idx=2)
    widget = SimpleNamespace(window=window, tab=tab, setFocus=MagicMock())
    ChatWebOutput.on_focus(widget, object())
    window.controller.ui.tabs.on_column_focus.assert_called_once_with(2)
    widget.setFocus.assert_called_once_with()

    window.controller.ui.tabs.on_column_focus.reset_mock()
    ChatWebOutput.on_focus_js(widget)
    window.controller.ui.tabs.on_column_focus.assert_called_once_with(2)


def test_web_find_and_update_delegate_to_finder():
    window = _window()
    finder = MagicMock()
    widget = SimpleNamespace(window=window, finder=finder)
    ChatWebOutput.find_open(widget)
    window.controller.finder.open.assert_called_once_with(finder)
    ChatWebOutput.on_update(widget)
    finder.clear.assert_called_once_with()


def test_custom_web_page_view_change_persists_zoom_after_loaded():
    window = _window()
    page = SimpleNamespace(
        loaded=True,
        window=window,
        zoomFactor=MagicMock(return_value=1.6),
    )
    CustomWebEnginePage.on_view_changed(page)
    window.core.config.set.assert_called_once_with("zoom", 1.6)
    option = window.controller.settings.editor.get_option.return_value
    assert option["value"] == 1.6
    window.controller.config.apply.assert_called_once_with(
        parent_id="config", key="zoom", option=option
    )


def test_custom_web_page_view_change_ignores_unloaded_page():
    window = _window()
    page = SimpleNamespace(loaded=False, window=window, zoomFactor=MagicMock())
    CustomWebEnginePage.on_view_changed(page)
    page.zoomFactor.assert_not_called()
    window.core.config.set.assert_not_called()


def test_custom_web_page_find_result_updates_finder():
    finder = SimpleNamespace(current_match_index=0, matches=0, on_find_finished=MagicMock())
    page = SimpleNamespace(view=SimpleNamespace(finder=finder))
    result = SimpleNamespace(activeMatch=lambda: 1, numberOfMatches=lambda: 5)
    CustomWebEnginePage.on_find_finished(page, result)
    assert finder.current_match_index == 1
    assert finder.matches == 5
    finder.on_find_finished.assert_called_once_with()


def test_web_bridge_routes_ready_code_and_scroll_state():
    window = _window()
    ready = SimpleNamespace(emit=MagicMock())
    bridge = SimpleNamespace(window=window, readyChanged=ready, deleteLater=MagicMock())
    Bridge.js_ready(bridge, 123)
    ready.emit.assert_called_once_with(True)
    window.controller.chat.render.on_js_ready.assert_called_once_with(123)

    Bridge.copy_text(bridge, "c")
    Bridge.preview_text(bridge, "p")
    Bridge.run_text(bridge, "r")
    window.controller.ctx.extra.copy_code_text.assert_called_once_with("c")
    window.controller.ctx.extra.preview_code_text.assert_called_once_with("p")
    window.controller.ctx.extra.run_code_text.assert_called_once_with("r")

    Bridge.update_scroll_position(bridge, 77)
    assert window.controller.chat.render.scroll == 77

    Bridge.cleanup(bridge)
    assert bridge.window is None
    bridge.deleteLater.assert_called_once_with()
