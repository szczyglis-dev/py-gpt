"""A flow session coordinates node preparation, execution, memory and navigation."""

from time import perf_counter

from pygpt_net.provider.api.openai.agents.response import StreamHandler

from .debug import ellipsize
from .flow_types import DebugConfig, FlowResult
from .flow_memory import FlowMemoryPolicy
from .flow_navigation import FlowNavigation
from .flow_preparation import FlowStepPreparation
from .flow_execution import FlowStepExecution
from .graph import build_graph
from .memory import MemoryManager
from .schema import parse_schema
from .utils import sanitize_input_items


class FlowRun:
    def __init__(self, window, logger, schema, messages, ctx, bridge, options):
        self.logger, self.ctx, self.bridge, self.options = logger, ctx, bridge, options
        self.schema = parse_schema(schema)
        self.graph = build_graph(self.schema)
        self.memory = MemoryManager()
        self.memory_policy = FlowMemoryPolicy(logger)
        self.preparation = FlowStepPreparation(window, logger, self.memory_policy)
        get = options.option_get
        self.debug = DebugConfig(
            log_runtime=bool(get("debug", "log_runtime", True)),
            log_routes=bool(get("debug", "log_routes", True)),
            log_inputs=bool(get("debug", "log_inputs", True)),
            log_outputs=bool(get("debug", "log_outputs", True)),
            preview_chars=int(get("debug", "preview_chars", 280)),
        )
        self.navigation = FlowNavigation(self.graph, logger, self.debug)
        self.window = window
        self.messages = messages
        self.steps = 0
        self.last_output = ""
        self.last_response_id = None
        self.first_dispatch_done = False
        self.begin = True

    # ========================================
    # Flow lifecycle
    # ========================================

    async def run(self):
        current_ids = self.navigation.start()
        if not current_ids:
            return FlowResult(self.ctx, "", None)
        self.initial_messages = sanitize_input_items(list(self.messages or []))
        self.handler = StreamHandler(self.window, self.bridge)
        self.execution = FlowStepExecution(self.window, self.logger, self.bridge, self.handler, self.options)
        while current_ids and self._can_continue():
            current_id = current_ids[0]
            self.steps += 1
            if current_id in self.schema.ends:
                self.logger.info(f"Reached END node: {current_id}")
                break
            if current_id not in self.schema.agents:
                current_ids = self._skip_invalid_node(current_id)
                continue
            current_ids = await self._run_step(current_id)
        if self.bridge.stopped():
            self.bridge.on_stop(self.ctx)
        self.logger.info(f"Flow finished. steps={self.steps} final_len={len(self.last_output)}")
        return FlowResult(self.ctx, self.last_output, self.last_response_id)

    # ========================================
    # Node lifecycle
    # ========================================

    async def _run_step(self, current_id):
        started = perf_counter()
        node = self.schema.agents[current_id]
        self.logger.debug(f"[step {self.steps}] agent_id={node.id} name={node.name} outs={node.outputs}")
        prepared = self.preparation.prepare(
            node, self.schema, self.graph, self.memory, self.initial_messages,
            self.first_dispatch_done, self.last_output, self.options, self.debug,
        )
        self._begin_step(prepared.built.instance)
        output = await self.execution.execute(prepared, self.ctx, self.last_response_id)
        self.memory_policy.update_after_step(
            node_id=current_id, mem_state=prepared.memory_state, baton_user_text=prepared.baton,
            display_text=output.text, last_response_id=output.response_id, dbg=self.debug,
        )
        next_id = self.navigation.next_route(current_id, prepared, output)
        self._log_output(current_id, next_id, output)
        self.first_dispatch_done = True
        self.last_output, self.last_response_id = output.text, output.response_id
        current_ids = self.navigation.advance(current_id, next_id)
        self._finish_step(current_ids)
        self.logger.debug(f"[step {self.steps}] duration={perf_counter() - started:.3f}s")
        return current_ids

    def _can_continue(self):
        limit = self.options.max_iterations
        return (self.steps < limit or limit == 0) and not self.bridge.stopped()

    def _skip_invalid_node(self, current_id):
        self.logger.warning(f"Next id {current_id} is not an agent; stopping or jumping to END.")
        return [self.graph.end_nodes[0]] if self.graph.end_nodes else []

    # ========================================
    # Presentation and diagnostics
    # ========================================

    def _begin_step(self, agent):
        self.ctx.set_agent_name(agent.name)
        self.bridge.on_step(self.ctx, self.begin)
        self.begin = False
        self.handler.begin = self.begin

    def _finish_step(self, current_ids):
        is_end = not current_ids or current_ids[0] in self.schema.ends
        if self.options.use_partial_ctx:
            self.ctx = self.bridge.on_next_ctx(
                ctx=self.ctx, input="", output=self.last_output,
                response_id=self.last_response_id or "", finish=is_end, stream=True,
            )
            self.handler.new()
        else:
            self.bridge.on_next(self.ctx)
        if current_ids and current_ids[0] in self.schema.agents:
            self.ctx.set_agent_name(self.schema.agents[current_ids[0]].name)

    def _log_output(self, current_id, next_id, output):
        if self.debug.log_outputs:
            self.logger.debug(f"[output] preview='{ellipsize(output.text, self.debug.preview_chars)}' "
                              f"last_response_id={output.response_id}")
        if self.debug.log_routes:
            self.logger.debug(f"[route] current={current_id} -> next={next_id} "
                              f"(end_connected={self.graph.first_connected_end(current_id)})")
