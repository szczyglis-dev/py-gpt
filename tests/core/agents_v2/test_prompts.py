from pygpt_net.core.agents_v2.prompts import (
    AGENT_RUNTIME_POLICY,
    STEP_BY_STEP_RULES,
    PRIMARY_AGENT_BASE_PROMPT,
    _render_base_prompt,
    resolve_step_by_step_prompt,
)


def test_default_prompt_has_runtime_policy_without_step_rules():
    text = str(PRIMARY_AGENT_BASE_PROMPT)
    assert AGENT_RUNTIME_POLICY in text
    assert STEP_BY_STEP_RULES not in text


def test_resolve_step_by_step_prompt_uses_optional_variant():
    text = resolve_step_by_step_prompt(PRIMARY_AGENT_BASE_PROMPT, True)
    assert AGENT_RUNTIME_POLICY in text
    assert STEP_BY_STEP_RULES in text


def test_resolve_step_by_step_prompt_leaves_plain_string_unchanged():
    assert resolve_step_by_step_prompt("plain", True) == "plain"
    assert resolve_step_by_step_prompt(None, True) == ""


def test_render_base_prompt_inserts_policy_before_additional_instruction():
    prompt = "HEAD\nADDITIONAL USER/PRESET INSTRUCTION\nTAIL"
    rendered = _render_base_prompt(prompt)
    text = str(rendered)
    assert text.index(AGENT_RUNTIME_POLICY) < text.index("ADDITIONAL USER/PRESET INSTRUCTION")
    assert text.endswith("TAIL")


def test_runtime_policy_defines_restored_worker_context_provenance():
    text = str(PRIMARY_AGENT_BASE_PROMPT)
    assert '<worker_history_policy>' in text
    assert '<agents_runtime_context type="worker_result">' in text
    assert 'actually ran in that earlier turn' in text
    assert 'matching historical delegate/agent tool call is NOT evidence' in text
    assert 'Trust the provenance of the worker result, not its factual correctness' in text
