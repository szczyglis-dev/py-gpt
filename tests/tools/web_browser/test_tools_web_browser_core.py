from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.types.canvas import CanvasSearchEngine
from pygpt_net.tools.web_browser.tool import WebBrowser
from pygpt_net.tools.web_browser.core.viewport import CanvasViewport


def _tool():
    tool = WebBrowser()
    tabs = MagicMock()
    tabs.get_current_column_idx.return_value = 0
    plugin = MagicMock()
    plugin.get_option_value.return_value = None
    core_tabs = MagicMock()
    core_tabs.get_max_idx_by_column.return_value = 0
    window = SimpleNamespace(
        controller=SimpleNamespace(
            ui=SimpleNamespace(),
            tabs=tabs,
            chat=SimpleNamespace(common=MagicMock()),
            kernel=SimpleNamespace(busy=False),
        ),
        core=SimpleNamespace(
            config=SimpleNamespace(get=MagicMock(return_value=True), get_user_path=MagicMock(return_value="/tmp")),
            plugins=SimpleNamespace(get=MagicMock(return_value=plugin)),
            tabs=core_tabs,
        ),
        ui=SimpleNamespace(
            dialogs=MagicMock(),
            dialog={},
            nodes={"icon.web_browser": MagicMock()},
            splitters={},
        ),
        state="idle",
        STATE_BUSY="busy",
    )
    tool.window = window
    from pygpt_net.controller.tabs.operations import TabOperations
    selection = SimpleNamespace(
        _state=SimpleNamespace(recent_pids=[]),
        window=SimpleNamespace(ui=SimpleNamespace(splitters={
            'columns': SimpleNamespace(sizes=lambda: [500, 500])})),
        get_current_tab=tabs.get_current_tab,
        get_current_by_column=tabs.get_current_by_column,
    )
    tabs.preferred_tab.side_effect = lambda items, **kwargs: TabOperations.preferred_tab(selection, items, **kwargs)

    # Core tests use a mocked viewport; real load completion is covered by
    # dedicated Qt backend tests and the WebEngine integration check.
    tool.qt.load_html = MagicMock(side_effect=lambda html, base_url: tool.surface.web.setHtml(html, base_url))
    return tool


def test_web_browser_defaults_setup_reload_and_dialog_id():
    tool = _tool()
    tool.update = MagicMock()
    tool.history.load = MagicMock()

    tool.setup()

    tool.history.load.assert_called_once_with()
    tool.update.assert_called_once_with()
    assert tool.id == "web_browser"
    assert tool.has_tab is True
    assert tool.single_instance is False
    assert tool.allow_dialog is True
    assert tool.multi_dialog is True
    assert tool.tab_title == "tool.web_browser.tab_title"
    assert tool.get_dialog_id() == "web_browser"

    tool.update.reset_mock()
    tool.history.load.reset_mock()
    tool.on_reload()
    tool.history.load.assert_called_once_with()
    tool.update.assert_called_once_with()


def test_web_browser_set_url_opens_surface_and_routes_to_canvas_runtime():
    tool = _tool()
    tool.open = MagicMock()
    tool.runtime_call = MagicMock(return_value={"ok": True})

    result = tool.set_url("https://example.com")

    tool.open.assert_called_once_with(load=False)
    tool.runtime_call.assert_called_once_with(
        "canvas_open",
        {"url": "https://example.com", "__ui": True},
    )
    assert result == {"ok": True}


@pytest.mark.parametrize("address", [
    "https://example.com/page", "about:blank", "file:///tmp/page.html",
    "example.com/page", "localhost:8080", "127.0.0.1:8080", "[::1]:8080",
    "./page.html", "/tmp/page.html",
])
def test_address_bar_routes_direct_addresses_to_canvas(address):
    tool = _tool()
    tool.runtime_call = MagicMock(return_value={"ok": True})

    assert tool.open_address(f"  {address}  ") == {"ok": True}

    tool.runtime_call.assert_called_once_with(
        "canvas_open", {"url": address, "__ui": True},
    )


