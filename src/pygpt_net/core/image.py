#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
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
        """
        self.config = config
        self.window = window
        if not self.config.initialized:
            self.config.init()

    def init(self):
        """Initialize OpenAI API key"""
        pass

    def generate(self, prompt, model="dall-e-3", num=None):
        """
        Calls DALL-E API

        :param prompt: Prompt
        :param model: Model name
        :param num: Number of variants
        :return: Images paths list
        """
        if not self.window.config.data['img_raw']:
            img_prompt = '''
            # Rules
            1. Apply these rules if the request is related to image generation or image description; otherwise, relay the user's prompt as is.
            2. Translate any non-English image prompts accurately into English, ensuring the essence of the original request is maintained for DALL-E's comprehension.
            3. Transform the translated prompt into a precise and specific instruction that DALL-E can unambiguously understand, focusing solely on describing the desired image.
            4. Preface your instruction with "A photograph of..." or "An image of..." to indicate a visual output request, refraining from using phrases like "Please generate..." or simply "Generate...".
            5. Emphasize the critical keywords and pertinent details within the prompt to assist DALL-E in producing an optimal image response.
            6. For prompts centered on intricate concepts or specialized topics, supply supplementary context to better inform DALL-E's interpretation and creativity.
            7. Designate the desired level of abstraction, realistic depiction, or a particular art style as part of the query to guide the image generation process.
            8. Set explicit parameters such as artistic style, composition, and any additional defining traits for the cognitive synthesis, tailored to enhance the final visual product.
            9. Compile and incorporate an exhaustive inventory of elements and nuances to achieve the most detailed and sophisticated image outcome possible.
            10. Return the enhanced, detail-rich description tailored for DALL-E, omitting any extraneous commentary or instruction.
            11. Use as many details as possible to describe the image.
            12. Use all possible different DESCENTS with EQUAL probability.
            '''

            # call GPT for generate best prompt
            response = self.window.gpt.quick_call(prompt, img_prompt, False, 200,
                                                  self.window.config.data['img_prompt_model'], 2.0)  # max creativity
            if response is not None and response != "":
                prompt = response

        print("Generating from: '{}'...".format(prompt))

        client = OpenAI(
            # This is the default and can be omitted
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
