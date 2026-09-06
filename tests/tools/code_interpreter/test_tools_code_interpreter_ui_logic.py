from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.tools.code_interpreter.ui.html import (
    Bridge,
    CodeBlock,
    CustomWebEnginePage,
    HtmlOutput,
)
from pygpt_net.tools.code_interpreter.ui.widgets import ToolWidget


def test_code_block_roundtrip_defaults_and_string_representation():
    block = CodeBlock("hello", "stderr", images=["a.png"], files=["x.txt"])

    assert block.as_dict() == {
        "content": "hello",
        "type": "stderr",
        "images": ["a.png"],
        "files": ["x.txt"],
    }
    assert str(block) == "CodeBlock(type=stderr, content=hello)"

    restored = CodeBlock("old", "stdin", images=["old"], files=["old"])
    restored.from_dict({"content": "new"})
    assert restored.content == "new"
    assert restored.type == "stdout"
    assert restored.images == []
    assert restored.files == []


def test_html_output_plain_and_html_buffers_are_independent():
    obj = SimpleNamespace(plain="a", html_content="<a>")

    HtmlOutput.append_plaintext(obj, "b")
    assert HtmlOutput.get_plaintext(obj) == "ab"
    HtmlOutput.set_plaintext(obj, "c")
    assert HtmlOutput.get_plaintext(obj) == "c"
    HtmlOutput.clear_plaintext(obj)
    assert HtmlOutput.get_plaintext(obj) == ""

    HtmlOutput.set_html_content(obj, "<b>")
    assert HtmlOutput.get_html_content(obj) == "<b>"
    HtmlOutput.reset_current_content(obj)
    assert obj.plain == ""
    assert obj.html_content == ""


def test_html_output_trim_nodes_filters_empty_blocks_and_keeps_newest_entries():
    nodes = [
        CodeBlock("first"),
        object(),
        CodeBlock(""),
        CodeBlock("image", images=["a.png"]),
        CodeBlock("last"),
    ]
    obj = SimpleNamespace(
        nodes=nodes,
        loaded=False,
        set_plaintext=MagicMock(),
        page=MagicMock(return_value=None),
        insert_output=MagicMock(),
        scroll_to_bottom=MagicMock(),
        update_current_content=MagicMock(),
    )

    changed = HtmlOutput.trim_nodes(obj, 2)

    assert changed is True
    assert [node.content for node in obj.nodes] == ["image", "last"]
    obj.set_plaintext.assert_called_once_with("imagelast")
    obj.insert_output.assert_not_called()
    obj.update_current_content.assert_called_once_with()


def test_html_output_trim_nodes_handles_unlimited_invalid_and_unchanged_values():
    block = CodeBlock("x")
    obj = SimpleNamespace(
        nodes=[block],
        loaded=False,
        set_plaintext=MagicMock(),
        page=MagicMock(return_value=None),
        update_current_content=MagicMock(),
    )

    assert HtmlOutput.trim_nodes(obj, 0) is False
    assert HtmlOutput.trim_nodes(obj, "bad") is False
    assert HtmlOutput.trim_nodes(obj, 1) is False
    obj.set_plaintext.assert_not_called()


def test_html_output_insert_nodes_buffers_only_nonempty_content_and_schedules_scroll():
    keep = CodeBlock("x")
    skip = CodeBlock("")
    obj = SimpleNamespace(
        nodes=[],
        loaded=False,
        insert_output=MagicMock(),
        update_current_content=MagicMock(),
        scroll_to_bottom=MagicMock(),
    )

    with patch("pygpt_net.tools.code_interpreter.ui.html.QTimer.singleShot") as single_shot:
        HtmlOutput.insert_nodes(obj, [skip, keep])

    assert obj.nodes == [keep]
    obj.insert_output.assert_not_called()
    obj.update_current_content.assert_called_once_with()
    single_shot.assert_called_once_with(100, obj.scroll_to_bottom)


def test_html_output_append_output_updates_current_block_and_plaintext_without_loaded_page():
    block = CodeBlock("a", "stdout")
    obj = SimpleNamespace(
        nodes=[block],
        loaded=False,
        append_plaintext=MagicMock(),
        init=MagicMock(),
        page=MagicMock(return_value=None),
        update_current_content=MagicMock(),
    )

    HtmlOutput.append_output(obj, "b", "stdout")

    obj.append_plaintext.assert_called_once_with("b")
    assert obj.nodes == [block]
    assert block.content == "ab"
    obj.init.assert_not_called()
    obj.update_current_content.assert_not_called()


