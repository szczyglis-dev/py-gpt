# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 03:00:00                  #
# ================================================== #

from agents import (
    Agent as OpenAIAgent,
)

from pygpt_net.item.model import ModelItem
from pygpt_net.item.preset import PresetItem

from pygpt_net.provider.api.openai.agents.remote_tools import append_tools


def get_experts(
    window,
    verbose: bool = False,
    preset: PresetItem = None,
    tools: list = None,
):
    """
    Return list of expert agents based on the preset

    :param window: window instance
    :param verbose: bool - if True, print expert names
    :param preset: PresetItem - preset containing expert UUIDs
    :param tools: list - list of function tools to append to experts
    :return: list of OpenAIAgent instances
    """
    experts = []
    uuids = preset.experts
    for uuid in uuids:
        expert = window.core.presets.get_by_uuid(uuid)
        if expert:
            experts.append(expert)

    expert_agents = []
    for expert in experts:
        model = window.core.models.get(expert.model)
        expert_agent = get_expert(
            window=window,
            prompt=expert.prompt,
            model=model,
            preset=expert,
            tools=tools,
        )
        expert_agents.append(expert_agent)
        if verbose:
            print(f"[Agents] Adding expert: {expert.name} ({model.id})")
    return expert_agents

def get_expert(
        window,
        prompt: str,
        model: ModelItem,
        preset: PresetItem = None,
        tools: list = None,
) -> OpenAIAgent:
    """
    Return Agent provider instance

    :param window: window instance
    :param prompt: Expert prompt
    :param model: Model item
    :param preset: Preset item
    :param tools: List of function tools
    :return: Agent provider instance
    """
    agent_name = preset.name if preset else "Agent"
    kwargs = {
        "name": agent_name,
        "instructions": prompt,
        "model": window.core.agents.provider.get_openai_model(model),
    }
    tool_kwargs = append_tools(
        tools=tools,
        window=window,
        model=model,
        preset=preset,
        allow_local_tools=True,
        allow_remote_tools=True,
        is_expert_call=True,
    )
    kwargs.update(tool_kwargs)  # update kwargs with tools
    return OpenAIAgent(**kwargs)