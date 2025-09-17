#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.17 00:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        # Endpoints / HTTP
        plugin.add_option(
            "api_base",
            type="text",
            value="https://api.wolframalpha.com",
            label="API base",
            description="Base API URL (default https://api.wolframalpha.com).",
        )
        plugin.add_option(
            "http_timeout",
            type="int",
            value=30,
            label="HTTP timeout (s)",
            description="Requests timeout in seconds.",
        )

        # Auth / Keys
        plugin.add_option(
            "wa_appid",
            type="text",
            value="",
            label="Wolfram Alpha AppID",
            description="Your Wolfram Alpha AppID (https://developer.wolframalpha.com).",
            secret=True,
        )

        # Defaults
        plugin.add_option(
            "units",
            type="text",
            value="metric",
            label="Units",
            description="metric | nonmetric (applied where supported).",
        )
        plugin.add_option(
            "simple_background",
            type="text",
            value="white",
            label="Simple API background",
            description="white | transparent",
        )
        plugin.add_option(
            "simple_layout",
            type="text",
            value="labelbar",
            label="Simple API layout",
            description="labelbar | inputonly | etc.",
        )
        plugin.add_option(
            "simple_width",
            type="int",
            value=600,
            label="Simple API width",
            description="Image width in pixels (optional).",
        )

        # ---------------- Commands ----------------

        # Generic endpoints
        plugin.add_cmd(
            "wa_short",
            instruction="WolframAlpha: Short answer (concise text).",
            params=[{"name": "query", "type": "str", "required": True, "description": "Natural language or math"}],
            enabled=True,
            description="Wolfram: short answer",
            tab="query",
        )
        plugin.add_cmd(
            "wa_spoken",
            instruction="WolframAlpha: Spoken result (single sentence).",
            params=[{"name": "query", "type": "str", "required": True, "description": "Natural language or math"}],
            enabled=True,
            description="Wolfram: spoken",
            tab="query",
        )
        plugin.add_cmd(
            "wa_simple",
            instruction="WolframAlpha: Simple image result (PNG/GIF).",
            params=[
                {"name": "query", "type": "str", "required": True, "description": "Query"},
                {"name": "out", "type": "str", "required": False, "description": "Output file path (relative or absolute)"},
                {"name": "background", "type": "str", "required": False, "description": "white|transparent"},
                {"name": "layout", "type": "str", "required": False, "description": "labelbar|inputonly|..."},
                {"name": "width", "type": "int", "required": False, "description": "Image width"},
            ],
            enabled=True,
            description="Wolfram: simple image",
            tab="query",
        )
        plugin.add_cmd(
            "wa_query",
            instruction="WolframAlpha: Full JSON query (pods).",
            params=[
                {"name": "query", "type": "str", "required": True, "description": "Query"},
                {"name": "format", "type": "str", "required": False, "description": "plaintext,image,..."},
                {"name": "assumptions", "type": "list", "required": False, "description": "List of 'assumption' strings"},
                {"name": "podstate", "type": "str", "required": False, "description": "Pod state id"},
                {"name": "scantimeout", "type": "int", "required": False, "description": "Scan timeout (s)"},
                {"name": "podtimeout", "type": "int", "required": False, "description": "Pod timeout (s)"},
                {"name": "maxwidth", "type": "int", "required": False, "description": "Max image width"},
                {"name": "download_images", "type": "bool", "required": False, "description": "Download pod images"},
                {"name": "max_images", "type": "int", "required": False, "description": "Max images to download"},
            ],
            enabled=True,
            description="Wolfram: full query (pods)",
            tab="query",
        )

        # Math convenience
        plugin.add_cmd(
            "wa_calculate",
            instruction="WolframAlpha: Evaluate/simplify numeric or symbolic expression.",
            params=[{"name": "expr", "type": "str", "required": True, "description": "Expression"}],
            enabled=True,
            description="Math: calculate",
            tab="math",
        )
        plugin.add_cmd(
            "wa_solve",
            instruction="WolframAlpha: Solve equation(s).",
            params=[
                {"name": "equation", "type": "str", "required": False, "description": "Single equation"},
                {"name": "equations", "type": "list", "required": False, "description": "List of equations"},
                {"name": "var", "type": "str", "required": False, "description": "Variable"},
                {"name": "variables", "type": "list", "required": False, "description": "Variables list"},
                {"name": "domain", "type": "str", "required": False, "description": "reals|integers|complexes"},
            ],
            enabled=True,
            description="Math: solve",
            tab="math",
        )
        plugin.add_cmd(
            "wa_derivative",
            instruction="WolframAlpha: Compute derivative.",
            params=[
                {"name": "expr", "type": "str", "required": True, "description": "Expression"},
                {"name": "var", "type": "str", "required": False, "description": "Variable (default x)"},
                {"name": "order", "type": "int", "required": False, "description": "Order (default 1)"},
                {"name": "at", "type": "str", "required": False, "description": "Evaluation point, e.g. 'x=0'"},
            ],
            enabled=True,
            description="Math: derivative",
            tab="math",
        )
        plugin.add_cmd(
            "wa_integral",
            instruction="WolframAlpha: Compute integral (indef/def).",
            params=[
                {"name": "expr", "type": "str", "required": True, "description": "Expression"},
                {"name": "var", "type": "str", "required": False, "description": "Variable (default x)"},
                {"name": "a", "type": "str", "required": False, "description": "Lower limit"},
                {"name": "b", "type": "str", "required": False, "description": "Upper limit"},
            ],
            enabled=True,
            description="Math: integral",
            tab="math",
        )
        plugin.add_cmd(
            "wa_units_convert",
            instruction="WolframAlpha: Convert units.",
            params=[
                {"name": "value", "type": "str", "required": True, "description": "Numeric value"},
                {"name": "from", "type": "str", "required": True, "description": "From unit"},
                {"name": "to", "type": "str", "required": True, "description": "To unit"},
            ],
            enabled=True,
            description="Units: convert",
            tab="units",
        )
        plugin.add_cmd(
            "wa_matrix",
            instruction="WolframAlpha: Matrix operations (determinant, inverse, eigenvalues, rank).",
            params=[
                {"name": "op", "type": "str", "required": False, "description": "determinant|inverse|eigenvalues|rank"},
                {"name": "matrix", "type": "list", "required": True, "description": "List of lists, e.g. [[1,2],[3,4]]"},
            ],
            enabled=True,
            description="Math: matrix ops",
            tab="math",
        )
        plugin.add_cmd(
            "wa_plot",
            instruction="WolframAlpha: Plot function (image file via Simple API).",
            params=[
                {"name": "func", "type": "str", "required": True, "description": "Function f(x)"},
                {"name": "var", "type": "str", "required": False, "description": "Variable (default x)"},
                {"name": "a", "type": "str", "required": False, "description": "From"},
                {"name": "b", "type": "str", "required": False, "description": "To"},
                {"name": "out", "type": "str", "required": False, "description": "Output file path"},
            ],
            enabled=True,
            description="Plots: function plot",
            tab="plots",
        )