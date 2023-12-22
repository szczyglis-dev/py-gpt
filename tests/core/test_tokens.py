import pytest
from unittest.mock import MagicMock, mock_open, patch

from PySide6.QtWidgets import QMainWindow

from pygpt_net.core.context import Context, ContextItem
from pygpt_net.core.tokens import *
from pygpt_net.core.config import Config


@pytest.fixture
def mock_window():
    window = MagicMock(spec=QMainWindow)
    window.config = MagicMock(spec=Config)
    window.config.path = 'test_path'
    window.app = MagicMock()
    return window


def mock_get(key):
    if key == "mode":
        return "test_mode"
    elif key == "context_threshold":
        return 200


def test_parse(mock_window):
    """
    Test parse context data
    """
    ctx = Context(mock_window)
    data = [
        {
            'input': 'input',
            'output': 'output',
            'mode': 'mode',
            'thread': 'thread',
            'msg_id': 'msg_id',
            'run_id': 'run_id',
            'input_name': 'input_name',
            'output_name': 'output_name',
            'input_tokens': 1,
            'output_tokens': 2,
            'total_tokens': 3,
            'input_timestamp': 4,
            'output_timestamp': 5
        }
    ]
    items = ctx.parse(data)
    assert len(items) == 1
    assert items[0].input == 'input'
    assert items[0].output == 'output'
    assert items[0].mode == 'mode'
    assert items[0].thread == 'thread'
    assert items[0].msg_id == 'msg_id'
    assert items[0].run_id == 'run_id'
    assert items[0].input_name == 'input_name'
    assert items[0].output_name == 'output_name'
    assert items[0].input_tokens == 1
    assert items[0].output_tokens == 2
    assert items[0].total_tokens == 3
    assert items[0].input_timestamp == 4
    assert items[0].output_timestamp == 5


def test_update(mock_window):
    """
    Test update context data
    """
    ctx = Context(mock_window)
    ctx.window.config.get.side_effect = mock_get
    ctx.current_ctx = 'test_ctx'
    ctx.current_mode = 'test_mode'
    ctx.contexts = {
        'test_ctx': {
            'mode': 'test_mode'
        }
    }
    ctx.dump_context = MagicMock()  # prevent dump context
    ctx.update()
    assert ctx.current_ctx == 'test_ctx'
    assert ctx.current_mode == 'test_mode'
    assert ctx.contexts['test_ctx']['mode'] == 'test_mode'
    ctx.dump_context.assert_called_once_with('test_ctx')


def test_num_tokens_from_string():
    """
    Test num_tokens_from_string
    """
    text = "This is a test"
    num_tokens_from_string = MagicMock(return_value=4)
    assert num_tokens_from_string(text, 'gpt-3.5') == 4


def test_num_tokens_extra():
    """
    Test num_tokens_extra
    """
    model = "gpt-4-0613"
    assert num_tokens_extra() == 3


def test_num_tokens_prompt():
    """
    Test num_tokens_prompt
    """
    text = "This is a test"
    input_name = "test"
    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_prompt(text, input_name, model) == 12


def test_num_tokens_completion():
    """
    Test num_tokens_completion
    """
    text = "This is a test"
    model = "gpt-3.5-turbo-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_completion(text, model) == 8


def test_num_tokens_only():
    """
    Test num_tokens_only
    """
    text = "This is a test"
    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_only(text, model) == 8

def test_num_tokens_from_messages():
    """
    Test num_tokens_from_messages
    """
    messages = [
        {
            'name': 'test',
            'content': 'This is a test'
        },
        {
            'name': 'test',
            'content': 'This is a second test'
        }
    ]
    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_from_messages(messages, model) == 43


def test_num_tokens_from_context_item():
    """
    Test num_tokens_from_context_item
    """
    item = ContextItem()
    item.input = "This is a test"
    item.output = "This is a second test"
    item.input_name = "test"
    item.output_name = "test"
    item.input_tokens = 4
    item.output_tokens = 4
    item.total_tokens = 8
    item.input_timestamp = 1
    item.output_timestamp = 2

    model = "gpt-4-0613"
    with patch('pygpt_net.core.tokens.num_tokens_from_string', return_value=8):
        assert num_tokens_from_context_item(item, 'chat', model) == 56


def test_get_tokens_values():
    """
    Test get_tokens_values
    """
    model = "gpt-4-0613"
    assert get_tokens_values(model) == ('gpt-4-0613', 3, 1)
