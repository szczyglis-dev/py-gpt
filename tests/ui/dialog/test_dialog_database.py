from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.dialog.db import DataBrowser


def _browser():
    return SimpleNamespace(
        current_offset=0,
        _last_fetch_sig=None,
        _last_count_sig=None,
        _last_columns_sig=None,
        _cached_total_rows=0,
        limit_input=MagicMock(), page_input=MagicMock(), table_select=MagicMock(),
        sort_by_select=MagicMock(), sort_order_select=MagicMock(), search_input=MagicMock(),
        search_column_select=MagicMock(), page_info_label=MagicMock(), prev_button=MagicMock(), next_button=MagicMock(),
        auto_backup_checkbox=MagicMock(),
        window=SimpleNamespace(core=SimpleNamespace(db=MagicMock()), ui=SimpleNamespace(dialogs=MagicMock())),
    )


def test_page_size_defaults_to_100_for_invalid_text():
    b = _browser()
    b.limit_input.text.return_value = "bad"
    assert DataBrowser.get_page_size(b) == 100


def test_limit_change_resets_offset_and_cache():
    b = _browser()
    b.limit_input.text.return_value = "25"
    b.current_offset = 100
    b.update_table_view = MagicMock()
    DataBrowser.on_limit_change(b)
    assert b.current_offset == 0
    assert b._last_fetch_sig is None
    assert b._last_count_sig is None
    b.update_table_view.assert_called_once_with()


def test_invalid_limit_restores_current_page_number():
    b = _browser()
    b.current_offset = 200
    b.limit_input.text.return_value = "0"
    b.get_page_size = MagicMock(return_value=100)
    DataBrowser.on_limit_change(b)
    b.limit_input.setText.assert_called_once_with("3")


def test_page_input_updates_offset_only_inside_range():
    b = _browser()
    b.page_input.text.return_value = "3"
    b.get_page_size = MagicMock(return_value=10)
    b._get_total_rows = MagicMock(return_value=50)
    b.update_table_view = MagicMock()
    DataBrowser.on_page_input_change(b)
    assert b.current_offset == 20
    b.update_table_view.assert_called_once_with()


def test_page_input_restores_current_page_for_out_of_range_value():
    b = _browser()
    b.current_offset = 20
    b.page_input.text.return_value = "99"
    b.get_page_size = MagicMock(return_value=10)
    b._get_total_rows = MagicMock(return_value=30)
    DataBrowser.on_page_input_change(b)
    b.page_input.setText.assert_called_once_with("3")


def test_pagination_info_sets_label_page_and_button_state():
    b = _browser()
    b.current_offset = 20
    b.get_page_size = MagicMock(return_value=10)
    b._get_total_rows = MagicMock(return_value=35)
    DataBrowser.update_pagination_info(b)
    b.page_info_label.setText.assert_called_once_with(" / 4  (35 rows)")
    b.page_input.setText.assert_called_once_with("3")
    b.prev_button.setEnabled.assert_called_once_with(True)
    b.next_button.setEnabled.assert_called_once_with(True)


def test_count_rows_is_cached_by_signature():
    b = _browser()
    b._params_signature_count = MagicMock(return_value=("ctx", "q", None, ()))
    b.get_filters = MagicMock(return_value={})
    b.get_viewer = MagicMock()
    b.get_viewer.return_value.count_rows.return_value = 12

    assert DataBrowser._get_total_rows(b) == 12
    assert DataBrowser._get_total_rows(b) == 12
    b.get_viewer.return_value.count_rows.assert_called_once_with(
        "ctx", search_query="q", search_column=None, filters={},
    )


def test_prev_and_next_page_respect_bounds():
    b = _browser()
    b.current_offset = 20
    b.get_page_size = MagicMock(return_value=10)
    b._get_total_rows = MagicMock(return_value=25)
    b.update_table_view = MagicMock()
    DataBrowser.prev_page(b)
    assert b.current_offset == 10
    DataBrowser.next_page(b)
    assert b.current_offset == 20
    assert b.update_table_view.call_count == 2


def test_force_refresh_invalidates_all_cached_signatures():
    b = _browser()
    b._last_fetch_sig = b._last_count_sig = b._last_columns_sig = object()
    b.update_table_view = MagicMock()
    DataBrowser.force_refresh(b)
    assert b._last_fetch_sig is None
    assert b._last_count_sig is None
    assert b._last_columns_sig is None
    b.update_table_view.assert_called_once_with()
