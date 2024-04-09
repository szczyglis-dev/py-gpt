#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.09 23:00:00                  #
# ================================================== #

import json
import os
from pathlib import Path
from uuid import uuid4


class Profile:

    PROFILE_FILE = 'profile.json'

    def __init__(self, window=None):
        """
        Profile core

        :param window: Window instance
        """
        self.window = window
        self.base_workdir = None
        self.initialized = False
        self.version = '1.0.0'
        self.current = None
        self.profiles = {}

    def init(self, workdir: str):
        """
        Initialize profile

        :param workdir: base workdir (in user's home, real path)
        """
        self.set_base_workdir(workdir)
        self.install()
        if not self.initialized:
            self.load()
            self.update_path()

    def set_base_workdir(self, workdir):
        """
        Set base workdir

        :param workdir: base workdir
        """
        self.base_workdir = workdir

    def has_file(self) -> bool:
        """
        Check if profile config exists

        :return: True if exists
        """
        return os.path.exists(os.path.join(self.base_workdir, self.PROFILE_FILE))

    def from_defaults(self):
        """Create default profile config"""
        is_test = os.environ.get('ENV_TEST') == '1'
        if is_test:
            return # DISABLE in tests!!!

        uuid = str(uuid4())
        path = self.base_workdir.replace("%HOME%", str(Path.home()))

        # from current path cfg
        path_file = "path.cfg"
        p = os.path.join(self.base_workdir, path_file)
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                prev_path = f.read().strip()
                if prev_path != "":
                    prev_path = prev_path.replace("%HOME%", str(Path.home()))
                    if os.path.exists(prev_path):
                        path = prev_path # use previously used path

        # create default profile
        self.current = uuid
        self.profiles = {}
        self.profiles[uuid] = {
            'name': 'Default',
            'workdir': path.replace(str(Path.home()), "%HOME%")
        }
        self.save()

    def install(self):
        """Install profiles"""
        if not self.has_file():
            self.from_defaults()

    def load(self):
        """Load profiles"""
        f = os.path.join(self.base_workdir, self.PROFILE_FILE)
        if os.path.exists(f):
            with open(f, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    self.current = data['current']
                    self.profiles = data['profiles']
                    self.initialized = True
                except Exception as e:
                    print('CRITICAL: Error loading profile file:', e)

    def save(self):
        """Save profiles"""
        config = {
            '_version': self.version,
            'current': self.current,
            'profiles': self.profiles
        }
        json_data = json.dumps(config, indent=4)
        f = os.path.join(self.base_workdir, self.PROFILE_FILE)
        with open(f, 'w', encoding='utf-8') as f:
            f.write(json_data)

    def add(self, name: str, workdir: str) -> str:
        """
        Add new profile

        :param name: profile name
        :param workdir: profile workdir
        :return: new profile uuid
        """
        uuid = str(uuid4())
        self.profiles[uuid] = {
            'name': name,
            'workdir': workdir.replace(str(Path.home()), "%HOME%")
        }
        self.save()
        return uuid

    def remove(self, uuid: str) -> bool:
        """
        Remove profile

        :param uuid: profile uuid
        :return: True if removed
        """
        if uuid in self.profiles:
            del self.profiles[uuid]
            self.save()
            return True
        return False

    def set_current(self, uuid: str) -> bool:
        """
        Set current profile

        :param uuid: profile uuid
        :return: True if set
        """
        if uuid in self.profiles:
            self.current = uuid
            self.save()
            self.update_path()
            return True
        return False

    def update_profile(self, uuid: str, name: str, workdir: str) -> bool:
        """
        Update profile

        :param uuid: profile uuid
        :param name: profile name
        :param workdir: profile workdir
        :return: True if updated
        """
        if uuid in self.profiles:
            self.profiles[uuid] = {
                'name': name,
                'workdir': workdir.replace(str(Path.home()), "%HOME%")
            }
            self.save()
            return True
        return False

    def get_current(self) -> str:
        """
        Get current profile

        :return: current profile uuid
        """
        return self.current

    def get(self, uuid: str) -> dict or None:
        """
        Get profile by uuid

        :param uuid: profile uuid
        :return: profile dict
        """
        if uuid in self.profiles:
            return self.profiles[uuid]
        return None

    def get_all(self) -> dict:
        """
        Get all profiles

        :return: all profiles dict
        """
        if not self.profiles:
            return {}
        sorted_profiles = sorted(self.profiles.items(), key=lambda item: item[1]['name'])
        return dict(sorted_profiles)

    def get_current_workdir(self) -> str:
        """
        Get current workdir

        :return: current workdir (real path)
        """
        if self.current is not None and self.current in self.profiles:
            tmp_dir = self.profiles[self.current]['workdir'].replace("%HOME%", str(Path.home()))
            if os.path.exists(tmp_dir):
                return tmp_dir
        return self.base_workdir

    def append(self, uuid: str, profile: dict):
        """
        Append profile

        :param uuid: profile uuid
        :param profile: profile dict
        """
        self.profiles[uuid] = profile
        self.save()

    def get_current_name(self) -> str:
        """
        Get current profile name

        :return: current profile name
        """
        if self.current is not None and self.current in self.profiles:
            return self.profiles[self.current]['name']
        return 'no profile'

    def update_current_workdir(self, path: str):
        """
        Update current workdir

        :param path: new workdir
        """
        if self.current is not None and self.current in self.profiles:
            self.profiles[self.current]['workdir'] = path.replace(str(Path.home()), "%HOME%")
            self.save()

    def update_path(self):
        """Update path.cfg of currently active profile"""
        path = self.get_current_workdir()
        if not os.path.exists(path):
            return  # abort if path does not exist
        if path == self.base_workdir:
            path = "" # default path
        path = path.replace(str(Path.home()), "%HOME%")
        path_file = "path.cfg"
        p = os.path.join(self.base_workdir, path_file)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(path)
