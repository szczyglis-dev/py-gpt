#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from .runner import Runner


class AgentsV2:
    def __init__(self, window=None):
        self.window = window
        self.runner = Runner(window)
