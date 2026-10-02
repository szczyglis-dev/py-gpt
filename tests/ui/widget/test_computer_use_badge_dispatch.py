from types import SimpleNamespace
from unittest.mock import Mock

from pygpt_net.plugin.cmd_mouse_control.plugin import Plugin


def test_desktop_badge_position_and_global_escape_listener_cleanup():
    import sys
    from unittest.mock import patch
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QMainWindow
    from pygpt_net.ui.widget.computer_use_badge import ComputerUseBadge
    app = QApplication.instance() or QApplication([])
    main = QMainWindow()
    listener = Mock()
    factory = Mock(return_value=listener)
    keyboard = SimpleNamespace(Key=SimpleNamespace(esc='ESC'), Listener=factory)
    window = SimpleNamespace(
        menuBar=main.menuBar,
        core=SimpleNamespace(config={'theme': 'dark'}, debug=Mock()),
        controller=SimpleNamespace(kernel=SimpleNamespace(stopped=lambda: False),
            theme=SimpleNamespace(common=SimpleNamespace(is_light_theme_id=lambda theme: False)),
            access=Mock()))
    with patch.dict(sys.modules, {'pynput': SimpleNamespace(keyboard=keyboard), 'pynput.keyboard': keyboard}):
        badge = ComputerUseBadge(window)
        assert badge._desktop_badge is None
        factory.assert_not_called()
        badge.set_active(True)
        rect = app.primaryScreen().geometry()
        overlay = badge._desktop_badge
        assert overlay.isWindow()
        assert overlay.windowFlags() & Qt.WindowDoesNotAcceptFocus
        assert overlay.y() == rect.y() + 50
        assert abs(overlay.geometry().center().x() - rect.center().x()) <= 1
        callback = factory.call_args.kwargs['on_press']
        callback('ESC', injected=True)
        app.processEvents()
        window.controller.access.on_escape.assert_not_called()
        callback('ESC', injected=False)
        app.processEvents()
        window.controller.access.on_escape.assert_called_once_with(close_dialog=False)
        listener.stop.assert_called_once()
        assert not overlay.isVisible()
        assert not badge.desktop_frame.active
        badge.close()
        badge.deleteLater()
        overlay.deleteLater()
        main.close()
        app.processEvents()


def test_native_computer_call_signals_badge_before_execution():
    badge = SimpleNamespace(active_changed=Mock())
    worker = Mock()
    plugin = SimpleNamespace(window=SimpleNamespace(computer_use_badge=badge),
                             get_worker=lambda: worker)
    plugin._show_computer_badge = lambda: Plugin._show_computer_badge(plugin)
    item = {'cmd': 'mouse_click', 'params': {}}
    Plugin.handle_call(plugin, item)
    badge.active_changed.emit.assert_called_once_with(True)
    worker.run.assert_called_once()
    assert item['params']['no_screenshot'] is True


def test_agents_native_computer_bridge_signals_badge_before_private_worker():
    import asyncio
    from pygpt_net.provider.llms.computer import AgentComputerBridge

    badge = SimpleNamespace(active_changed=Mock())
    runtime = SimpleNamespace(
        window=SimpleNamespace(computer_use_badge=badge),
        is_stopped=lambda: False,
        local_tool_lock=asyncio.Lock(),
        status=SimpleNamespace(show_tool=lambda name: False),
        verbose=Mock(),
    )
    bridge = AgentComputerBridge(runtime)
    def execute(commands):
        badge.active_changed.emit.assert_called_once_with(True)
        return [{'result': True}]
    bridge._execute_direct = execute
    result = asyncio.run(bridge.execute([{'cmd': 'mouse_click', 'params': {'x': 1, 'y': 2}}]))
    assert result.response == [{'result': True}]


def test_first_text_delta_stops_computer_indicator_immediately():
    from pygpt_net.controller.chat.render import Render
    from pygpt_net.core.events import RenderEvent
    badge = Mock()
    renderer = Mock()
    controller = Render.__new__(Render)
    controller.window = SimpleNamespace(computer_use_badge=badge)
    controller.instance = lambda: renderer
    controller._handle_stream_event(RenderEvent.STREAM_APPEND, {'chunk': ''})
    badge.stop.assert_not_called()
    controller._handle_stream_event(RenderEvent.STREAM_APPEND, {'chunk': 'Done'})
    badge.stop.assert_called_once_with()
    renderer.append_chunk.assert_called()


def test_sandbox_activation_retires_indicator_without_showing_it():
    from pygpt_net.ui.widget.computer_use_badge import ComputerUseBadge
    badge = SimpleNamespace(
        window=SimpleNamespace(core=SimpleNamespace(config={'computer_use.sandbox': True})),
        stop=Mock(),
    )
    ComputerUseBadge.set_active(badge, True)
    badge.stop.assert_called_once_with()


def test_queued_activation_after_escape_cannot_restore_indicator():
    from pygpt_net.ui.widget.computer_use_badge import ComputerUseBadge
    badge = SimpleNamespace(
        window=SimpleNamespace(core=SimpleNamespace(config={}),
                               controller=SimpleNamespace(kernel=SimpleNamespace(stopped=lambda: True))),
        stop=Mock(),
    )
    ComputerUseBadge.set_active(badge, True)
    badge.stop.assert_called_once_with()


def test_computer_bridge_returns_fresh_screenshot_after_each_action():
    import asyncio
    from pygpt_net.provider.llms.computer import AgentComputerBridge
    runtime = SimpleNamespace(
        window=SimpleNamespace(computer_use_badge=None), is_stopped=lambda: False,
        local_tool_lock=asyncio.Lock(), status=SimpleNamespace(show_tool=lambda name: False), verbose=Mock())
    bridge = AgentComputerBridge(runtime)
    bridge._execute_direct = Mock(return_value=[{'result': True}])
    bridge._capture_direct = Mock(side_effect=[('/tmp/one.png', 'first-image'), ('/tmp/two.png', 'second-image')])
    async def settle(commands):
        pass
    bridge._settle_before_direct_capture = settle
    async def execute():
        first = await bridge.execute([{'cmd': 'mouse_click'}], require_screenshot=True)
        second = await bridge.execute([{'cmd': 'mouse_move'}], require_screenshot=True)
        assert first.screenshot_b64 == 'first-image'
        assert second.screenshot_b64 == 'second-image'
    asyncio.run(execute())
    assert bridge._capture_direct.call_count == 2
