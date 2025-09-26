# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.26 14:00:00                  #
# ================================================== #

# >>> Based on LlamaIndex CodeActAgent implementation, with custom plugin tool support <<<

import asyncio
import inspect
import json
import re
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Union

from pydantic import PrivateAttr
from llama_index.core.agent.workflow.base_agent import BaseWorkflowAgent
from llama_index.core.agent.workflow.workflow_events import (
    AgentInput,
    AgentOutput,
    AgentStream,
    ToolCallResult,
)
from llama_index.core.base.llms.types import ChatResponse
from llama_index.core.bridge.pydantic import BaseModel, Field
from llama_index.core.llms import ChatMessage
from llama_index.core.llms.llm import ToolSelection, LLM
from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.core.memory import BaseMemory
from llama_index.core.objects import ObjectRetriever
from llama_index.core.prompts import BasePromptTemplate, PromptTemplate
from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.workflow import Context
from workflows.errors import WorkflowCancelledByUser

from pygpt_net.provider.agents.llama_index.workflow.events import StepEvent

DEFAULT_CODE_ACT_PROMPT = """You are a helpful AI assistant that can write and execute Python code to solve problems.
In addition to executing code using the <execute> tags, you have access to a unified plugin tool via the function tool(cmd, **params). 
When you want to use one of the additional tools, please wrap your command in <tool> ... </tool> tags using JSON syntax.
For example:
<tool>
{ "cmd": "name_of_command", "params": {"arg1": "value1", "arg2": 10} }
</tool>

You will be given a task to perform. You should output:
- Python code wrapped in <execute>...</execute> tags that provides the solution to the task, or a step towards the solution.
- If you want to call a tool, include a tool call as described above.
- Text to be shown directly to the user, if you want to ask for more information or provide the final answer.

You are in a IPython environment, so in your code, you can reference any previously used variables or functions.
To restart the IPython kernel, type the code: `<execute>/restart</execute>`. This will clear all variables and functions.
If any missing python modules are required, install them using the command: `<execute>!pip install module_name</execute>`.
When generating any images or plots, use the `matplotlib` library and return only the path to the saved image file instead of showing it.
By default, store all files in the current working directory, which is `{workdir}`.

## Response Format:
Example of a proper code block:
<execute>
import math

def calculate_area(radius):
    return math.pi * radius**2

area = calculate_area(5)
print(f"The area of the circle is {area:.2f} square units")
</execute>

Example of a plugin tool call:
<tool>
{ "cmd": "fetch_weather", "params": {"location": "Warsaw"} }
</tool>

In addition to the Python Standard Library and any functions you have already written, you can use the following functions:

{tool_descriptions}

Variables defined at the top level of previous code snippets can be also be referenced in your code.

## Final Answer Guidelines:
- When providing a final answer, focus on directly answering the user's question
- Avoid referencing the code you generated unless specifically asked
- Present the results clearly and concisely as if you computed them directly
- If relevant, you can briefly mention general methods used, but don't include code snippets in the final answer
- Structure your response like you're directly answering the user's query, not explaining how you solved it

Remember: Always place your Python code between <execute>...</execute> tags when you want to run code.
Always place tool calls between <tool>...</tool> tags when you want to run a tool.
You can include explanations and other content outside these tags.
"""

EXECUTE_TOOL_NAME = "execute"
PLUGIN_TOOL_NAME = "tool"


