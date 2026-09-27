"""Non-destructive mapping of saved legacy agent presets to LlamaIndex modes."""
from copy import deepcopy

RETIRED_LLAMA_PROVIDERS = {'openai', 'react', 'openai_assistant'}
OPENAI_TO_LLAMA = {
    'openai_agent_base': 'llama_agent_base',
    'openai_agent_experts': 'llama_agent_experts',
    'openai_agent_feedback': 'llama_agent_feedback',
    'openai_agent_experts_feedback': 'llama_agent_experts_feedback',
    'openai_agent_b2b': 'llama_agent_b2b',
    'openai_agent_evolve': 'llama_agent_evolve',
    'openai_agent_bot_researcher': 'llama_agent_researcher',
    'openai_agent_planner': 'llama_agent_planner',
    'openai_agent_supervisor': 'supervisor',
}


def migrate_preset(preset):
    if preset.agent_openai and preset.agent_provider_openai in OPENAI_TO_LLAMA:
        # Existing explicitly configured Llama workflows retain precedence.
        if not preset.agent_llama:
            preset.agent_provider = OPENAI_TO_LLAMA[preset.agent_provider_openai]
            preset.agent_llama = True
    if preset.agent_provider in RETIRED_LLAMA_PROVIDERS:
        preset.agent_provider = 'llama_agent_base'
        if preset.agent_llama and preset.name in ('OpenAI Agent', 'ReAct Agent'):
            preset.name = 'Simple agent'
    # Materialize migrated options for the preset editor as well as execution.
    # Keep separate copies so editing one engine cannot change the other engine.
    source = preset.agent_provider_openai
    target = preset.agent_provider
    if (target and target.startswith('llama_agent_') and OPENAI_TO_LLAMA.get(source) == target
            and isinstance(preset.extra, dict) and source in preset.extra
            and target not in preset.extra):
        preset.extra[target] = deepcopy(preset.extra[source])
