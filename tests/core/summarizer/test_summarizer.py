from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pygpt_net.core.summarizer import Summarizer
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.item.model import ModelItem
from pygpt_net.item.ctx import CtxItem


def setup_summary(**config):
    values = {"context.extra_summary.enabled": True, "max_output_tokens": 128, **config}
    model = ModelItem("test")
    model.ctx = 4096
    model.tokens = 256
    core = SimpleNamespace(config=SimpleNamespace(get=lambda key, default=None: values.get(key, default)),
                           tokens=SimpleNamespace(from_str=lambda text, model: len(text)),
                           models=SimpleNamespace(has=lambda key: key == "small", get=lambda key: small,
                                                  get_num_ctx=lambda key: 4096))
    small = ModelItem("small")
    small.ctx = 1024
    small.tokens = 128
    window = SimpleNamespace(core=core, dispatch=Mock())
    summary = Summarizer(window)
    context = BridgeContext(model=model, prompt="User question", system_prompt="Policy", max_tokens=128)
    return summary, context, small


def test_disabled_and_small_text_never_call_a_model():
    summary, context, _ = setup_summary(**{"context.extra_summary.enabled": False})
    assert summary.process("x" * 20000, context) == "x" * 20000
    summary.window.dispatch.assert_not_called()
    summary, context, _ = setup_summary()
    assert summary.process("small", context) == "small"
    summary.window.dispatch.assert_not_called()


def test_budget_reserves_history_tools_output_and_advanced_threshold():
    summary, context, _ = setup_summary(**{"max_total_tokens": 2048, "context.advanced.enabled": True,
                                         "context.advanced.threshold": 50})
    item = CtxItem()
    item.input, item.output = "past question", "past answer"
    context.history = [item]
    context.external_functions = [{"name": "tool", "description": "documentation" * 10}]
    base = summary.budget(context)
    assert base.window == 2048
    assert base.available == 2048 - base.used - 128 - 64
    assert base.trigger <= 1024 - base.used - 128
    context.tools_outputs = ["result" * 100]
    assert summary.budget(context).available < base.available


def test_map_reduce_obeys_override_limit_and_reads_every_source_character():
    summary, context, small = setup_summary(**{"context.extra_summary.model": "small"})
    inputs = []
    def dispatch(event):
        request = event.data["context"]
        assert request.model is small
        assert len(request.prompt) + len(request.system_prompt) + request.max_tokens + 64 <= small.ctx
        assert not request.history and not request.external_functions and not request.attachments
        assert request.ctx.internal
        inputs.append(request.prompt.split("External evidence:\n", 1)[1])
        event.data["response"] = "facts " + str(len(inputs))
    summary.window.dispatch.side_effect = dispatch
    text = "0123456789" * 500
    result = summary.process(text, context, "source.txt")
    first = []
    consumed = 0
    for chunk in inputs:
        if consumed >= len(text):
            break
        first.append(chunk)
        consumed += len(chunk)
    assert "".join(first) == text
    assert "source.txt" in result
    assert len(result) <= summary.budget(context).target
    assert len(inputs) > 1


def test_exhausted_budget_and_failed_model_do_not_send_oversized_text():
    summary, context, _ = setup_summary()
    context.prompt = "question" * 1000
    with pytest.raises(ValueError, match="No room"):
        summary.process("source" * 1000, context)
    summary, context, _ = setup_summary()
    with pytest.raises(ValueError, match="returned no text"):
        summary.process("source" * 1000, context)


def test_unicode_chunking_preserves_source_and_zero_token_fallback():
    summary, context, _ = setup_summary()
    text = "Zażółć 🐈‍⬛" * 30
    chunks = list(summary.chunks(text, 15, context.model))
    assert "".join(chunks) == text
    assert all(len(chunk) <= 15 for chunk in chunks)
    summary.window.core.tokens.from_str = lambda *args: 0
    assert summary.count("ą", context.model) == 2


def test_summary_model_failure_or_unknown_limit_is_explicit():
    summary, context, small = setup_summary(**{"context.extra_summary.model": "missing"})
    with pytest.raises(ValueError, match="unavailable"):
        summary.process("x" * 5000, context)
    context.model.ctx = 0
    summary.window.core.models.get_num_ctx = lambda key: 0
    with pytest.raises(ValueError, match="Unknown context"):
        summary.budget(context)


