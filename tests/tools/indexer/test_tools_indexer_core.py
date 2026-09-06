from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from pygpt_net.tools.indexer.tool import IndexerTool


class _UtcDateTime(datetime):
    @classmethod
    def fromtimestamp(cls, timestamp, tz=None):
        value = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return cls(value.year, value.month, value.day, value.hour, value.minute, value.second, value.microsecond)

    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 6, 12, 34, 56, 123456)


def _tool():
    tool = IndexerTool()
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "llama.idx.list": [{"id": "base"}, {"id": "docs"}],
        "llama.idx.storage": "sqlite",
        "llama.idx.auto": "off",
        "llama.idx.db.last": 0,
    }.get(key, default)
    config.has.return_value = False

    nodes = {
        "tool.indexer.btn.idx": MagicMock(),
        "tool.indexer.idx": MagicMock(),
        "tool.indexer.provider": MagicMock(),
        "tool.indexer.ctx.last_meta_id": MagicMock(),
        "tool.indexer.ctx.last_meta_ts": MagicMock(),
        "tool.indexer.ctx.auto_enabled": MagicMock(),
        "tool.indexer.ctx.last_auto": MagicMock(),
        "tool.indexer.file.loaders": MagicMock(),
        "tool.indexer.browser": MagicMock(),
        "tool.indexer.status": MagicMock(),
        "tool.indexer.file.options.recursive": MagicMock(),
        "tool.indexer.file.options.replace": MagicMock(),
        "tool.indexer.file.options.clear": MagicMock(),
        "tool.indexer.file.path_dir": SimpleNamespace(value="", clear=MagicMock()),
        "tool.indexer.file.path_file": SimpleNamespace(value=[], clear=MagicMock()),
        "tool.indexer.web.loader": MagicMock(),
        "tool.indexer.web.options.replace": MagicMock(),
    }
    indexing = MagicMock()
    db = MagicMock()
    window = SimpleNamespace(
        idx_logger_message=MagicMock(),
        core=SimpleNamespace(
            config=config,
            idx=SimpleNamespace(indexing=indexing, ui=SimpleNamespace(loaders=MagicMock()), remove_doc=MagicMock()),
            db=SimpleNamespace(get_db=MagicMock(return_value=db)),
            debug=MagicMock(),
        ),
        controller=SimpleNamespace(
            settings=MagicMock(),
            idx=SimpleNamespace(indexer=MagicMock()),
            config=SimpleNamespace(placeholder=MagicMock()),
        ),
        ui=SimpleNamespace(nodes=nodes, dialogs=MagicMock(), tabs={"tool.indexer": MagicMock()}),
    )
    tool.window = window
    return tool, db


def test_indexer_defaults_attach_setup_and_open_close():
    tool, _ = _tool()
    assert tool.id == "indexer"
    assert tool.current_idx == "base"

    new_window = MagicMock()
    tool.attach(new_window)
    assert tool.window is new_window

    tool, _ = _tool()
    tool.setup()
    tool.window.idx_logger_message.connect.assert_called_once_with(tool.handle_log)

    tool.refresh = MagicMock(); tool.update = MagicMock()
    tool.open()
    tool.window.ui.dialogs.open.assert_called_once_with("tool.indexer", width=800, height=600)
    assert tool.opened is True
    tool.refresh.assert_called_once_with()

    tool.close()
    tool.window.ui.dialogs.close.assert_called_once_with("tool.indexer")
    assert tool.opened is False


def test_indexer_toggle_settings_show_hide_and_close_state():
    tool, _ = _tool()
    tool.open = MagicMock(); tool.close = MagicMock()
    tool.opened = False
    tool.toggle(); tool.open.assert_called_once_with()
    tool.opened = True; tool.toggle(); tool.close.assert_called_once_with()

    tool.open.reset_mock(); tool.close.reset_mock()
    tool.show_hide(True); tool.show_hide(False)
    tool.open.assert_called_once_with(); tool.close.assert_called_once_with()

    tool.open_settings()
    tool.window.controller.settings.open_section.assert_called_once_with("llama-index")
    tool.opened = True
    tool.on_close()
    assert tool.opened is False


