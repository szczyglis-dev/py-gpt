from types import SimpleNamespace
from unittest.mock import Mock

from packaging.version import Version

from pygpt_net.provider.core.config.patch import Patch
from pygpt_net.core.summarizer.summarizer import DEFAULTS


def test_291_adds_defaults_preserves_choices_and_is_idempotent():
    data = {"__meta__": {"version": "2.9.0"}, "context.extra_summary.enabled": True,
            "context.extra_summary.model": "custom", "ctx.attachment.project_share": True}
    config = SimpleNamespace(all=lambda: data, save=Mock())
    window = SimpleNamespace(core=SimpleNamespace(config=config, updater=SimpleNamespace(post_check_config=lambda: False)))
    assert Patch(window).execute(Version("2.9.1"))
    assert config.data["context.extra_summary.enabled"] is True
    assert config.data["context.extra_summary.model"] == "custom"
    assert "ctx.attachment.project_share" not in config.data
    assert config.data["context.extra_summary.threshold"] == DEFAULTS["context.extra_summary.threshold"]
    assert config.data["context.extra_summary.target"] == DEFAULTS["context.extra_summary.target"]
    data.update(config.data)
    data["__meta__"]["version"] = "2.9.1"
    config.save.reset_mock()
    assert Patch(window).execute(Version("2.9.1")) is False
    config.save.assert_not_called()