def test_empty_model_combo_uses_current_model():
    summary, context, _ = setup_summary(**{"context.extra_summary.model": "_"})
    assert summary.resolve_model(context.model) is context.model


def test_advanced_checkpoint_filter_and_notes_are_counted():
    summary, context, _ = setup_summary(**{"context.advanced.enabled": True})
    old, recent = CtxItem(), CtxItem()
    old.input, recent.input = "old evidence " * 200, "recent question"
    context.ctx = CtxItem()
    context.history = [old, recent]
    manager = SimpleNamespace(filter_history=Mock(return_value=[recent]), notes_for_model=Mock(return_value="checkpoint notes"))
    summary.window.core.context_manager = manager
    budget = summary.budget(context)
    assert budget.used < len(old.input)
    manager.filter_history.assert_called_once_with([old, recent])
    manager.notes_for_model.assert_called_once_with(context.ctx, model=context.model)


def test_long_history_guidance_reads_every_segment_before_evidence():
    summary, context, small = setup_summary(**{"context.extra_summary.model": "small"})
    past = CtxItem()
    past.input = "history-" * 400
    context.history = [past]
    # Use a larger final window to keep historical usage within the main budget.
    context.model.ctx = 16000
    prompts = []
    def dispatch(event):
        request = event.data["context"]
        assert len(request.prompt) + len(request.system_prompt) + request.max_tokens + 64 <= small.ctx
        prompts.append(request.prompt)
        event.data["response"] = "concise history facts"
    summary.window.dispatch.side_effect = dispatch
    summary.process("evidence " * 600, context)
    history_chunks = [prompt.split("Conversation segment:\n", 1)[1] for prompt in prompts if "Conversation segment:\n" in prompt]
    full_history = summary.history_text(context.history)
    consumed = []
    total = 0
    for chunk in history_chunks:
        if total >= len(full_history):
            break
        consumed.append(chunk)
        total += len(chunk)
    assert "".join(consumed) == full_history
    assert any("External evidence:\n" in prompt for prompt in prompts)


def test_tool_response_preserves_raw_payload_without_automatic_summary():
    from pygpt_net.plugin.base.worker import BaseWorker
    from pygpt_net.plugin.base.plugin import BasePlugin
    from pygpt_net.core.summarizer import model_payload
    summary, context, _ = setup_summary()
    core = summary.window.core
    core.summarizer = summary
    core.ctx = SimpleNamespace(all=lambda meta_id: [])
    core.models.from_defaults = lambda: context.model
    core.command = SimpleNamespace(is_tool_hidden=lambda name: False)
    summary.window.dispatch.side_effect = lambda event: event.data.update(response="Budget is 4200 EUR.")
    ctx = CtxItem()
    ctx.input = "What is the budget?"
    plugin = BasePlugin(window=summary.window)
    worker = BaseWorker(plugin=plugin)
    worker.ctx = ctx
    raw = {"data": "external evidence " * 400, "source": "project plans"}
    response = worker.make_response({"cmd": "read"}, raw)
    assert response["result"] is raw
    assert "model_result" not in response
    summary.window.dispatch.assert_not_called()
    payload = model_payload([response])[0]
    assert "model_result" not in payload
    assert payload["result"] == raw
    plugin.prepare_reply_ctx(response, ctx)
    assert ctx.results[-1]["result"] == raw
    assert ctx.extra["tool_output"][-1]["result"] == raw
    assert response["result"] is raw


def test_execution_local_context_is_never_sent_to_summary_model():
    from pygpt_net.plugin.base.worker import BaseWorker
    summary, context, _ = setup_summary()
    core = summary.window.core
    core.summarizer = summary
    core.ctx = SimpleNamespace(all=lambda meta_id: [])
    core.models.from_defaults = lambda: context.model
    prompts = []
    def dispatch(event):
        prompts.append(event.data["context"].prompt)
        event.data["response"] = "Execution finished successfully."
    summary.window.dispatch.side_effect = dispatch
    worker = BaseWorker(plugin=SimpleNamespace(window=summary.window))
    worker.ctx = CtxItem()
    raw = {"stdout": "large public output " * 400, "stderr": "", "context": "LOCAL_ONLY_SECRET"}
    response = worker.make_response({"cmd": "execute"}, raw, {"context": "LOCAL_ONLY_EXTRA"})
    assert response["result"] is raw
    assert "model_result" not in response
    summary.window.dispatch.assert_not_called()
    assert not any("LOCAL_ONLY" in prompt for prompt in prompts)
