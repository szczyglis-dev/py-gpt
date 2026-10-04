#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 14:00:00                  #
# ================================================== #

"""Plugin-owned tool display rules. Return text blocks or None for RAW fallback."""

import json


def decode(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            pass
    return value


def block(text, label, language='text'):
    return dict(text=text, label=label, language=language)


def render_execution(value, name, direction):
    if direction == 'input':
        params = value.get('params', value)
        if not isinstance(params, dict):
            return None
        key = next((key for key in ('code', 'command', 'path') if isinstance(params.get(key), str)), None)
        return [block(params[key], 'Input', 'python' if key == 'code' else 'bash')] if key else None
    streams = [block(value[key], key.upper()) for key in ('stdout', 'stderr')
               if isinstance(value.get(key), str) and value[key]]
    if streams:
        return streams
    result = value.get('result')
    nested = decode(result)
    if isinstance(nested, dict) and any(key in nested for key in ('result', 'stdout', 'stderr')):
        return render_execution(nested, name, direction)
    if isinstance(result, str):
        return [block(result, 'Output')]
    if 'stdout' in value or 'stderr' in value:
        return [block('', 'STDOUT')]
    return None


class BaseToolRender:
    """Optional plugin-owned renderer; import subclasses statically."""

    def __init__(self, plugin=None):
        self.plugin = plugin

    def get_rules(self):
        return {}
