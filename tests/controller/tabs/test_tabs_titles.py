from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from pygpt_net.core.tabs.tab import Tab


def test_reload_titles_delegates_and_debugs(tabs_env):
    tabs = tabs_env.tabs
    tabs.debug = MagicMock()
    tabs.reload_titles()
    tabs_env.core_tabs.reload_titles.assert_called_once_with()
    tabs.debug.assert_called_once_with()


def test_get_current_tab_name_reads_real_tab_widget(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=1, idx=0, column_idx=0, title="Visible")
    tabs_env.install(tab)
    tabs._state.activate(0, 0, 1)
    assert tabs.get_current_tab_name() == "Visible"

    tabs.get_current_tab = MagicMock(return_value=None)
    assert tabs.get_current_tab_name() == ""


def test_get_current_tab_name_for_audio_formats_type_order_and_tooltip(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=2, idx=3, type=Tab.TAB_CHAT, title="T")
    tab.tooltip = "Full"
    tabs.get_current_tab = MagicMock(return_value=tab)
    tabs_env.core_tabs.count_by_type.return_value = 2
    tabs_env.core_tabs.get_order_by_idx_and_type.return_value = 2

    with patch("pygpt_net.controller.tabs.titles.trans", side_effect=lambda key: {"output.tab.chat": "Chat"}.get(key, key)):
        assert tabs.get_current_tab_name_for_audio() == "Chat #2 - Full"

    tabs.get_current_tab.return_value = None
    assert tabs.get_current_tab_name_for_audio() == ""


def test_update_tooltip_targets_current_chat_or_all_matching_context_tabs(tabs_env):
    tabs = tabs_env.tabs
    a = tabs_env.make_tab(pid=3, idx=0, column_idx=0, data_id=7)
    b = tabs_env.make_tab(pid=4, idx=0, column_idx=1, data_id=7)
    tool = tabs_env.make_tab(pid=5, idx=1, column_idx=0, type=Tab.TAB_TOOL, data_id=7)
    tabs_env.install(a, b, tool)
    tabs.debug = MagicMock()
    tabs.get_current_tab = MagicMock(return_value=a)

    tabs.update_tooltip("One")
    assert a.tooltip == "One"
    tabs_env.widgets[0].setTabToolTip.assert_called_with(0, "One")

    tabs_env.widgets[0].setTabToolTip.reset_mock(); tabs_env.widgets[1].setTabToolTip.reset_mock()
    tabs.update_tooltip("Both", meta_id=7)
    assert a.tooltip == "Both" and b.tooltip == "Both"
    tabs_env.widgets[0].setTabToolTip.assert_called_with(0, "Both")
    tabs_env.widgets[1].setTabToolTip.assert_called_with(0, "Both")
    tabs.debug.assert_called()


def test_rename_dialog_uses_pid_as_stable_identity(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=99, idx=2, column_idx=1, title="Old")
    tabs_env.core_tabs.get_tab_by_index.side_effect = lambda idx, col: tab if (idx, col) == (2, 1) else None
    dialog = tabs_env.window.ui.dialog["rename"]

    tabs.rename(2, 1)

    assert dialog.id == "tab.pid"
    assert dialog.current == 99
    dialog.input.setText.assert_called_once_with("Old")
    dialog.show.assert_called_once_with()


def test_update_name_nonempty_sets_custom_metadata_saves_and_closes(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=6, idx=0, column_idx=0)
    tabs_env.install(tab)
    tabs_env.core_tabs.update_title.return_value = True
    tabs.debug = MagicMock()

    assert tabs.update_name(0, "Mine", close=True, column_idx=0) is True

    tabs_env.core_tabs.update_title.assert_called_once_with(
        0,
        "Mine",
        "Mine",
        column_idx=0,
        custom_name=True,
        title_source="custom",
    )
    tabs_env.core_tabs.save.assert_called_once_with()
    tabs_env.window.ui.dialog["rename"].close.assert_called_once_with()
    tabs.debug.assert_called_once_with()


def test_update_name_empty_chat_clears_custom_and_restores_context_title(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=7, idx=0, column_idx=0, data_id=70, title="Custom")
    tab.custom_name = True
    tab.title_source = "custom"
    tabs_env.install(tab)
    meta = SimpleNamespace(id=70, name="Context")
    tabs_env.core_ctx.get_meta_by_id.return_value = meta
    tabs.update_title_by_tab = MagicMock(return_value=True)

    assert tabs.update_name(0, "   ", close=False, column_idx=0) is True
    tabs.update_title_by_tab.assert_called_once_with(tab, "Context", force=True)
    tabs_env.core_tabs.update_title.assert_not_called()
    tabs_env.core_tabs.save.assert_called_once_with()
    tabs_env.window.ui.dialog["rename"].close.assert_not_called()


