"""UI gateway to BasePlugin.get_tool_render_rules(); no imports or tool rules.

Rules are supplied by registered plugin instances, including disabled plugins
whose tools can appear in history. Missing/broken rules fall back to RAW.
"""
import copy
import json
import logging

logger = logging.getLogger(__name__)


def decode(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            pass
    return value


def rules_for(window=None):
    rules = {}
    if window is None:
        return rules
    plugins = getattr(getattr(window.core, 'plugins', None), 'plugins', {})
    if isinstance(plugins, dict):
        for plugin in plugins.values():
            try:
                provider = getattr(plugin, 'get_tool_render_rules', None)
                plugin_rules = provider() if callable(provider) else {}
                if isinstance(plugin_rules, dict):
                    rules.update(plugin_rules)
            except Exception:
                logger.exception('Cannot get plugin tool render rules')
    return rules


def project(value, name='', direction='output', window=None):
    value = decode(value)
    if isinstance(value, list):
        groups = [project(item, name, direction, window) for item in value]
        return sum(groups, []) if all(group is not None for group in groups) else None
    if not isinstance(value, dict):
        return None
    request = decode(value.get('request', {}))
    name = str(value.get('cmd') or (request.get('cmd') if isinstance(request, dict) else '') or name)
    rule = rules_for(window).get(name, {})
    rule = rule.get(direction) if isinstance(rule, dict) else None
    renderer = rule.get('parser') if isinstance(rule, dict) else None
    if not callable(renderer):
        return None
    try:
        blocks = renderer(copy.deepcopy(value), name, direction)
        if blocks is None:
            return None
        if isinstance(blocks, list) and all(isinstance(part, dict) and isinstance(part.get('text'), str) for part in blocks):
            language = rule.get('language')
            for part in blocks:
                if isinstance(language, str) and language:
                    part['language'] = language
                native_language = part.get('language')
                if direction == 'input' and isinstance(native_language, str) and native_language:
                    part['label'] = native_language
            return blocks
    except Exception:
        logger.exception('Tool display rule failed: %s', name)
    return None


def enrich(call, window=None):
    for source, direction in (('request', 'input'), ('response', 'output')):
        if source in call:
            friendly = project(call[source], call.get('name', ''), direction, window)
            if friendly is not None:
                call[source + '_friendly'] = friendly
    return call