def test_address_bar_routes_plain_text_to_configured_search_engine():
    tool = _tool()
    tool.search_engine = MagicMock(return_value=CanvasSearchEngine.DUCKDUCKGO)
    tool.runtime_call = MagicMock(return_value={"ok": True})

    assert tool.open_address("  canvas refactor & tests  ") == {"ok": True}

    tool.runtime_call.assert_called_once_with(
        "canvas_open",
        {"url": "https://duckduckgo.com/?q=canvas+refactor+%26+tests", "__ui": True},
    )


def test_empty_address_bar_does_not_navigate():
    tool = _tool()
    tool.runtime_call = MagicMock()
    tool.current_state = MagicMock(return_value={"url": "about:blank"})

    assert tool.open_address("  ") == {"url": "about:blank"}

    tool.runtime_call.assert_not_called()


def _registered(tool, qapp, tab):
    from PySide6.QtWidgets import QWidget
    runtime = SimpleNamespace(surface_owner=SimpleNamespace(tab=tab))
    widget = QWidget()
    tool.register_surface(runtime, widget, tab=tab)
    tool.window.controller.tabs.get_tabs_by_tool.return_value = [tab]
    tool.window.controller.tabs.get_current_tab.return_value = None
    return runtime, widget


def test_web_browser_open_creates_runtime_in_second_column_and_focuses_it(qapp):
    tool = _tool()
    tabs = tool.window.controller.tabs
    tab = SimpleNamespace(idx=7, column_idx=1)
    tool.window.core.tabs.get_max_idx_by_column.return_value = 4
    tabs.get_tabs_by_tool.return_value = []
    tabs.is_split_screen_enabled.return_value = False
    created = []
    def append(**kwargs):
        created.append(_registered(tool, qapp, tab))
    tabs.append.side_effect = append

    result = tool.open()

    assert result is created[0][0]
    tabs.append.assert_called_once_with(type=Tab.TAB_TOOL, tool_id="web_browser",
                                       idx=4, column_idx=1)
    tabs.enable_split_screen.assert_called_once_with(update_switch=True)
    tabs.activate_tab.assert_called_once_with(tab, sync_context=False)


def test_web_browser_open_reuses_selected_runtime(qapp):
    tool = _tool()
    tab = SimpleNamespace(idx=3, column_idx=1)
    runtime, widget = _registered(tool, qapp, tab)
    assert tool.open() is runtime
    tool.window.controller.tabs.append.assert_not_called()
    tool.window.controller.tabs.activate_tab.assert_called_once_with(tab, sync_context=False)


def test_web_browser_toggle_is_an_opener_not_dialog_state_toggle():
    tool = _tool()
    tool.open = MagicMock(return_value="tab")

    assert tool.toggle() == "tab"
    tool.open.assert_called_once_with()


def test_web_browser_close_targets_selected_tab(qapp):
    tool = _tool()
    tab = SimpleNamespace(idx=3, column_idx=1)
    runtime, widget = _registered(tool, qapp, tab)
    assert tool.close() == {"closed": "tab", "session_alive": False}
    tool.window.controller.tabs.close.assert_called_once_with(3, 1)
    tool.unregister_surface(runtime)
    assert tool.close() == {"closed": "none", "session_alive": False}


def test_web_browser_agent_surface_reveals_and_activates_selected_runtime(qapp):
    tool = _tool()
    tab = SimpleNamespace(idx=3, column_idx=1)
    runtime, widget = _registered(tool, qapp, tab)
    tool.window.controller.tabs.is_split_screen_enabled.return_value = False
    assert tool.ensure_agent_surface() == "tab"
    tool.window.controller.tabs.enable_split_screen.assert_called_once_with(update_switch=True)
    tool.window.controller.tabs.activate_tab.assert_called_once_with(tab, sync_context=False)


def test_canvas_click_selects_runtime_and_column_without_reopening_surface(qapp):
    from PySide6.QtWidgets import QWidget
    tool = _tool()
    first, second = tool.new_runtime(), tool.new_runtime()
    tabs = tool.window.controller.tabs
    first_tab = SimpleNamespace(idx=0, column_idx=0)
    second_tab = SimpleNamespace(idx=0, column_idx=1)
    first_widget, second_widget = QWidget(), QWidget()
    tool.register_surface(first, first_widget, tab=first_tab)
    tool.register_surface(second, second_widget, tab=second_tab)
    tabs.get_tabs_by_tool.return_value = [first_tab, second_tab]
    second.surface_owner = SimpleNamespace(tab=second_tab)
    tool.mark_surface_used(first)

    second.viewport.on_user_interaction()

    assert tool.resolve_surface() is second
    tabs.on_column_focus.assert_called_once_with(1)
    tabs.append.assert_not_called()
    tabs.activate_tab.assert_not_called()