def test_html_output_append_output_creates_block_when_buffer_has_no_code_block():
    obj = SimpleNamespace(
        nodes=[],
        loaded=False,
        append_plaintext=MagicMock(),
        update_current_content=MagicMock(),
    )

    HtmlOutput.append_output(obj, "err", "stderr")

    assert len(obj.nodes) == 1
    assert obj.nodes[0].as_dict() == {
        "content": "err",
        "type": "stderr",
        "images": [],
        "files": [],
    }


def test_html_output_begin_and_end_output_attach_ctx_assets_even_without_page():
    obj = SimpleNamespace(
        nodes=[],
        init=MagicMock(),
        page=MagicMock(return_value=None),
        update_current_content=MagicMock(),
    )
    ctx = SimpleNamespace(images=["img.png"], files=["result.csv"])

    HtmlOutput.begin_output(obj, "stdout")
    assert len(obj.nodes) == 1
    assert obj.nodes[-1].type == "stdout"

    HtmlOutput.end_output(obj, "stdout", ctx)
    assert obj.nodes[-1].images == ["img.png"]
    assert obj.nodes[-1].files == ["result.csv"]
    assert obj.init.call_count == 2


def test_html_output_set_history_and_clear_update_buffers_before_page_load():
    obj = SimpleNamespace(
        loaded=False,
        nodes=[CodeBlock("old")],
        set_plaintext=MagicMock(),
        init=MagicMock(),
        page=MagicMock(return_value=None),
        update_current_content=MagicMock(),
    )

    HtmlOutput.set_history(obj, "history")
    obj.set_plaintext.assert_called_once_with("history")
    assert [n.content for n in obj.nodes] == ["history"]

    obj.set_plaintext.reset_mock()
    HtmlOutput.clear(obj)
    obj.set_plaintext.assert_called_once_with("")
    assert obj.nodes == []


def test_html_output_update_current_content_runs_only_after_page_loaded():
    page = MagicMock()
    obj = SimpleNamespace(loaded=False, page=MagicMock(return_value=page), set_html_content=MagicMock())

    HtmlOutput.update_current_content(obj)
    page.runJavaScript.assert_not_called()

    obj.loaded = True
    HtmlOutput.update_current_content(obj)
    page.runJavaScript.assert_called_once_with(
        "document.documentElement.innerHTML", 0, obj.set_html_content
    )


def test_html_output_page_loaded_replays_nodes_once_and_updates_snapshot():
    nodes = [CodeBlock("a"), CodeBlock("b")]
    obj = SimpleNamespace(
        nodes=list(nodes),
        loaded=False,
        is_dialog=False,
        init=MagicMock(),
        insert_output=MagicMock(),
        scroll_to_bottom=MagicMock(),
        update_current_content=MagicMock(),
    )

    with patch("pygpt_net.tools.code_interpreter.ui.html.QTimer.singleShot") as single_shot:
        HtmlOutput.on_page_loaded(obj, True)

    obj.init.assert_called_once_with()
    assert obj.insert_output.call_args_list[0].args == (nodes[0],)
    assert obj.insert_output.call_args_list[1].args == (nodes[1],)
    assert obj.loaded is True
    single_shot.assert_called_once_with(100, obj.scroll_to_bottom)
    obj.update_current_content.assert_called_once_with()


def test_code_interpreter_tool_widget_get_nodes_uses_html_output_public_api():
    nodes = [CodeBlock("x")]
    output = MagicMock()
    output.get_nodes.return_value = nodes
    obj = SimpleNamespace(output=output)

    assert ToolWidget.get_nodes(obj) is nodes
    output.get_nodes.assert_called_once_with()


def test_code_interpreter_tool_widget_restore_and_end_trim_output():
    output = MagicMock()
    tool = MagicMock()
    tool.get_output_max_entries.return_value = 5
    obj = SimpleNamespace(output=output, tool=tool)
    nodes = [CodeBlock("x")]

    ToolWidget.restore_nodes(obj, nodes)
    output.restore_nodes.assert_called_once_with(nodes)
    output.trim_nodes.assert_called_once_with(5)

    output.trim_nodes.reset_mock()
    output.trim_nodes.return_value = True
    ctx = SimpleNamespace(images=[], files=[])
    ToolWidget.end_output(obj, "stdout", ctx)
    output.init.assert_called_once_with()
    output.end_output.assert_called_once_with(type="stdout", ctx=ctx)
    output.trim_nodes.assert_called_once_with(5)
    tool.save_output.assert_called_once_with()


def test_code_interpreter_tool_widget_set_output_splits_live_lines_and_handles_stdin():
    output = MagicMock()
    obj = SimpleNamespace(output=output)

    ToolWidget.set_output(obj, "a\nb", "stdout", live=True)
    assert [c.args[0] for c in output.append_output.call_args_list] == ["a", "\n", "b"]

    output.reset_mock()
    ToolWidget.set_output(obj, "answer", "stdin", live=False)
    output.set_output.assert_called_once_with(">> answer")

    output.reset_mock()
    ToolWidget.set_output(obj, "", "stdout", live=True)
    output.append_output.assert_not_called()


