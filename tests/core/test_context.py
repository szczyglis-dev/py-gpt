import pytest
from unittest.mock import MagicMock, mock_open, patch
from PySide6.QtWidgets import QMainWindow

from pygpt_net.core.context import Context, ContextItem

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


def test_post_update(mock_window):
    """
    Test post update context data
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
    ctx.post_update('test_mode')
    assert ctx.current_ctx == 'test_ctx'
    assert ctx.current_mode == 'test_mode'
    assert ctx.contexts['test_ctx']['mode'] == 'test_mode'
    ctx.dump_context.assert_called_once_with('test_ctx')


def test_create_id(mock_window):
    """
    Test create context ID
    """
    ctx = Context(mock_window)
    ctx.create_id = MagicMock(return_value='test_id')
    assert ctx.create_id() == 'test_id'


def test_is_empty(mock_window):
    """
    Test is_empty
    """
    ctx = Context(mock_window)
    assert ctx.is_empty() is True
    ctx.current_ctx = 'test_ctx'
    assert ctx.is_empty() is True
    ctx.items = [1]
    assert ctx.is_empty() is False


def test_new(mock_window):
    """
    Test new context
    """
    ctx = Context(mock_window)
    ctx.create_id = MagicMock(return_value='test_id')
    ctx.window.config.get.side_effect = mock_get
    ctx.current_ctx = 'test_ctx'
    ctx.current_mode = 'test_mode'
    ctx.contexts = {
        'test_ctx': {
            'mode': 'test_mode'
        }
    }
    ctx.dump_context = MagicMock()  # prevent dump context
    assert ctx.new() == 'test_id'
    assert ctx.current_ctx == 'test_id'
    assert ctx.current_mode == 'test_mode'
    assert ctx.contexts['test_id']['mode'] == 'test_mode'
    ctx.dump_context.assert_called_once_with('test_id')


def test_is_ctx_initialized(mock_window):
    """
    Test is_ctx_initialized
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {
        'test_ctx': {
            'initialized': True
        }
    }
    assert ctx.is_ctx_initialized() is True
    ctx.contexts = {
        'test_ctx': {
            'initialized': False
        }
    }
    assert ctx.is_ctx_initialized() is False
    ctx.contexts = {
        'test_ctx': {}
    }
    assert ctx.is_ctx_initialized() is True
    ctx.current_ctx = None
    assert ctx.is_ctx_initialized() is None


def test_set_ctx_initialized(mock_window):
    """
    Test set_ctx_initialized
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {
        'test_ctx': {
            'initialized': False
        }
    }
    ctx.dump_context = MagicMock()  # prevent dump context
    ctx.set_ctx_initialized()
    assert ctx.contexts['test_ctx']['initialized'] is True
    ctx.dump_context.assert_called_once_with('test_ctx')
    ctx.current_ctx = None
    ctx.set_ctx_initialized()
    ctx.dump_context.assert_called_once_with('test_ctx')


def test_append_thread(mock_window):
    """
    Test append_thread
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.current_thread = 'test_thread'
    ctx.contexts = {
        'test_ctx': {
            'thread': 'test_thread'
        }
    }
    ctx.dump_context = MagicMock()  # prevent dump context
    ctx.append_thread('test_thread')
    assert ctx.contexts['test_ctx']['thread'] == 'test_thread'
    ctx.dump_context.assert_called_once_with('test_ctx')
    ctx.current_ctx = None
    ctx.append_thread('test_thread')
    ctx.dump_context.assert_called_once_with('test_ctx')


def test_append_run(mock_window):
    """
    Test append_run
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.current_run = 'test_run'
    ctx.contexts = {
        'test_ctx': {
            'run': 'test_run'
        }
    }
    ctx.dump_context = MagicMock()  # prevent dump context
    ctx.append_run('test_run')
    assert ctx.contexts['test_ctx']['run'] == 'test_run'
    ctx.dump_context.assert_called_once_with('test_ctx')
    ctx.current_ctx = None
    ctx.append_run('test_run')
    ctx.dump_context.assert_called_once_with('test_ctx')


def test_append_status(mock_window):
    """
    Test append_status
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.current_status = 'test_status'
    ctx.contexts = {
        'test_ctx': {
            'status': 'test_status'
        }
    }
    ctx.dump_context = MagicMock()  # prevent dump context
    ctx.append_status('test_status')
    assert ctx.contexts['test_ctx']['status'] == 'test_status'
    ctx.dump_context.assert_called_once_with('test_ctx')
    ctx.current_ctx = None
    ctx.append_status('test_status')
    ctx.dump_context.assert_called_once_with('test_ctx')


def test_get_list(mock_window):
    """
    Test list
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }
    assert ctx.get_list() == {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }


def test_get_name_by_idx(mock_window):
    """
    Test get_name_by_idx
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }

    # WARNING: list is sorted: get_list() sorts items before returning!
    assert ctx.get_name_by_idx(0) == 'test_ctx20221207'
    assert ctx.get_name_by_idx(1) == 'test_ctx20221204'
    assert ctx.get_name_by_idx(2) is None


