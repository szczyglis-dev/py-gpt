from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from pygpt_net.ui.layout.ctx.ctx_list import CtxList


class _FixedDateTime(datetime):
    fixed_now = datetime(2026, 9, 6, 12, 0, 0)

    @classmethod
    def today(cls):
        return cls.fixed_now

    @classmethod
    def fromtimestamp(cls, timestamp, tz=None):
        # Interpret test timestamps in UTC so assertions do not depend on host TZ.
        return cls.fromisoformat(datetime.fromtimestamp(timestamp, tz=__import__("datetime").timezone.utc).replace(tzinfo=None).isoformat())


def _utc_timestamp(days_ago):
    from datetime import timezone

    dt = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc) - timedelta(days=days_ago)
    return int(dt.timestamp())


def test_convert_date_categories_are_timezone_independent():
    widget = SimpleNamespace()

    with patch("pygpt_net.ui.layout.ctx.ctx_list.datetime", _FixedDateTime), \
            patch("pygpt_net.ui.layout.ctx.ctx_list.trans", side_effect=lambda key: key):
        assert CtxList.convert_date(widget, _utc_timestamp(0)) == "dt.today"
        assert CtxList.convert_date(widget, _utc_timestamp(1)) == "dt.yesterday"
        assert CtxList.convert_date(widget, _utc_timestamp(7)) == "dt.week"
        assert CtxList.convert_date(widget, _utc_timestamp(14)) == "2 dt.weeks"
        assert CtxList.convert_date(widget, _utc_timestamp(29)) == "4 dt.weeks"
        assert CtxList.convert_date(widget, _utc_timestamp(30)) == "dt.month"
        assert CtxList.convert_date(widget, _utc_timestamp(40)) == "dt.month"
        assert CtxList.convert_date(widget, _utc_timestamp(70)) == "2 dt.months"
        assert CtxList.convert_date(widget, _utc_timestamp(370)) == "dt.year"
