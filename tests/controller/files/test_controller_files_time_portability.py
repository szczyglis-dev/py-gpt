import datetime as dt

from unittest.mock import MagicMock, patch

from pygpt_net.controller.files.files import Files


FIXED_NOW = dt.datetime(2025, 1, 2, 3, 4, 5)


class FixedDateTime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return FIXED_NOW
        return FIXED_NOW.replace(tzinfo=dt.timezone.utc).astimezone(tz)


def test_files_timestamp_prefix_uses_fixed_clock_without_timezone_dependency():
    files = Files(MagicMock())

    with patch("pygpt_net.controller.files.files.datetime.datetime", FixedDateTime):
        assert files.make_ts_prefix() == "2025-01-02_03-04-05"
