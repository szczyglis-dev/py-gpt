"""Real provider/config fixtures shared by native tool-builder tests."""
import copy
from types import SimpleNamespace

from pygpt_net.config import Config
from pygpt_net.provider.core.config.patches.patch_before_2_8_35 import migrate_remote_tools, metadata_providers


def bind_remote_providers(window, data=None):
    config = object.__new__(Config)
    config.data = copy.deepcopy(data or {})
    migrate_remote_tools(config.data)
    providers = {p.id: p.bind(SimpleNamespace(core=SimpleNamespace(config=config)))
                 for p in metadata_providers()}
    window.core.llm = SimpleNamespace(get=providers.get, llms=providers)
    return config
