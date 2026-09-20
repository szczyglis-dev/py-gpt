from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.security import Security, SecurityError


def make_security(tmp_path, *, os_id="linux", values=None):
    values = dict(values or {})
    data_dir = tmp_path / "data"
    tmp_dir = tmp_path / "tmp"
    data_dir.mkdir(exist_ok=True)
    tmp_dir.mkdir(exist_ok=True)

    def get(key, default=None):
        return values.get(key, default)

    config = SimpleNamespace(
        get=MagicMock(side_effect=get),
        get_user_dir=MagicMock(side_effect=lambda key: str(data_dir if key == "data" else tmp_dir)),
    )
    platforms = SimpleNamespace(
        is_windows=MagicMock(return_value=os_id == "windows"),
        is_mac=MagicMock(return_value=os_id == "macos"),
    )
    filesystem = SimpleNamespace(get_data_dir=MagicMock(return_value=str(data_dir)))
    window = SimpleNamespace(core=SimpleNamespace(
        config=config, platforms=platforms, filesystem=filesystem, ctx=SimpleNamespace(update_item=MagicMock())
    ))
    return Security(window), window, data_dir, tmp_dir


def test_paths_os_and_restriction_defaults(tmp_path):
    sec, _, data_dir, tmp_dir = make_security(tmp_path)
    assert sec.get_workdir() == str(data_dir)
    assert sec.get_os_id() == "linux"
    assert sec.get_os_label() == "Linux"
    assert sec.is_read_restricted() is True
    assert sec.is_write_restricted() is False
    assert sec.is_in_workdir(data_dir / "a.txt") is True
    assert sec.is_in_internal_tmp(tmp_dir / "a.txt") is True
    assert sec.is_in_allowed_workdir(tmp_dir / "nested" / "a.txt") is True
    assert sec.is_in_allowed_workdir(tmp_path / "outside.txt") is False


@pytest.mark.parametrize("os_id,label", [("windows", "Windows"), ("macos", "macOS")])
def test_os_labels(tmp_path, os_id, label):
    sec, *_ = make_security(tmp_path, os_id=os_id)
    assert sec.get_os_id() == os_id
    assert sec.get_os_label() == label


def test_ensure_read_and_write_enforce_only_when_enabled(tmp_path):
    values = {
        Security.READ_RESTRICT_KEY: True,
        Security.WRITE_RESTRICT_KEY: True,
    }
    sec, _, data_dir, tmp_dir = make_security(tmp_path, values=values)
    inside = str(data_dir / "ok.txt")
    internal = str(tmp_dir / "ok.txt")
    outside = str(tmp_path / "outside.txt")

    assert sec.ensure_read(inside) == inside
    assert sec.ensure_write(internal) == internal
    assert sec.ensure_read(outside, sandbox=True) == outside
    assert sec.ensure_write(outside, sandbox=True) == outside
    assert sec.ensure_read("") == ""
    assert sec.ensure_write(None) is None

    with pytest.raises(SecurityError, match="filesystem read access"):
        sec.ensure_read(outside)
    with pytest.raises(SecurityError, match="filesystem write access"):
        sec.ensure_write(outside)


def test_bulk_path_checks_delegate(tmp_path):
    sec, *_ = make_security(tmp_path)
    sec.ensure_read = MagicMock()
    sec.ensure_write = MagicMock()
    sec.ensure_reads(["a", "b"], sandbox=True)
    sec.ensure_writes(["c", "d"], sandbox=False)
    assert sec.ensure_read.call_args_list[0].args == ("a",)
    assert sec.ensure_read.call_args_list[0].kwargs == {"sandbox": True, "ctx": None}
    assert sec.ensure_read.call_count == 2
    assert sec.ensure_write.call_count == 2


def test_command_lists_and_posix_extraction(tmp_path):
    values = {
        "security.commands.whitelist.linux": "git, python; ls",
        "security.commands.blacklist.linux": ["rm", "SHUTDOWN"],
        Security.WHITELIST_ENABLED_KEY: True,
    }
    sec, *_ = make_security(tmp_path, values=values)
    assert sec.get_command_whitelist() == {"git", "python", "ls"}
    assert sec.get_command_blacklist() == {"rm", "shutdown"}
    assert sec.is_command_whitelist_enabled() is True
    assert sec.extract_command_names("FOO=1 /usr/bin/python script.py && git status | sed -n 1p; git log") == [
        "python", "git", "sed"
    ]
    assert sec.extract_command_names(None) == []
    assert sec.extract_command_names("   ") == []


def test_windows_command_name_normalization_and_ampersand_split(tmp_path):
    sec, *_ = make_security(tmp_path, os_id="windows")
    assert sec.extract_command_names(r'python.exe script.py & git.cmd status') == ["python", "git"]


def test_ensure_command_whitelist_blacklist_and_sandbox(tmp_path):
    values = {
        Security.WHITELIST_ENABLED_KEY: True,
        "security.commands.whitelist.linux": "git,python",
        "security.commands.blacklist.linux": "git",
    }
    sec, *_ = make_security(tmp_path, values=values)
    assert sec.ensure_command("git status && python x.py") == ["git", "python"]
    with pytest.raises(SecurityError, match="not allowed by the enabled whitelist"):
        sec.ensure_command("curl example.com")

    values[Security.WHITELIST_ENABLED_KEY] = False
    sec, *_ = make_security(tmp_path, values=values)
    with pytest.raises(SecurityError, match="blocked by the blacklist"):
        sec.ensure_command("git status")
    assert sec.ensure_command("git status", sandbox=True) == ["git"]


def test_computer_safety_state_and_messages(tmp_path):
    values = {
        "remote_tools.computer_use.sandbox": False,
        Security.COMPUTER_HALT_INSECURE_KEY: True,
    }
    sec, window, *_ = make_security(tmp_path, values=values)
    ctx = SimpleNamespace(extra={
        "pending_safety_checks": [{"message": "Sensitive action"}, {"code": "C1"}],
        "computer_safety_decisions": [
            {"decision": "SafetyDecision.REQUIRE_CONFIRMATION", "explanation": "Needs approval"},
            {"decision": "allow", "explanation": "Sensitive action"},
        ],
    })
    assert sec.has_pending_computer_safety(ctx) is True
    assert sec.should_halt_computer(ctx) is True
    assert sec.can_acknowledge_computer_safety(ctx) is False
    assert sec.get_computer_safety_messages(ctx) == ["Sensitive action", "C1", "Needs approval"]

    sec.mark_computer_safety_confirmed(ctx)
    assert ctx.extra["computer_safety_confirmed"] is True
    assert ctx.extra["computer_safety_waiting"] is False
    assert sec.should_halt_computer(ctx) is False
    assert sec.can_acknowledge_computer_safety(ctx) is True


def test_computer_safety_sandbox_or_disabled_halt_can_acknowledge(tmp_path):
    ctx = SimpleNamespace(extra={"computer_safety_decisions": [{"decision": "require_confirmation"}]})
    sec, *_ = make_security(tmp_path, values={"remote_tools.computer_use.sandbox": True})
    assert sec.should_halt_computer(ctx) is False
    assert sec.can_acknowledge_computer_safety(ctx) is True

    sec, *_ = make_security(tmp_path, values={Security.COMPUTER_HALT_INSECURE_KEY: False})
    assert sec.should_halt_computer(ctx) is False
    assert sec.can_acknowledge_computer_safety(ctx) is True
    assert sec.has_pending_computer_safety(SimpleNamespace(extra={})) is False
    assert sec.get_computer_safety_messages(None) == []
