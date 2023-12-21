import pytest
from unittest.mock import MagicMock, mock_open, patch
from PySide6.QtWidgets import QMainWindow

from langchain.schema import SystemMessage, HumanMessage, AIMessage
from pygpt_net.core.context import ContextItem

from pygpt_net.core.config import Config
from pygpt_net.core.chain import Chain


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.config = MagicMock(spec=Config)
    window.config.path = 'test_path'
    window.app = MagicMock()
    return window


def test_build_chat_messages(mock_window):
    items = []
    ctx_item = ContextItem()
    ctx_item.input = 'user message'
    items.append(ctx_item)

    ctx_item = ContextItem()
    ctx_item.output = 'AI message'
    items.append(ctx_item)

    chain = Chain(mock_window)
    chain.system_prompt = 'test_system_prompt'
    chain.window.config.get.return_value = True
    chain.window.app.context.get_all_items.return_value = items

    messages = chain.build_chat_messages('test_prompt')
    assert len(messages) == 4
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert isinstance(messages[2], AIMessage)
    assert messages[0].content == 'test_system_prompt'
    assert messages[1].content == 'user message'
    assert messages[2].content == 'AI message'
    assert messages[3].content == 'test_prompt'


def test_build_completion(mock_window):
    items = []
    ctx_item = ContextItem()
    ctx_item.input = 'user message'
    items.append(ctx_item)

    ctx_item = ContextItem()
    ctx_item.output = 'AI message'
    items.append(ctx_item)

    chain = Chain(mock_window)
    chain.system_prompt = 'test_system_prompt'
    chain.window.config.get.return_value = True
    chain.window.app.context.get_all_items.return_value = items

    message = chain.build_completion('test_prompt')
    assert message == 'test_system_prompt\nuser message\nAI message\ntest_prompt'


def test_build_completion_with_names(mock_window):
    items = []
    ctx_item = ContextItem()
    ctx_item.input = 'user message'
    ctx_item.input_name = 'User'
    ctx_item.output_name = 'AI'
    items.append(ctx_item)

    ctx_item = ContextItem()
    ctx_item.output = 'AI message'
    ctx_item.input_name = 'User'
    ctx_item.output_name = 'AI'
    items.append(ctx_item)

    chain = Chain(mock_window)
    chain.system_prompt = 'test_system_prompt'
    chain.user_name = 'User'
    chain.ai_name = 'AI'
    chain.window.config.get.return_value = True
    chain.window.app.context.get_all_items.return_value = items

    message = chain.build_completion('test_prompt')
    assert message == 'test_system_prompt\nUser: user message\nAI: AI message\nUser: test_prompt\nAI:'


def test_chat(mock_window):
    cfg = {'langchain': {'provider': 'test'}}
    mock_window.config.get_model_cfg.return_value = cfg
    chain = Chain(mock_window)
    chain.build_chat_messages = MagicMock()
    chain.build_chat_messages.return_value = 'test_messages'
    mock_chat_instance = MagicMock()
    mock_chat_instance.invoke.return_value = 'test_response'

    chain.llms = {'test': MagicMock()}
    chain.llms['test'].chat = MagicMock(return_value=mock_chat_instance)
    response = chain.chat('test_prompt')
    assert response == 'test_response'
    chain.build_chat_messages.assert_called_once_with('test_prompt')
    chain.llms['test'].chat.assert_called_once_with(
        mock_window.config.all(), cfg['langchain'], False
    )
    mock_chat_instance.invoke.assert_called_once_with('test_messages')


def test_completion(mock_window):
    cfg = {'langchain': {'provider': 'test'}}
    mock_window.config.get_model_cfg.return_value = cfg
    chain = Chain(mock_window)
    chain.build_completion = MagicMock()
    chain.build_completion.return_value = 'test_messages'
    mock_chat_instance = MagicMock()
    mock_chat_instance.invoke.return_value = 'test_response'

    chain.llms = {'test': MagicMock()}
    chain.llms['test'].completion = MagicMock(return_value=mock_chat_instance)
    response = chain.completion('test_prompt')
    assert response == 'test_response'
    chain.build_completion.assert_called_once_with('test_prompt')
    chain.llms['test'].completion.assert_called_once_with(
        mock_window.config.all(), cfg['langchain'], False
    )
    mock_chat_instance.invoke.assert_called_once_with('test_messages')


def test_call(mock_window):
    ctx = ContextItem()
    ctx.input = 'test_input'

    cfg = {'langchain': {'provider': 'test', 'mode': ['chat', 'completion']}}
    mock_window.config.get_model_cfg.return_value = cfg
    chain = Chain(mock_window)
    chain.chat = MagicMock()
    chain.chat.content = MagicMock()
    chain.completion = MagicMock()
    chain.chat.content.return_value = 'test_chat_response'
    chain.completion.return_value = 'test_completion_response'

    chain.call('test_text', ctx)
    chain.chat.assert_called_once_with('test_text', False)
