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

"""Compact execution responses shared by execution plugins."""


def text(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    return value if isinstance(value, str) else ''


def output_text(response):
    if 'stdout' in response or 'stderr' in response:
        return '\n'.join(part for part in (text(response.get('stdout')), text(response.get('stderr'))) if part)
    return str(response.get('result', ''))


def execution_response(request, stdout='', stderr='', return_code=None, context=None):
    stdout, stderr = text(stdout), text(stderr)
    response = {'request': request, 'result': not bool(stderr) and return_code in (None, 0),
                'stdout': stdout, 'stderr': stderr}
    if isinstance(return_code, int):
        response['return_code'] = return_code
    if context is not None:
        response['context'] = context
    return response
