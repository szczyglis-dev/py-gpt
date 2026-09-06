from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView

from pygpt_net.tools.indexer.ui.widgets import IdxBrowseList, IdxBrowser


def test_idx_browse_list_adjust_columns_stretches_last_column():
    model = MagicMock(); model.columnCount.return_value = 4
    header = MagicMock()
    widget = SimpleNamespace(model=lambda: model, horizontalHeader=lambda: header)

    IdxBrowseList.adjustColumns(widget)

    header.setSectionResizeMode.assert_called_once_with(3, QHeaderView.Stretch)


def test_idx_browser_tables_filters_names_and_flags():
    indexer = MagicMock()
    indexer.current_idx = "docs"
    indexer.get_tables.return_value = {
        "idx_ctx": {"x": 1},
        "idx_file": {"x": 2},
        "idx_external": {"x": 3},
        "other": {"x": 4},
    }
    window = SimpleNamespace(
        tools=SimpleNamespace(get=MagicMock(return_value=indexer)),
        core=SimpleNamespace(config=MagicMock()),
        ui=SimpleNamespace(nodes={}),
    )
    window.core.config.get.return_value = "sqlite"
    browser = SimpleNamespace(window=window)
    browser.get_tables = lambda: IdxBrowser.get_tables(browser)

    assert IdxBrowser.get_tables(browser) == {
        "idx_ctx": {"x": 1}, "idx_file": {"x": 2}, "idx_external": {"x": 3}
    }
    assert IdxBrowser.get_filters(browser) == {"idx": "docs", "store": "sqlite"}
    assert IdxBrowser.get_table_name(browser, "Files") == "idx_file"
    assert IdxBrowser.get_table_name(browser, "Web") == "idx_external"
    assert IdxBrowser.get_table_name(browser, "Context") == "idx_ctx"
    assert IdxBrowser.get_table_name(browser, "Missing") is None
    assert IdxBrowser.get_table_names(browser) == ["Files", "Web", "Context"]
    assert IdxBrowser.get_default_table(browser) == "idx_file"
    assert IdxBrowser.is_editable(browser) is False
    assert IdxBrowser.is_inline(browser) is True


def test_idx_browser_list_widget_set_and_get():
    window = SimpleNamespace(ui=SimpleNamespace(nodes={}))
    browser = SimpleNamespace(window=window)
    list_widget = object()
    with patch("pygpt_net.tools.indexer.ui.widgets.IdxBrowseList", return_value=list_widget) as cls:
        IdxBrowser.set_list_widget(browser)
    cls.assert_called_once_with(window)
    assert IdxBrowser.get_list_widget(browser) is list_widget


def test_idx_browse_context_menu_copy_and_delete_callbacks():
    parent = MagicMock()
    index = MagicMock(); index.isValid.return_value = True; index.row.return_value = 2
    value_index = MagicMock(); value_index.data.return_value = "copied"
    id_index = MagicMock(); id_index.data.return_value = "41"
    index.sibling.side_effect = lambda row, col: id_index if col == 0 else value_index
    parent.currentIndex.return_value = index

    copy_action = MagicMock(); delete_action = MagicMock()
    callbacks = {}
    copy_action.triggered.connect.side_effect = lambda cb: callbacks.__setitem__("copy", cb)
    delete_action.triggered.connect.side_effect = lambda cb: callbacks.__setitem__("delete", cb)
    menu = MagicMock(); menu.addAction.side_effect = [copy_action, delete_action]
    clipboard = MagicMock()
    indexer = MagicMock()
    widget = SimpleNamespace(window=SimpleNamespace(tools=SimpleNamespace(get=MagicMock(return_value=indexer))))

    with patch("pygpt_net.tools.indexer.ui.widgets.QMenu", return_value=menu), \
            patch("pygpt_net.tools.indexer.ui.widgets.QApplication.clipboard", return_value=clipboard), \
            patch("pygpt_net.tools.indexer.ui.widgets.QCursor.pos", return_value="pos"), \
            patch("pygpt_net.tools.indexer.ui.widgets.trans", side_effect=lambda key: key):
        IdxBrowseList.create_context_menu(widget, parent)
        callbacks["copy"]()
        callbacks["delete"]()

    clipboard.setText.assert_called_once_with("copied")
    indexer.delete_db_idx.assert_called_once_with(41)
    menu.exec_.assert_called_once_with("pos")
