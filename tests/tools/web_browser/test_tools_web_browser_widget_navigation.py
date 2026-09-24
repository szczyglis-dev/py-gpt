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
        detach_surface=MagicMock(),
        runtime_call=MagicMock(),
        current_state=MagicMock(return_value={
            "url": "https://example.com",
            "can_go_back": False,
            "can_go_forward": True,
        }),
        request_viewport_policy=MagicMock(),
    )
    window = SimpleNamespace(
        controller=SimpleNamespace(
            ui=SimpleNamespace(tabs=MagicMock()),
        ),
        ui=SimpleNamespace(splitters={}),
    )
    return SimpleNamespace(
        tool=tool,
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
        _update_plugin_hint=MagicMock(),
        _column_visible=MagicMock(return_value=True),
    )


def test_web_browser_widget_on_delete_disconnects_hooks_and_detaches_surface():
    obj = _widget()

    ToolWidget.on_delete(obj)

    obj._disconnect_viewport_hooks.assert_called_once_with()
    obj.tool.detach_surface.assert_called_once_with(obj)


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
    obj.btn_back.setEnabled.assert_called_once_with(False)
    obj.btn_next.setEnabled.assert_called_once_with(True)
    obj.btn_reload.setEnabled.assert_called_once_with(True)


def test_web_browser_widget_address_enter_routes_raw_user_input_to_runtime():
    obj = _widget()
    obj.address_bar.text.return_value = "example.com"

    ToolWidget._on_address_enter(obj)

    obj.tool.runtime_call.assert_called_once_with(
        "canvas_open",
        {"url": "example.com", "__ui": True},
    )


def test_web_browser_widget_runtime_state_updates_view_and_real_tab_title():
    obj = _widget()

    ToolWidget.on_runtime_state(obj, {"title": "Example", "width": 900, "height": 600})

    obj._sync_from_runtime.assert_called_once_with()
    obj._update_viewport_badge.assert_called_once_with(
        {"title": "Example", "width": 900, "height": 600}
    )
    obj._update_plugin_hint.assert_called_once_with()
    obj.window.controller.ui.tabs.update_title_by_tab.assert_called_once_with(obj.tab, "Example")

    obj.window.controller.ui.tabs.update_title_by_tab.reset_mock()
    ToolWidget.on_runtime_state(obj, {"title": "about:blank"})
    ToolWidget.on_runtime_state(obj, {"title": ""})
    obj.window.controller.ui.tabs.update_title_by_tab.assert_not_called()

    obj.tab = None
    ToolWidget.on_runtime_state(obj, {"title": "Ignored"})
    obj.window.controller.ui.tabs.update_title_by_tab.assert_not_called()


def test_web_browser_widget_viewport_sync_tracks_visible_runtime_area():
    obj = _widget()

    ToolWidget._sync_runtime_viewport(obj)

    obj.tool.request_viewport_policy.assert_called_once_with(
        900,
        600,
        visible=True,
        delay=0,
    )


def test_web_browser_widget_viewport_sync_uses_hidden_policy_for_collapsed_column():
    obj = _widget()
    obj._column_visible.return_value = False

    ToolWidget._sync_runtime_viewport(obj)

    obj.tool.request_viewport_policy.assert_called_once_with(visible=False, delay=0)


def test_web_browser_address_line_edit_enter_invokes_callback_and_accepts_event():
    callback = MagicMock()
    event = SimpleNamespace(key=MagicMock(return_value=Qt.Key_Enter), accept=MagicMock())
    obj = SimpleNamespace(_on_return_callback=callback)

    AddressLineEdit.keyPressEvent(obj, event)

    callback.assert_called_once_with()
    event.accept.assert_called_once_with()
