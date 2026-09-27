"""LlamaIndex implementations of the legacy multi-agent working modes.

Only option definitions/prompts are shared with the OpenAI providers. Execution,
models, tools, memory and streaming belong to LlamaIndex.
"""
import json
from importlib import import_module

from pygpt_net.core.types import AGENT_TYPE_LLAMA, AGENT_MODE_WORKFLOW
from pygpt_net.provider.agents.base import BaseAgent

SOURCES = {
    'base': 'agent',
    'experts': 'agent_with_experts',
    'feedback': 'agent_with_feedback',
    'experts_feedback': 'agent_with_experts_feedback',
    'b2b': 'agent_b2b',
    'evolve': 'evolve',
    'researcher': 'bot_researcher',
    # 'planner': 'agent_planner',
}


class ModeAgent(BaseAgent):
    def __init__(self, strategy):
        super().__init__()
        self.strategy = strategy
        source = import_module('pygpt_net.provider.agents.openai.' + SOURCES[strategy]).Agent()
        self.option_source = source
        self.id = 'llama_agent_' + strategy
        self.name = source.name
        self.type = AGENT_TYPE_LLAMA
        self.mode = AGENT_MODE_WORKFLOW

    def get_options(self):
        options = self.option_source.get_options()
        if self.strategy == 'b2b':
            options['conversation'] = {'label': 'Conversation', 'options': {
                'max_rounds': {'type': 'int', 'label': 'Maximum rounds (0 = until stopped)',
                               'min': 0, 'default': 0}}}
        return options

    def get_option(self, preset, section, key):
        if preset is None:
            return self.get_default(section, key)
        # A copied OpenAI preset can retain its options without a destructive rewrite.
        if self.id not in (preset.extra or {}) and self.option_source.id in (preset.extra or {}):
            return self.option_source.get_option(preset, section, key)
        return super().get_option(preset, section, key)

    def get_agent(self, window, kwargs):
        from .workflow.modes import ModesWorkflow
        return ModesWorkflow(self, window, kwargs)

    def build_role(self, window, kwargs, section, name, schema=None, *, workflow, ctx, expert=None, query=""):
        from llama_index.core.agent.workflow import FunctionAgent
        from llama_index.core.tools import FunctionTool
        preset = kwargs['context'].preset
        tools = list(kwargs.get('tools') or [])
        options = self.get_options().get(section, {}).get('options', {})
        local = self.get_option(preset, section, 'allow_local_tools') if 'allow_local_tools' in options else True
        remote = self.get_option(preset, section, 'allow_remote_tools') if 'allow_remote_tools' in options else True
        model = self.resolve_model_option(window, preset, section, kwargs.get('model'))
        prompt_key = 'initial_prompt' if self.strategy == 'planner' and section == 'planner' else 'prompt'
        prompt = self.get_option(preset, section, prompt_key) or kwargs.get('system_prompt') or 'Help the user.'
        if expert is not None:
            model = window.core.models.get(expert.model) or kwargs.get('model')
            prompt = expert.prompt
            local = getattr(expert, 'agent_v2_allow_local_tools', True)
            remote = getattr(expert, 'agent_v2_allow_remote_tools', True)
        # Planner templates contain literal JSON braces as well as named slots.
        # Replace only known slots rather than formatting arbitrary JSON/tool text.
        values = {'task': query, 'tools_str': '\n'.join(tool.metadata.name for tool in tools),
                  'memory_context': '\n'.join(str(msg.content or '') for msg in workflow.initial_history),
                  'completed_outputs': 'See the current task message.',
                  'remaining_sub_tasks': 'See the current task message.'}
        for key, value in values.items():
            prompt = prompt.replace('{' + key + '}', value)
        prompt = self.append_system_prompt_extra(prompt, kwargs)
        if schema:
            prompt += '\n\nReturn only a JSON object matching this schema:\n' + json.dumps(schema.model_json_schema(), ensure_ascii=False)
        llm = window.core.idx.llm.get_agent(model, stream=True, allow_remote_tools=bool(remote),
            computer_runtime=kwargs.get('computer_runtime') if remote else None)
        role_tools = tools if local else []
        use_experts = self.strategy in ('experts', 'experts_feedback', 'b2b', 'evolve', 'researcher', 'planner')
        if expert is None and use_experts:
            for index, uuid in enumerate(getattr(preset, 'experts', []) or []):
                expert_preset = window.core.presets.get_by_uuid(uuid)
                if expert_preset is None:
                    continue

                def make_consult(selected):
                    async def consult(query: str) -> str:
                        """Ask this expert to complete a task and return its answer."""
                        async with workflow.expert_lock:
                            answer = await workflow.role(ctx, 'expert', query, name=selected.name,
                                                         expert=selected)
                            workflow.announce(ctx, name)
                            return answer
                    return consult

                role_tools.append(FunctionTool.from_defaults(
                    async_fn=make_consult(expert_preset), name=f'consult_expert_{index + 1}',
                    description=f'Consult {expert_preset.name}: {expert_preset.description or expert_preset.name}'))
        return FunctionAgent(name=name, llm=llm, tools=role_tools, system_prompt=prompt, streaming=True,
                             allow_parallel_tool_calls=False)


def get_mode_agents():
    return [ModeAgent(strategy) for strategy in SOURCES]
