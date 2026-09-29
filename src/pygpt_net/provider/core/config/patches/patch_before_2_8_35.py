"""Move remote tool settings into provider-owned configuration (2.8.35)."""
import copy


def metadata_providers():
    # Config migration runs before LLM registration. Instantiate only metadata
    # providers; no SDK clients or API calls are needed for their setup().
    from pygpt_net.provider.llms.openai.provider import OpenAILLM
    from pygpt_net.provider.llms.google.provider import GoogleLLM
    from pygpt_net.provider.llms.anthropic.provider import AnthropicLLM
    from pygpt_net.provider.llms.x_ai.provider import xAILLM

    return (OpenAILLM(), GoogleLLM(), AnthropicLLM(), xAILLM())


def legacy_defaults() -> dict:
    return {field["legacy_key"]: copy.deepcopy(field.get("default"))
            for provider in metadata_providers()
            for field in provider.get_remote_tools_schema().values()
            if "legacy_key" in field}


def migrate_remote_tools(data: dict) -> bool:
    changed = False
    providers = data.get("providers")
    if not isinstance(providers, dict):
        providers = {}
        data["providers"] = providers
        changed = True
    for provider in metadata_providers():
        config_id = provider.get_config_id()
        entry = providers.get(config_id)
        if not isinstance(entry, dict):
            entry = {}
            providers[config_id] = entry
            changed = True
        remote = entry.get("remote_tools")
        if not isinstance(remote, dict):
            remote = {}
            entry["remote_tools"] = remote
            changed = True
        for key, field in provider.get_remote_tools_schema().items():
            legacy = field.get("legacy_key")
            aliases = field.get("legacy_aliases", [])
            old_keys = [legacy, *aliases] if legacy else aliases
            if key not in remote:
                value = next((data[k] for k in old_keys if k in data), field.get("default"))
                remote[key] = copy.deepcopy(value)
                changed = True
            for old_key in old_keys:
                if old_key in data:
                    del data[old_key]
                    changed = True

    # Retain also retired/manual provider options not exposed by today's schema.
    for old_key in list(data):
        if not old_key.startswith("remote_tools.") or old_key.startswith("remote_tools.global."):
            continue
        if old_key in ("remote_tools.computer_use.env", "remote_tools.computer_use.sandbox"):
            continue
        local_key = old_key[len("remote_tools."):]
        config_id = "openai"
        for prefix, provider_id in (("google.", "google"), ("anthropic.", "anthropic"), ("xai.", "x_ai")):
            if local_key.startswith(prefix):
                config_id, local_key = provider_id, local_key[len(prefix):]
                break
        if local_key.startswith("tool_search."):
            config_id = "anthropic"
        providers[config_id]["remote_tools"].setdefault(local_key, data.pop(old_key))
        changed = True

    # These are shared computer-runtime settings, not OpenAI tool options.
    for key in ("env", "sandbox"):
        old_key = "remote_tools.computer_use." + key
        if old_key in data:
            data.setdefault("computer_use." + key, data.pop(old_key))
            changed = True
    return changed
