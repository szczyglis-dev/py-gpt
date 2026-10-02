"""Choose flow edges without mixing graph policy with provider execution."""


class FlowNavigation:
    def __init__(self, graph, logger, debug):
        self.graph = graph
        self.logger = logger
        self.debug = debug

    def start(self):
        if self.graph.start_targets:
            target = self.graph.start_targets[0]
            self.logger.info(f"Using explicit START -> {target}")
            return [target]
        target = self.graph.pick_default_start_agent()
        if target is None:
            self.logger.error("No START and no agents in schema.")
            return []
        self.logger.info(f"No START found, using lowest-id agent: {target}")
        return [target]

    def next_route(self, current_id, prepared, output):
        if output.decision is None:
            outs = self.graph.get_next(current_id)
            return outs[0] if outs else self.graph.first_connected_end(current_id)
        decision = output.decision
        if decision.valid:
            return decision.route
        if self.debug.log_routes:
            if output.router_mode == "realtime":
                self.logger.warning("[router-realtime] Invalid JSON; fallback to first route.")
            else:
                self.logger.warning(f"[router-{output.router_mode}] Invalid JSON: {decision.error}; fallback first route.")
        routes = prepared.built.allowed_routes
        return routes[0] if routes else None

    def advance(self, current_id, next_id):
        if isinstance(next_id, str) and next_id.lower() == "end":
            end = self.graph.first_connected_end(current_id) or (self.graph.end_nodes[0] if self.graph.end_nodes else None)
            return [end] if end else []
        if next_id:
            return [next_id]
        end = self.graph.first_connected_end(current_id)
        return [end] if end else []