def test_indexer_tab_changed_controls_index_button_and_refreshes():
    tool, _ = _tool()
    tool.refresh = MagicMock()
    button = tool.window.ui.nodes["tool.indexer.btn.idx"]

    tool.on_tab_changed(2)
    button.hide.assert_called_once_with()
    tool.on_tab_changed(1)
    button.show.assert_called_once_with()
    assert tool.refresh.call_count == 2


def test_indexer_set_and_check_current_idx_use_first_configured_fallback():
    tool, _ = _tool()
    tool.refresh = MagicMock()
    tool.set_current_idx("docs", check=False)
    assert tool.current_idx == "docs"
    tool.refresh.assert_called_once_with(False)

    tool.current_idx = "missing"
    tool.check_current_idx()
    assert tool.current_idx == "base"

    tool.current_idx = "-"
    tool.check_current_idx()
    assert tool.current_idx == "-"


def test_indexer_reload_refresh_and_on_reload_delegate_consistently():
    tool, _ = _tool()
    tool.update_tab_web = MagicMock()
    tool.set_current_idx = MagicMock()
    tool.window.controller.config.placeholder.apply_by_id.return_value = ["base", "docs"]

    tool.reload()
    tool.window.core.idx.indexing.reload_loaders.assert_called_once_with()
    tool.update_tab_web.assert_called_once_with()
    tool.window.ui.nodes["tool.indexer.idx"].set_keys.assert_called_once_with(["base", "docs"])
    tool.set_current_idx.assert_called_once_with("base")
    tool.window.ui.nodes["tool.indexer.idx"].set_value.assert_called_once_with("base")

    tool.check_current_idx = MagicMock(); tool.update_tabs = MagicMock()
    tool.refresh(check=True)
    tool.check_current_idx.assert_called_once_with()
    tool.update_tabs.assert_called_once_with()

    with patch.object(tool, "reload") as reload:
        tool.on_reload()
    reload.assert_called_once_with()


def test_indexer_update_tabs_sets_provider_and_delegates_three_tabs():
    tool, _ = _tool()
    tool.update_tab_ctx = MagicMock(); tool.update_tab_files = MagicMock(); tool.update_tab_browse = MagicMock()
    tool.update_tabs()
    tool.window.ui.nodes["tool.indexer.provider"].setText.assert_called_once_with("sqlite")
    tool.update_tab_ctx.assert_called_once_with()
    tool.update_tab_files.assert_called_once_with()
    tool.update_tab_browse.assert_called_once_with()


def test_indexer_update_tab_ctx_formats_timestamps_without_host_timezone_dependency():
    tool, db = _tool()
    conn = db.connect.return_value.__enter__.return_value
    row_meta = MagicMock(); row_meta._asdict.return_value = {"meta_id": 9, "updated_ts": 0}
    row_ts = MagicMock(); row_ts._asdict.return_value = {"meta_id": 10, "updated_ts": 3600}
    conn.execute.return_value.fetchall.side_effect = [[row_meta], [row_ts]]
    tool.window.core.config.has.return_value = True
    tool.window.core.config.get.side_effect = lambda key, default=None: {
        "llama.idx.storage": "sqlite",
        "llama.idx.auto": "projects",
        "llama.idx.db.last": 7200,
    }.get(key, default)

    class _Stmt:
        def bindparams(self, **kwargs):
            return self

    with patch("pygpt_net.tools.indexer.tool.text", side_effect=lambda q: _Stmt()), \
            patch("pygpt_net.tools.indexer.tool.datetime.datetime", _UtcDateTime), \
            patch("pygpt_net.tools.indexer.tool.trans", side_effect=lambda key: key):
        tool.update_tab_ctx()

    tool.window.ui.nodes["tool.indexer.ctx.last_meta_id"].setText.assert_called_once_with("9 (1970-01-01 00:00:00)")
    tool.window.ui.nodes["tool.indexer.ctx.last_meta_ts"].setText.assert_called_once_with("10 (1970-01-01 01:00:00)")
    tool.window.ui.nodes["tool.indexer.ctx.auto_enabled"].setText.assert_called_once_with(
        "tool.indexer.tab.ctx.auto.yes (settings.llama.extra.btn.idx_auto.mode.projects)"
    )
    tool.window.ui.nodes["tool.indexer.ctx.last_auto"].setText.assert_called_once_with("1970-01-01 02:00:00")


