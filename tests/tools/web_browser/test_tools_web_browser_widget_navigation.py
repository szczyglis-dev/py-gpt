from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt

from pygpt_net.tools.web_browser.ui.widgets import AddressLineEdit, ToolWidget


def _widget():
    output = MagicMock()
    viewport = MagicMock()
    viewport.width.return_value = 900
    viewport.height.return_value = 600
    scroll = MagicMock()
    scroll.viewport.return_value = viewport

    tool = SimpleNamespace(
        runtime_root=SimpleNamespace(release_runtime=MagicMock()),
        viewport=SimpleNamespace(
            detach_surface=MagicMock(),
            request_viewport_policy=MagicMock(),
        ),
        runtime_call=MagicMock(),
        open_address=MagicMock(),
        current_state=MagicMock(return_value={
            "url": "https://example.com",
            "can_go_back": False,
            "can_go_forward": True,
        }),
        history=SimpleNamespace(entries=MagicMock(return_value=[
            {"url": "https://example.com", "title": "Example"},
        ])),
    )
    window = SimpleNamespace(
        controller=SimpleNamespace(
            ui=SimpleNamespace(),
            tabs=MagicMock(),
        ),
        ui=SimpleNamespace(splitters={}),
    )
    return SimpleNamespace(
        tool=tool,
        _disposed=False,
        surface_kind="tab",
        window=window,
        output=output,
        tab=SimpleNamespace(idx=4, column_idx=1),
        nav_bar=MagicMock(),
        address_bar=MagicMock(),
        btn_back=MagicMock(),
        btn_next=MagicMock(),
        btn_reload=MagicMock(),
        scroll=scroll,
        viewport_badge=MagicMock(),
        _disconnect_viewport_hooks=MagicMock(),
        request_viewport_sync=MagicMock(),
        _sync_from_runtime=MagicMock(),
        _update_viewport_badge=MagicMock(),
        _column_visible=MagicMock(return_value=True),
        _hide_address_history_popup=MagicMock(),
        update_address_history=MagicMock(),
        _address_history_lookup={},
    )


def test_web_browser_widget_on_delete_disconnects_hooks_and_releases_runtime():
    obj = _widget()

    ToolWidget.on_delete(obj)

    obj._disconnect_viewport_hooks.assert_called_once_with()
    obj.tool.runtime_root.release_runtime.assert_called_once_with(obj.tool)
    obj.tool.viewport.detach_surface.assert_not_called()


def test_web_browser_widget_set_tab_and_open_url_use_persistent_runtime():
    obj = _widget()
    tab = SimpleNamespace(idx=7, column_idx=1)

    ToolWidget.set_tab(obj, tab)

    assert obj.tab is tab
    obj.output.set_tab.assert_called_once_with(tab)
    obj.request_viewport_sync.assert_called_once_with(immediate=True)

    ToolWidget.open_url(obj, "https://example.com")
    obj.tool.runtime_call.assert_called_once_with(
        "canvas_open",
        {"url": "https://example.com", "__ui": True},
    )


def test_web_browser_widget_sync_from_runtime_updates_address_and_history_controls():
    obj = _widget()
    obj._sync_from_runtime = ToolWidget._sync_from_runtime.__get__(obj, ToolWidget)

    ToolWidget._sync_from_runtime(obj)

    obj.address_bar.setText.assert_called_once_with("https://example.com")
    obj.update_address_history.assert_called_once_with([
        {"url": "https://example.com", "title": "Example"},
    ])
    obj.btn_back.setEnabled.assert_called_once_with(False)
    obj.btn_next.setEnabled.assert_called_once_with(True)
    obj.btn_reload.setEnabled.assert_called_once_with(True)


def test_web_browser_widget_address_enter_routes_raw_user_input_to_runtime():
    obj = _widget()
    obj.address_bar.text.return_value = "example.com"

    ToolWidget._on_address_enter(obj)

    obj.tool.open_address.assert_called_once_with("example.com")


def test_web_browser_widget_runtime_state_updates_view_and_real_tab_title():
    obj = _widget()
    tab = obj.tab

    ToolWidget.on_runtime_state(obj, {"title": "Example", "width": 900, "height": 600})

    obj._sync_from_runtime.assert_called_once_with()
    obj._update_viewport_badge.assert_called_once_with(
        {"title": "Example", "width": 900, "height": 600}
    )
    obj.window.controller.tabs.update_title_by_tab.assert_called_once_with(tab, "Example")

    # Empty/about:blank titles must not overwrite the real tab title.
    ToolWidget.on_runtime_state(obj, {"title": "about:blank"})
    ToolWidget.on_runtime_state(obj, {"title": ""})
    obj.window.controller.tabs.update_title_by_tab.assert_called_once_with(tab, "Example")

    obj.tab = None
    ToolWidget.on_runtime_state(obj, {"title": "Ignored"})
    obj.window.controller.tabs.update_title_by_tab.assert_called_once_with(tab, "Example")


def test_web_browser_widget_viewport_sync_tracks_visible_runtime_area():
    obj = _widget()

    ToolWidget._sync_runtime_viewport(obj)

    obj.tool.viewport.request_viewport_policy.assert_called_once_with(
        900,
        600,
        visible=True,
        delay=0,
    )