def test_code_interpreter_tool_widget_input_and_checkbox_helpers():
    input_widget = MagicMock()
    input_widget.toPlainText.return_value = "one"
    obj = SimpleNamespace(
        input=input_widget,
        history=MagicMock(),
        output=MagicMock(),
        is_dialog=True,
        checkbox_all=MagicMock(),
        checkbox_auto_clear=MagicMock(),
        checkbox_ipython=MagicMock(),
    )

    ToolWidget.append_to_input(obj, "two")
    input_widget.setPlainText.assert_called_once_with("one\ntwo")
    ToolWidget.set_input(obj, "new")
    input_widget.setPlainText.assert_called_with("new")
    ToolWidget.set_focus(obj)
    input_widget.setFocus.assert_called_once_with()

    ToolWidget.set_checkbox_all(obj, True)
    ToolWidget.set_checkbox_auto_clear(obj, False)
    ToolWidget.set_checkbox_ipython(obj, True)
    ToolWidget.toggle_all_visible(obj, False)
    obj.checkbox_all.setChecked.assert_called_once_with(True)
    obj.checkbox_auto_clear.setChecked.assert_called_once_with(False)
    obj.checkbox_ipython.setChecked.assert_called_once_with(True)
    obj.checkbox_all.setVisible.assert_called_once_with(False)


def test_bridge_delegates_copy_preview_scroll_and_cleanup():
    window = SimpleNamespace(
        controller=SimpleNamespace(
            ctx=SimpleNamespace(extra=MagicMock()),
            chat=SimpleNamespace(render=SimpleNamespace(scroll=0)),
        )
    )
    obj = SimpleNamespace(window=window, deleteLater=MagicMock())

    Bridge.copy_text(obj, "copy")
    Bridge.preview_text(obj, "preview")
    Bridge.update_scroll_position(obj, 123)
    window.controller.ctx.extra.copy_code_text.assert_called_once_with("copy")
    window.controller.ctx.extra.preview_code_text.assert_called_once_with("preview")
    assert window.controller.chat.render.scroll == 123

    Bridge.cleanup(obj)
    assert obj.window is None
    obj.deleteLater.assert_called_once_with()


def test_custom_web_engine_page_find_and_zoom_callbacks_delegate_to_controllers():
    finder = SimpleNamespace(current_match_index=0, matches=0, on_find_finished=MagicMock())
    result = SimpleNamespace(activeMatch=MagicMock(return_value=2), numberOfMatches=MagicMock(return_value=7))
    parent = SimpleNamespace(finder=finder)
    config = MagicMock()
    option = {"value": 0.0}
    window = SimpleNamespace(
        core=SimpleNamespace(config=config),
        controller=SimpleNamespace(
            settings=SimpleNamespace(editor=SimpleNamespace(get_option=MagicMock(return_value=option))),
            config=SimpleNamespace(apply=MagicMock()),
        ),
    )
    obj = SimpleNamespace(parent=parent, window=window, zoomFactor=MagicMock(return_value=1.25))

    CustomWebEnginePage.on_find_finished(obj, result)
    assert finder.current_match_index == 2
    assert finder.matches == 7
    finder.on_find_finished.assert_called_once_with()

    CustomWebEnginePage.on_view_changed(obj)
    config.set.assert_called_once_with("zoom", 1.25)
    assert option["value"] == 1.25
    window.controller.config.apply.assert_called_once_with(
        parent_id="config", key="zoom", option=option
    )


def test_html_output_detach_gl_filter_clears_state_and_reports_disconnect_errors():
    gl = MagicMock()
    obj = SimpleNamespace(
        _glwidget=gl,
        _glwidget_filter_installed=True,
        _on_delete_failed=MagicMock(),
    )
    HtmlOutput._detach_gl_event_filter(obj)
    gl.removeEventFilter.assert_called_once_with(obj)
    assert obj._glwidget is None
    assert obj._glwidget_filter_installed is False

    gl = MagicMock(); gl.removeEventFilter.side_effect = RuntimeError("gone")
    obj = SimpleNamespace(_glwidget=gl, _glwidget_filter_installed=True, _on_delete_failed=MagicMock())
    HtmlOutput._detach_gl_event_filter(obj)
    obj._on_delete_failed.assert_called_once()
    assert obj._glwidget is None


