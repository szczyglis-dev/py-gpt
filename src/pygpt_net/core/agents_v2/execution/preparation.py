#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.26 21:15:00                  #
# ================================================== #

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass
class PreparedTurn:
    agent: Any
    llm: Any
    history: list
    memory: Any


class TurnPreparation:
    """Prepare durable history, model, tools and bounded working memory."""

    def __init__(self, runtime):
        self.runtime = runtime

    async def prepare(self, context, emitter) -> PreparedTurn:
        runtime = self.runtime
        emitter.begin()
        current_input = str(getattr(context.ctx, "final_input", None) or context.prompt or "")
        runtime.verbose.text("USER INPUT", current_input)
        history = runtime.memory_store.load_history(
            context.ctx,
            model=context.model,
            current_input=current_input,
        )
        runtime.verbose.log(runtime.main_event("HISTORY"), history)


        # Match Agents/Chat with Files RAG behavior: retrieve relevant context
        # before the first main-agent call and inject it into both the main agent
        # and subsequently created workers/specialists.
        rag_query = str(context.prompt or current_input)
        runtime.inputs.prefetch(rag_query)
        llm = runtime.inputs.llm(stream=True, actor_id="orchestrator")
        main_system_prompt = runtime.prompts.main()
        main_tools = runtime.tools.main()
        main_agent = runtime.inputs.agent(
            name=runtime.main_agent_name,
            description=runtime.main_agent_description,
            llm=llm,
            system_prompt=main_system_prompt,
            tools=main_tools,
        )

        main_memory = None
        if runtime.window.core.context_manager.enabled():
            # Bounded LlamaIndex Memory is required inside a single long agent
            # run. Without it, top-level CTX_END checkpoints arrive too late: a
            # tool-heavy workflow can exceed the provider context window before
            # the user-visible turn has finished.
            main_memory = runtime.window.core.context_manager.build_agent_memory(
                runtime,
                actor_id="orchestrator",
                system_prompt=main_system_prompt,
                tools=main_tools,
                persistent=True,
            )
            await main_memory.aput_messages(history)

        return PreparedTurn(main_agent, llm, history, main_memory)

    def start(self, context, prepared):
        runtime = self.runtime
        main_memory = prepared.memory
        history = prepared.history
        shared = ""
        if runtime.shared_context_text:
            shared = (
                "\n\n<turn_context>\nThis turn contains shared user attachments/context. "
                "Use shared_context for extracted text/manifest. Current image attachments are also supplied "
                "as native image blocks when the selected model supports image input.\n</turn_context>"
            )
        main_input = runtime.inputs.message(str(context.prompt or "") + shared)
        runtime.verbose.log(runtime.main_event("INPUT"), main_input)
        main_max_iterations = runtime.main_max_iterations
        # Managed modes spend one extra internal LLM pass on the final
        # user-facing answer after workflow_finish validates the workflow.
        # Do not consume the user's configured work-iteration budget for that
        # transport/finalization pass (0/unlimited already maps to sys.maxsize).
        if runtime.uses_workflow_finish and runtime.main_max_iterations_configured > 0:
            main_max_iterations += 1
        run_kwargs = {
            "user_msg": main_input,
            "max_iterations": main_max_iterations,
            "early_stopping_method": "generate",
        }
        if main_memory is not None:
            # Passing ``memory`` lets LlamaIndex manage the FIFO after every
            # internal model/tool pass. The initial durable history was seeded
            # through SafeAgentMemory above.
            run_kwargs["memory"] = main_memory
        else:
            run_kwargs["chat_history"] = history
        runtime.window.core.api.logger.log_input(
            type="llama_index.agent.run",
            provider=str(getattr(runtime.model, "provider", "") or ""),
            kwargs=run_kwargs,
            input=main_input,
            history=history,
            model=getattr(runtime.model, "id", None),
            path="main_agent.run",
            extra={"actor": "orchestrator", "agent_mode": runtime.agent_mode.value},
        )
        return prepared.agent.run(**run_kwargs)