def test_canvas_dialog_click_selects_runtime_without_switching_tab_column(qapp):
    from PySide6.QtWidgets import QWidget
    tool = _tool()
    runtime = tool.new_runtime()
    dialog = QWidget()
    dialog.show()
    tool.register_surface(runtime, dialog, dialog_id='canvas.test')
    runtime.surface_owner = SimpleNamespace(tab=None)
    tool.window.controller.tabs.get_tabs_by_tool.return_value = []

    runtime.viewport.on_user_interaction()

    assert tool.resolve_surface() is runtime
    tool.window.controller.tabs.on_column_focus.assert_not_called()
    dialog.close()


def test_web_browser_handle_save_as_cleans_and_defers_to_chat_save():
    tool = _tool()

    def immediately(_delay, callback):
        callback()

    with patch("pygpt_net.tools.web_browser.tool.output_clean_html", return_value="clean") as clean, \
            patch("pygpt_net.tools.web_browser.tool.output_html2text", return_value="plain") as plain, \
            patch("pygpt_net.tools.web_browser.tool.QTimer.singleShot", side_effect=immediately):
        tool.handle_save_as("<p>x</p>", "html")
        clean.assert_called_once_with("<p>x</p>")
        tool.window.controller.chat.common.save_text.assert_called_with("clean", "html")

        tool.handle_save_as("<p>x</p>", "txt")
        plain.assert_called_once_with("<p>x</p>")
        tool.window.controller.chat.common.save_text.assert_called_with("plain", "txt")


def test_web_browser_show_hide_toolbar_icon_and_toggle_icon():
    tool = _tool()
    tool.open = MagicMock()
    tool.close = MagicMock()

    tool.show_hide(True)
    tool.show_hide(False)

    tool.open.assert_called_once_with()
    tool.close.assert_called_once_with()
    icon = tool.get_toolbar_icon()
    assert icon is tool.window.ui.nodes["icon.web_browser"]
    tool.toggle_icon(False)
    icon.setVisible.assert_called_once_with(False)


def test_web_browser_as_tab_and_setup_dialogs():
    tool = _tool()
    tab = SimpleNamespace(idx=0, column_idx=0)
    dialog_tool = MagicMock()
    inner = MagicMock()
    dialog_tool.as_tab.return_value = inner
    tab_widget = MagicMock()

    with patch("pygpt_net.tools.web_browser.tool.Tool", return_value=dialog_tool), \
            patch("pygpt_net.tools.web_browser.tool.TabWidget", return_value=tab_widget):
        result = tool.as_tab(tab)

    assert result is tab_widget
    tab_widget.from_tool.assert_called_once_with(inner)
    tab_widget.setup.assert_called_once_with()
    dialog_tool.set_tab.assert_called_once_with(tab)

    tool.dialog = MagicMock()
    tool.setup_dialogs()
    assert tool.dialog is None


def test_web_browser_lang_mappings_use_canvas_menu_label():
    tool = _tool()
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.web_browser": "menu.tools.canvas_html"}
    }


def test_source_edits_preserve_url_origin_and_reload_external_document():
    for backend in ("qt", "playwright"):
        for url in ("http://example.com/page", "https://example.com/page", "file:///tmp/page.html"):
            tool = _tool()
            tool.backend = backend
            tool.surface = MagicMock()
            tool.surface._source_visible = False
            tool.ensure_visible_surface = MagicMock()
            tool.playwright.ensure = MagicMock()
            tool.preview.start = MagicMock()
            tool.server_url = "http://127.0.0.1:1234/"
            tool.pw_page = MagicMock()
            tool.playwright.refresh_frame = MagicMock()
            tool.current_state = MagicMock(return_value={})
            tool.current_url = MagicMock(return_value=url)
            tool.notify_state = MagicMock()
            tool.history.push({"kind": "url", "url": url})

            tool.document.apply_source("<p>first edit</p>", url)
            tool.document.apply_source("<p>second edit</p>", url)
            assert tool.canvas_history[-1]["reload_url"] == url
            tool.surface.web.reset_mock()
            tool.pw_page.reset_mock()

            tool.commands.reload({})
            assert tool.canvas_history[-1] == {"kind": "url", "url": url}
            if backend == "qt":
                assert tool.surface.web.setUrl.call_args.args[0].toString() == url
                tool.surface.web.setHtml.assert_not_called()
            else:
                tool.pw_page.goto.assert_called_once_with(url, wait_until="domcontentloaded")
                tool.pw_page.reload.assert_not_called()


