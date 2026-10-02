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
from pygpt_net.plugin.base.render import BaseToolRender


def block(text, label, language='text'):
    return dict(text=text, label=label, language=language)


def render(value, name, direction):
    if direction == 'input':
        params = value.get('params', value)
        if name in {'save_file', 'append_file'} and isinstance(params, dict) and isinstance(params.get('data'), str):
            return [block(params['data'], str(params.get('path') or 'Input'))]
        return None
    result = value.get('result')
    if name == 'read_file' and isinstance(result, list):
        if all(isinstance(item, dict) and isinstance(item.get('content'), str) for item in result):
            return [block(item['content'], str(item.get('path') or 'Output')) for item in result]
        return None
    if name in {'read_file', 'tree', 'query_file'} and isinstance(result, str):
        return [block(result, 'Output')]
    return None


class Render(BaseToolRender):
    def get_rules(self):
        rules = {name: {'output': {'parser': render, 'language': 'text'}}
                 for name in ('read_file', 'tree', 'query_file')}
        rules.update({name: {'input': {'parser': render, 'language': 'text'}}
                      for name in ('save_file', 'append_file')})
        return rules
