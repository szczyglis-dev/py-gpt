from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from pygpt_net.controller import Controller


def _bare_controller():
    controller = Controller.__new__(Controller)
    controller.window = MagicMock()
    controller.reloading = False

    for name in (
        "debug", "kernel", "chat", "layout", "ui", "lang", "assistant",
        "remote_store", "agent", "tools", "ctx", "presets", "idx",
        "dialogs", "audio", "attachment", "camera", "access", "realtime",
        "media", "settings", "plugins", "model", "launcher", "calendar",
        "painter", "notepad", "files", "theme",
    ):
        setattr(controller, name, MagicMock())

    controller.ui.tabs = MagicMock()
    controller.plugins.settings = MagicMock()
    controller.model.editor = MagicMock()
    controller.dialogs.info = MagicMock()
    controller.window.core.config.get = MagicMock(return_value=True)
    controller.window.core.agents.custom = MagicMock()
    controller.window.tools = MagicMock()
    controller.presets.lock = MagicMock()
    controller.presets.unlock = MagicMock()
    return controller


def test_controller_setup_calls_all_primary_components():
    controller = _bare_controller()

    controller.setup()

    controller.debug.setup.assert_called_once_with()
    controller.kernel.init.assert_called_once_with()
    controller.chat.init.assert_called_once_with()
    controller.layout.setup.assert_called_once_with()
    controller.ui.setup.assert_called_once_with()
    controller.ui.tabs.setup.assert_called_once_with()
    controller.lang.setup.assert_called_once_with()
    controller.assistant.setup.assert_called_once_with()
    controller.remote_store.setup.assert_called_once_with()
    controller.chat.setup.assert_called_once_with()
    controller.agent.setup.assert_called_once_with()
    controller.tools.setup.assert_called_once_with()
    controller.ctx.setup.assert_called_once_with()
    controller.presets.setup.assert_called_once_with()
    controller.idx.setup.assert_called_once_with()
    controller.ui.update_tokens.assert_called_once_with()
    controller.dialogs.setup.assert_called_once_with()
    controller.audio.setup.assert_called_once_with()
    controller.attachment.setup.assert_called_once_with()
    controller.camera.setup_ui.assert_called_once_with()
    controller.access.setup.assert_called_once_with()
    controller.realtime.setup.assert_called_once_with()
    controller.media.setup.assert_called_once_with()


def test_controller_post_setup_does_not_open_license_when_accepted():
    controller = _bare_controller()
    controller.window.core.config.get.return_value = True

    controller.post_setup()

    controller.settings.setup.assert_called_once_with()
    controller.plugins.settings.setup.assert_called_once_with()
    controller.model.editor.setup.assert_called_once_with()
    controller.launcher.post_setup.assert_called_once_with()
    controller.calendar.setup.assert_called_once_with()
    controller.painter.setup.assert_called_once_with()
    controller.debug.post_setup.assert_called_once_with()
    controller.ui.tabs.restore_data.assert_called_once_with()
    controller.dialogs.info.toggle.assert_not_called()


def test_controller_post_setup_opens_license_when_not_accepted():
    controller = _bare_controller()
    controller.window.core.config.get.return_value = False
    controller.window.ui.dialog = {"info.license": MagicMock()}

    controller.post_setup()

    controller.dialogs.info.toggle.assert_called_once_with(
        "license",
        width=500,
        height=480,
    )
    controller.window.ui.dialog["info.license"].setFocus.assert_called_once_with()


def test_controller_after_setup_updates_plugins():
    controller = _bare_controller()

    controller.after_setup()

    controller.plugins.update.assert_called_once_with()


def test_controller_init_loads_settings():
    controller = _bare_controller()

    controller.init()

    controller.settings.load.assert_called_once_with()


def test_controller_reload_success_unlocks_and_restarts_components():
    controller = _bare_controller()

    with patch("pygpt_net.controller.mem_clean") as mem_clean:
        controller.reload()

    assert controller.reloading is False
    controller.presets.lock.assert_called_once_with()
    controller.presets.unlock.assert_called_once_with()
    controller.window.core.reload.assert_called_once_with()
    controller.ui.tabs.reload.assert_called_once_with(restore_data=False)
    controller.ctx.reload.assert_called_once_with()
    controller.ui.tabs.reload_after.assert_called_once_with()
    controller.ctx.reload_after.assert_called_once_with()
    controller.kernel.restart.assert_called_once_with()
    controller.theme.reload_all.assert_called_once_with()
    controller.window.tools.on_reload.assert_called_once_with()
    mem_clean.assert_called_once_with(force=True)


def test_controller_reload_recovers_from_component_error_and_unlocks():
    controller = _bare_controller()
    error = RuntimeError("reload failed")
    controller.window.core.reload.side_effect = error

    with patch("pygpt_net.controller.mem_clean") as mem_clean:
        controller.reload()

    controller.window.core.debug.log.assert_called_once_with(error)
    controller.presets.unlock.assert_called_once_with()
    assert controller.reloading is False
    mem_clean.assert_called_once_with(force=True)


def test_controller_reload_ignores_memory_cleanup_error():
    controller = _bare_controller()

    with patch("pygpt_net.controller.mem_clean", side_effect=RuntimeError("cleanup")):
        controller.reload()

    assert controller.reloading is False
    controller.presets.unlock.assert_called_once_with()
