import io
import tarfile
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import pygpt_net.core.docker.docker as mod
from pygpt_net.core.docker.docker import Docker, _normalize_dockerfile, get_sandbox_user_ids, migrate_default_dockerfile


def make_plugin(values=None, options=None):
    values = dict(values or {})
    options = dict(options or {})
    config = SimpleNamespace(
        get_user_dir=MagicMock(return_value="/work/data"),
        update_plugin_config=MagicMock(),
        save=MagicMock(),
    )
    window = SimpleNamespace(core=SimpleNamespace(config=config), update_status=MagicMock())
    plugin = SimpleNamespace(
        id="plugin-x",
        window=window,
        options=options,
        get_option_value=MagicMock(side_effect=lambda key: values.get(key)),
    )
    return plugin, config


def test_normalize_dockerfile_dedents_strips_and_trims_lines():
    raw = """
        FROM python:3.12   
        RUN echo hi    
    """
    assert _normalize_dockerfile(raw) == "FROM python:3.12\nRUN echo hi"
    assert _normalize_dockerfile(None) == ""


def test_migrate_default_dockerfile_only_when_unchanged():
    plugin, config = make_plugin(
        values={"dockerfile": "  FROM old  \n"},
        options={"dockerfile": {"value": "old"}},
    )
    assert migrate_default_dockerfile(plugin, "dockerfile", "FROM old", "FROM new") is True
    assert plugin.options["dockerfile"]["value"] == "FROM new"
    config.update_plugin_config.assert_called_once_with("plugin-x", "dockerfile", "FROM new")
    config.save.assert_called_once_with()

    plugin, config = make_plugin(
        values={"dockerfile": "FROM custom"},
        options={"dockerfile": {"value": "custom"}},
    )
    assert migrate_default_dockerfile(plugin, "dockerfile", "FROM old", "FROM new") is False
    config.update_plugin_config.assert_not_called()


def test_get_sandbox_user_ids_linux_and_fallback(monkeypatch):
    monkeypatch.setattr(mod.platform, "system", lambda: "Linux")
    monkeypatch.setattr(mod.os, "getuid", lambda: 1234)
    monkeypatch.setattr(mod.os, "getgid", lambda: 2345)
    assert get_sandbox_user_ids() == (1234, 2345)
    monkeypatch.setattr(mod.os, "getuid", lambda: 0)
    assert get_sandbox_user_ids() == (1000, 1000)
    monkeypatch.setattr(mod.platform, "system", lambda: "Windows")
    assert get_sandbox_user_ids() == (1000, 1000)


def test_option_getters_and_local_data_dir():
    values = {
        "dockerfile": "FROM x",
        "image_name": "img",
        "container_name": "ctr",
        "docker_entrypoint": "python -V",
    }
    plugin, _ = make_plugin(values=values)
    docker = Docker(plugin)
    assert docker.get_dockerfile() == "FROM x"
    assert docker.get_image_name() == "img"
    assert docker.get_container_name() == "ctr"
    assert docker.get_entrypoint() == "python -V"
    assert docker.get_local_data_dir() == "/work/data"


def test_create_docker_context_contains_only_dockerfile():
    docker = Docker(SimpleNamespace())
    stream = docker.create_docker_context("FROM scratch\n")
    assert isinstance(stream, io.BytesIO)
    with tarfile.open(fileobj=stream, mode="r") as tf:
        assert tf.getnames() == ["Dockerfile"]
        assert tf.extractfile("Dockerfile").read() == b"FROM scratch\n"


def test_prepare_local_data_dir_is_idempotent(tmp_path):
    docker = Docker(SimpleNamespace())
    target = tmp_path / "data"
    docker.get_local_data_dir = MagicMock(return_value=str(target))
    docker.prepare_local_data_dir()
    docker.prepare_local_data_dir()
    assert target.is_dir()


def test_volume_mapping_substitutes_workdir_and_skips_disabled():
    plugin, _ = make_plugin(values={
        "docker_volumes": [
            {"enabled": True, "host": "{workdir}/files", "docker": "/data"},
            {"enabled": False, "host": "/skip", "docker": "/skip"},
        ]
    })
    docker = Docker(plugin)
    docker.get_local_data_dir = MagicMock(return_value="/host/work")
    assert docker.get_volumes() == {"/host/work/files": {"bind": "/data", "mode": "rw"}}


def test_port_mapping_normalizes_protocol_and_skips_invalid(capsys):
    plugin, _ = make_plugin(values={
        "docker_ports": [
            {"enabled": True, "docker": "8000", "host": "18000"},
            {"enabled": True, "docker": "9000/udp", "host": "19000"},
            {"enabled": True, "docker": "bad", "host": "x"},
            {"enabled": False, "docker": "1", "host": "2"},
        ]
    })
    docker = Docker(plugin)
    assert docker.get_ports() == {"8000/tcp": 18000, "9000/udp": 19000}
    assert "Invalid host port" in capsys.readouterr().out


def test_run_as_root_user_and_labels_use_optional_option():
    plugin, _ = make_plugin(values={"docker_run_as_root": True}, options={"docker_run_as_root": {}})
    docker = Docker(plugin)
    assert docker.get_run_as_root() is True
    assert docker.get_container_user() == "0:0"
    assert docker.get_container_labels() == {"pygpt.run_as_root": "true"}

    plugin2, _ = make_plugin(values={})
    docker2 = Docker(plugin2)
    assert docker2.get_run_as_root() is False
    assert docker2.get_container_user() is None
    assert docker2.get_container_labels() == {"pygpt.run_as_root": "false"}


def test_end_restart_attach_signals_and_log_delegate():
    plugin, _ = make_plugin(values={"container_name": "ctr"})
    docker = Docker(plugin)
    docker.stop_container = MagicMock()
    docker.restart_container = MagicMock()
    docker.end(all=False)
    docker.stop_container.assert_not_called()
    docker.end(all=True)
    docker.stop_container.assert_called_once_with("ctr")
    docker.restart()
    docker.restart_container.assert_called_once_with("ctr")
    signals = object()
    docker.attach_signals(signals)
    assert docker.signals is signals
    docker.log("hello")
    plugin.window.update_status.assert_called_once_with("hello")


def test_build_image_passes_uid_gid_and_logs_streams(monkeypatch):
    plugin, _ = make_plugin(values={"dockerfile": "FROM x", "image_name": "img"})
    docker = Docker(plugin)
    client = SimpleNamespace(images=SimpleNamespace(build=MagicMock(return_value=(object(), [
        {"stream": " step 1 \n"}, {"other": "ignored"}
    ]))))
    docker.get_docker_client = MagicMock(return_value=client)
    docker.log = MagicMock()
    monkeypatch.setattr(mod, "get_sandbox_user_ids", lambda: (111, 222))
    docker.build_image()
    kwargs = client.images.build.call_args.kwargs
    assert kwargs["tag"] == "img"
    assert kwargs["buildargs"] == {"PYGPT_UID": "111", "PYGPT_GID": "222"}
    assert kwargs["custom_context"] is True and kwargs["rm"] is True
    assert docker.log.call_args_list[-1].args == ("step 1",)
