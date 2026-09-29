from pygpt_net.core.agents_v2.prompts import (
    AGENT_RUNTIME_POLICY,
    STEP_BY_STEP_RULES,
    PRIMARY_AGENT_BASE_PROMPT,
    _render_base_prompt,
    resolve_step_by_step_prompt,
)


def test_default_prompt_has_runtime_policy_with_integrated_step_rules():
    text = str(PRIMARY_AGENT_BASE_PROMPT)
    assert AGENT_RUNTIME_POLICY in text
    assert STEP_BY_STEP_RULES in text


def test_resolve_step_by_step_prompt_is_compatibility_noop():
    text = resolve_step_by_step_prompt(PRIMARY_AGENT_BASE_PROMPT, False, "legacy steps")
    assert text == str(PRIMARY_AGENT_BASE_PROMPT)
    assert AGENT_RUNTIME_POLICY in text
    assert STEP_BY_STEP_RULES in text
    assert "legacy steps" not in text


def test_resolve_step_by_step_prompt_leaves_plain_string_unchanged():
    assert resolve_step_by_step_prompt("plain", True) == "plain"
    assert resolve_step_by_step_prompt(None, True) == ""


def test_render_base_prompt_inserts_policy_before_additional_instruction():
    prompt = "HEAD\n## Additional user/preset instruction\nTAIL"
    rendered = _render_base_prompt(prompt)
    text = str(rendered)
    assert text.index(AGENT_RUNTIME_POLICY) < text.index("## Additional user/preset instruction")
    assert text.endswith("TAIL")


def test_runtime_policy_defines_restored_worker_context_provenance():
    text = str(PRIMARY_AGENT_BASE_PROMPT)
    assert "## Historical worker output" in text
    assert '<agents_runtime_context type="worker_result">' in text
    assert "runtime-injected prior worker output" in text
    assert "Missing historical tool envelopes do not invalidate runtime-provided provenance" in text
    assert "Trust provenance, not factual correctness" in text
