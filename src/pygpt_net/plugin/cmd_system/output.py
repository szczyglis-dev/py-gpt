#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.20 03:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem

class Output:
    def __init__(self, plugin=None):
        self.plugin = plugin

    def handle(self, ctx: CtxItem, content) -> str:
        """
        Handle output

        :param ctx: CtxItem
        :param content: dict
        :return: HTML output
        """
        html = ""
        lang = "python"
        if isinstance(content, dict) and "code" in content:
            if "input" in content["code"]:
                if "lang" in content["code"]["input"] and "content" in content["code"]["input"]:
                    lang = content["code"]["input"]["lang"]
                    raw = "```{}\n{}\n```".format(lang, content["code"]["input"]["content"])
                    code = self.plugin.window.controller.chat.render.instance().parser.parse_code(raw)
                    html += "<div class=\"tool-output-header\">Input</div><div class=\"code-wrapper\">{}</div>".format(code)
            if "output" in content["code"] and "content" in content["code"]["output"]:
                if "lang" in content["code"]["output"]:
                    lang = content["code"]["output"]["lang"]
                    raw = "```{}\n{}\n```".format(lang, content["code"]["output"]["content"])
                    code = self.plugin.window.controller.chat.render.instance().parser.parse_code(raw)
                    html += "<div class=\"tool-output-header\">Output</div><div class=\"code-wrapper\">{}</div>".format(
                        code)
        return html