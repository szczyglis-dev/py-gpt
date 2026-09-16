from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.docker.builder as builder_module
from pygpt_net.core.docker.builder import Builder, Worker
from pygpt_net.core.events import RenderEvent


def make_plugin():
    window = SimpleNamespace(
        update_status=MagicMock(),
        threadpool=SimpleNamespace(start=MagicMock()),
        ui=SimpleNamespace(dialogs=SimpleNamespace(alert=MagicMock())),
        controller=SimpleNamespace(kernel=SimpleNamespace(stop=MagicMock())),
        dispatch=MagicMock(),
    )
    return SimpleNamespace(window=window)


def test_docker_builder_starts_worker_and_connects_callbacks(monkeypatch):
    plugin = make_plugin()
    fake_worker = SimpleNamespace(
        plugin=None,
        docker=None,
        restart=None,
        signals=SimpleNamespace(
            build_finished=SimpleNamespace(connect=MagicMock()),
            error=SimpleNamespace(connect=MagicMock()),
        ),
    )
    monkeypatch.setattr(builder_module, "Worker", MagicMock(return_value=fake_worker))

    builder = Builder(plugin)
    builder.docker = object()
    builder.build_image(restart=True)

    plugin.window.update_status.assert_called_once_with("Please wait... building...")
    assert fake_worker.plugin is plugin
    assert fake_worker.docker is builder.docker
    assert fake_worker.restart is True
    fake_worker.signals.build_finished.connect.assert_called_once_with(builder.handle_build_finished)
    fake_worker.signals.error.connect.assert_called_once_with(builder.handle_build_failed)
    plugin.window.threadpool.start.assert_called_once_with(fake_worker)


def test_docker_builder_build_start_error_is_reported(monkeypatch):
    plugin = make_plugin()
    monkeypatch.setattr(builder_module, "Worker", MagicMock(side_effect=RuntimeError("worker failed")))
    builder = Builder(plugin)

    builder.build_image()

    error = plugin.window.ui.dialogs.alert.call_args.args[0]
    assert isinstance(error, RuntimeError)
    assert str(error) == "worker failed"


def test_docker_builder_finish_and_failure_stop_kernel_and_end_render(monkeypatch):
    plugin = make_plugin()
    builder = Builder(plugin)
    monkeypatch.setattr(builder_module, "trans", lambda key: "finished")

    builder.handle_build_finished()
    plugin.window.ui.dialogs.alert.assert_called_with("finished")
    plugin.window.update_status.assert_called_with("finished")
    plugin.window.controller.kernel.stop.assert_called_once_with()
    event = plugin.window.dispatch.call_args.args[0]
    assert event.name == RenderEvent.END

    plugin.window.controller.kernel.stop.reset_mock()
    plugin.window.dispatch.reset_mock()
    builder.handle_build_failed(ValueError("bad build"))
    plugin.window.ui.dialogs.alert.assert_called_with("bad build")
    plugin.window.update_status.assert_called_with("bad build")
    plugin.window.controller.kernel.stop.assert_called_once_with()
    assert plugin.window.dispatch.call_args.args[0].name == RenderEvent.END


def test_docker_builder_worker_run_emits_success_restarts_and_cleans(monkeypatch):
    worker = Worker()
    worker.docker = SimpleNamespace(build_image=MagicMock(), restart=MagicMock())
    worker.restart = True
    signals = MagicMock()
    worker.signals = signals
    emitted = []
    monkeypatch.setattr(builder_module, "safe_emit", lambda source, name, *args: emitted.append((source, name, args)) or True)

    worker.run()

    worker.docker.build_image.assert_called_once_with()
    worker.docker.restart.assert_called_once_with()
    assert emitted == [(signals, "build_finished", ())]
    signals.deleteLater.assert_called_once_with()
    assert worker.signals is None


def test_docker_builder_worker_run_emits_error_and_does_not_restart(monkeypatch):
    worker = Worker()
    error = RuntimeError("build failed")
    worker.docker = SimpleNamespace(build_image=MagicMock(side_effect=error), restart=MagicMock())
    worker.restart = True
    signals = MagicMock()
    worker.signals = signals
    emitted = []
    monkeypatch.setattr(builder_module, "safe_emit", lambda source, name, *args: emitted.append((source, name, args)) or True)

    worker.run()

    worker.docker.restart.assert_not_called()
    assert emitted == [(signals, "error", (error,))]
    assert worker.signals is None
