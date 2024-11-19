#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 21:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem

class Output:
    def __init__(self, plugin=None):
        self.plugin = plugin

    def handle(self, ctx: CtxItem) -> str:
        """
        Handle output

        :param ctx: CtxItem
        :return: HTML output
        """
        html = ""
        lang = "bash"
        if "code" in ctx.extra:
            if "input" in ctx.extra["code"]:
                if "lang" in ctx.extra["code"]["input"] and "content" in ctx.extra["code"]["input"]:
                    lang = ctx.extra["code"]["input"]["lang"]
                    raw = "```{}\n{}\n```".format(lang, ctx.extra["code"]["input"]["content"])
                    code = self.plugin.window.controller.chat.render.get_renderer().parser.parse_code(raw)
                    html += "<div class=\"tool-output-header\">INPUT</div><div class=\"code-wrapper\">{}</div>".format(code)
            if "output" in ctx.extra["code"] and "content" in ctx.extra["code"]["output"]:
                if "lang" in ctx.extra["code"]["output"]:
                    lang = ctx.extra["code"]["output"]["lang"]
                    raw = "```{}\n{}\n```".format(lang, ctx.extra["code"]["output"]["content"])
                    code = self.plugin.window.controller.chat.render.get_renderer().parser.parse_code(raw)
                    html += "<div class=\"tool-output-header\">OUTPUT</div><div class=\"code-wrapper\">{}</div>".format(
                        code)
        return html