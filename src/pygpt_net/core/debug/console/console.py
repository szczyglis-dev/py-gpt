#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

from pygpt_net.utils import mem_clean


class Console:
    def __init__(self, window=None):
        """
        Console core

        :param window: Window instance
        """
        self.window = window

    def on_send(self):
        """Called on send message from console"""
        msg = self.window.console.text().strip()
        if msg:
            self.clear()
            self.log(msg)
            QApplication.processEvents()
            self.handle(msg)

    def clear(self):
        """Clear console input"""
        self.window.console.clear()

    def log(self, msg: str):
        """
        Log message to console

        :param msg: Message to log
        """
        self.window.core.debug.log("[Console] " + str(msg))

    def handle(self, msg: str):
        """
        Handle message from console

        :param msg: Message from console
        """
        if msg == 'clr':
            self.window.logger.clear()
        elif msg == "mem":
            res = "\n" + self.window.core.debug.mem("Console")
            self.log(res)
        elif msg == "free":
            mem_clean()
            self.log("Memory cleaned")
        elif msg in ["quit", "exit", "/q"]:
            self.window.close()
        elif msg == "css":
            self.window.controller.theme.reload(force=True)
            self.log("Theme reloaded")
        elif msg == "lang":
            self.window.controller.lang.reload()
            self.log("Language reloaded")
        elif msg.lower() == "mpkfa":
            self.log("GOD MODE ACTIVATED ;)")
        elif msg == "oclr":
            if self.window.core.api.openai.client:
                self.window.core.api.openai.client.close()
                self.log("OpenAI client closed")
            else:
                self.log("OpenAI client not initialized")
        elif msg.lower() in ["help", "/help", "/h"]:
            self.log(self.get_help())
        elif msg.startswith("dump(") and msg.endswith(")"):
            expr = msg[5:-1].strip()
            self.log(f"{expr}:")
            self.log(self.dump(expr))
        elif msg.startswith("js(") and msg.endswith(")"):
            expr = msg[3:-1].strip()
            if self.window.controller.chat.render.get_engine() == "web":
                self.window.controller.chat.render.web_renderer.eval_js(expr)  # async result
            else:
                self.log("JS eval is only available in web rendering engine")
        else:
            self.log(f"Unknown command: {msg}. Type 'help' for available commands.")

    def dump(self, expr: str) -> str:
        """
        Dump object in console

        :param expr: Path to object or eval() expression
        :return: Dumped object or error message
        """
        try:
            return eval(expr)
        except Exception as e:
            return f"Error while dumping: {str(e)}"

    def get_help(self):
        """
        Get help message for console commands

        :return: Help message
        """
        return (
            "\n\n================\nAvailable commands:\n================\n"
            "  clr - clear output\n"
            "  mem - show memory usage\n"
            "  free - clean memory\n"
            "  css - reload theme CSS\n"
            "  lang - reload language\n"
            "  oclr - close OpenAI client\n"
            "  dump(object|expr) - dump object or eval() expression\n"
            "  js(expr) - evaluate JavaScript expression (current PID)\n"
            "  help - show this help message\n"
            "  quit|exit - close application\n"
            "  JS debug (window.*): STREAM_DEBUG|MD_LANG_DEBUG|CM_DEBUG\n"
        )
