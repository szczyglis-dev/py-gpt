#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.16 17:00:00                  #
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
        You can execute commands and also use them to run commands on the user's environment. 

        Important rules:
        1) List of available commands is defined below.
        2) To execute defined command return JSON object with "cmd" key and command name as value.
        3) Always use syntax defined in command definition and correct command name.
        4) Put command parameters in "params" key. Example: {"cmd": "web", "params": {"query": "some query"}}. Use ONLY syntax like this. DO NOT use any other syntax.
        5) Append JSON object to response at the end of response and split it with ~###~ character. Example: text response ~###~ {"cmd": "web", "params": {"query": "some query"}}.
        6) If you want to execute command without any response, return only JSON object.
        7) Responses from commands will be returned in "result" key.
        8) Commands are listed one command per line and every command is described with syntax: "<name>": <action>, params: <params>
        9) Always use correct command name, e.g. if command name is "sys_exec" then use "sys_exec" and don't imagine other names, like "run" or something.
        10) With those commands you are allowed to run external commands and apps in user's system (environment)
        11) Always use defined syntax to prevent errors
        12) Always choose the most appropriate command from list to perform the task, based on the description of the action performed by a given comment
        13) Reply to the user in the language in which he started the conversation with you
        14) Use ONLY params described in command definition, do NOT use any additional params not described on list
        15) ALWAYS remember that any text content must appear at the beginning of your response and commands must only be included at the end.
        16) Try to run commands executed in the user's system in the background if running them may prevent receiving a response (e.g. when it is a desktop application)
        17) Every command param must be placed in one line, so when you generate code you must put all of code in one line
        Commands list:
        '''

        # get custom prompt from config if exists
        if 'cmd.prompt' in self.config.data:
            if self.config.data['cmd.prompt'] is not None and self.config.data['cmd.prompt'] != '':
                cmd = self.config.data['cmd.prompt']

        # syntax for commands:
        # cmd += '\n"save_file": save data to file, params: "filename", "data"'
        # cmd += '\n"read_file": read data from file, params: "filename"'
        return cmd

    def extract_cmds(self, response):
        """
        Extracts commands from response

        :param response: response
        :return: commands list
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