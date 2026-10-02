"""Prepare legacy agent calls without coupling preparation to runner selection."""

from dataclasses import dataclass
from typing import Any

from llama_index.core.base.llms.types import ChatMessage, MessageRole

from pygpt_net.core.agents_v2.prompts import agents_directory_exists, append_agents_directory_support
from pygpt_net.core.types import AGENT_MODE_WORKFLOW
from pygpt_net.provider.agents.base import BaseAgent
from pygpt_net.provider.llms.computer import ComputerRuntime

from .runners.llama_session import LlamaSession
from .tools import Tools


@dataclass
class PreparedAgentCall:
    agent_id: str
    provider: Any
    agent: Any
    context: Any
    prompt: str
    signals: Any
    verbose: bool
    session: Any
    history: Any
    llm: Any
    agent_kwargs: dict
    stream: bool
    is_expert_call: bool

    def execution_kwargs(self):
        return {
            "agent": self.agent,
            "ctx": self.context.ctx,
            "prompt": self.prompt,
            "signals": self.signals,
            "verbose": self.verbose,
        }


class AgentPreparation:
    """Compose provider inputs while retaining the distinct quick-call policy."""

    def __init__(self, window, append_system_prompt_to_msg, additional_context_prefix):
        self.window = window
        self.append_system_prompt_to_msg = append_system_prompt_to_msg
        self.additional_context_prefix = additional_context_prefix

    # ========================================
    # Request preparation
    # ========================================

    def prepare(self, context, extra, signals, agent_id, verbose, *, once=False):
        provider = self._get_provider(agent_id, context, once, validate=True)
        session = self._create_session(provider, context, extra, signals, once)
        self._mark_input(context.ctx, once)
        system_prompt = self._system_prompt(provider, context, once)
        is_expert_call = context.is_expert_call if once else False
        max_steps = self.window.core.config.get("agent.llama.steps", 10)
        stream = False if once else self.window.core.config.get("stream", False)
        is_cmd = self.window.core.command.is_cmd(inline=False)
        history = None if once else self.window.core.agents.memory.prepare(context)
        computer, llm = self._prepare_model(context, session)
        workdir = self.window.core.config.get_workdir_prefix(ctx=context.ctx)
        idx = self._select_index(context, extra, once)
        agent_tools = self._prepare_tool_factory(context, session, computer, idx)
        tool_kwargs = self._prepare_tools(context, extra, agent_tools, is_cmd, once)
        if once:
            history = extra["agent_history"] if "agent_history" in extra else self.window.core.agents.memory.prepare(context)
        prompt = context.prompt if once else self._append_retrieved_context(context, idx)
        self._append_system_message(agent_id, system_prompt, history)
        if once:
            tool_kwargs.update(
                plugin_tools=agent_tools.get_plugin_tools(context, extra, force=True) if is_cmd else {},
                plugin_specs=agent_tools.get_plugin_specs(context, extra, force=True) if is_cmd else [],
            )
        agent_kwargs = {
            "context": context,
            **tool_kwargs,
            "llm": llm,
            "model": context.model,
            "chat_history": history,
            "max_iterations": max_steps,
            "verbose": verbose,
            "system_prompt": system_prompt,
            "are_commands": is_cmd,
            "workdir": workdir,
            "preset": context.preset if context else None,
            "schema": self.window.core.agents.custom.get_schema(agent_id),
            "computer_runtime": computer,
            "agent_tools": agent_tools,
            "input_builder": session.build_worker_message if session is not None else None,
            "stream": bool(getattr(context, "stream", False)),
        }
        provider = self._get_provider(agent_id, context, once)
        agent = self._build_agent(provider, agent_kwargs)
        if verbose:
            print(f"Using Agent: {agent_id}, model: {context.model.id}")
        return PreparedAgentCall(agent_id, provider, agent, context, prompt, signals, verbose,
                                 session, history, llm, agent_kwargs, stream, is_expert_call)

    # ========================================
    # Provider and session
    # ========================================

    def _get_provider(self, agent_id, context, once, validate=False):
        registry = self.window.core.agents.provider
        args = (agent_id,) if once else (agent_id, context.mode)
        if validate and not registry.has(*args):
            raise Exception(f"Agent not found: {agent_id}")
        return registry.get(*args)

    def _create_session(self, provider, context, extra, signals, once):
        if once:
            return LlamaSession(self.window, context, extra, signals, visible=False)
        if provider.get_mode() == AGENT_MODE_WORKFLOW:
            return LlamaSession(self.window, context, extra, signals)
        return None

    def _mark_input(self, ctx, once):
        ctx.extra["agent_input"] = True
        if once:
            ctx.extra["agent_output"] = True
        ctx.agent_call = True

    def _build_agent(self, provider, kwargs):
        # Workflows receive the full composed request prompt; other providers
        # retain their extracted-extra convention.
        kwargs["system_prompt_extra"] = (
            kwargs["system_prompt"] if provider.get_mode() == AGENT_MODE_WORKFLOW
            else provider.get_system_prompt_extra(kwargs)
        )
        return provider.get_agent(self.window, kwargs)

    # ========================================
    # Prompts and history
    # ========================================

    def _system_prompt(self, provider, context, once):
        prompt = context.system_prompt or ""
        if (provider.get_mode() == AGENT_MODE_WORKFLOW
                and self.window.core.config.get("agent.llama.agents_dir.enabled", True)):
            prompt = append_agents_directory_support(
                prompt, directory_exists=agents_directory_exists(self.window, ctx=context.ctx))
        if not once:
            # REQUEST_NEXT skips normal prompt hooks. Persist their composed
            # result for loop/evaluation continuations.
            context.ctx.agents_v2_system_prompt = prompt
        return BaseAgent.append_security_rule(prompt)

    def _append_system_message(self, agent_id, prompt, history):
        if agent_id in self.append_system_prompt_to_msg and prompt:
            history.insert(0, ChatMessage(role=MessageRole.SYSTEM, content=prompt))

    def _append_retrieved_context(self, context, idx):
        prompt = context.prompt
        if not (idx and idx != "_" and self.window.core.config.get("agent.idx.auto_retrieve", True)):
            return prompt
        retrieved = self.window.core.idx.chat.query_retrieval(query=prompt, idx=idx, model=context.model)
        if retrieved:
            ctx = context.ctx
            if ctx.hidden_input is None:
                ctx.hidden_input = ""
            to_append = ""
            if not ctx.hidden_input:
                to_append = self.additional_context_prefix
            to_append += "\n" + retrieved
            ctx.hidden_input += to_append
            prompt += "\n\n" + to_append
        return prompt

    # ========================================
    # Model and tools
    # ========================================

    def _prepare_model(self, context, session):
        computer = ComputerRuntime(self.window, context, artifact_runtime=session)
        llm = self.window.core.idx.llm.get_agent(
            context.model, stream=True, allow_remote_tools=True, computer_runtime=computer)
        if session is not None:
            session.bind_llm(llm)
        return computer, llm

    def _select_index(self, context, extra, once):
        idx = extra.get("agent_idx", None)
        if not once and context.preset:
            idx = context.preset.idx
            extra["agent_idx"] = idx
        return idx

    def _prepare_tool_factory(self, context, session, computer, idx):
        tools = Tools(self.window, executor=session.execute_plugin) if session is not None else self.window.core.agents.tools
        tools.cmd_blacklist = list(self.window.core.agents.tools.cmd_blacklist)
        tools.set_context(context)
        tools.set_computer_runtime(computer)
        tools.set_idx(idx)
        return tools

    def _prepare_tools(self, context, extra, factory, is_cmd, once):
        if once:
            tools = extra["agent_tools"] if "agent_tools" in extra else factory.prepare(context, extra, force=True)
            if "agent_tools" not in extra and not is_cmd:
                tools = []
            return {"tools": tools}
        tools = factory.prepare(context, extra, force=True)
        functions = factory.get_function_tools(context.ctx, extra, force=True)
        plugins = factory.get_plugin_tools(context, extra, force=True)
        specs = factory.get_plugin_specs(context, extra, force=True)
        retriever = factory.get_retriever_tool(context, extra)
        return {
            "tools": tools if is_cmd else [],
            "function_tools": functions if is_cmd else [],
            "plugin_tools": plugins if is_cmd else [],
            "plugin_specs": specs if is_cmd else [],
            "retriever_tool": retriever,
        }
