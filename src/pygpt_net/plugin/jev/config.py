#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 19:27:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """Set default Jev plugin and command configuration."""
        plugin.add_option(
            "model",
            type="text",
            value="jev-latest",
            label="Model",
            description="Jev model ID used for System One requests. Default: jev-latest.",
            tooltip="Model used by Jev / System One. Default: jev-latest.",
        )

        plugin.add_cmd(
            "jev_evaluate",
            instruction=(
                "Use TypeSafe AI Jev / System One for bounded semantic decisions over structured state. "
                "Call it when ordinary code needs semantic judgment but the possible outcome is defined in "
                "advance: classification/routing/selection with type='choice', condition or verification "
                "probability with type='noul', or ordered rubric/severity/ranking signals with type='score'. "
                "It is useful for routing, selecting candidate values/spans, verification and reusable "
                "scoring; it is not a chat/text-generation model and should not do open-ended writing, exact "
                "lookup, or unconstrained reasoning. Evaluate independent questions over the same state in "
                "one request. choice.criteria is an option->description object (max 255); score.criteria is "
                "an ordered 2-10 item array; noul.criteria is optional true/false guidance. Returns raw typed "
                "Jev JSON with answers and distributions/confidence where applicable. "
                "Examples: (1) state={'message':'Refund never arrived.'}, "
                "questions={'intent':{'type':'choice','instructions':'Classify support intent.',"
                "'criteria':{'refund':'Refund issue','other':'Other'}}}. Possible response: "
                "{'answers':{'intent':{'type':'choice','choice':'refund',"
                "'confidence':0.98,'probabilities':{'refund':0.98,'other':0.02}}}}. "
                "(2) state={'text':'The package arrived broken.'}, "
                "questions={'damaged':{'type':'noul','instructions':'Is the item described as damaged?',"
                "'criteria':{'true':'Damaged','false':'Not damaged'}}}. Possible response: "
                "{'answers':{'damaged':{'type':'noul','noul':0.99}}}. Values are illustrative; actual "
                "probabilities and confidence vary by request."
            ),
            params=[
                {
                    "name": "state",
                    "type": "dict",
                    "required": True,
                    "description": (
                        "Structured JSON object that all questions evaluate. Put unstructured source text "
                        "inside a field such as 'text', 'message', or 'document'. Example: "
                        "{'message': 'Refund never arrived.', 'customer_tier': 'pro'}."
                    ),
                },
                {
                    "name": "questions",
                    "type": "dict",
                    "required": True,
                    "description": (
                        "Question map keyed by stable IDs. Each value must contain type ('choice', 'score', "
                        "or 'noul') and instructions. choice.criteria is an option->description object "
                        "(up to 255 options); score.criteria is an ordered array with 2-10 entries; "
                        "noul.criteria is optional and can describe true/false outcomes. Example: "
                        "{'intent': {'type': 'choice', 'instructions': 'Classify support intent.', "
                        "'criteria': {'refund': 'Refund issue', 'other': 'Other'}}}."
                    ),
                },
            ],
            enabled=True,
            description="Evaluate/classify structured data with Jev / System One",
        )