def test_manual_html_with_http_base_reloads_committed_html():
    tool = _tool()
    tool.surface = MagicMock()
    tool.surface._source_visible = False
    tool.current_url = MagicMock(return_value="https://example.com/")
    tool.commands.set_html = MagicMock(return_value={"ok": True})
    tool.history.push({"kind": "html", "html": "<p>committed</p>",
                        "base_url": "https://example.com/"})

    tool.commands.reload({})

    assert tool.commands.set_html.call_args.args[0]["html"] == "<p>committed</p>"
    tool.surface.web.reload.assert_not_called()


def test_playwright_does_not_poll_frames_while_editing_source():
    tool = _tool()
    tool.backend = "playwright"
    tool.pw_page = MagicMock()
    tool.surface_owner = MagicMock()
    tool.surface = SimpleNamespace(_source_visible=True)

    tool.playwright.poll_frame()

    tool.pw_page.screenshot.assert_not_called()


def test_plugin_commands_follow_last_used_runtime_and_fallback_after_close(qapp):
    from PySide6.QtWidgets import QWidget
    tool = _tool()
    tabs = tool.window.controller.tabs
    first_tab = SimpleNamespace(idx=0, column_idx=0)
    second_tab = SimpleNamespace(idx=1, column_idx=0)
    first, second = tool.new_runtime(), tool.new_runtime()
    first_widget, second_widget = QWidget(), QWidget()
    tool.register_surface(first, first_widget, tab=first_tab)
    tool.register_surface(second, second_widget, tab=second_tab)
    tabs.get_tabs_by_tool.return_value = [first_tab, second_tab]
    tabs.get_current_tab.return_value = second_tab
    first.commands.execute = MagicMock(return_value='first')
    second.commands.execute = MagicMock(return_value='second')
    plugin = object()
    tool.mark_surface_used(second)
    for cmd in ('canvas_set_html', 'canvas_get_html', 'canvas_eval', 'canvas_screenshot',
                'canvas_inspect', 'canvas_open', 'web_server_start'):
        assert tool.runtime_call(cmd, {'html': 'test'}, plugin=plugin) == 'second'
    assert first.commands.execute.call_count == 0
    assert second.commands.execute.call_count == 7
    tool.unregister_surface(second)
    tabs.get_current_tab.return_value = first_tab
    assert tool.runtime_call('canvas_get_html', {}, plugin=plugin) == 'first'
    tabs.activate_tab.assert_called_with(first_tab, sync_context=False)


def test_canvas_annotation_context_uses_selected_runtime_without_creating_one(qapp):
    tool = _tool()
    tool.window.controller.tabs.get_tabs_by_tool.return_value = []
    tool.create_surface = MagicMock()
    assert tool.get_annotations() == []
    tool.create_surface.assert_not_called()
    runtime, widget = _registered(tool, qapp, SimpleNamespace(idx=0, column_idx=0))
    runtime.get_annotations = MagicMock(return_value=[{'id': 1}])
    assert tool.get_annotations() == [{'id': 1}]


