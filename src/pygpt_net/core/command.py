#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.08 11:00:00                  #
# ================================================== #
import json


class Command:
    def __init__(self, config=None):
        """
        Command

        :param config: config object
        """
        self.config = config

    def get_prompt(self):
        """
        Returns cmd prompt instruction

        :return: prompt instruction
        """
        cmd = '''RUNNING COMMANDS:
        You are allowed to run commands in user's environment. To run command return JSON object with "cmd" key and command name
        as value. Put command parameters in "params" key. Example: {"cmd": "web", "params": {"query": "some query"}}.
        Use ONLY syntax like this. DO NOT use any other syntax. Append JSON object to response at the end of response
        and split it with ~###~ character. Example: response text ~###~ {"cmd": "web", "params": {"query": "some query"}}.
        If you want to run command without any response, return only JSON object. Responses from commands will be returned
        in "result" key. List of available commands is below.'''

        # syntax
        # cmd += '\n"save_file": save data to file, params: "filename", "data"'
        # cmd += '\n"read_file": read data from file, params: "filename"'
        return cmd

    def extract_cmds(self, response):
        """
        Extracts commands from response

        :param response: response
        :return: commands
        """
        cmds = []
        try:
            chunks = response.split('~###~')
            for chunk in chunks:
                try:
                    cmds.append(json.loads(chunk.strip()))
                except:
                    pass
        except:
            pass
        return cmds