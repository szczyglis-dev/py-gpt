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

import datetime
import os
import requests
from openai import OpenAI


class Image:
    DIRNAME = "img"

    def __init__(self, config, window):
        """
        DALL-E Wrapper

        :param config: Config object
        :param window: Main window object
        """
        self.config = config
        self.window = window
        if not self.config.initialized:
            self.config.init()

    def init(self):
        """Initialize OpenAI API key"""
        pass

    def get_prompt(self, allow_custom=True):
        """
        Returns image generate prompt command

        :param allow_custom: Allow custom prompt
        :return: System command for generate image prompt
        """
        cmd = '''
        1. Apply these rules if the request is related to image generation or image description; otherwise, return the user's prompt as is.
        2. Translate any non-English image prompts accurately into English.
        3. Start from "A photograph of..." or "An image of...", etc. DO NOT use asking, like "Please generate...", "I want to see...", etc.
        4. Use as many details as possible to describe the image.
        5. If the user only wants to talk, then return the user's prompt as is (AND ONLY their prompt, without adding any text to it).
        '''
        # get custom prompt from config if exists
        if allow_custom:
            if 'img_prompt' in self.config.data:
                if self.config.data['img_prompt'] is not None and self.config.data['img_prompt'] != '':
                    cmd = self.config.data['img_prompt']
                    print("user custom prompt")
        return cmd

    def generate(self, prompt, model="dall-e-3", num=None):
        """
        Calls DALL-E API

        :param prompt: Prompt
        :param model: Model name
        :param num: Number of variants
        :return: Images paths list
        """
        if not self.window.config.data['img_raw']:
            system_cmd = self.get_prompt()
            max_tokens = 200
            temperature = 1.0
            try:
                # call GPT for generate best image generate prompt
                response = self.window.gpt.quick_call(prompt, system_cmd, False, max_tokens,
                                                      self.window.config.data['img_prompt_model'], temperature)
                if response is not None and response != "":
                    prompt = response
            except Exception as e:
                print("Image prompt generate by model error: " + str(e))

        print("Generating image from: '{}'".format(prompt))

        client = OpenAI(
            api_key=self.config.data["api_key"],
            organization=self.config.data["organization_key"],
        )
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=num,
            size=self.config.data["img_resolution"],
        )

        # generate and download images
        paths = []
        for i in range(num):
            if i >= len(response.data):
                break
            url = response.data[i].url
            res = requests.get(url)
            name = self.make_safe_filename(prompt) + "-" + datetime.date.today().strftime(
                "%Y-%m-%d") + "_" + datetime.datetime.now().strftime("%H-%M-%S") + "-" + str(i + 1) + ".png"
            path = os.path.join(self.config.path, self.DIRNAME, name)
            print("Downloading... [" + str(i + 1) + " of " + str(num) + "] to: " + path)
            open(path, "wb").write(res.content)
            paths.append(path)

        return paths, prompt

    def make_safe_filename(self, name):
        """
        Makes safe filename

        :param name: Filename to make safe
        :return: Safe filename
        """

        def safe_char(c):
            if c.isalnum():
                return c
            else:
                return "_"

        return "".join(safe_char(c) for c in name).rstrip("_")[:30]