def test_canvas_html_and_navigation_state_are_independent_per_runtime(qapp):
    from PySide6.QtWidgets import QWidget
    tool = _tool()
    tabs = tool.window.controller.tabs
    runtimes, widgets, descriptors = [], [], []
    for index in range(2):
        runtime = tool.new_runtime()
        tab = SimpleNamespace(idx=index, column_idx=0)
        widget = QWidget()
        runtime.surface = SimpleNamespace(web=MagicMock())
        runtime.viewport.ensure_surface = MagicMock(return_value=runtime.surface)
        runtime.qt.eval = lambda script, runtime=runtime: runtime.runtime_html
        runtime.qt.load_html = lambda html, base_url, runtime=runtime: runtime.surface.web.setHtml(html, base_url)
        tool.register_surface(runtime, widget, tab=tab)
        runtimes.append(runtime)
        widgets.append(widget)
        descriptors.append(tab)
    tabs.get_tabs_by_tool.return_value = descriptors
    tabs.get_current_tab.return_value = None
    for index, runtime in enumerate(runtimes):
        tool.mark_surface_used(runtime)
        tool.runtime_call('canvas_set_html', {'html': f'<h1>Canvas {index}</h1>'})
    for index, runtime in enumerate(runtimes):
        tool.mark_surface_used(runtime)
        result = tool.runtime_call('canvas_get_html', {})
        assert result['html'] == f'<h1>Canvas {index}</h1>'
        assert len(runtime.canvas_history) == 1
        assert runtime.surface.web.setHtml.call_count == 1
    assert runtimes[0].console is not runtimes[1].console
    assert runtimes[0].annotations is not runtimes[1].annotations


def test_canvas_dialogs_have_independent_runtimes_and_are_removed_on_close(qapp):
    from PySide6.QtWidgets import QWidget, QVBoxLayout
    tool = _tool()
    original_window = tool.window
    window = QWidget()
    window.ui = original_window.ui
    window.core = original_window.core
    window.controller = original_window.controller
    window.core.config.has = MagicMock(return_value=False)
    window.controller.tabs.get_tabs_by_tool.return_value = []
    tool.attach(window)
    with patch('pygpt_net.tools.web_browser.ui.widgets.ToolWidget.setup',
               side_effect=lambda: QVBoxLayout()), \
            patch.object(CanvasViewport, 'attach_surface'):
        first = tool.open_window()
        second = tool.open_window()
    assert first is not second
    assert len(window.ui.dialog) == 2
    assert tool.resolve_surface() is second
    second_entry = next(entry for entry in tool._surfaces if entry['instance'] is second)
    second_entry['widget'].close()
    assert len(window.ui.dialog) == 1
    assert tool.resolve_surface() is first
    first_entry = tool._surfaces[0]
    first_entry['widget'].close()
    assert tool.resolve_surface() is None
    assert window.ui.dialog == {}
    window.close()


def test_playwright_driver_is_shared_but_contexts_are_independent(qapp):
    import sys
    tool = _tool()
    first, second = tool.new_runtime(), tool.new_runtime()
    driver = MagicMock()
    first_browser, second_browser = MagicMock(), MagicMock()
    driver.chromium.launch.side_effect = [first_browser, second_browser]
    factory = MagicMock()
    factory.return_value.start.return_value = driver
    module = SimpleNamespace(sync_playwright=factory)
    with patch.dict(sys.modules, {'playwright.sync_api': module}):
        first.playwright.refresh_frame = MagicMock()
        second.playwright.refresh_frame = MagicMock()
        first.playwright.ensure()
        second.playwright.ensure()
    factory.return_value.start.assert_called_once_with()
    assert first.pw is second.pw is driver
    assert first.pw_context is not second.pw_context
    first.playwright.stop()
    driver.stop.assert_not_called()
    second.playwright.stop()
    driver.stop.assert_called_once_with()


def test_annotation_delivery_clears_original_canvas_after_selection_changes(qapp):
    from PySide6.QtWidgets import QWidget
    from pygpt_net.item.ctx import CtxItem
    from pygpt_net.plugin.canvas_web.plugin import Plugin
    from pygpt_net.ui.widget.textarea.annotations import clear_sent_annotations
    tool = _tool()
    tool.window.tools = SimpleNamespace(get=lambda name: tool)
    tabs = tool.window.controller.tabs
    runtimes, widgets, descriptors = [], [], []
    for index in range(2):
        runtime = tool.new_runtime()
        runtime.annotations = [dict(id=1, time=1, source='canvas_web', note=f'note {index}')]
        runtime._render_annotations = MagicMock()
        widget = QWidget()
        tab = SimpleNamespace(idx=index, column_idx=0)
        tool.register_surface(runtime, widget, tab=tab)
        runtimes.append(runtime)
        widgets.append(widget)
        descriptors.append(tab)
    tabs.get_tabs_by_tool.return_value = descriptors
    tool.mark_surface_used(runtimes[1])
    ctx = CtxItem()
    prompt = Plugin.append_runtime_context(SimpleNamespace(window=tool.window), 'system', ctx)
    assert 'note 1' in prompt
    assert 'note 0' not in prompt
    tool.mark_surface_used(runtimes[0])
    clear_sent_annotations(ctx)
    assert len(runtimes[0].annotations) == 1
    assert runtimes[1].annotations == []
    runtimes[1]._render_annotations.assert_called_once_with()


