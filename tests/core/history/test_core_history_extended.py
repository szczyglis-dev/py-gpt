import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.core.history.history import History


REAL_DATETIME = datetime.datetime
FIXED_TS = 1_735_689_600


class UtcDateTime(REAL_DATETIME):
    @classmethod
    def fromtimestamp(cls, timestamp, tz=None):
        value = REAL_DATETIME.fromtimestamp(timestamp, tz=datetime.timezone.utc)
        if tz is None:
            return value.replace(tzinfo=None)
        return value.astimezone(tz)


def make_history(tmp_path):
    history_dir = tmp_path / "history"
    history_dir.mkdir()
    config = SimpleNamespace(get_user_dir=MagicMock(return_value=str(history_dir)))
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    history = History(window)
    history.provider = MagicMock()
    return history, history_dir


def test_truncate_delegates_to_provider(tmp_path):
    history, _ = make_history(tmp_path)
    history.truncate()
    history.provider.truncate.assert_called_once_with()


def test_remove_items_uses_input_and_output_timestamps(tmp_path):
    history, _ = make_history(tmp_path)
    history.remove_entry = MagicMock()
    item = SimpleNamespace(input="in", input_timestamp=1_735_689_600, output="out", output_timestamp=1_735_689_601)
    history.remove_items([item])
    assert history.remove_entry.call_args_list == [
        (("in", 1_735_689_600), {}), (("out", 1_735_689_601), {})
    ]


def test_remove_items_returns_when_history_directory_missing(tmp_path):
    history, history_dir = make_history(tmp_path)
    history_dir.rmdir()
    history.remove_entry = MagicMock()
    history.remove_items([SimpleNamespace(input="x", input_timestamp=1, output="y", output_timestamp=2)])
    history.remove_entry.assert_not_called()


def history_path_for_timestamp(history_dir, ts):
    value = REAL_DATETIME.fromtimestamp(ts, tz=datetime.timezone.utc)
    return history_dir / f"{value:%Y_%m_%d}.txt", f"{value:%H:%M:%S}: "


def test_remove_entry_removes_prefixed_line_with_utc_fixed_timestamp(tmp_path):
    history, history_dir = make_history(tmp_path)
    path, prefix = history_path_for_timestamp(history_dir, FIXED_TS)
    path.write_text(f"{prefix}remove me\nkeep me\n", encoding="utf-8")

    with patch("pygpt_net.core.history.history.datetime.datetime", UtcDateTime):
        history.remove_entry("remove me", FIXED_TS)

    assert path.read_text(encoding="utf-8") == "keep me\n"


def test_remove_entry_falls_back_to_unprefixed_and_deletes_empty_file(tmp_path):
    history, history_dir = make_history(tmp_path)
    path, _ = history_path_for_timestamp(history_dir, FIXED_TS)
    path.write_text("remove me\n", encoding="utf-8")

    with patch("pygpt_net.core.history.history.datetime.datetime", UtcDateTime):
        history.remove_entry("remove me", FIXED_TS)

    assert not path.exists()


def test_remove_entry_ignores_blank_or_missing_file(tmp_path):
    history, history_dir = make_history(tmp_path)
    path, _ = history_path_for_timestamp(history_dir, FIXED_TS)

    with patch("pygpt_net.core.history.history.datetime.datetime", UtcDateTime):
        history.remove_entry("", FIXED_TS)
        history.remove_entry(None, FIXED_TS)

    assert not path.exists()
