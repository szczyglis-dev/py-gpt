"""Prepare a node's model, input and SDK agent before execution."""

from .debug import ellipsize, items_preview
from .factory import AgentFactory
from .flow_types import PreparedStep
from .utils import resolve_node_runtime


class FlowStepPreparation:
    def __init__(self, window, logger, memory_policy):
        self.window = window
        self.logger = logger
        self.memory_policy = memory_policy
        self.factory = AgentFactory(window, logger)

    # ========================================
    # Node preparation
    # ========================================

    def prepare(self, node, schema, graph, memory, initial_messages,
                first_dispatch_done, last_plain_output, options, dbg):
        runtime = self._resolve_runtime(node, options)
        self._log_runtime(runtime, dbg)
        items, baton, memory_id, memory_state, source = self.memory_policy.build_input(
            node_id=node.id, g=graph, mem=memory, initial_messages=initial_messages,
            first_dispatch_done=first_dispatch_done, last_plain_output=last_plain_output, dbg=dbg,
        )
        self._log_input(items, memory_id, memory_state, source, dbg)
        built = self._build_agent(node, schema, runtime, options)
        if dbg.log_runtime and built.multi_output:
            self.logger.debug(f"[routing] multi_output=True routes={built.allowed_routes} mode={options.router_stream_mode}")
        run_kwargs = {
            "input": items,
            "max_turns": int(options.agent_kwargs.get("max_iterations", options.max_iterations)),
        }
        return PreparedStep(built, run_kwargs, baton, memory_state)

    # ========================================
    # Runtime and agent definition
    # ========================================

    def _resolve_runtime(self, node, options):
        return resolve_node_runtime(
            window=self.window, node=node, option_get=options.option_get,
            default_model=options.model, base_prompt=options.base_prompt,
            system_prompt_extra=options.system_prompt_extra,
            schema_allow_local=node.allow_local_tools, schema_allow_remote=node.allow_remote_tools,
            default_allow_local=options.allow_local_tools, default_allow_remote=options.allow_remote_tools,
        )

    def _build_agent(self, node, schema, runtime, options):
        allowed_names = {rid: schema.agents[rid].name or rid for rid in (node.outputs or []) if rid in schema.agents}
        return self.factory.build(
            node=node, node_runtime=runtime, preset=options.preset, function_tools=options.function_tools,
            force_router=False, friendly_map=allowed_names, handoffs_enabled=True,
            context=options.agent_kwargs.get("context"), system_prompt_extra=options.system_prompt_extra or "",
        )

    # ========================================
    # Diagnostics
    # ========================================

    def _log_runtime(self, runtime, dbg):
        if dbg.log_runtime:
            self.logger.debug(
                f"[runtime] model={getattr(runtime.model, 'name', str(runtime.model))} "
                f"allow_local={runtime.allow_local_tools} allow_remote={runtime.allow_remote_tools} "
                f"instructions='{ellipsize(runtime.instructions, dbg.preview_chars)}'"
                f" role='{runtime.role}'"
            )

    def _log_input(self, items, memory_id, memory_state, source, dbg):
        if dbg.log_inputs:
            self.logger.debug(f"[input] source={source} items={len(items)} "
                              f"preview={items_preview(items, dbg.preview_chars)}")
            if memory_id:
                mem_info = f"{memory_id} (len={len(memory_state.items) if memory_state else 0})"
                self.logger.debug(f"[memory] attached={bool(memory_id)} mem_id={mem_info}")
