from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from pygpt_net.core.debug.loggers.base import BaseDebugLogger


@dataclass
class Payload:
    value: int
    api_key: str


def test_enabled_reads_config_and_is_safe_without_window():
    logger = BaseDebugLogger()
    assert logger.enabled("x") is False

    window = SimpleNamespace(core=SimpleNamespace(config=SimpleNamespace(get=lambda key, default=False: key == "x")))
    assert BaseDebugLogger(window).enabled("x") is True


def test_safe_value_masks_secrets_and_summarizes_binary():
    value = BaseDebugLogger.safe_value({
        "api_key": "secret",
        "nested": {"access_token": "token"},
        "image_bytes": b"abc",
    })
    assert value["api_key"] == "***MASKED***"
    assert value["nested"]["access_token"] == "***MASKED***"
    assert value["image_bytes"] == "<bytes: 3 bytes>"


def test_safe_value_handles_paths_dataclasses_and_long_strings():
    assert BaseDebugLogger.safe_value(Path("/tmp/file")) == "/tmp/file"
    result = BaseDebugLogger.safe_value(Payload(7, "secret"))
    assert result["value"] == 7
    assert result["api_key"] == "***MASKED***"

    long_text = "x" * 200_001
    clipped = BaseDebugLogger.safe_value(long_text)
    assert clipped.startswith("x" * 100)
    assert "truncated 1 chars" in clipped


def test_emit_prints_json_payload(capsys):
    BaseDebugLogger().emit("TEST", {"value": 1})
    output = capsys.readouterr().out
    assert "TEST" in output
    assert '"value": 1' in output