def test_update_name_empty_unbound_chat_restores_default_title(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=8, idx=0, column_idx=0, data_id=None, title="Custom")
    tabs_env.install(tab)
    tabs._reset_unbound_chat_title = MagicMock(return_value=True)

    assert tabs.update_name(0, "", column_idx=0) is True
    tabs._reset_unbound_chat_title.assert_called_once_with(tab, force=True)


def test_update_name_by_pid_and_update_current_name_use_stable_tab_identity(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=9, idx=2, column_idx=1)
    tabs_env.install(tab)
    tabs.update_name = MagicMock(return_value=True)

    assert tabs.update_name_by_pid(9, "X", close=False) is True
    tabs.update_name.assert_called_once_with(2, "X", False, column_idx=1)

    tabs.update_name.reset_mock()
    tabs.get_current_tab = MagicMock(return_value=tab)
    tabs.update_name_by_pid = MagicMock(return_value=True)
    assert tabs.update_current_name("Y") is True
    tabs.update_name_by_pid.assert_called_once_with(9, "Y")



def test_update_name_by_pid_returns_false_when_tab_missing(tabs_env):
    tabs = tabs_env.tabs
    tabs_env.core_tabs.get_tab_by_pid.side_effect = lambda _pid: None
    assert tabs.update_name_by_pid(404, "X") is False


def test_update_current_name_returns_false_without_current_tab(tabs_env):
    tabs = tabs_env.tabs
    tabs.get_current_tab = MagicMock(return_value=None)
    assert tabs.update_current_name("X") is False


def test_format_tab_title_preserves_tooltip_and_truncates_display(tabs_env):
    tabs = tabs_env.tabs
    short = "abc"
    assert tabs._format_tab_title(short) == (short, short)
    long = "x" * (tabs.TAB_CHAT_MAX_CHARS + 5)
    display, tooltip = tabs._format_tab_title(long)
    assert display == "x" * tabs.TAB_CHAT_MAX_CHARS + "..."
    assert tooltip == long
    assert tabs._format_tab_title(None) == ("", "")


def test_legacy_chat_title_is_automatic_recognizes_context_placeholder_and_default(tabs_env):
    tabs = tabs_env.tabs
    meta = SimpleNamespace(name="Long Context Name")
    tab = tabs_env.make_tab(title="Long Context Name")
    tab.tooltip = "Long Context Name"
    with patch("pygpt_net.controller.tabs.titles.trans", side_effect=lambda key: {
        "ctx.new.prefix": "New",
        "output.tab.chat": "Chat",
    }.get(key, key)):
        assert tabs._legacy_chat_title_is_automatic(tab, meta) is True
        tab.title = "..."; tab.tooltip = "..."
        assert tabs._legacy_chat_title_is_automatic(tab, meta) is True
        tab.title = "Chat #2"; tab.tooltip = "other"
        assert tabs._legacy_chat_title_is_automatic(tab, meta) is True
        tab.title = "My custom"; tab.tooltip = "custom"
        assert tabs._legacy_chat_title_is_automatic(tab, meta) is False


def test_update_title_only_targets_chat_in_active_column(tabs_env):
    tabs = tabs_env.tabs
    chat = tabs_env.make_tab(pid=10, idx=0, column_idx=1, type=Tab.TAB_CHAT)
    tabs.set_current_column_idx(1)
    tabs_env.core_tabs.get_tab_by_index.side_effect = lambda idx, col: chat if (idx, col) == (0, 1) else None
    tabs.update_title_by_tab = MagicMock(return_value=True)
    assert tabs.update_title(0, "Title") is True
    tabs.update_title_by_tab.assert_called_once_with(chat, "Title")

    chat.type = Tab.TAB_NOTEPAD
    assert tabs.update_title(0, "No") is False


def test_update_title_by_tab_respects_custom_name_and_writes_automatic_metadata(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=11, idx=0, column_idx=0, type=Tab.TAB_CHAT, title="Old")
    tabs_env.install(tab)
    tabs.debug = MagicMock()

    tab.custom_name = True
    assert tabs.update_title_by_tab(tab, "Context") is False
    tabs_env.widgets[0].setTabText.assert_not_called()

    assert tabs.update_title_by_tab(tab, "Context", force=True) is True
    assert tab.title == "Context"
    assert tab.tooltip == "Context"
    assert tab.custom_name is False
    assert tab.title_source == "context"
    tabs_env.widgets[0].setTabText.assert_called_once_with(0, "Context")
    tabs_env.widgets[0].setTabToolTip.assert_called_once_with(0, "Context")
    tabs.debug.assert_called_once_with()


def test_update_title_by_tab_uses_auto_source_for_tool(tabs_env):
    tabs = tabs_env.tabs
    tool = tabs_env.make_tab(pid=12, idx=0, column_idx=0, type=Tab.TAB_TOOL)
    tabs_env.install(tool)
    assert tabs.update_title_by_tab(tool, "Dynamic") is True
    assert tool.title_source == "auto"


