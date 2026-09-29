from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.types import MODE_AGENT_V2, MODE_CHAT
from pygpt_net.plugin.canvas_web.worker import Worker


def _plugin(*, mode=MODE_CHAT, files_io=False):
    filesystem = SimpleNamespace(
        materialize_runtime_artifact=MagicMock(return_value={
            "name": "painter-user.png",
            "path": "/mnt/tmp/runtime_artifacts/2026-09-24/painter-user.png",
            "host_path": "/profile/tmp/runtime_artifacts/2026-09-24/painter-user.png",
            "sandbox_path": "/mnt/tmp/runtime_artifacts/2026-09-24/painter-user.png",
            "runtime_paths": {},
        }),
    )
    plugins = SimpleNamespace(is_enabled=MagicMock(return_value=files_io))
    return SimpleNamespace(
        id="canvas_web",
        allowed_cmds={"get_user_painter_image"},
        has_cmd=lambda name: name == "get_user_painter_image",
        window=SimpleNamespace(
            core=SimpleNamespace(
                config=SimpleNamespace(get=lambda key: mode if key == "mode" else None),
                filesystem=filesystem,
            ),
            controller=SimpleNamespace(
                kernel=SimpleNamespace(stopped=lambda: False),
                plugins=plugins,
            ),
        ),
    )


def _run_painter_tool(*, mode=MODE_CHAT, files_io=False, agent_call=False):
    worker = Worker()
    worker.plugin = _plugin(mode=mode, files_io=files_io)
    worker.cmds = [{"cmd": "get_user_painter_image", "params": {}}]
    worker.ctx = SimpleNamespace(agent_call=agent_call, runtime_artifacts=[])
    worker._call = MagicMock(return_value={
        "path": "/profile/tmp/runtime_artifacts/2026-09-24/raw-painter-user.png",
        "name": "painter-user.png",
        "width": 1024,
        "height": 768,
    })
    worker.reply_more = MagicMock()
    worker.cleanup = MagicMock()

    worker.run()

    worker._call.assert_called_once_with("get_user_painter_image", {})
    worker.plugin.window.core.filesystem.materialize_runtime_artifact.assert_called_once_with(
        "/profile/tmp/runtime_artifacts/2026-09-24/raw-painter-user.png",
        ctx=worker.ctx,
        name="painter-user.png",
    )
    return worker.reply_more.call_args.args[0][0]


def test_get_user_painter_image_agents_returns_runtime_tmp_path_without_auto_attachment():
    response = _run_painter_tool(mode=MODE_AGENT_V2, files_io=False)

    assert response["cmd"] == "get_user_painter_image"
    assert response["result"] == {
        "path": "/mnt/tmp/runtime_artifacts/2026-09-24/painter-user.png",
    }
    assert "agent_runtime_attachments" not in response


def test_get_user_painter_image_chat_internal_agent_call_flag_does_not_change_mode_policy():
    response = _run_painter_tool(mode=MODE_CHAT, files_io=False, agent_call=True)

    assert response["result"] == "Attached for native analysis in the next model request: painter-user.png"
    assert response["agent_runtime_attachments"] == [
        {
            "path": "/profile/tmp/runtime_artifacts/2026-09-24/painter-user.png",
            "name": "painter-user.png",
        },
    ]


def test_get_user_painter_image_with_files_io_returns_path_for_explicit_attach_runtime_file():
    response = _run_painter_tool(mode=MODE_CHAT, files_io=True)

    assert response["result"] == {
        "path": "/mnt/tmp/runtime_artifacts/2026-09-24/painter-user.png",
    }
    assert "agent_runtime_attachments" not in response


def test_get_user_painter_image_without_files_io_uses_attach_runtime_file_transport_contract():
    response = _run_painter_tool(mode=MODE_CHAT, files_io=False)

    assert response["result"] == "Attached for native analysis in the next model request: painter-user.png"
    assert response["agent_runtime_attachments"] == [
        {
            "path": "/profile/tmp/runtime_artifacts/2026-09-24/painter-user.png",
            "name": "painter-user.png",
        },
    ]


def test_canvas_plugin_exposes_painter_tool_with_conditional_runtime_guidance():
    from pygpt_net.plugin.canvas_web.plugin import Plugin

    plugin = Plugin()

    assert "get_user_painter_image" in plugin.allowed_cmds
    assert plugin.has_cmd("get_user_painter_image") is True
    tool = plugin.get_cmd("get_user_painter_image")
    instruction = tool["instruction"]
    assert "Painter tab" in instruction
    assert "runtime temporary storage" in instruction
    assert "attach_runtime_file" in instruction
    assert "Agents" in instruction
    assert tool["params"] == []

    prompt = plugin.on_system_prompt("")
    assert "get_user_painter_image" in prompt
    assert "user created or edited" in prompt
    assert "attach_runtime_file" in prompt
    assert "persistent chat attachment list" in prompt
