"""Graph start selection and per-node override precedence."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.agents.custom.graph import FlowGraph, build_graph
from pygpt_net.core.agents.custom.utils import make_option_getter, patch_last_assistant_output, resolve_node_runtime


def test_default_graph_start_prefers_numeric_suffix_and_copies_edges():
    schema = SimpleNamespace(agents={'agent10': SimpleNamespace(outputs=['end'], memory_out='memory'),
                                    'agent2': SimpleNamespace(outputs=[], memory_out=None),
                                    'custom': SimpleNamespace(outputs=[], memory_out=None)},
                             starts={'start': SimpleNamespace(outputs=['agent10'])}, ends={'end': object()})
    graph = build_graph(schema)
    assert graph.pick_default_start_agent() == 'agent2'
    assert graph.start_targets == ['agent10'] and graph.end_nodes == ['end']
    assert graph.get_next('missing') == []
    assert graph.first_connected_end('agent10') == 'end'
    assert graph.first_connected_end('agent2') is None
    schema.agents['agent10'].outputs.append('other')
    assert graph.get_next('agent10') == ['end']
    assert FlowGraph(SimpleNamespace(agents={})).pick_default_start_agent() is None


def test_option_getter_preserves_false_and_handles_missing_or_faulty_options():
    base = MagicMock()
    assert make_option_getter(base, None)('a', 'x', 'default') == 'default'
    getter = make_option_getter(base, 'preset')
    for value in (None, ''):
        base.get_option.return_value = value
        assert getter('a', 'x', 'default') == 'default'
    base.get_option.return_value = False
    assert getter('a', 'x', True) is False
    base.get_option.side_effect = ValueError('invalid')
    assert getter('a', 'x', 'default') == 'default'


def test_patch_last_assistant_only_and_does_not_mutate_original():
    items = [{'role': 'assistant', 'id': 'old', 'content': 'old'}, {'role': 'user', 'content': 'Q'}]
    result = patch_last_assistant_output(items, 'visible')
    assert result[0] == {'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'visible'}]}
    assert items[0]['id'] == 'old' and items[0]['content'] == 'old'
    assert patch_last_assistant_output([], 'x') == []
    assert patch_last_assistant_output([{'role': 'user'}], 'x') == [{'role': 'user'}]


@pytest.mark.parametrize('overwrite', [False, True])
def test_node_runtime_precedence_and_system_context(overwrite):
    window = MagicMock()
    model = object()
    overrides = {'model_overwrite': overwrite, 'model': 'selected', 'prompt': ' override ', 'role': ' writer ', 'allow_local_tools': False}
    result = resolve_node_runtime(window=window, node=SimpleNamespace(id='a', instruction='schema', role='schema-role'),
        option_get=lambda section,key,default=None: overrides.get(key, default), default_model=model, base_prompt='base',
        system_prompt_extra='context', schema_allow_local=True, schema_allow_remote=False,
        default_allow_local=True, default_allow_remote=True)
    assert result.model is (window.core.models.get.return_value if overwrite else model)
    assert result.instructions == 'override\n\ncontext' and result.role == 'writer'
    assert result.allow_local_tools is False and result.allow_remote_tools is False


def test_invalid_custom_flow_node_jumps_to_end_or_stops():
    from pygpt_net.core.agents.custom.flow import FlowRun
    session = object.__new__(FlowRun)
    session.logger = MagicMock()
    session.graph = SimpleNamespace(end_nodes=['end'])
    assert session._skip_invalid_node('invalid') == ['end']
    session.graph.end_nodes = []
    assert session._skip_invalid_node('invalid') == []
    assert session.logger.warning.call_count == 2
