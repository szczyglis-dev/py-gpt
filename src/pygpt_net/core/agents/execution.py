"""Select legacy execution modes and translate their workflow monitoring."""

import asyncio

from pygpt_net.core.agent_workflow import AgentWorkflowBridge
from pygpt_net.core.types import (
    AGENT_MODE_ASSISTANT, AGENT_MODE_PLAN, AGENT_MODE_STEP,
    AGENT_MODE_WORKFLOW, AGENT_MODE_OPENAI,
)


class AgentExecution:
    def __init__(self, runner):
        self.runner = runner
        self.workflow_bridge = None

    # ========================================
    # Execution modes
    # ========================================

    def run(self, prepared):
        mode = prepared.provider.get_mode()
        kwargs = prepared.execution_kwargs()
        schema = prepared.agent_kwargs["schema"]
        if schema:
            kwargs["schema"] = schema
        self._start_monitor(prepared, mode, kwargs)
        synchronous = {
            AGENT_MODE_PLAN: self.runner.llama_plan,
            AGENT_MODE_STEP: self.runner.llama_steps,
            AGENT_MODE_ASSISTANT: self.runner.llama_assistant,
        }
        if mode in synchronous:
            return synchronous[mode].run(**kwargs)
        if mode == AGENT_MODE_WORKFLOW:
            kwargs.update(session=prepared.session, history=prepared.history, llm=prepared.llm)
            return asyncio.run(self.runner.llama_workflow.run(**kwargs))
        if mode == AGENT_MODE_OPENAI:
            kwargs.update(run=prepared.provider.run, agent_kwargs=prepared.agent_kwargs, stream=prepared.stream)
            return asyncio.run(self.runner.openai_workflow.run(**kwargs))

    def run_once(self, prepared):
        kwargs = prepared.execution_kwargs()
        kwargs.update(history=prepared.history, llm=prepared.llm,
                      is_expert_call=prepared.is_expert_call)
        if prepared.provider.get_mode() == AGENT_MODE_WORKFLOW:
            kwargs["session"] = prepared.session
            return asyncio.run(self.runner.llama_workflow.run_once(**kwargs))

    def fail(self, error):
        if self.workflow_bridge is not None:
            self.workflow_bridge.fail(error)

    # ========================================
    # Workflow monitoring
    # ========================================

    def _start_monitor(self, prepared, mode, kwargs):
        if mode not in (AGENT_MODE_WORKFLOW, AGENT_MODE_OPENAI):
            return
        self.workflow_bridge = AgentWorkflowBridge(
            self.runner.window,
            source="llama_index" if mode == AGENT_MODE_WORKFLOW else "openai_agents",
            root_name=(getattr(prepared.agent, "name", None)
                       or getattr(prepared.provider, "name", None)
                       or str(prepared.agent_id)),
            model=prepared.context.model,
            preset=prepared.context.preset if prepared.context else None,
            system_prompt=prepared.agent_kwargs["system_prompt"],
            prompt=prepared.prompt,
        )
        self.workflow_bridge.start()
        kwargs["workflow_bridge"] = self.workflow_bridge