def test_html_output_unload_discards_page_and_marks_unloaded_even_on_error():
    page = MagicMock()
    obj = SimpleNamespace(
        hide=MagicMock(),
        page=MagicMock(return_value=page),
        _on_delete_failed=MagicMock(),
        _unloaded=False,
    )
    HtmlOutput.unload(obj)
    obj.hide.assert_called_once_with()
    page.triggerAction.assert_called_once()
    page.history.return_value.clear.assert_called_once_with()
    page.setLifecycleState.assert_called_once()
    assert obj._unloaded is True

    obj = SimpleNamespace(
        hide=MagicMock(side_effect=RuntimeError("hidden")),
        page=MagicMock(),
        _on_delete_failed=MagicMock(),
        _unloaded=False,
    )
    HtmlOutput.unload(obj)
    obj._on_delete_failed.assert_called_once()
    assert obj._unloaded is True


def test_html_output_reload_css_updates_styles_and_block_mode():
    page = MagicMock()
    config = MagicMock(); config.get.return_value = True
    body = MagicMock(); body.prepare_styles.return_value = {"font-size": "12px"}
    obj = SimpleNamespace(
        body=body,
        page=MagicMock(return_value=page),
        window=SimpleNamespace(core=SimpleNamespace(config=config)),
    )

    HtmlOutput.reload_css(obj)

    assert page.runJavaScript.call_count == 2
    assert "updateCSS" in page.runJavaScript.call_args_list[0].args[0]
    assert "enableBlocks" in page.runJavaScript.call_args_list[1].args[0]

    page.reset_mock(); config.get.return_value = False
    HtmlOutput.reload_css(obj)
    assert "disableBlocks" in page.runJavaScript.call_args_list[1].args[0]


def test_html_output_reload_from_plaintext_meta_and_clear_content_helpers():
    obj = SimpleNamespace(
        reload_css=MagicMock(),
        set_output=MagicMock(),
        get_plaintext=MagicMock(return_value="plain"),
        clear_plaintext=MagicMock(),
        meta=None,
    )
    HtmlOutput.reload(obj)
    obj.reload_css.assert_called_once_with()
    HtmlOutput.from_plaintext(obj)
    obj.set_output.assert_called_once_with("plain", store_plain=False)

    meta = object()
    HtmlOutput.set_meta(obj, meta)
    assert obj.meta is meta
    HtmlOutput.clear_content(obj)
    obj.clear_plaintext.assert_called_once_with()


def test_html_output_zoom_selection_actions_and_finder_delegation():
    page = MagicMock(); page.selectedText.return_value = "selected"; page.zoomFactor.return_value = 1.5
    config = MagicMock(); config.has.return_value = True; config.get.return_value = 1.25
    finder = MagicMock()
    window = SimpleNamespace(
        core=SimpleNamespace(config=config),
        controller=SimpleNamespace(finder=MagicMock()),
    )
    obj = SimpleNamespace(page=MagicMock(return_value=page), window=window, finder=finder)

    HtmlOutput.update_zoom(obj)
    page.setZoomFactor.assert_called_once_with(1.25)
    assert HtmlOutput.get_zoom_value(obj) == 1.5
    assert HtmlOutput.get_selected_text(obj) == "selected"

    HtmlOutput.copy_selected_text(obj)
    HtmlOutput.select_all_text(obj)
    HtmlOutput.unselect_text(obj)
    assert page.triggerAction.call_count == 3

    HtmlOutput.find_open(obj)
    window.controller.finder.open.assert_called_once_with(finder)
    HtmlOutput.on_update(obj)
    finder.clear.assert_called_once_with()


def test_custom_web_engine_page_link_click_is_routed_to_filesystem_handler():
    from PySide6.QtWebEngineCore import QWebEnginePage

    handler = MagicMock()
    obj = SimpleNamespace(
        window=SimpleNamespace(core=SimpleNamespace(filesystem=SimpleNamespace(url=SimpleNamespace(handle=handler))))
    )
    url = object()

    result = CustomWebEnginePage.acceptNavigationRequest(
        obj, url, QWebEnginePage.NavigationTypeLinkClicked, True
    )

    assert result is False
    handler.assert_called_once_with(url)


def test_custom_web_engine_page_cleanup_releases_bridge_channel_and_signals():
    bridge = MagicMock(); channel = MagicMock(); signals = MagicMock()
    obj = SimpleNamespace(
        findTextFinished=SimpleNamespace(disconnect=MagicMock()),
        zoomFactorChanged=SimpleNamespace(disconnect=MagicMock()),
        selectionChanged=SimpleNamespace(disconnect=MagicMock()),
        bridge=bridge,
        channel=channel,
        signals=signals,
    )

    CustomWebEnginePage.cleanup(obj)

    bridge.cleanup.assert_called_once_with()
    channel.unregisterObject.assert_called_once_with("bridge")
    signals.deleteLater.assert_called_once_with()
    assert obj.bridge is None
    assert obj.channel is None
    assert obj.signals is None