def test_get_idx_by_name(mock_window):
    """
    Test get_idx_by_name
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }

    # WARNING: list is sorted: get_list() sorts items before returning!
    assert ctx.get_idx_by_name('test_ctx20221207') == 0
    assert ctx.get_idx_by_name('test_ctx20221204') == 1
    assert ctx.get_idx_by_name('test_ctx20221205') is None


def test_get_first_ctx(mock_window):
    """
    Test get_first_ctx
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }

    # WARNING: list is sorted: get_list() sorts items before returning!
    assert ctx.get_first_ctx() == 'test_ctx20221207'
    ctx.contexts = {}
    assert ctx.get_first_ctx() is None


def test_get_context_by_name(mock_window):
    """
    Test get_context_by_name
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }

    # WARNING: list is sorted: get_list() sorts items before returning!
    assert ctx.get_context_by_name('test_ctx20221207') == {
        'mode': 'test_mode2'
    }
    assert ctx.get_context_by_name('test_ctx20221204') == {
        'mode': 'test_mode'
    }
    assert ctx.get_context_by_name('test_ctx20221205') is None


def test_delete_ctx(mock_window):
    """
    Test delete_ctx
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }
    ctx.dump_context = MagicMock()  # prevent dump context
    ctx.delete_ctx('test_ctx20221207')
    assert ctx.contexts == {
        'test_ctx20221204': {
            'mode': 'test_mode'
        }
    }
    ctx.current_ctx = None
    ctx.delete_ctx('test_ctx20221204')


def test_prepare(mock_window):
    """
    Test prepare
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {}
    ctx.new = MagicMock()  # prevent dump context
    ctx.prepare()
    ctx.new.assert_called_once_with()


def test_get_all_items(mock_window):
    """
    Test get_all_items
    """
    ctx = Context(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.get_all_items() == [
        'item1',
        'item2'
    ]


def test_clear(mock_window):
    """
    Test clear
    """
    ctx = Context(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    ctx.clear()
    assert ctx.items == []


def test_select(mock_window):
    """
    Test select
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx'
    ctx.contexts = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }
    ctx.load = MagicMock()  # prevent load
    ctx.select('test_ctx20221207')
    assert ctx.current_ctx == 'test_ctx20221207'
    ctx.load.assert_called_once_with('test_ctx20221207')


def test_add(mock_window):
    """
    Test add
    """
    ctx = Context(mock_window)
    ctx.items = []
    ctx.store = MagicMock()  # prevent store
    ctx.add('item1')
    assert ctx.items == ['item1']
    ctx.store.assert_called_once_with()


def test_store(mock_window):
    """
    Test store
    """
    ctx = Context(mock_window)
    ctx.current_ctx = 'test_ctx20221204'
    ctx.contexts = {
        'test_ctx20221204': {
            'mode': 'test_mode'
        },
        'test_ctx20221207': {
            'mode': 'test_mode2'
        }
    }
    ctx.dump_context = MagicMock()  # prevent dump context
    ctx.store()
    ctx.dump_context.assert_called_once_with('test_ctx20221204')


def test_get_total_tokens(mock_window):
    """
    Test get_total_tokens
    """
    last_item = ContextItem()
    last_item.total_tokens = 66
    ctx = Context(mock_window)
    ctx.get_last = MagicMock()
    ctx.get_last.return_value = last_item

    assert ctx.get_total_tokens() == 66


def test_count(mock_window):
    """
    Test count
    """
    ctx = Context(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.count() == 2


def test_all(mock_window):
    """
    Test all
    """
    ctx = Context(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.all() == [
        'item1',
        'item2'
    ]


def test_get(mock_window):
    """
    Test get
    """
    ctx = Context(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.get(0) == 'item1'
    assert ctx.get(1) == 'item2'
    assert ctx.get(2) is None


def test_get_last(mock_window):
    """
    Test get_last
    """
    ctx = Context(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    assert ctx.get_last() == 'item2'
    ctx.items = []
    assert ctx.get_last() is None


def test_get_tokens_left(mock_window):
    """
    Test get_tokens_left
    """
    ctx = Context(mock_window)
    ctx.get_total_tokens = MagicMock()
    ctx.get_total_tokens.return_value = 10
    assert ctx.get_tokens_left(20) == 10
    ctx.get_total_tokens.return_value = 20
    assert ctx.get_tokens_left(20) == 0


def test_check(mock_window):
    """
    Test check
    """
    ctx = Context(mock_window)
    ctx.get_tokens_left = MagicMock()
    ctx.get_tokens_left.return_value = 10
    ctx.remove_first = MagicMock()
    ctx.check(5, 20)
    ctx.remove_first.assert_not_called()
    ctx.check(10, 20)
    ctx.remove_first.assert_called_once_with()


def test_remove_last(mock_window):
    """
    Test remove_last
    """
    ctx = Context(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    ctx.remove_last()
    assert ctx.items == [
        'item1'
    ]
    ctx.items = []
    ctx.remove_last()
    assert ctx.items == []


def test_remove_first(mock_window):
    """
    Test remove_first
    """
    ctx = Context(mock_window)
    ctx.items = [
        'item1',
        'item2'
    ]
    ctx.remove_first()
    assert ctx.items == [
        'item2'
    ]
    ctx.items = []
    ctx.remove_first()
    assert ctx.items == []


def test_get_last_tokens(mock_window):
    """
    Test get_last_tokens
    """
    ctx = Context(mock_window)
    ctx.get_last = MagicMock()
    ctx.get_last.return_value = ContextItem()
    ctx.get_last().total_tokens = 10
    assert ctx.get_last_tokens() == 10
    ctx.get_last.return_value = None
    assert ctx.get_last_tokens() == 0