def test_indexer_update_tab_ctx_migrates_legacy_boolean_auto_policy():
    tool, db = _tool()
    conn = db.connect.return_value.__enter__.return_value
    conn.execute.return_value.fetchall.side_effect = [[], []]
    tool.window.core.config.get.side_effect = lambda key, default=None: {
        "llama.idx.storage": "sqlite",
        "llama.idx.auto": True,
    }.get(key, default)
    tool.window.core.config.has.return_value = False

    class _Stmt:
        def bindparams(self, **kwargs): return self

    with patch("pygpt_net.tools.indexer.tool.text", side_effect=lambda q: _Stmt()), \
            patch("pygpt_net.tools.indexer.tool.trans", side_effect=lambda key: key):
        tool.update_tab_ctx()

    tool.window.ui.nodes["tool.indexer.ctx.auto_enabled"].setText.assert_called_once_with(
        "tool.indexer.tab.ctx.auto.yes (settings.llama.extra.btn.idx_auto.mode.all)"
    )


def test_indexer_update_tab_files_collects_file_loader_extensions_sorted():
    tool, _ = _tool()
    tool.window.core.idx.indexing.get_data_providers.return_value = {
        "a": SimpleNamespace(type=["file"], extensions=["pdf", "md"]),
        "b": SimpleNamespace(type=["web"], extensions=["html"]),
    }
    with patch("pygpt_net.tools.indexer.tool.trans", return_value="Loaders"):
        result = tool.update_tab_files()
    assert result == ["md", "pdf", "txt (plain-text files)"]
    tool.window.ui.nodes["tool.indexer.file.loaders"].setText.assert_called_once_with(
        "Loaders: md, pdf, txt (plain-text files)"
    )


def test_indexer_update_tab_browse_delegates_table_refresh():
    tool, _ = _tool()
    tool.update_tab_browse()
    tool.window.ui.nodes["tool.indexer.browser"].update_table_view.assert_called_once_with()


def test_indexer_update_tab_web_serializes_list_dict_scalar_and_logs_bad_values():
    tool, _ = _tool()
    tool.window.core.idx.indexing.get_external_config.return_value = {
        "web": {
            "list": {"type": "list", "value": ["a", "b"]},
            "dict": {"type": "dict", "value": {"x": 1}},
            "str": {"type": "str", "value": 7},
            "none": {"type": "str", "value": None},
        }
    }
    for key in ("list", "dict", "str", "none"):
        tool.window.ui.nodes[f"tool.indexer.web.loader.config.web.{key}"] = MagicMock()

    tool.update_tab_web()

    expected = {"list": "a, b", "dict": '{"x": 1}', "str": "7", "none": ""}
    for key, value in expected.items():
        node = tool.window.ui.nodes[f"tool.indexer.web.loader.config.web.{key}"]
        node.setText.assert_called_once_with(value)
        assert node.value == value


def test_indexer_context_index_actions_delegate_current_idx():
    tool, _ = _tool()
    tool.current_idx = "docs"
    tool.idx_ctx_db_all(); tool.idx_ctx_db_update()
    tool.window.controller.idx.indexer.index_ctx_from_ts.assert_called_once_with("docs", 0)
    tool.window.controller.idx.indexer.index_ctx_current.assert_called_once_with("docs")