def test_annotation_update_and_reload_use_latest_committed_html():
    tool = _tool()
    tool.surface = SimpleNamespace(web=MagicMock(), _source_visible=False)
    tool.auto_open_enabled = lambda: False
    tool.sandbox_enabled = lambda: False
    old, new = '<canvas>cat</canvas>', '<canvas>cat with hat</canvas>'
    tool.commands.set_html({'html': old})
    tool.annotations = [dict(id=1, source='canvas_web', note='add a hat')]
    tool.commands.set_html({'html': new})
    tool.commands.reload({})

    assert tool.surface.web.setHtml.call_args.args[0] == new
    assert tool.canvas_history[-1]['html'] == new
    assert len(tool.canvas_history) == 2
    assert tool.annotations[0]['note'] == 'add a hat'


def test_source_uses_committed_code_and_discards_stale_serialization_callback():
    tool = _tool()
    tool.surface = SimpleNamespace(web=MagicMock(), show_source=MagicMock(), _source_visible=False)
    tool.current_url = lambda: 'https://example.com/'
    tool.viewport.ensure_surface = MagicMock()
    tool.history.push({'kind': 'url', 'url': 'https://example.com/'})
    tool.document.show_source()
    ready = tool.surface.web.page().runJavaScript.call_args.args[-1]
    tool.auto_open_enabled = lambda: False
    tool.sandbox_enabled = lambda: False
    tool.commands.set_html({'html': '<canvas>new cat</canvas>'})
    ready('<canvas>old cat and stale overlay</canvas>')
    tool.surface.show_source.assert_not_called()

    tool.document.show_source()
    assert tool.surface.show_source.call_args.args[0] == '<canvas>new cat</canvas>'


def test_aborted_qt_load_does_not_replace_html_history_or_render_annotation():
    tool = _tool()
    tool.surface = SimpleNamespace(web=MagicMock(), _source_visible=False)
    tool.history.push({'kind': 'html', 'html': '<canvas>latest</canvas>'})
    tool._history_loading = True
    tool._render_annotations = MagicMock()
    tool.notify_state = MagicMock()
    tool.qt.on_load_finished(False)

    assert tool._history_loading is True
    assert tool.canvas_history[-1]['kind'] == 'html'
    tool._render_annotations.assert_not_called()
    tool.notify_state.assert_not_called()


def test_hidden_qt_events_cannot_overwrite_playwright_document():
    from PySide6.QtCore import QUrl
    tool = _tool()
    tool.backend = 'playwright'
    tool.virtual_url = 'https://latest.example/'
    tool.surface = SimpleNamespace(web=MagicMock())
    tool._render_annotations = MagicMock()
    tool.notify_state = MagicMock()
    tool._history_loading = True
    tool.history.on_qt_url_changed(QUrl('https://old.example/'))
    tool.history.on_qt_title_changed('old page')
    tool.qt.on_load_finished(True)

    assert tool.virtual_url == 'https://latest.example/'
    assert tool._history_loading is True
    tool._render_annotations.assert_not_called()
    tool.notify_state.assert_not_called()


def test_model_update_resets_source_buffer_before_return_to_preview():
    tool = _tool()
    tool.auto_open_enabled = lambda: False
    tool.sandbox_enabled = lambda: False
    tool.surface = SimpleNamespace(web=MagicMock(), show_source=MagicMock(), _source_visible=True)
    tool.commands.set_html({'html': '<canvas>with hat</canvas>'})
    assert tool.surface.show_source.call_args.args[0] == '<canvas>with hat</canvas>'
