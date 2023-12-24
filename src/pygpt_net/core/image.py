#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 22:00:00                  #
# ================================================== #

import datetime
import os
import requests
from openai import OpenAI


class Image:
    DIRNAME = "img"

    def __init__(self, window=None):
        """
        DALL-E Wrapper

        :param window: Window instance
        """
        self.window = window

    def init(self):
        """Initialize OpenAI API key"""
        pass

    def get_prompt(self, allow_custom=True):
        """
        Return image generate prompt command

        :param allow_custom: allow custom prompt
        :return: system command for generate image prompt
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
            if self.window.app.config.has('img_prompt'):
                prompt = self.window.app.config.get('img_prompt')
                if prompt is not None and prompt != '':
                    cmd = prompt
        return cmd

    def get_client(self):
        """
        Return OpenAI client

        :return: OpenAI client
        """
        return OpenAI(
            api_key=self.window.app.config.get('api_key'),
            organization=self.window.app.config.get('organization_key'),
        )

    def generate(self, prompt, model="dall-e-3", num=1):
        """
        Call DALL-E API

        :param prompt: prompt
        :param model: model name
        :param num: number of variants
        :return: images paths list
        :rtype: list
        """
        if not self.window.app.config.get('img_raw'):
            system_cmd = self.get_prompt()
            max_tokens = 200
            temperature = 1.0
            try:
                # call GPT for generate best image generate prompt
                response = self.window.app.gpt.quick_call(prompt, system_cmd, False, max_tokens,
                                                          self.window.app.config.get('img_prompt_model'), temperature)
                if response is not None and response != "":
                    prompt = response
            except Exception as e:
                self.window.app.errors.log(e)
                print("Image prompt generate by model error: " + str(e))

        print("Generating image from: '{}'".format(prompt))
        client = self.get_client()
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=num,
            size=self.window.app.config.get('img_resolution'),
        )

        # generate and download images
        paths = []
        for i in range(num):
            if i >= len(response.data):
                break
            url = response.data[i].url
            res = requests.get(url)

            # generate filename
            name = self.make_safe_filename(prompt) + "-" + datetime.date.today().strftime(
                "%Y-%m-%d") + "_" + datetime.datetime.now().strftime("%H-%M-%S") + "-" + str(i + 1) + ".png"
            path = os.path.join(self.window.app.config.path, self.DIRNAME, name)

            print("Downloading... [" + str(i + 1) + " of " + str(num) + "] to: " + path)
            # save image
            if self.save_image(path, res.content):
                paths.append(path)

        return paths, prompt

    def save_image(self, path, image):
        """
        Save image to file

        :param path: path to save
        :param image: image data
        :return: True if success
        """
        try:
            with open(path, 'wb') as file:
                file.write(image)
            return True
        except Exception as e:
            self.window.app.errors.log(e)
            print("Image save error: " + str(e))
            return False

    def make_safe_filename(self, name):
        """
        Make safe filename

        :param name: filename to make safe
        :return: safe filename
        :rtype: str
        """

        def safe_char(c):
            if c.isalnum():
                return c
            else:
                return "_"

        return "".join(safe_char(c) for c in name).rstrip("_")[:30]
