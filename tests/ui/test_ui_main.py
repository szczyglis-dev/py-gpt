import importlib.util
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt


def _load_main_module():
    """Load ui.main while stubbing optional heavy app stacks only for this module load."""
    events = types.ModuleType("pygpt_net.core.events")

    class BaseEvent:
        pass

    class KernelEvent:
        STATUS = "status"

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class ControlEvent:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    events.BaseEvent = BaseEvent
    events.Event = BaseEvent
    events.AppEvent = BaseEvent
    events.KernelEvent = KernelEvent
    events.ControlEvent = ControlEvent

    stubs = {
        "pygpt_net.core.events": events,
        "pygpt_net.app_core": types.SimpleNamespace(Core=type("Core", (), {})),
        "pygpt_net.controller": types.SimpleNamespace(Controller=type("Controller", (), {})),
        "pygpt_net.tools": types.SimpleNamespace(Tools=type("Tools", (), {})),
        "pygpt_net.ui.widget.textarea.web": types.SimpleNamespace(ChatWebOutput=type("ChatWebOutput", (), {})),
    }

    import pygpt_net.ui as ui_package
    marker = object()
    old_ui = getattr(ui_package, "UI", marker)
    ui_package.UI = type("UI", (), {})
    try:
        spec = importlib.util.find_spec("pygpt_net.ui.main")
        module_spec = importlib.util.spec_from_file_location("_pygpt_ui_main_unit", spec.origin)
        module = importlib.util.module_from_spec(module_spec)
        with patch.dict(sys.modules, stubs):
            module_spec.loader.exec_module(module)
        return module
    finally:
        if old_ui is marker:
            delattr(ui_package, "UI")
        else:
            ui_package.UI = old_ui


MainModule = _load_main_module()
MainWindow = MainModule.MainWindow


def _window():
    return SimpleNamespace(
        controller=SimpleNamespace(
            plugins=MagicMock(), debug=MagicMock(), kernel=MagicMock(), ctx=MagicMock(),
            notepad=MagicMock(), calendar=MagicMock(), painter=MagicMock(), layout=MagicMock(),
            access=MagicMock(),
        ),
        tools=MagicMock(),
        core=SimpleNamespace(
            config=MagicMock(), tabs=MagicMock(), presets=MagicMock(), dispatcher=MagicMock(),
        ),
        ui=SimpleNamespace(tray=MagicMock(), tray_menu={"restore": MagicMock()}),
        state="idle", is_post_update=False, is_closing=False,
        timer=None, post_timer=None, update_timer=None, prevState=None,
        hide=MagicMock(), restore=MagicMock(), activateWindow=MagicMock(),
        showMinimized=MagicMock(), showMaximized=MagicMock(), showNormal=MagicMock(),
        isVisible=MagicMock(return_value=True), isActiveWindow=MagicMock(return_value=True),
        isMinimized=MagicMock(return_value=False), isMaximized=MagicMock(return_value=False),
        dispatch=MagicMock(), _esc_shortcut=None,
    )


def test_update_calls_plugins_and_tools():
    w = _window()
    MainWindow.update(w)
    w.controller.plugins.on_update.assert_called_once_with()
    w.tools.on_update.assert_called_once_with()


def test_post_update_is_reentrancy_guarded_and_resets_flag():
    w = _window()
    MainWindow.post_update(w)
    w.controller.debug.on_post_update.assert_called_once_with()
    w.controller.plugins.on_post_update.assert_called_once_with()
    w.tools.on_post_update.assert_called_once_with()
    assert w.is_post_update is False

    w.is_post_update = True
    MainWindow.post_update(w)
    assert w.controller.debug.on_post_update.call_count == 1


def test_update_state_changes_tray_icon_only_for_new_state():
    w = _window()
    MainWindow.update_state(w, "idle")
    w.ui.tray.set_icon.assert_not_called()

    MainWindow.update_state(w, "busy")
    assert w.state == "busy"
    w.ui.tray.set_icon.assert_called_once_with("busy")


def test_dispatch_forwards_all_flag():
    w = _window()
    event = object()
    MainWindow.dispatch(w, event, all=True)
    w.core.dispatcher.dispatch.assert_called_once_with(event, all=True)


def test_shutdown_runs_all_persistence_and_stops_timers():
    w = _window()
    timers = [MagicMock(), MagicMock(), MagicMock()]
    w.timer, w.post_timer, w.update_timer = timers

    with patch.object(MainModule, "trans", return_value="bye"):
        MainWindow.shutdown(w)

    assert w.is_closing is True
    w.controller.kernel.terminate.assert_called_once_with()
    w.controller.ctx.save_all.assert_called_once_with()
    w.core.tabs.save.assert_called_once_with()
    w.controller.notepad.save_all.assert_called_once_with()
    w.controller.calendar.save_all.assert_called_once_with()
    w.controller.painter.save_all.assert_called_once_with()
    w.controller.plugins.save_all.assert_called_once_with()
    w.tools.on_exit.assert_called_once_with()
    w.controller.kernel.close_clients.assert_called_once_with()
    w.controller.layout.save.assert_called_once_with()
    w.core.config.save.assert_called_once_with()
    w.core.presets.save_all.assert_called_once_with()
    for timer in timers:
        timer.stop.assert_called_once_with()
        timer.deleteLater.assert_called_once_with()
    assert w.timer is w.post_timer is w.update_timer is None


def test_shutdown_is_idempotent():
    w = _window()
    w.is_closing = True
    MainWindow.shutdown(w)
    w.controller.kernel.terminate.assert_not_called()


def test_tray_toggle_restores_hidden_window_when_minimize_to_tray_enabled():
    w = _window()
    w.core.config.get.return_value = True
    w.isVisible.return_value = False
    MainWindow.tray_toggle(w)
    w.restore.assert_called_once_with()


def test_tray_toggle_hides_active_visible_window_when_enabled():
    w = _window()
    w.core.config.get.return_value = True
    MainWindow.tray_toggle(w)
    w.ui.tray_menu["restore"].setVisible.assert_called_once_with(True)
    w.hide.assert_called_once_with()


def test_restore_preserves_maximized_state():
    w = _window()
    w.prevState = Qt.WindowMaximized
    MainWindow.restore(w)
    w.showMaximized.assert_called_once_with()
    w.activateWindow.assert_called_once_with()
    w.ui.tray_menu["restore"].setVisible.assert_called_once_with(False)


def test_escape_shortcut_falls_back_to_access_handler():
    w = _window()
    w._route_escape_to_focus_or_popup = MagicMock(return_value=False)
    MainWindow._on_escape_shortcut(w)
    w.controller.access.on_escape.assert_called_once_with()


def test_escape_shortcut_stops_after_popup_handled():
    w = _window()
    w._route_escape_to_focus_or_popup = MagicMock(return_value=True)
    MainWindow._on_escape_shortcut(w)
    w.controller.access.on_escape.assert_not_called()