def test_indexer_index_data_rejects_placeholder_index_and_routes_tab():
    tool, _ = _tool()
    tool.index_files = MagicMock(); tool.index_web = MagicMock()
    with patch("pygpt_net.tools.indexer.tool.trans", return_value="no idx"):
        for invalid in ("-", None, "_"):
            tool.current_idx = invalid
            tool.index_data()
    assert tool.window.ui.dialogs.alert.call_count == 3
    tool.index_files.assert_not_called(); tool.index_web.assert_not_called()

    tool.current_idx = "base"
    tool.window.ui.tabs["tool.indexer"].currentIndex.return_value = 0
    tool.index_data(force=True)
    tool.index_files.assert_called_once_with(True)
    tool.window.ui.tabs["tool.indexer"].currentIndex.return_value = 1
    tool.index_data(force=False)
    tool.index_web.assert_called_once_with(False)


def test_indexer_index_files_validation_confirmation_and_dispatch():
    tool, _ = _tool()
    nodes = tool.window.ui.nodes
    nodes["tool.indexer.file.options.recursive"].isChecked.return_value = True
    nodes["tool.indexer.file.options.replace"].isChecked.return_value = False

    with patch("pygpt_net.tools.indexer.tool.trans", side_effect=lambda key: key):
        tool.index_files()
    tool.window.ui.dialogs.alert.assert_called_once_with("tool.indexer.alert.no_files")

    tool.window.ui.dialogs.alert.reset_mock()
    nodes["tool.indexer.file.path_dir"].value = "/docs"
    nodes["tool.indexer.file.path_file"].value = ["/a.txt", "/b.pdf"]
    with patch("pygpt_net.tools.indexer.tool.trans", side_effect=lambda key: key):
        tool.index_files(force=False)
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="idx.tool.index", id=0, msg="tool.indexer.confirm.idx")

    tool.index_files(force=True)
    tool.window.controller.idx.indexer.index_paths.assert_called_once_with(
        ["/docs", "/a.txt", "/b.pdf"], "base", False, True
    )


def test_indexer_index_web_validation_confirmation_and_dispatch():
    tool, _ = _tool()
    loader_ui = tool.window.core.idx.ui.loaders
    loader_ui.handle_options.return_value = (False, None, None, None)
    with patch("pygpt_net.tools.indexer.tool.trans", side_effect=lambda key: key):
        tool.index_web()
    tool.window.ui.dialogs.alert.assert_called_once_with("tool.indexer.alert.no_loader")

    tool.window.ui.dialogs.alert.reset_mock()
    loader_ui.handle_options.return_value = (True, "loader", {"url": "x"}, {"depth": 1})
    tool.window.ui.nodes["tool.indexer.web.options.replace"].isChecked.return_value = True
    with patch("pygpt_net.tools.indexer.tool.trans", side_effect=lambda key: key):
        tool.index_web(force=False)
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="idx.tool.index", id=0, msg="tool.indexer.confirm.idx")

    tool.index_web(force=True)
    tool.window.controller.idx.indexer.index_web.assert_called_once_with(
        "base", "loader", {"url": "x"}, {"depth": 1}, True
    )


def test_indexer_finish_files_clears_inputs_conditionally(capsys):
    tool, _ = _tool()
    clear = tool.window.ui.nodes["tool.indexer.file.options.clear"]
    clear.isChecked.return_value = True
    tool.on_finish_files()
    tool.window.ui.nodes["tool.indexer.file.path_file"].clear.assert_called_once_with()
    tool.window.ui.nodes["tool.indexer.file.path_dir"].clear.assert_called_once_with()
    assert "Indexing files finished" in capsys.readouterr().out

    tool.on_finish_web()
    assert "Indexing web finished" in capsys.readouterr().out


def test_indexer_truncate_idx_delegates_clear():
    tool, _ = _tool()
    tool.current_idx = "docs"
    tool.truncate_idx()
    tool.window.controller.idx.indexer.clear.assert_called_once_with("docs")


