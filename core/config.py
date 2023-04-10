#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

import datetime
import os
import re
from pathlib import Path
import shutil
import json


class Config:
    CONFIG_DIR = 'pygpt-net'
    TYPE_STR = 0
    TYPE_INT = 1
    TYPE_FLOAT = 2
    TYPE_BOOL = 3

    def __init__(self):
        """Config handler"""
        self.path = str(Path(os.path.join(Path.home(), '.config', self.CONFIG_DIR)))
        self.initialized = False
        self.models = {}
        self.data = {}
        self.presets = {}
        self.version = self.get_version()

    def get_available_langs(self):
        """
        Get available languages

        :return: list of available languages
        """
        langs = []
        path = os.path.join('.', 'data', 'locale')
        for file in os.listdir(path):
            if file.endswith(".ini"):
                langs.append(file.replace('locale.', '').replace('.ini', ''))

        # put english first
        if 'en' in langs:
            langs.remove('en')
            langs.insert(0, 'en')
        return langs

    def init(self, all=True):
        """
        Init config

        :param all: load all configs
        """
        if not self.initialized:
            self.install()
            self.load(all)
            self.initialized = True

    def get_version(self):
        """
        Get version

        :return: version
        """
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '__init__.py'))
        result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format("__version__"),
                           open(path).read())
        return result.group(1)

    def load(self, all=True):
        """
        Load config

        :param all: load all configs
        """
        self.load_config()

        if all:
            self.load_models()
            self.load_presets()

    def save_preset(self, preset):
        """
        Save preset

        :param preset: preset name
        """
        if preset not in self.presets:
            return

        filepath = os.path.join(self.path, 'presets', preset + '.json')
        try:
            f = open(filepath, "w", encoding="utf-8")
            json.dump(self.presets[preset], f, indent=4)
            f.close()
        except Exception as e:
            print(e)

    def load_models(self):
        """Load models configs"""
        path = os.path.join(self.path, 'models.json')
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            f = open(path, "r", encoding="utf-8")
            self.models = json.load(f)
            f.close()
        except Exception as e:
            print(e)

    def load_config(self):
        """Load app config"""
        path = os.path.join(self.path, 'config.json')
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            f = open(path, "r", encoding="utf-8")
            self.data = json.load(f)
            f.close()
        except Exception as e:
            print(e)

    def sort_presets_by_name(self):
        """Sort prompts by name"""
        self.presets = dict(sorted(self.presets.items(), key=lambda item: item[1]['name']))

    def load_presets(self):
        """Load presets templates"""
        path = os.path.join(self.path, 'presets')
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            for filename in os.listdir(path):
                if filename.endswith(".json"):
                    f = open(os.path.join(path, filename), "r", encoding="utf-8")
                    self.presets[filename[:-5]] = json.load(f)
                    f.close()
            self.sort_presets_by_name()
            self.append_current_presets()
        except Exception as e:
            print(e)

    def build_empty_preset(self):
        """
        Build empty preset

        :return: empty preset
        """
        return {
            'name': '',
            'ai_name': '',
            'user_name': '',
            'prompt': '',
            'chat': False,
            'completion': False,
            'img': False,
            'temperature': 1,
        }

    def append_current_presets(self):
        """Append current presets"""
        # create empty presets
        curr_chat = self.build_empty_preset()
        curr_completion = self.build_empty_preset()
        curr_img = self.build_empty_preset()

        # prepare ids
        id_chat = 'current.chat'
        id_completion = 'current.completion'
        id_img = 'current.img'

        # set default initial prompt for chat mode
        curr_chat['prompt'] = self.data['default_prompt']

        # get data from presets if exists
        if id_chat in self.presets:
            curr_chat = self.presets[id_chat].copy()
            del self.presets[id_chat]
        if id_completion in self.presets:
            curr_completion = self.presets[id_completion].copy()
            del self.presets[id_completion]
        if id_img in self.presets:
            curr_img = self.presets[id_img].copy()
            del self.presets[id_img]

        # allow usage in specific mode
        curr_chat['chat'] = True
        curr_completion['completion'] = True
        curr_img['img'] = True

        # always apply default name
        curr_chat['name'] = '*'
        curr_completion['name'] = '*'
        curr_img['name'] = '*'

        # append at first position
        self.presets = {id_chat: curr_chat, id_completion: curr_completion, id_img: curr_img, **self.presets}

    def get_mode_by_idx(self, idx):
        """
        Get mode by index

        :param idx: index
        :return: mode
        """
        modes = self.get_modes()
        return list(modes.keys())[idx]

    def get_model_by_idx(self, idx, mode):
        """
        Get model by index

        :param idx: index
        :param mode: mode
        :return: model
        """
        models = self.get_models(mode)
        return list(models.keys())[idx]

    def get_preset_by_idx(self, idx, mode):
        """
        Get prompt by index

        :param idx: index
        :param mode: mode
        :return: prompt
        """
        presets = self.get_presets(mode)
        return list(presets.keys())[idx]

    def get_modes(self):
        """
        Get modes

        :return: modes list
        """
        modes = {}
        modes['chat'] = {
            'name': 'Chat'
        }
        modes['completion'] = {
            'name': 'Completion'
        }
        modes['img'] = {
            'name': 'Image (DALL-E 2)'
        }
        return modes

    def get_presets(self, mode):
        """
        Get presets for mode

        :param mode: mode
        :return: presets dict
        """
        presets = {}
        for key in self.presets:
            if (mode == 'chat' and self.presets[key]['chat']) \
                    or (mode == 'completion' and self.presets[key]['completion']) \
                    or (mode == 'img' and self.presets[key]['img']):
                presets[key] = self.presets[key]
        return presets

    def get_models(self, mode):
        """
        Get models for mode

        :param mode: mode
        :return: models dict
        """
        models = {}
        for key in self.models:
            if mode in self.models[key]['mode']:
                models[key] = self.models[key]
        return models

    def get_preset_idx(self, mode, name):
        """
        Get preset index

        :param name: name
        :return: index
        """
        presets = self.get_presets(mode)
        i = 0
        for key in presets:
            if key == name:
                return i
            i += 1
        return 0

    def delete_preset(self, name, remove_file=True):
        """
        Delete preset

        :param name: name
        """
        if name in self.presets:
            self.presets.pop(name)

        if remove_file:
            path = os.path.join(self.path, 'presets', name + '.json')
            if os.path.exists(path):
                os.remove(path)
            self.load_presets()

    def get_default_mode(self):
        """
        Get default mode

        :return: default mode
        """
        return 'chat'

    def get_default_model(self, mode):
        """
        Get default model for mode

        :param mode: mode
        :return: default model
        """
        models = self.get_models(mode)
        if len(models) == 0:
            return None
        return list(models.keys())[0]

    def get_default_preset(self, mode):
        """
        Get default preset for mode

        :param mode: mode
        :return: default prompt
        """
        presets = self.get_presets(mode)
        if len(presets) == 0:
            return None
        return list(presets.keys())[0]

    def get_preset_duplicate_name(self, name):
        """
        Make duplicate name

        :param name: name
        :return: duplicate name
        """

        old_name = self.presets[name]['name']
        i = 1
        while True:
            new_name = name + '_' + str(i)
            if new_name not in self.presets:
                return new_name, old_name + ' (' + str(i) + ')'
            i += 1

    def duplicate_preset(self, name):
        """
        Make duplicate preset

        :param name: name
        :return: duplicate preset
        """
        id, title = self.get_preset_duplicate_name(name)
        self.presets[id] = self.presets[name].copy()
        self.presets[id]['name'] = title
        self.sort_presets_by_name()
        return id

    def save(self):
        """Save config"""
        self.data['__meta__'] = self.append_meta()
        dump = json.dumps(self.data, indent=4)
        path = os.path.join(self.path, 'config.json')
        with open(path, 'w', encoding="utf-8") as f:
            f.write(dump)
            f.close()

    def save_config(self):
        """Save config"""
        self.data['__meta__'] = self.append_meta()
        dump = json.dumps(self.data, indent=4)
        path = os.path.join(self.path, 'config.json')
        with open(path, 'w', encoding="utf-8") as f:
            f.write(dump)
            f.close()

    def save_presets(self):
        """Save presets"""
        for key in self.presets:
            self.presets[key]['__meta__'] = self.append_meta()
            path = os.path.join(self.path, 'presets', key + '.json')
            dump = json.dumps(self.presets[key], indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
                f.close()

    def get_model_tokens(self, model):
        """
        Get model tokens

        :param model: model
        :return: tokens
        """
        if model in self.models:
            return self.models[model]['tokens']
        return 1

    def append_meta(self):
        """
        Append meta data

        :return: meta data
        """
        return {
            'version': self.version,
            'app.version': self.version,
            'updated_at': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        }

    def install(self):
        """Install config files"""
        try:
            # create user config directory
            path = Path(self.path)
            path.mkdir(parents=True, exist_ok=True)

            # install config file
            dst = os.path.join(self.path, 'config.json')
            if not os.path.exists(dst):
                src = os.path.join('.', 'data', 'config', 'config.json')
                shutil.copyfile(src, dst)

            # install models file
            dst = os.path.join(self.path, 'models.json')
            if not os.path.exists(dst):
                src = os.path.join('.', 'data', 'config', 'models.json')
                shutil.copyfile(src, dst)

            # install prompts templates
            presets_dir = os.path.join(self.path, 'presets')
            if not os.path.exists(presets_dir):
                src = os.path.join('.', 'data', 'config', 'presets')
                shutil.copytree(src, presets_dir)

            # create history directory
            history_dir = os.path.join(self.path, 'history')
            if not os.path.exists(history_dir):
                os.mkdir(history_dir)

            # create context directory
            context_dir = os.path.join(self.path, 'context')
            if not os.path.exists(context_dir):
                os.mkdir(context_dir)

            # create images directory
            img_dir = os.path.join(self.path, 'img')
            if not os.path.exists(img_dir):
                os.mkdir(img_dir)

        except Exception as e:
            print(e)
