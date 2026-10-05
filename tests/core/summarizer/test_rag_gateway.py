from types import SimpleNamespace
from unittest.mock import Mock

from llama_index.core.schema import TextNode, NodeWithScore

from pygpt_net.core.idx.rag_context import RAGContextPreparer
from pygpt_net.core.idx.chat import Chat
from pygpt_net.item.model import ModelItem


def test_rag_gateway_sees_all_sources_before_packing_discards_overflow():
    preparer = RAGContextPreparer()
    nodes = [NodeWithScore(node=TextNode(text="Evidence A", metadata={"filename": "a.txt"}), score=1),
             NodeWithScore(node=TextNode(text="Evidence B", metadata={"filename": "b.txt"}), score=1)]
    preparer._retrieve_nodes = Mock(return_value=nodes)
    preparer._pack_context = Mock(return_value=["bounded evidence"])
    transform = Mock(return_value="summary of both sources")
    result = preparer.prepare(index=object(), llm=object(), query="question", context_transform=transform)
    text = transform.call_args.args[0]
    assert "Evidence A" in text and "Evidence B" in text
    assert "a.txt" in text and "b.txt" in text
    assert preparer._pack_context.call_args.kwargs["chunks"] == ["summary of both sources"]
    assert "bounded evidence" in result.context


def test_chat_integration_supplies_real_history_and_system_to_gateway():
    model = ModelItem("test")
    model.ctx = 4096
    summary = SimpleNamespace(process=Mock(return_value="condensed"))
    core = SimpleNamespace(config=SimpleNamespace(get=lambda key, default=None: True if key == "context.extra_summary.enabled" else default),
                           models=SimpleNamespace(get_num_ctx=lambda key: 4096), summarizer=summary)
    chat = Chat(SimpleNamespace(core=core))
    preparer = SimpleNamespace(prepare=Mock(return_value="result"))
    chat._rag_context = preparer
    history = [SimpleNamespace(content="Earlier discussion")]
    assert chat.prepare_rag_context(object(), object(), "question", history, "context", "policy", model) == "result"
    transform = preparer.prepare.call_args.kwargs["context_transform"]
    assert transform("all evidence") == "condensed"
    request = summary.process.call_args.args[1]
    assert request.history == history and request.system_prompt == "policy"
    assert request.prompt == "question" and request.model is model