def test_indexer_delete_db_idx_confirmation_and_forced_delete():
    tool, db = _tool()
    with patch("pygpt_net.tools.indexer.tool.trans", return_value="confirm"):
        tool.delete_db_idx(5)
    tool.window.ui.dialogs.confirm.assert_called_once_with(type="idx.tool.truncate", id=5, msg="confirm")

    tool.window.ui.nodes["tool.indexer.browser"].get_current_table.return_value = "idx_file"
    row = MagicMock(); row._asdict.return_value = {"doc_id": "doc-1"}
    db.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [row]
    tool.refresh = MagicMock()

    class _Stmt:
        def __init__(self, query): self.query = query
        def bindparams(self, **kwargs): return self

    with patch("pygpt_net.tools.indexer.tool.text", side_effect=lambda q: _Stmt(q)):
        tool.delete_db_idx(5, force=True)

    db.begin.return_value.__enter__.return_value.execute.assert_called_once()
    tool.window.core.idx.remove_doc.assert_called_once_with("base", "doc-1")
    tool.refresh.assert_called_once_with()


def test_indexer_delete_db_idx_without_matching_row_does_not_reference_unbound_doc_id():
    tool, db = _tool()
    tool.window.ui.nodes["tool.indexer.browser"].get_current_table.return_value = "idx_file"
    db.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = []
    tool.refresh = MagicMock()

    class _Stmt:
        def __init__(self, query):
            self.query = query

        def bindparams(self, **kwargs):
            return self

    with patch("pygpt_net.tools.indexer.tool.text", side_effect=lambda q: _Stmt(q)):
        tool.delete_db_idx(404, force=True)

    db.begin.return_value.__enter__.return_value.execute.assert_called_once()
    tool.window.core.idx.remove_doc.assert_not_called()
    tool.refresh.assert_called_once_with()


def test_indexer_log_uses_fixed_timestamp_and_cursor_without_local_timezone():
    tool, _ = _tool()
    tool.opened = True
    cursor = MagicMock()
    tool.window.ui.nodes["tool.indexer.status"].textCursor.return_value = cursor

    with patch("pygpt_net.tools.indexer.tool.datetime.datetime", _UtcDateTime):
        tool.log("hello")

    cursor.movePosition.assert_called_once()
    inserted = "".join(c.args[0] for c in cursor.insertText.call_args_list)
    assert inserted == "12:34:56.123456: hello\n"
    tool.window.ui.nodes["tool.indexer.status"].setTextCursor.assert_called_once_with(cursor)


def test_indexer_log_skips_closed_none_and_blank_and_handle_log_delegates():
    tool, _ = _tool()
    tool.log = MagicMock()
    tool.handle_log("x")
    tool.log.assert_called_once_with("x")

    tool.log = IndexerTool.log.__get__(tool, IndexerTool)
    tool.opened = False
    tool.window.ui.nodes["tool.indexer.status"].textCursor.reset_mock()
    tool.log("x"); tool.log(None); tool.log("  ")
    tool.window.ui.nodes["tool.indexer.status"].textCursor.assert_not_called()


def test_indexer_clear_log_tables_setup_dialogs_and_lang_mappings():
    tool, _ = _tool()
    tool.clear_log()
    tool.window.ui.nodes["tool.indexer.status"].clear.assert_called_once_with()

    tables = tool.get_tables()
    assert set(tables) == {"idx_ctx", "idx_file", "idx_external"}
    assert tables["idx_ctx"]["timestamp_columns"] == ["updated_ts"]
    assert tables["idx_file"]["primary_key"] == "id"

    dialog = MagicMock()
    with patch("pygpt_net.tools.indexer.tool.DialogBuilder", return_value=dialog):
        tool.setup_dialogs()
    dialog.setup.assert_called_once_with()
    assert tool.get_lang_mappings() == {
        "menu.text": {"tools.indexer": "tool.indexer"}
    }