class CodeActAgent(BaseWorkflowAgent):
    """
    A workflow agent that can execute python code and call additional plugin tools.

    In addition to code execution, you can call other tools via the unified tool(cmd, **params) interface.
    Available plugin tool commands are provided in the '_plugin_tools' argument (as a dict mapping command names to callables).
    """
    scratchpad_key: str = "scratchpad"

    code_execute_fn: Union[Callable, Awaitable] = Field(
        description=(
            "The function to execute code. Required in order to execute code generated by the agent.\n"
            "Protocol: async def code_execute_fn(code: str) -> Dict[str, Any]"
        ),
    )

    code_act_system_prompt: Union[str, BasePromptTemplate] = Field(
        default=DEFAULT_CODE_ACT_PROMPT,
        description="The system prompt for the code act agent.",
        validate_default=True,
    )

    _plugin_tools: Dict[str, Callable] = PrivateAttr(default_factory=dict)
    _plugin_specs: Optional[List] = PrivateAttr(default_factory=list)
    _plugin_tool_fn: Union[Callable, Awaitable] = PrivateAttr(default=None)
    _on_stop: Optional[Callable] = PrivateAttr(default=None)

    # Always emit this human-friendly agent name in workflow events for UI consumption.
    _display_agent_name: str = PrivateAttr(default="CodeAct")

    def __init__(
        self,
        code_execute_fn: Union[Callable, Awaitable],
        plugin_tool_fn: Union[Callable, Awaitable],
        name: str = "code_act_agent",
        description: str = "A workflow agent that can execute code and call plugin tools.",
        system_prompt: Optional[str] = None,
        tools: Optional[List[Union[BaseTool, Callable]]] = None,
        plugin_tools: Optional[Dict[str, Callable]] = None,
        plugin_specs: Optional[List] = None,
        tool_retriever: Optional[ObjectRetriever] = None,
        can_handoff_to: Optional[List[str]] = None,
        llm: Optional[LLM] = None,
        code_act_system_prompt: Union[str, BasePromptTemplate] = DEFAULT_CODE_ACT_PROMPT,
        on_stop: Optional[Callable] = None,
    ):
        tools = tools or []
        tools.append(FunctionTool.from_defaults(plugin_tool_fn, name=PLUGIN_TOOL_NAME))
        tools.append(FunctionTool.from_defaults(code_execute_fn, name=EXECUTE_TOOL_NAME))

        object.__setattr__(self, "_plugin_tools", plugin_tools or {})
        object.__setattr__(self, "_plugin_tool_fn", plugin_tool_fn)
        object.__setattr__(self, "_plugin_specs", plugin_specs or [])
        object.__setattr__(self, "_on_stop", on_stop)

        if self._plugin_tools and self._plugin_specs:
            available_commands = "\n".join(self._plugin_specs)

            async def plugin_tool_wrapper(cmd: str, **params) -> Any:
                """
                Executes a plugin tool.

                Available commands:

                {available_commands}
                """
                tool_fn = plugin_tool_fn
                if asyncio.iscoroutinefunction(tool_fn):
                    return await tool_fn(cmd, **params)
                else:
                    return tool_fn(cmd, **params)

            plugin_tool_wrapper.__doc__ = plugin_tool_wrapper.__doc__.format(
                available_commands=available_commands
            )
            tools.append(FunctionTool.from_defaults(plugin_tool_wrapper, name=PLUGIN_TOOL_NAME))

        if isinstance(code_act_system_prompt, str):
            if system_prompt:
                code_act_system_prompt += "\n" + system_prompt
            code_act_system_prompt = PromptTemplate(code_act_system_prompt)
        elif isinstance(code_act_system_prompt, BasePromptTemplate):
            code_act_system_str = code_act_system_prompt.get_template()
            if system_prompt:
                code_act_system_str += "\n" + system_prompt
            code_act_system_prompt = PromptTemplate(code_act_system_str)

        super().__init__(
            name=name,
            description=description,
            system_prompt=system_prompt,
            tools=tools,
            tool_retriever=tool_retriever,
            can_handoff_to=can_handoff_to,
            llm=llm,
            code_act_system_prompt=code_act_system_prompt,
            code_execute_fn=code_execute_fn,
        )

    def _stopped(self) -> bool:
        """
        Check if the workflow has been stopped.

        :return: True if the workflow is stopped, False otherwise.
        """
        if self._on_stop:
            try:
                return self._on_stop()
            except Exception:
                return False
        return False

    def _get_tool_fns(self, tools: Sequence[BaseTool]) -> List[Callable]:
        """
        Get the tool functions while validating that they are valid for CodeActAgent.

        :param tools: A sequence of BaseTool instances.
        :return: A list of callable functions from the tools.
        :raises ValueError: If a tool requires context or is not a FunctionTool.
        """
        callables = []
        for tool in tools:
            if tool.metadata.name in {"handoff", EXECUTE_TOOL_NAME}:
                continue
            if isinstance(tool, FunctionTool):
                if tool.requires_context:
                    raise ValueError(
                        f"Tool {tool.metadata.name} requires context. "
                        "CodeActAgent only supports tools that do not require context."
                    )
                callables.append(tool.real_fn)
            else:
                raise ValueError(
                    f"Tool {tool.metadata.name} is not a FunctionTool. "
                    "CodeActAgent only supports Functions and FunctionTools."
                )
        return callables

    def _extract_code_from_response(self, response_text: str) -> Optional[str]:
        """
        Extract code from the LLM response using XML-style <execute> tags.

        Expected format:
        <execute>
        print('Hello, World!')
        </execute>

        :param response_text: The text response from the LLM.
        :return: The extracted code as a string, or None if no code is found.
        """
        execute_pattern = r"<execute>(.*?)</execute>"
        execute_matches = re.findall(execute_pattern, response_text, re.DOTALL)
        if execute_matches:
            return "\n\n".join(x.strip() for x in execute_matches)
        return None

    def _extract_plugin_tool_calls(self, response_text: str) -> List[Dict]:
        """
        Extract plugin tool calls from the LLM response.

        Expected format (JSON inside XML-style <tool> tags):
        <tool>
        { "cmd": "tool_name", "params": {"arg": "value"} }
        </tool>

        :param response_text: The text response from the LLM.
        :return: A list of dictionaries representing the plugin tool calls.
        """
        pattern = r"<tool>(.*?)</tool>"
        matches = re.findall(pattern, response_text, re.DOTALL)
        plugin_calls = []
        for match in matches:
            try:
                call_data = json.loads(match.strip())
                if "cmd" in call_data:
                    plugin_calls.append(call_data)
            except Exception:
                continue
        return plugin_calls

    def _emit_step_event(
            self,
            ctx: Context,
            name: str,
            index: Optional[int] = None,
            total: Optional[int] = None,
            meta: Optional[dict] = None,
    ) -> None:
        """
        Emits a step event to the context stream.

        :param ctx: The context to write the event to.
        :param name: The name of the step (e.g., "make_plan", "execute_plan", "subtask").
        :param index: The index of the step (optional).
        :param total: The total number of steps (optional).
        :param meta: Additional metadata for the step (optional).
        """
        try:
            ctx.write_event_to_stream(
                StepEvent(name=name, index=index, total=total, meta=meta or {})
            )
        except Exception:
            # Fallback for environments lacking StepEvent wiring.
            try:
                ctx.write_event_to_stream(
                    AgentStream(
                        delta="",
                        response="",
                        current_agent_name=self._display_agent_name,  # always "CodeAct"
                        tool_calls=[],
                        raw={"StepEvent": {"name": name, "index": index, "total": total, "meta": meta or {}}}
                    )
                )
            except Exception:
                pass

    def _get_tool_descriptions(self, tools: Sequence[BaseTool]) -> str:
        """
        Generate tool descriptions for the system prompt using tool metadata.

        :param tools: A sequence of BaseTool instances.
        :return: A string containing the formatted tool descriptions.
        """
        tool_descriptions = []
        tool_fns = self._get_tool_fns(tools)
        for fn in tool_fns:
            signature = inspect.signature(fn)
            fn_name: str = fn.__name__
            docstring: Optional[str] = inspect.getdoc(fn)
            tool_description = f"def {fn_name}{signature!s}:"
            if docstring:
                tool_description += f'\n  """\n{docstring}\n  """\n'
            tool_description += "\n  ...\n"
            tool_descriptions.append(tool_description)
        return "\n\n".join(tool_descriptions)

    async def take_step(
        self,
        ctx: Context,
        llm_input: List[ChatMessage],
        tools: Sequence[BaseTool],
        memory: BaseMemory,
    ) -> AgentOutput:
        """
        Takes a step in the agent's workflow, executing code and calling tools as needed.

        :param ctx: The context for the agent's execution.
        :param llm_input: The input messages for the LLM.
        :param tools: The tools available for the agent to use.
        :param memory: The memory object to store and retrieve messages.
        :return: An AgentOutput object containing the response and any tool calls made.
        :raises ValueError: If code_execute_fn is not provided or if an unknown tool name is encountered.
        """
        if not self.code_execute_fn:
            raise ValueError("code_execute_fn must be provided for CodeActAgent")

        # self._emit_step_event(ctx, name="step", meta={"query": str(llm_input)})

        scratchpad: List[ChatMessage] = await ctx.store.get(self.scratchpad_key, default=[])
        current_llm_input = [*llm_input, *scratchpad]
        tool_descriptions = self._get_tool_descriptions(tools)
        system_prompt = self.code_act_system_prompt.format(tool_descriptions=tool_descriptions)

        has_system = False
        for i, msg in enumerate(current_llm_input):
            if msg.role.value == "system":
                current_llm_input[i] = ChatMessage(role="system", content=system_prompt)
                has_system = True
                break
        if not has_system:
            current_llm_input.insert(0, ChatMessage(role="system", content=system_prompt))

        ctx.write_event_to_stream(
            AgentInput(input=current_llm_input, current_agent_name=self._display_agent_name)  # always "CodeAct"
        )

        if any(tool.metadata.name == "handoff" for tool in tools):
            if not isinstance(self.llm, FunctionCallingLLM):
                raise ValueError("llm must be a function calling LLM to use handoff")
            tools = [tool for tool in tools if tool.metadata.name == "handoff"]
            response = await self.llm.astream_chat_with_tools(tools, chat_history=current_llm_input)
        else:
            response = await self.llm.astream_chat(current_llm_input)

        last_chat_response = ChatResponse(message=ChatMessage())
        full_response_text = ""

        async for last_chat_response in response:

            # stop callback
            if self._stopped():
                raise WorkflowCancelledByUser("Workflow was stopped by user.")

            delta = last_chat_response.delta or ""
            full_response_text += delta
            raw = (
                last_chat_response.raw.model_dump()
                if isinstance(last_chat_response.raw, BaseModel)
                else last_chat_response.raw
            )
            ctx.write_event_to_stream(
                AgentStream(
                    delta=delta,
                    response=full_response_text,
                    tool_calls=[],
                    raw=raw,
                    current_agent_name=self._display_agent_name,  # always "CodeAct"
                )
            )

        code = self._extract_code_from_response(full_response_text)
        plugin_calls = self._extract_plugin_tool_calls(full_response_text)

        tool_calls = []
        if code:
            tool_calls.append(
                ToolSelection(
                    tool_id=str(uuid.uuid4()),
                    tool_name=EXECUTE_TOOL_NAME,
                    tool_kwargs={"code": code},
                )
            )
        for call in plugin_calls:
            tool_calls.append(
                ToolSelection(
                    tool_id=str(uuid.uuid4()),
                    tool_name=PLUGIN_TOOL_NAME,
                    tool_kwargs=call,
                )
            )

        if isinstance(self.llm, FunctionCallingLLM):
            extra_tool_calls = self.llm.get_tool_calls_from_response(last_chat_response, error_on_no_tool_call=False)
            tool_calls.extend(extra_tool_calls)

        message = ChatMessage(role="assistant", content=full_response_text)
        scratchpad.append(message)
        await ctx.store.set(self.scratchpad_key, scratchpad)

        raw = (
            last_chat_response.raw.model_dump()
            if isinstance(last_chat_response.raw, BaseModel)
            else last_chat_response.raw
        )

        return AgentOutput(
            response=message,
            tool_calls=tool_calls,
            raw=raw,
            current_agent_name=self._display_agent_name,  # always "CodeAct"
        )

    async def handle_tool_call_results(
        self,
        ctx: Context,
        results: List[ToolCallResult],
        memory: BaseMemory
    ) -> None:
        """
        Handles the results of tool calls made by the agent.

        :param ctx: The context for the agent's execution.
        :param results: The results of the tool calls made.
        :param memory: The memory object to store and retrieve messages.
        :raises ValueError: If an unknown tool name is encountered.
        """
        scratchpad: List[ChatMessage] = await ctx.store.get(self.scratchpad_key, default=[])

        for tool_call_result in results:
            if tool_call_result.tool_name == EXECUTE_TOOL_NAME:
                code_result = (
                    f"Result of executing the code given:\n\n{tool_call_result.tool_output.content}"
                )
                scratchpad.append(ChatMessage(role="user", content=code_result))
            elif tool_call_result.tool_name == "handoff":
                scratchpad.append(
                    ChatMessage(
                        role="tool",
                        content=str(tool_call_result.tool_output.content),
                        additional_kwargs={"tool_call_id": tool_call_result.tool_id},
                    )
                )
            elif tool_call_result.tool_name == PLUGIN_TOOL_NAME:
                plugin_result = (
                    f"Result of executing plugin tool call:\n\n{tool_call_result.tool_output.content}"
                )
                scratchpad.append(ChatMessage(role="user", content=plugin_result))
            else:
                raise ValueError(f"Unknown tool name: {tool_call_result.tool_name}")

        await ctx.store.set(self.scratchpad_key, scratchpad)

    async def finalize(
        self,
        ctx: Context,
        output: AgentOutput,
        memory: BaseMemory
    ) -> AgentOutput:
        """
        Finalizes the agent's workflow, clearing the scratchpad and returning the output.

        :param ctx: The context for the agent's execution.
        :param output: The output from the agent's workflow.
        :param memory: The memory object to store and retrieve messages.
        :return: The final output of the agent's workflow.
        """
        scratchpad: List[ChatMessage] = await ctx.store.get(self.scratchpad_key, default=[])
        await memory.aput_messages(scratchpad)
        await ctx.store.set(self.scratchpad_key, [])
        return output