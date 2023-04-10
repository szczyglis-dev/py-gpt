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
import requests
import openai


class Image:
    DIRNAME = "img"

    def __init__(self, config):
        """
        DALL-E Wrapper

        :param config: Config
        """
        self.config = config
        if not self.config.initialized:
            self.config.init()

    def init(self):
        """Initialize OpenAI API"""
        openai.api_key = self.config.data["api_key"]

    def generate(self, prompt, num=None):
        """
        Call DALL-E API

        :param prompt: Prompt
        :return: Image paths list
        """
        if num is None:
            num = int(input("How many variants generate? [1] ") or 1)
        print("Generating from: '{}'...".format(prompt))
        response = openai.Image.create(
            prompt=prompt,
            n=num,
            size=self.config.data["img_resolution"],
        )

        # generate and download images
        paths = []
        for i in range(num):
            url = response['data'][i]['url']
            res = requests.get(url)
            name = self.make_safe_filename(prompt) + "-" + datetime.date.today().strftime(
                "%Y-%m-%d") + "_" + datetime.datetime.now().strftime("%H-%M-%S") + "-" + str(i + 1) + ".png"
            path = os.path.join(self.config.path, self.DIRNAME, name)
            print("Downloading... [" + str(i + 1) + " of " + str(num) + "] to: " + path)
            open(path, "wb").write(res.content)
            paths.append(path)

        return paths

    def make_safe_filename(self, name):
        """
        Make safe filename

        :param name: Filename to make safe
        :return: Safe filename
        """

        def safe_char(c):
            if c.isalnum():
                return c
            else:
                return "_"

        return "".join(safe_char(c) for c in name).rstrip("_")[:30]
