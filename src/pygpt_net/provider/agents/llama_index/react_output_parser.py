#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from llama_index.core.agent.react.output_parser import ReActOutputParser
from llama_index.core.agent.react.types import ResponseReasoningStep


class PyGPTReActOutputParser(ReActOutputParser):
    """ReAct parser with a compatibility fix for LlamaIndex 0.14.23.

    LlamaIndex 0.14.23 accepts an Action without ``Thought:``, but its final
    answer parser still requires ``Thought: ... Answer: ...``. Local models
    often return a perfectly valid ``Answer: ...`` after a tool observation,
    which otherwise makes the workflow retry until max_iterations.
    """

    def parse(self, output: str, is_streaming: bool = False):
        try:
            return super().parse(output, is_streaming=is_streaming)
        except ValueError:
            marker = "Answer:"
            if marker not in output:
                raise

            prefix, answer = output.split(marker, 1)
            answer = answer.strip()
            if not answer:
                raise

            thought = prefix.strip()
            if thought.startswith("Thought:"):
                thought = thought[len("Thought:"):].strip()
            if not thought:
                thought = "(Implicit) I can answer without any more tools!"

            return ResponseReasoningStep(
                thought=thought,
                response=answer,
                is_streaming=is_streaming,
            )
