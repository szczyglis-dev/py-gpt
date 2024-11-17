#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

from llama_index.core.tools import FunctionTool


class Evaluation:
    def __init__(self, window=None):
        self.window = window
        self.prompt = """
        Please review the result below to determine if the agent's response is satisfactory and if the assigned 
        task was completed correctly. Evaluate the quality and accuracy of the response, as well as the successful 
        completion of the task, using a percentage scale from 0% to 100%. Use the tool provided to send feedback to the agent, 
        including instructions addressed directly to him on how to improve the previous result, along with a 
        numerical rating. The instructions should be prepared in the language used by the user.
        
        ## Tool for sending feedback:
        
        - send_feedback
        
        ## When creating an instruction, please use the following format:
        
        ```
        Please extend your response by including the following:
        
        1. ...
        2. ...
        ```
        
        ## Content to evaluate:
        
        MAIN TASK:
        
        ```
        
        {task}
        
        ```
        
        LAST USER INPUT:
        
        ```
        
        {input}
        
        ```
        
        AGENT RESPONSE:
        
        ```
        
        {output}
        
        ```
        
        ## Additional rules:
        
        - ALWAYS provide the instruction for the agent in the language used by the user in main task description.
        - Do not repeat the suggested improvements if they have already been correctly included in the agent's response.
        """

    def get_last_user_input(self, history) -> str:
        """
        Get the last user input from the history

        :param history: ctx items
        :return: last user input
        """
        input = ""
        use_prev = self.window.core.config.get("agent.llama.append_eval", False)
        for ctx in history:
            if ctx.extra is not None and "agent_input" in ctx.extra:
                if not use_prev and "agent_evaluate" in ctx.extra:  # exclude evaluation inputs
                        continue
                if ctx.input:
                    input = ctx.input
        return input

    def get_main_task(self, history) -> str:
        """
        Get the main task from the history

        :param history: ctx items
        :return: main task
        """
        first = history[0]
        task = ""
        if first.extra is not None and "agent_input" in first.extra:
            task = first.input
        return task

    def get_final_response(self, history) -> str:
        """
        Get the final response from the agent

        :param history: ctx items
        :return: final response
        """
        output = ""
        for ctx in history:
            if ctx.extra is not None and "agent_finish" in ctx.extra:
                if ctx.output:
                    output = ctx.output
        return output

    def get_prompt(self, history) -> str:
        """
        Return the evaluation prompt

        :param history:
        :return: evaluation prompt
        """
        prompt = self.window.core.config.get("prompt.agent.llama.eval")
        main_task = self.get_main_task(history)
        last_input = self.get_last_user_input(history)
        final_response = self.get_final_response(history)
        return prompt.format(
            task=main_task,
            input=last_input,
            output=final_response
        )

    def get_tools(self) -> list:
        """
        Get the tools for evaluating the result

        :return: list of tools
        """
        def send_feedback(instructions: str, rating_percent: int) -> str:
            """Send feedback with evaluation result"""
            self.handle_evaluation(instructions, rating_percent)
            return "OK. Feedback has been sent."

        tool = FunctionTool.from_defaults(fn=send_feedback)
        tools = []
        tools.append(tool)
        return tools

    def handle_evaluation(self, instruction: str, score: int):
        """
        Update the evaluation values of the agent response

        :param instruction: instruction
        :param score: score
        """
        self.window.core.agents.runner.next_instruction = instruction
        self.window.core.agents.runner.prev_score = score
