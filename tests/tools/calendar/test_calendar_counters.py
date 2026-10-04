from types import SimpleNamespace
from unittest.mock import MagicMock
from pygpt_net.tools.calendar.core.counters import Counters


def counters(all_notes=True):
    window = SimpleNamespace(core=SimpleNamespace(config=MagicMock(), ctx=MagicMock()))
    window.core.config.get.return_value = all_notes
    session = SimpleNamespace(window=window, widgets={'select': MagicMock()}, tool=MagicMock())
    return Counters(session), window.core.ctx


def test_counters_include_adjacent_months_across_year_boundary():
    service, ctx = counters()
    ctx.provider.get_ctx_count_by_day.side_effect = [{'2025-12-31': 1}, {'2026-01-01': 2}, {'2026-02-01': 3}]
    assert service.get_counts_around_month(2026, 1) == {
        '2025-12-31': 1, '2026-01-01': 2, '2026-02-01': 3}
    assert [item.kwargs['year'] for item in ctx.provider.get_ctx_count_by_day.call_args_list] == [2025, 2026, 2026]
    assert [item.kwargs['month'] for item in ctx.provider.get_ctx_count_by_day.call_args_list] == [12, 1, 2]


def test_context_counter_filtering_is_shared_with_chat_search():
    service, ctx = counters(False)
    ctx.get_search_string.return_value = 'needle'
    ctx.is_search_content.return_value = True
    ctx.get_parsed_filters.return_value = {'pinned': True}
    service.get_ctx_counters(2026, 9)
    ctx.provider.get_ctx_count_by_day.assert_called_once_with(
        year=2026, month=9, day=None, search_string='needle',
        filters={'pinned': True}, search_content=True)


def test_all_contexts_ignore_chat_search_filters():
    service, ctx = counters(True)
    service.get_ctx_labels_counters(2026, 9)
    ctx.provider.get_ctx_labels_count_by_day.assert_called_once_with(
        year=2026, month=9, day=None, search_string=None, filters=None, search_content=False)
