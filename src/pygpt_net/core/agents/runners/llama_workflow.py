"""Execute native and user-defined LlamaIndex workflows through one timeline."""
import asyncio

from llama_index.core.workflow import Context
from llama_index.core.agent.workflow.base_agent import BaseWorkflowAgent
from workflows.errors import WorkflowCancelledByUser

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.agents_v2.utils import effective_iteration_limit
from .base import BaseRunner
from .llama_session import LlamaSession, result_text


class LlamaWorkflow(BaseRunner):
    async def run(self, agent, ctx, prompt, signals, verbose=False, history=None,
                  llm=None, schema=None, workflow_bridge=None, session=None):
        session = session or self._session(ctx, signals)
        self.set_busy(signals)
        try:
            if self.is_stopped():
                raise WorkflowCancelledByUser()
            session.emitter.begin()
            memory = self.window.core.idx.chat.get_memory_buffer(history, llm)
            await self.run_agent(agent, Context(agent), prompt, memory, verbose,
                                 ctx, signals, workflow_bridge=workflow_bridge, session=session)
            if workflow_bridge is not None:
                workflow_bridge.finish(session.final_answer)
            return True
        except (WorkflowCancelledByUser, asyncio.CancelledError):
            session.abort()
            if workflow_bridge is not None:
                workflow_bridge.stop()
            return True
        except Exception as exc:
            session.abort()
            self.set_error(exc)
            ctx.extra["error"] = str(exc)
            if workflow_bridge is not None:
                workflow_bridge.fail(exc)
            return False
        finally:
            if not session.final_answer:
                self.set_idle(signals)

    def _session(self, ctx, signals, visible=True):
        context = BridgeContext(ctx=ctx, mode=ctx.mode,
                                stream=bool(self.window.core.config.get("stream", False)))
        return LlamaSession(self.window, context, {}, signals, visible=visible)

    async def run_once(self, agent, ctx, prompt, signals, verbose=False, history=None,
                       llm=None, is_expert_call=False, session=None):
        session = session or self._session(ctx, signals, visible=False)
        try:
            if self.is_stopped():
                return None
            memory = self.window.core.idx.chat.get_memory_buffer(history, llm)
            return await self.run_agent(agent, Context(agent), prompt, memory, verbose,
                                        ctx, signals, flush=False, session=session)
        except (WorkflowCancelledByUser, asyncio.CancelledError):
            session.abort()
            return None
        except Exception as exc:
            session.abort()
            self.set_error(exc)
            ctx.extra["error"] = str(exc)
            return None

    async def run_agent(self, agent, ctx, query, memory, verbose=False, item_ctx=None,
                        signals=None, use_partials=True, flush=True,
                        workflow_bridge=None, session=None):
        session = session or self._session(item_ctx, signals, visible=flush)
        # Built-in agents and custom Workflows have different public run APIs.
        # Pass iteration limits at run time: constructor kwargs are ignored by
        # recent LlamaIndex versions.
        if isinstance(agent, BaseWorkflowAgent):
            handler = agent.run(
                user_msg=query, ctx=ctx, memory=memory,
                max_iterations=effective_iteration_limit(
                    int(self.window.core.config.get("agent.llama.steps", 10))),
            )
        else:
            handler = agent.run(query, ctx=ctx, memory=memory, verbose=verbose,
                                on_stop=self.is_stopped)

        from .llama_events import consume_handler

        async def consume(event):
            if workflow_bridge is not None:
                workflow_bridge.llama_event(event)
            await session.event(event)

        result = await consume_handler(handler, consume, self.is_stopped)
        await session.finish(result)
        return item_ctx

    _workflow_result_to_text = staticmethod(result_text)

    @staticmethod
    def _tool_output_to_text(value):
        return str(getattr(value, "content", value) or "").strip()
