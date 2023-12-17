#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

import copy


class Plugins:
    def __init__(self, config):
        """
        Plugins handler

        :param config: Config instance
        """
        self.config = config
        self.allowed_types = ['audio.input', 'audio.output', 'text.input', 'text.output']
        self.plugins = {}

    def dispatch(self, id, event, data):
        """
        Dispatch custom plugin event

        :param id: plugin id
        :param event: event name
        :param data: event data
        :return: event data
        """
        if id in self.plugins:
            try:
                return self.plugins[id].on_dispatch(event, data)
            except AttributeError:
                pass
        return data

    def apply(self, id, event, data):
        """
        Apply plugin event

        :param id: plugin id
        :param event: event name
        :param data: event data
        :return: event data
        """
        if id in self.plugins:
            try:
                if event == 'input.before':
                    return self.plugins[id].on_input_before(data)
                elif event == 'ctx.before':
                    return self.plugins[id].on_ctx_before(data)
                elif event == 'ctx.after':
                    return self.plugins[id].on_ctx_after(data)
                elif event == 'ctx.begin':
                    return self.plugins[id].on_ctx_begin(data)
                elif event == 'ctx.end':
                    return self.plugins[id].on_ctx_end(data)
                elif event == 'system.prompt':
                    return self.plugins[id].on_system_prompt(data)
                elif event == 'ai.name':
                    return self.plugins[id].on_ai_name(data)
                elif event == 'user.name':
                    return self.plugins[id].on_user_name(data)
                elif event == 'user.send':
                    return self.plugins[id].on_user_send(data)
                elif event == 'enable':
                    return self.plugins[id].on_enable()
                elif event == 'disable':
                    return self.plugins[id].on_disable()
                elif event == 'cmd.syntax':
                    return self.plugins[id].cmd_syntax(data)
            except AttributeError:
                pass

        return data

    def apply_cmd(self, id, ctx, cmds):
        """
        Apply commands

        :param id: plugin id
        :param ctx: event data
        :param cmds: commands
        :return: event data
        """
        if id in self.plugins:
            try:
                return self.plugins[id].cmd(ctx, cmds)
            except AttributeError:
                pass

        return ctx

    def is_registered(self, id):
        """
        Check if plugin is registered

        :param id: plugin id
        :return: true if registered
        :rtype: bool
        """
        return id in self.plugins

    def register(self, plugin):
        """
        Register plugin

        :param plugin: plugin instance
        """
        id = plugin.id
        self.plugins[id] = plugin

        # make copy of options
        if hasattr(plugin, 'options'):
            self.plugins[id].initial_options = copy.deepcopy(plugin.options)

        try:
            plugins = self.config.get('plugins')
            if id in plugins:
                for key in plugins[id]:
                    if key in self.plugins[id].options:
                        self.plugins[id].options[key]['value'] = plugins[id][key]
        except Exception as e:
            print('Error while loading plugin options: {}'.format(id))
            print(e)

    def restore_options(self, id):
        """
        Restore options to initial values

        :param id: plugin id
        """
        persisted_options = []
        persisted_values = {}
        for key in self.plugins[id].options:
            if 'persist' in self.plugins[id].options[key] and self.plugins[id].options[key]['persist']:
                persisted_options.append(key)

        # store persisted values
        for key in persisted_options:
            persisted_values[key] = self.plugins[id].options[key]['value']

        # restore initial values
        if id in self.plugins:
            if hasattr(self.plugins[id], 'initial_options'):
                self.plugins[id].options = dict(self.plugins[id].initial_options)

        # restore persisted values
        for key in persisted_options:
            self.plugins[id].options[key]['value'] = persisted_values[key]