def test_set_chat_placeholder_keeps_tab_noncustom_and_updates_widget(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=13, idx=0, column_idx=0, type=Tab.TAB_CHAT, title="Old")
    tab.custom_name = True
    tab.title_source = "custom"
    tabs_env.install(tab)

    assert tabs.set_chat_placeholder(tab) is True
    assert (tab.title, tab.tooltip, tab.custom_name, tab.title_source) == ("...", "...", False, "default")
    tabs_env.widgets[0].setTabText.assert_called_once_with(0, "...")
    tabs_env.widgets[0].setTabToolTip.assert_called_once_with(0, "...")
    assert tabs.set_chat_placeholder(tabs_env.make_tab(type=Tab.TAB_TOOL)) is False


def test_reset_unbound_chat_title_respects_custom_unless_forced(tabs_env):
    tabs = tabs_env.tabs
    tab = tabs_env.make_tab(pid=14, idx=0, column_idx=0, type=Tab.TAB_CHAT, title="Mine")
    tab.custom_name = True
    tab.title_source = "custom"
    tabs_env.install(tab)
    with patch("pygpt_net.controller.tabs.titles.trans", return_value="Chat"):
        assert tabs._reset_unbound_chat_title(tab) is False
        assert tabs._reset_unbound_chat_title(tab, force=True) is True
    assert (tab.title, tab.tooltip, tab.custom_name, tab.title_source) == ("Chat", "Chat", False, "default")


def test_sync_chat_titles_updates_automatic_skips_custom_and_detaches_stale(tabs_env):
    tabs = tabs_env.tabs
    auto = tabs_env.make_tab(pid=20, idx=0, column_idx=0, data_id=1, title="Old")
    auto.title_source = "context"
    custom = tabs_env.make_tab(pid=21, idx=1, column_idx=0, data_id=2, title="Mine")
    custom.custom_name = True; custom.title_source = "custom"
    stale = tabs_env.make_tab(pid=22, idx=0, column_idx=1, data_id=3, title="Stale")
    stale.title_source = "context"
    tabs_env.install(auto, custom, stale)

    metas = {
        1: SimpleNamespace(id=1, name="New Auto"),
        2: SimpleNamespace(id=2, name="New Custom"),
    }
    tabs_env.core_ctx.get_meta_by_id.side_effect = lambda meta_id: metas.get(meta_id)
    tabs.update_title_by_tab = MagicMock(return_value=True)
    tabs._reset_unbound_chat_title = MagicMock(return_value=True)

    assert tabs.sync_chat_titles() is True

    tabs.update_title_by_tab.assert_called_once_with(auto, "New Auto")
    assert stale.data_id is None
    assert stale.loaded is False
    tabs_env.output.remove_pid.assert_called_once_with(22)
    tabs._reset_unbound_chat_title.assert_called_once_with(stale)


def test_sync_chat_titles_migrates_legacy_automatic_and_preserves_legacy_custom(tabs_env):
    tabs = tabs_env.tabs
    auto = tabs_env.make_tab(pid=30, idx=0, column_idx=0, data_id=1, title="Ctx")
    auto.custom_name = True; auto.title_source = None; auto.tooltip = "Ctx"
    custom = tabs_env.make_tab(pid=31, idx=1, column_idx=0, data_id=2, title="Mine")
    custom.custom_name = True; custom.title_source = None; custom.tooltip = "Mine"
    tabs_env.install(auto, custom)
    tabs_env.core_ctx.get_meta_by_id.side_effect = lambda meta_id: SimpleNamespace(id=meta_id, name="Ctx" if meta_id == 1 else "Different")
    tabs.update_title_by_tab = MagicMock(return_value=False)

    with patch.object(tabs, "_legacy_chat_title_is_automatic", side_effect=[True, False]):
        assert tabs.sync_chat_titles() is True

    assert auto.custom_name is False and auto.title_source == "context"
    assert custom.custom_name is True and custom.title_source == "custom"


def test_sync_chat_titles_specific_meta_does_not_detach_missing_other_context(tabs_env):
    tabs = tabs_env.tabs
    stale = tabs_env.make_tab(pid=32, idx=0, column_idx=0, data_id=3)
    tabs_env.install(stale)
    tabs_env.core_ctx.get_meta_by_id.return_value = None
    assert tabs.sync_chat_titles(meta_id=3) is False
    assert stale.data_id == 3


def test_update_title_current_only_applies_to_current_chat(tabs_env):
    tabs = tabs_env.tabs
    chat = tabs_env.make_tab(pid=40, type=Tab.TAB_CHAT)
    tabs.get_current_tab = MagicMock(return_value=chat)
    tabs.update_title_by_tab = MagicMock(return_value=True)
    assert tabs.update_title_current("X") is True
    tabs.update_title_by_tab.assert_called_once_with(chat, "X")

    tabs.get_current_tab.return_value = tabs_env.make_tab(type=Tab.TAB_NOTEPAD)
    assert tabs.update_title_current("Y") is False
