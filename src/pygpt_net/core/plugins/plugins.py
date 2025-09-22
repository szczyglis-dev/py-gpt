#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #

import copy
import configparser
import io
import os
from typing import Optional, Dict, List, Any

from pygpt_net.provider.core.plugin_preset.json_file import JsonFileProvider
from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.utils import trans


class Plugins:
    def __init__(self, window):
        """
        Plugins core

        :param window: Window instance
        """
        self.window = window
        self.allowed_types = [
            'audio.input',
            'audio.output',
            'text.input',
            'text.output',
            'vision',
            'schedule'
        ]
        self.plugins: Dict[str, BasePlugin] = {}
        self.presets: Dict[str, Any] = {}  # presets config
        self.provider = JsonFileProvider(window)

    def is_registered(self, plugin_id: str) -> bool:
        """
        Check if plugin is registered

        :param plugin_id: plugin id
        :return: True if registered
        """
        return plugin_id in self.plugins

    def all(self) -> Dict[str, BasePlugin]:
        """
        Get all plugins

        :return: plugins dict
        """
        return self.plugins

    def get_ids(self, sort: bool = False) -> List[str]:
        """
        Get all plugins ids

        :param sort: if True, return sorted ids
        :return: plugins ids list
        """
        if sort:
            return self.get_sorted_ids()
        return list(self.plugins.keys())

    def get_sorted_ids(self) -> List[str]:
        """
        Get all plugins ids sorted by name

        :return: sorted plugins ids list
        """
        return sorted(self.plugins.keys(), key=lambda pid: self.get_name(pid).lower())

    def get(self, plugin_id: str) -> Optional[BasePlugin]:
        """
        Get plugin by id

        :param plugin_id: plugin id
        :return: plugin instance
        """
        return self.plugins.get(plugin_id)

    def get_option(self, plugin_id: str, key: str) -> Any:
        """
        Get plugin option

        :param plugin_id: plugin id
        :param key: option key
        :return: option value
        """
        plugin = self.plugins.get(plugin_id)
        if plugin and hasattr(plugin, 'options'):
            opt = plugin.options.get(key)
            if opt is not None:
                return opt.get('value')
        return None

    def register(self, plugin: BasePlugin):
        """
        Register plugin

        :param plugin: plugin instance
        """
        plugin.attach(self.window)
        plugin_id = plugin.id
        self.plugins[plugin_id] = plugin

        if hasattr(plugin, 'options'):
            self.plugins[plugin_id].initial_options = copy.deepcopy(plugin.options)

        try:
            removed = False
            cfg = self.window.core.config
            plugins_cfg = cfg.get('plugins')
            if plugin_id in plugins_cfg:
                p_cfg = plugins_cfg[plugin_id]
                for key in list(p_cfg):
                    if hasattr(self.plugins[plugin_id], 'options') and key in self.plugins[plugin_id].options:
                        self.plugins[plugin_id].options[key]['value'] = p_cfg[key]
                    else:
                        removed = True
                        del p_cfg[key]

            if removed:
                cfg.save()

            self.register_options(plugin_id, self.plugins[plugin_id].options if hasattr(self.plugins[plugin_id], 'options') else {})
        except Exception as e:
            self.window.core.debug.log(e)
            print('Error while loading plugin options: {}'.format(plugin_id))

    def apply_all_options(self):
        """Apply all options to plugins"""
        removed = False
        user_config = self.window.core.config.get('plugins')
        for plugin_id, plugin in self.plugins.items():
            if hasattr(plugin, 'initial_options'):
                plugin.options = copy.deepcopy(plugin.initial_options)
            if plugin_id in user_config:
                ucfg = user_config[plugin_id]
                for key in list(ucfg):
                    if hasattr(plugin, 'options') and key in plugin.options:
                        plugin.options[key]['value'] = ucfg[key]
                    else:
                        print("removed")
                        removed = True
                        del ucfg[key]
        if removed:
            self.window.core.config.save()

    def register_options(self, plugin_id: str, options: Dict[str, dict]):
        """
        Register plugin options

        :param plugin_id: plugin id
        :param options: options dict
        """
        dict_types = ("dict", "cmd")
        for key, option in options.items():
            if option.get('type') in dict_types:
                key_name = f"{key}.params" if option['type'] == "cmd" else key
                parent = f"plugin.{plugin_id}"
                option['label'] = key_name
                self.window.ui.dialogs.register_dictionary(key_name, parent, option)

    def unregister(self, plugin_id: str):
        """
        Unregister plugin

        :param plugin_id: plugin id
        """
        self.plugins.pop(plugin_id, None)

    def enable(self, plugin_id: str):
        """
        Enable plugin by ID

        :param plugin_id: plugin id
        """
        plugin = self.plugins.get(plugin_id)
        if plugin:
            plugin.enabled = True
            cfg = self.window.core.config
            cfg.data['plugins_enabled'][plugin_id] = True
            cfg.save()

    def disable(self, plugin_id: str):
        """
        Disable plugin by ID

        :param plugin_id: plugin id
        """
        plugin = self.plugins.get(plugin_id)
        if plugin:
            plugin.enabled = False
            cfg = self.window.core.config
            cfg.data['plugins_enabled'][plugin_id] = False
            cfg.save()

    def destroy(self, plugin_id: str):
        """
        Destroy plugin workers (send stop signal)

        :param plugin_id: plugin id
        """
        plugin = self.plugins.get(plugin_id)
        if plugin:
            if hasattr(plugin, 'destroy'):
                plugin.destroy()

    def has_options(self, plugin_id: str) -> bool:
        """
        Check if plugin has options

        :param plugin_id: plugin id
        :return: True if has options
        """
        plugin = self.plugins.get(plugin_id)
        return bool(plugin and hasattr(plugin, 'options') and len(plugin.options) > 0)

    def restore_options(self, plugin_id: str, all: bool = False):
        """
        Restore options to initial values

        :param plugin_id: plugin id
        :param all: restore all options (including persisted)
        """
        plugin = self.plugins.get(plugin_id)
        if not plugin:
            return

        options_to_preserve: List[str] = []
        values: Dict[str, Any] = {}

        if not all and hasattr(plugin, 'options'):
            for key, opt in plugin.options.items():
                if 'persist' in opt and opt['persist']:
                    options_to_preserve.append(key)
            for key in options_to_preserve:
                values[key] = plugin.options[key]['value']

        if hasattr(plugin, 'initial_options'):
            plugin.options = copy.deepcopy(plugin.initial_options)

        if not all:
            for key in options_to_preserve:
                plugin.options[key]['value'] = values[key]

    def get_name(self, plugin_id: str) -> str:
        """
        Get plugin name (translated)

        :param plugin_id: plugin id
        :return: plugin name
        """
        plugin = self.get(plugin_id)
        default = plugin.name
        trans_key = f'plugin.{plugin_id}'
        name = trans(trans_key)
        if name == trans_key:
            name = default
        if plugin.use_locale:
            domain = f'plugin.{plugin_id}'
            name = trans('plugin.name', domain=domain)
        return name

    def get_desc(self, plugin_id: str) -> str:
        """
        Get description (translated)

        :param plugin_id: plugin id
        :return: plugin description
        """
        plugin = self.get(plugin_id)
        default = plugin.description
        trans_key = f'plugin.{plugin_id}.description'
        tooltip = trans(trans_key)
        if tooltip == trans_key:
            tooltip = default
        if plugin.use_locale:
            domain = f'plugin.{plugin_id}'
            tooltip = trans('plugin.description', domain=domain)
        return tooltip

    def dump_locale(self, plugin: BasePlugin, path: str):
        """
        Dump locale

        :param plugin: plugin
        :param path: path to locale file
        """
        options = {}
        options['plugin.name'] = plugin.name
        options['plugin.description'] = plugin.description

        plugin_options = getattr(plugin, 'options', {})
        for key in sorted(plugin_options.keys()):
            option = plugin_options[key]
            if 'label' in option:
                option_key = key + '.label'
                options[option_key] = option['label']
            if 'description' in option:
                option_key = key + '.description'
                options[option_key] = option['description']
            if 'tooltip' in option and option['tooltip'] is not None and option['tooltip'] != '':
                option_key = key + '.tooltip'
                options[option_key] = option['tooltip']

        ini = configparser.ConfigParser()
        ini['LOCALE'] = options

        with io.open(path, mode="w", encoding="utf-8") as f:
            ini.write(f)

    def has_preset(self, preset_id: str) -> bool:
        """
        Check if preset exists

        :param preset_id: preset id
        :return: True if preset exists
        """
        return preset_id in self.presets

    def get_preset(self, preset_id: str) -> Dict[str, Any]:
        """
        Get preset by id

        :param preset_id: preset id
        :return: preset dict
        """
        if self.has_preset(preset_id):
            return self.presets[preset_id]

    def set_preset(self, preset_id: str, preset: Dict[str, Any]):
        """
        Set config value

        :param preset_id: id
        :param preset: preset
        """
        self.presets[preset_id] = preset

    def replace_presets(self, presets: Dict[str, Any]):
        """
        Replace presets

        :param presets: presets dict
        """
        self.presets = presets

    def load_presets(self):
        """Load presets"""
        self.presets = self.provider.load()

    def remove_plugin_param_from_presets(self, plugin_id: str, param: str = None) -> bool:
        """
        Remove plugin param from all presets

        :param plugin_id: plugin id
        :param param: param key
        :return: True if updated
        """
        updated = False
        if self.presets is None:
            self.load_presets()

        if self.presets is None:
            return False

        if param is None:
            # remove all params for plugin
            for _preset_id, preset in self.presets.items():
                preset_config = preset["config"]
                if plugin_id in preset_config:
                    preset_config.pop(plugin_id)
                    updated = True
            if updated:
                self.save_presets()
            return updated

        for _preset_id, preset in self.presets.items():
            preset_config = preset["config"]
            if plugin_id in preset_config and param in preset_config[plugin_id]:
                preset_config[plugin_id].pop(param)
                updated = True
        if updated:
            self.save_presets()
        return updated

    def update_param_in_presets(self, plugin_id: str, param: str, value: Any) -> bool:
        """
        Update plugin param in all presets

        :param plugin_id: plugin id
        :param param: param key
        :param value: param value
        :return: True if updated
        """
        updated = False
        if self.presets is None:
            self.load_presets()

        if self.presets is None:
            return False

        for _preset_id, preset in self.presets.items():
            preset_config = preset["config"]
            if plugin_id in preset_config and param in preset_config[plugin_id]:
                preset_config[plugin_id][param] = value
                updated = True
        if updated:
            self.save_presets()
        return updated

    def get_presets(self) -> Dict[str, Any]:
        """
        Return all presets

        :return: dict with presets
        """
        return self.presets

    def reset_options(self, plugin_id: str, keys: List[str]):
        """
        Reset plugin options

        :param plugin_id: plugin id
        :param keys: list of keys
        """
        updated = False
        user_config = self.window.core.config.get('plugins')
        if plugin_id in user_config:
            for key in keys:
                if key in user_config[plugin_id]:
                    del user_config[plugin_id][key]
                self.remove_preset_values(plugin_id, key)
                updated = True

        if updated:
            print("[FIX] Updated options for plugin: {}".format(plugin_id))
            self.window.core.config.save()

    def reload_all(self):
        """Reload all plugins"""
        if self.presets is None or len(self.presets) == 0:
            self.reset_all()

    def reset_all(self):
        """Reset all options to initial values if presets"""
        for plugin_id in self.plugins:
            self.restore_options(plugin_id, all=True)
        self.apply_all_options()

    def clean_presets(self):
        """Remove invalid options from presets"""
        if self.presets is None:
            self.load_presets()

        removed = False
        if self.presets is not None:
            for _preset_id, preset in self.presets.items():
                preset_config = preset["config"]
                for config_preset, cfg_values in preset_config.items():
                    if config_preset in self.plugins:
                        for key in list(cfg_values):
                            if key not in self.plugins[config_preset].options:
                                removed = True
                                cfg_values.pop(key)
        if removed:
            self.save_presets()
            print("[FIX] Removed invalid keys from plugin presets.")

    def remove_preset_values(self, plugin_id: str, key: str):
        """
        Update preset value

        :param plugin_id: plugin id
        :param key: key
        """
        updated = False
        if self.presets is None:
            self.load_presets()

        if self.presets is None:
            return

        for _preset_id, preset in self.presets.items():
            preset_config = preset["config"]
            if plugin_id in preset_config and key in preset_config[plugin_id]:
                preset_config[plugin_id].pop(key)
                updated = True
        if updated:
            self.save_presets()

    def update_preset_values(self, plugin_id: str, key: str, value: Any):
        """
        Update preset value

        :param plugin_id: plugin id
        :param key: key
        :param value: value
        """
        updated = False
        if self.presets is None:
            self.load_presets()

        if self.presets is None:
            return

        for _preset_id, preset in self.presets.items():
            preset_config = preset["config"]
            if plugin_id in preset_config and key in preset_config[plugin_id]:
                preset_config[plugin_id][key] = value
                updated = True
        if updated:
            self.save_presets()

    def save_presets(self):
        """Save presets"""
        self.provider.save(self.presets)

    def dump_locale_by_id(self, plugin_id: str, path: str):
        """
        Dump locale by id

        :param plugin_id: plugin id
        :param path: path to locale file
        """
        plugin = self.plugins.get(plugin_id)
        if plugin:
            self.dump_locale(plugin, path)

    def dump_locales(self):
        """Dump all locales"""
        langs = ['en', 'pl']
        base_path = os.path.join(self.window.core.config.get_app_path(), 'data', 'locale')
        for plugin_id, plugin in self.plugins.items():
            domain = f'plugin.{plugin_id}'
            for lang in langs:
                path = os.path.join(base_path, f'{domain}.{lang}.ini')
                self.dump_locale(plugin, path)