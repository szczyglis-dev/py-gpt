#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.10 23:00:00                  #
# ================================================== #

from typing import Dict, Any

from llama_index.core.agent.workflow import CodeActAgent as Agent

from .base import BaseAgent

class CodeActAgent(BaseAgent):

    DEFAULT_CODE_ACT_PROMPT = """You are a helpful AI assistant that can write and execute Python code to solve problems.

        You will be given a task to perform. You should output:
        - Python code wrapped in <execute>...</execute> tags that provides the solution to the task, or a step towards the solution. Any output you want to extract from the code should be printed to the console.
        - Text to be shown directly to the user, if you want to ask for more information or provide the final answer.
        - You are in a IPython environment, so in your code, you can reference any previously used variables or functions.
        - To restart the IPython kernel, type the code: `<execute>/restart</execute>`. This will clear all variables and functions.
        - If the previous code execution can be used to respond to the user, then respond directly (typically you want to avoid mentioning anything related to the code execution in your response).

        ## Response Format:
        Example of proper code format:
        <execute>
        import math

        def calculate_area(radius):
            return math.pi * radius**2

        # Calculate the area for radius = 5
        area = calculate_area(5)
        print(f"The area of the circle is {area:.2f} square units")
        </execute>

        In addition to the Python Standard Library and any functions you have already written, you can use the following functions:
        {tool_descriptions}

        Variables defined at the top level of previous code snippets can be also be referenced in your code.

        ## Final Answer Guidelines:
        - When providing a final answer, focus on directly answering the user's question
        - Avoid referencing the code you generated unless specifically asked
        - Present the results clearly and concisely as if you computed them directly
        - If relevant, you can briefly mention general methods used, but don't include code snippets in the final answer
        - Structure your response like you're directly answering the user's query, not explaining how you solved it

        Reminder: Always place your Python code between <execute>...</execute> tags when you want to run code. You can include explanations and other content outside these tags.
        """

    def __init__(self, *args, **kwargs):
        super(CodeActAgent, self).__init__(*args, **kwargs)
        self.id = "code_act"
        self.mode = "workflow"

    def get_agent(self, window, kwargs: Dict[str, Any]):
        """
        Return Agent provider instance

        :param window: window instance
        :param kwargs: keyword arguments
        :return: Agent provider instance
        """
        tools = kwargs.get("tools", [])
        llm = kwargs.get("llm", None)
        system_prompt = kwargs.get("system_prompt", "")

        return Agent(
            code_execute_fn=window.core.agents.tools.code_execute_fn.execute,
            # tools=tools,  # TODO: implement tools for code_act agent
            llm=llm,
            code_act_system_prompt=self.DEFAULT_CODE_ACT_PROMPT,
            system_prompt=system_prompt,
        )