def test_web_browser_widget_viewport_sync_uses_hidden_policy_for_collapsed_column():
    obj = _widget()
    obj._column_visible.return_value = False

    ToolWidget._sync_runtime_viewport(obj)

    obj.tool.viewport.request_viewport_policy.assert_called_once_with(visible=False, delay=0)


def test_web_browser_address_line_edit_enter_invokes_callback_and_accepts_event():
    callback = MagicMock()
    event = SimpleNamespace(key=MagicMock(return_value=Qt.Key_Enter), accept=MagicMock())
    obj = SimpleNamespace(_on_return_callback=callback)

    AddressLineEdit.keyPressEvent(obj, event)

    callback.assert_called_once_with()
    event.accept.assert_called_once_with()


def test_source_is_applied_only_once_on_return_to_canvas():
    from pygpt_net.tools.web_browser.ui.widgets import BrowserViewport
    obj = SimpleNamespace(
        _source_visible=True, _source_loading=False, _mode="qt",
        source=MagicMock(), tool=MagicMock(), _source_base_url="https://example.com/",
        set_mode=MagicMock(), active_view=MagicMock(),
    )
    obj.source.toPlainText.return_value = "<p>edited</p>"
    obj.source.document().isModified.return_value = True
    obj._apply_source = lambda: BrowserViewport._apply_source(obj)

    BrowserViewport.show_canvas(obj)
    BrowserViewport.show_canvas(obj)

    obj.tool.document.apply_source.assert_called_once_with("<p>edited</p>", "https://example.com/")


def test_source_highlighting_restores_debounce_after_initial_refresh():
    from pygpt_net.core.text.editor.syntax import SyntaxHighlighter
    obj = SimpleNamespace(timer=MagicMock())

    SyntaxHighlighter._on_contents_change(obj, 10, 0, 1)

    obj.timer.start.assert_called_once_with(180)


def test_canvas_tracks_clicks_in_replaced_render_children_without_consuming_input(qapp, monkeypatch):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QWidget, QPlainTextEdit
    from pygpt_net.tools.web_browser.ui import widgets

    class RenderChild(QWidget):
        def __init__(self, parent):
            super().__init__(parent)
            self.clicks = 0
            self.setFocusPolicy(Qt.StrongFocus)

        def mousePressEvent(self, event):
            self.clicks += 1
            super().mousePressEvent(event)

    # A lightweight WebEngine stand-in lets this test exercise native child
    # replacement and mouse propagation without launching a Chromium process.
    monkeypatch.setattr(widgets, 'BrowserOutput', lambda *args: QWidget())
    monkeypatch.setattr(widgets, 'SourceEditor', lambda tool, parent: QPlainTextEdit(parent))
    tool = MagicMock()
    tool._closing = False
    viewport = widgets.BrowserViewport(tool=tool)
    renderer = RenderChild(viewport.web)
    renderer.resize(200, 100)
    tool.viewport.on_user_interaction.reset_mock()

    # Focus is already on this child: clicking must still select its runtime.
    QTest.mouseClick(renderer, Qt.LeftButton)
    assert renderer.clicks == 1
    tool.viewport.on_user_interaction.assert_called()

    renderer.deleteLater()
    replacement = RenderChild(viewport.web)
    replacement.resize(200, 100)
    tool.viewport.on_user_interaction.reset_mock()
    QTest.mouseClick(replacement, Qt.LeftButton)
    assert replacement.clicks == 1
    tool.viewport.on_user_interaction.assert_called()
    viewport.close()


def test_canvas_sandbox_and_source_clicks_select_the_session(qapp, monkeypatch):
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QWidget, QPlainTextEdit
    from pygpt_net.tools.web_browser.ui import widgets

    monkeypatch.setattr(widgets, 'BrowserOutput', lambda *args: QWidget())
    monkeypatch.setattr(widgets, 'SourceEditor', lambda tool, parent: QPlainTextEdit(parent))
    tool = MagicMock()
    tool._closing = False
    viewport = widgets.BrowserViewport(tool=tool)
    viewport.set_mode('playwright')
    tool.viewport.on_user_interaction.reset_mock()
    QTest.mouseClick(viewport.sandbox, Qt.LeftButton)
    tool.viewport.on_user_interaction.assert_called()

    viewport.show_source('<p>source</p>')
    tool.viewport.on_user_interaction.reset_mock()
    QTest.mouseClick(viewport.source.viewport(), Qt.LeftButton)
    tool.viewport.on_user_interaction.assert_called()
    viewport.close()


def test_canvas_outer_viewport_reports_clicks_separately_from_geometry(qapp):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QWidget
    from pygpt_net.tools.web_browser.ui.widgets import ViewportEventFilter

    source = QWidget()
    event_filter = ViewportEventFilter(source)
    interacted, changed = MagicMock(), MagicMock()
    event_filter.interacted.connect(interacted)
    event_filter.changed.connect(changed)

    assert event_filter.eventFilter(source, QEvent(QEvent.MouseButtonPress)) is False
    interacted.assert_called_once_with()
    changed.assert_not_called()
