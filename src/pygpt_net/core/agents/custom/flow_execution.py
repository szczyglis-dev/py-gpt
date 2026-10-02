"""Execute one prepared node with the selected streaming presentation policy."""

from agents import Runner

from .flow_types import StepOutput
from .router import parse_route_output
from .router_streamer import DelayedRouterStreamer, RealtimeRouterStreamer
from .utils import extract_text_output


class FlowStepExecution:
    def __init__(self, window, logger, bridge, handler, options):
        self.window = window
        self.logger = logger
        self.bridge = bridge
        self.handler = handler
        self.options = options

    # ========================================
    # Node execution
    # ========================================

    async def execute(self, prepared, ctx, last_response_id):
        built = prepared.built
        if self.options.stream and not built.multi_output:
            return await self._stream_answer(prepared, ctx, last_response_id)
        mode = (self.options.router_stream_mode or "off").lower()
        if built.multi_output and self.options.stream and mode in {"realtime", "delayed"}:
            raw, response_id = await self._stream_router(prepared, ctx, last_response_id, mode)
        else:
            result = await Runner.run(built.instance, **prepared.run_kwargs)
            raw, response_id = extract_text_output(result), getattr(result, "last_response_id", None)
            mode = "off"
        decision = parse_route_output(raw or "", built.allowed_routes) if built.multi_output else None
        text = (decision.content if decision else raw) or ""
        if mode != "realtime":
            self._display_answer(ctx, text)
        return StepOutput(text, response_id, decision, mode)

    # ========================================
    # Streaming
    # ========================================

    async def _stream_answer(self, prepared, ctx, response_id):
        result = Runner.run_streamed(prepared.built.instance, **prepared.run_kwargs)
        self.handler.reset()
        last_chunk = ""
        async for event in result.stream_events():
            if self._stop_stream(result, ctx):
                break
            chunk, response_id = self.handler.handle(event, ctx)
            if chunk:
                last_chunk = chunk
        return StepOutput(getattr(self.handler, "buffer", "") or last_chunk or "", response_id)

    async def _stream_router(self, prepared, ctx, response_id, mode):
        result = Runner.run_streamed(prepared.built.instance, **prepared.run_kwargs)
        collector = self._router_collector(mode)
        collector.reset()
        async for event in result.stream_events():
            if self._stop_stream(result, ctx):
                break
            if mode == "realtime":
                collector.handle_event(event, ctx)
                rid = collector.last_response_id
            else:
                _, rid = collector.handle_event(event, ctx)
            if rid:
                response_id = rid
        return collector.buffer or "", response_id

    def _router_collector(self, mode):
        if mode == "delayed":
            return DelayedRouterStreamer(self.window, self.bridge)
        return RealtimeRouterStreamer(
            window=self.window, bridge=self.bridge,
            handler=self.handler if not self.options.use_partial_ctx else None,
            buffer_to_handler=not self.options.use_partial_ctx, logger=self.logger,
        )

    def _stop_stream(self, result, ctx):
        if not self.bridge.stopped():
            return False
        result.cancel()
        self.bridge.on_stop(ctx)
        return True

    # ========================================
    # Presentation
    # ========================================

    def _display_answer(self, ctx, text):
        if text:
            ctx.stream = text
            self.bridge.on_step(ctx, False)
            if not self.options.use_partial_ctx:
                self.handler.to_buffer(text)
