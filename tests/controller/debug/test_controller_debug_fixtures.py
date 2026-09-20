from unittest.mock import MagicMock, patch

from pygpt_net.controller.debug.fixtures import Fixtures
from pygpt_net.core.types.chunk import ChunkType


def test_debug_fixtures_enable_disable_toggle_and_unknown_names():
    fixtures = Fixtures(MagicMock())

    assert fixtures.is_enabled("stream") is False
    fixtures.enable("stream")
    assert fixtures.is_enabled("stream") is True
    fixtures.toggle("stream")
    assert fixtures.is_enabled("stream") is False
    fixtures.disable("stream")
    assert fixtures.is_enabled("stream") is False

    fixtures.enable("missing")
    fixtures.toggle("missing")
    fixtures.disable("missing")
    assert fixtures.is_enabled("missing") is False


def test_debug_fixtures_toggle_from_menu_updates_stream_and_debug_menu():
    window = MagicMock()
    item = MagicMock()
    window.ui.menu = {"debug.fixtures.stream": item}
    fixtures = Fixtures(window)

    item.isChecked.return_value = True
    fixtures.toggle_from_menu("stream")
    assert fixtures.is_enabled("stream") is True
    window.controller.debug.update.assert_called_once_with()

    window.controller.debug.update.reset_mock()
    item.isChecked.return_value = False
    fixtures.toggle_from_menu("stream")
    assert fixtures.is_enabled("stream") is False
    window.controller.debug.update.assert_called_once_with()


def test_debug_fixtures_toggle_from_menu_ignores_missing_menu_item():
    window = MagicMock()
    window.ui.menu = {}
    fixtures = Fixtures(window)

    fixtures.toggle_from_menu("stream")

    window.controller.debug.update.assert_not_called()


def test_debug_fixtures_get_stream_generator_mocks_external_stream_reader():
    window = MagicMock()
    window.core.config.get_app_path.return_value = "/app"
    ctx = MagicMock()
    stream = MagicMock(name="stream")
    fake = MagicMock()
    fake.stream.return_value = stream
    fixtures = Fixtures(window)

    with patch("pygpt_net.controller.debug.fixtures.os.path.join", return_value="/fixture/fake_stream.txt") as join, \
            patch("pygpt_net.controller.debug.fixtures.FakeOpenAIStream", return_value=fake) as stream_cls:
        result = fixtures.get_stream_generator(ctx)

    assert ctx.chunk_type == ChunkType.API_CHAT
    join.assert_called_once_with("/app", "data", "fixtures", "fake_stream.txt")
    stream_cls.assert_called_once_with(code_path="/fixture/fake_stream.txt")
    fake.stream.assert_called_once_with(api="raw", chunk="code")
    assert result is stream
