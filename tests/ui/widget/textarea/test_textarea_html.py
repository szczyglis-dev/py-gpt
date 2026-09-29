from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.textarea.html import HtmlOutput, CustomWebEnginePage, Bridge


def _window():
    return SimpleNamespace(
        core=SimpleNamespace(
            config=SimpleNamespace(has=MagicMock(return_value=True), get=MagicMock(return_value=1.5)),
            debug=SimpleNamespace(log=MagicMock()),
            filesystem=SimpleNamespace(url=SimpleNamespace(handle=MagicMock())),
        ),
        controller=SimpleNamespace(
            finder=SimpleNamespace(open=MagicMock(), focus_in=MagicMock()),
            chat=SimpleNamespace(render=SimpleNamespace(scroll=0)),
            ctx=SimpleNamespace(extra=SimpleNamespace(
                copy_code_text=MagicMock(), preview_code_text=MagicMock(), run_code_text=MagicMock()
            )),
        ),
    )


def test_html_content_state_accessors_and_reset():
    widget = SimpleNamespace(plain="", html_content="", setHtml=MagicMock())
    HtmlOutput.set_plaintext(widget, "plain")
    HtmlOutput.set_html_content(widget, "<b>x</b>")
    assert widget.plain == "plain"
    assert HtmlOutput.get_html_content(widget) == "<b>x</b>"
    widget.setHtml.assert_called_once_with("<b>x</b>", baseUrl="file://")
    HtmlOutput.reset_current_content(widget)
    assert widget.plain == ""
    assert widget.html_content == ""


def test_html_tab_and_meta_setters_store_objects():
    widget = SimpleNamespace(tab=None, meta=None)
    tab = object()
    meta = object()
    HtmlOutput.set_tab(widget, tab)
    HtmlOutput.set_meta(widget, meta)
    assert widget.tab is tab
    assert widget.meta is meta


def test_html_update_zoom_reads_config_and_updates_page():
    window = _window()
    page = MagicMock()
    widget = SimpleNamespace(window=window, page=MagicMock(return_value=page))
    HtmlOutput.update_zoom(widget)
    page.setZoomFactor.assert_called_once_with(1.5)

    page.setZoomFactor.reset_mock()
    window.core.config.has.return_value = False
    HtmlOutput.update_zoom(widget)
    page.setZoomFactor.assert_not_called()


def test_html_zoom_and_selection_helpers_route_to_page():
    page = MagicMock()
    page.zoomFactor.return_value = 1.25
    page.selectedText.return_value = "selected"
    widget = SimpleNamespace(page=MagicMock(return_value=page))
    assert HtmlOutput.get_zoom_value(widget) == 1.25
    assert HtmlOutput.get_selected_text(widget) == "selected"
    HtmlOutput.copy_selected_text(widget)
    HtmlOutput.select_all_text(widget)
    HtmlOutput.unselect_text(widget)
    assert page.triggerAction.call_count == 3


def test_html_update_current_content_requests_plain_and_html_snapshots():
    page = MagicMock()
    widget = SimpleNamespace(
        page=MagicMock(return_value=page),
        set_plaintext=MagicMock(),
        set_html_content=MagicMock(),
    )
    HtmlOutput.update_current_content(widget)
    assert page.runJavaScript.call_count == 2
    assert page.runJavaScript.call_args_list[0].args == (
        "document.getElementById('container').outerHTML", 0, widget.set_plaintext
    )
    assert page.runJavaScript.call_args_list[1].args == (
        "document.documentElement.innerHTML", 0, widget.set_html_content
    )


def test_html_find_and_update_delegate_to_finder():
    window = _window()
    finder = MagicMock()
    widget = SimpleNamespace(window=window, finder=finder)
    HtmlOutput.find_open(widget)
    window.controller.finder.open.assert_called_once_with(finder)
    HtmlOutput.on_update(widget)
    finder.clear.assert_called_once_with()


def test_html_detach_gl_filter_clears_state_even_on_failure():
    gl = MagicMock()
    widget = SimpleNamespace(
        _glwidget=gl,
        _glwidget_filter_installed=True,
        _on_delete_failed=MagicMock(),
    )
    HtmlOutput._detach_gl_event_filter(widget)
    gl.removeEventFilter.assert_called_once_with(widget)
    assert widget._glwidget is None
    assert widget._glwidget_filter_installed is False


def test_custom_page_find_result_updates_finder_state():
    finder = SimpleNamespace(current_match_index=0, matches=0, on_find_finished=MagicMock())
    page = SimpleNamespace(parent=SimpleNamespace(finder=finder))
    result = SimpleNamespace(activeMatch=lambda: 2, numberOfMatches=lambda: 7)
    CustomWebEnginePage.on_find_finished(page, result)
    assert finder.current_match_index == 2
    assert finder.matches == 7
    finder.on_find_finished.assert_called_once_with()


def test_custom_page_set_loaded_is_simple_flag():
    page = SimpleNamespace(loaded=False)
    CustomWebEnginePage.set_loaded(page, True)
    assert page.loaded is True


def test_bridge_routes_code_actions_and_cleanup():
    window = _window()
    bridge = SimpleNamespace(window=window, deleteLater=MagicMock())
    Bridge.copy_text(bridge, "copy")
    Bridge.preview_text(bridge, "preview")
    Bridge.update_scroll_position(bridge, 123)
    window.controller.ctx.extra.copy_code_text.assert_called_once_with("copy")
    window.controller.ctx.extra.preview_code_text.assert_called_once_with("preview")
    assert window.controller.chat.render.scroll == 123
    Bridge.cleanup(bridge)
    assert bridge.window is None
    bridge.deleteLater.assert_called_once_with()
