from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.ui.widget.textarea.input import ChatInput


def _debug_window():
    return SimpleNamespace(core=SimpleNamespace(debug=SimpleNamespace(log=MagicMock())))


def _input(**overrides):
    values = dict(
        _paste_max_chars=1000,
        window=_debug_window(),
    )
    values.update(overrides)
    obj = SimpleNamespace(**values)
    obj._sanitize_text = lambda text: ChatInput._sanitize_text(obj, text)
    return obj


@pytest.mark.parametrize(
    "value, expected",
    [
        ("a\r\nb\rc", "a\nb\nc"),
        ("a\x00b\x7fc", "abc"),
        ("a\x01b\tc\nd", "a b\tc\nd"),
        ("a\u200bb\u202ec\u2066d", "abcd"),
        (123, "123"),
        ("", ""),
        (None, ""),
    ],
)
def test_sanitize_text_normalizes_controls(value, expected):
    assert ChatInput._sanitize_text(_input(), value) == expected


def test_sanitize_text_honors_hard_cap_and_logs_truncation():
    widget = _input(_paste_max_chars=4)
    assert ChatInput._sanitize_text(widget, "abcdef") == "abcd"
    widget.window.core.debug.log.assert_called_once()


def test_sanitize_text_falls_back_to_default_limit_when_limit_is_invalid():
    widget = _input(_paste_max_chars="bad")
    text = "x" * 250001
    out = ChatInput._sanitize_text(widget, text)
    assert len(out) == 250000


@pytest.mark.parametrize("text, urls, image, expected", [
    (True, False, False, True),
    (False, True, False, True),
    (False, False, True, True),
    (False, False, False, False),
])
def test_can_insert_from_mime_data_allows_only_supported_payloads(text, urls, image, expected):
    source = MagicMock()
    source.hasText.return_value = text
    source.hasUrls.return_value = urls
    source.hasImage.return_value = image
    assert ChatInput.canInsertFromMimeData(SimpleNamespace(), source) is expected


def test_can_insert_from_mime_data_rejects_none_and_broken_source():
    assert ChatInput.canInsertFromMimeData(SimpleNamespace(), None) is False
    source = MagicMock()
    source.hasText.side_effect = RuntimeError("broken")
    assert ChatInput.canInsertFromMimeData(SimpleNamespace(), source) is False


def test_mime_has_local_file_urls_detects_any_local_url():
    remote = SimpleNamespace(isLocalFile=lambda: False)
    local = SimpleNamespace(isLocalFile=lambda: True)
    source = MagicMock()
    source.hasUrls.return_value = True
    source.urls.return_value = [remote, local]
    assert ChatInput._mime_has_local_file_urls(SimpleNamespace(), source) is True

    source.urls.return_value = [remote]
    assert ChatInput._mime_has_local_file_urls(SimpleNamespace(), source) is False


def test_safe_text_from_mime_prefers_text_over_urls():
    source = MagicMock()
    source.hasText.return_value = True
    source.text.return_value = " hello\r\nworld "
    widget = _input()
    assert ChatInput._safe_text_from_mime(widget, source) == " hello\nworld "
    source.hasUrls.assert_not_called()


def test_safe_text_from_mime_joins_only_remote_urls():
    local = SimpleNamespace(isLocalFile=lambda: True, toString=lambda: "file:///tmp/a")
    remote = SimpleNamespace(isLocalFile=lambda: False, toString=lambda: "https://example.com")
    source = MagicMock()
    source.hasText.return_value = False
    source.hasUrls.return_value = True
    source.urls.return_value = [local, remote]
    widget = _input()
    assert ChatInput._safe_text_from_mime(widget, source) == "https://example.com"


def test_safe_text_from_mime_logs_failure_and_returns_empty():
    source = MagicMock()
    source.hasText.side_effect = RuntimeError("bad mime")
    widget = _input()
    assert ChatInput._safe_text_from_mime(widget, source) == ""
    widget.window.core.debug.log.assert_called_once()


def test_set_text_top_padding_clamps_negative_and_reapplies_margins():
    widget = SimpleNamespace(_text_top_padding=5, _apply_margins=MagicMock())
    ChatInput.set_text_top_padding(widget, -10)
    assert widget._text_top_padding == 0
    widget._apply_margins.assert_called_once_with()

    ChatInput.set_text_top_padding(widget, "12")
    assert widget._text_top_padding == 12


def _icons_widget():
    left_a, left_b, right = MagicMock(), MagicMock(), MagicMock()
    return SimpleNamespace(
        _icons={"a": left_a, "b": left_b},
        _icons_right={"r": right},
        _icon_meta={"a": {"active": False}, "b": {"active": True}},
        _icon_meta_right={"r": {"active": False}},
        _icon_order=["a", "b"],
        _icon_order_right=["r"],
        _apply_icon_visual=MagicMock(),
        _rebuild_icon_layout=MagicMock(),
        _rebuild_icon_layout_right=MagicMock(),
        _update_icon_bar_geometry=MagicMock(),
        _update_icon_bar_geometry_right=MagicMock(),
        _apply_margins=MagicMock(),
    )


def test_icon_visibility_searches_both_bars():
    widget = _icons_widget()
    widget._icons["a"].isHidden.return_value = False
    widget._icons_right["r"].isHidden.return_value = True
    assert ChatInput.is_icon_visible(widget, "a") is True
    assert ChatInput.is_icon_visible(widget, "r") is False
    assert ChatInput.is_icon_visible(widget, "missing") is False


def test_icon_order_keeps_unlisted_existing_icons_at_end():
    widget = _icons_widget()
    ChatInput.set_icon_order(widget, ["b", "missing", "b"])
    assert widget._icon_order == ["b", "a"]
    widget._rebuild_icon_layout.assert_called_once_with()
    widget._update_icon_bar_geometry.assert_called_once_with()
    widget._apply_margins.assert_called_once_with()


def test_right_icon_order_filters_duplicates_and_unknown_keys():
    widget = _icons_widget()
    widget._icons_right["s"] = MagicMock()
    widget._icon_order_right = ["r", "s"]
    ChatInput.set_right_icon_order(widget, ["s", "unknown", "s"])
    assert widget._icon_order_right == ["s", "r"]
    widget._rebuild_icon_layout_right.assert_called_once_with()


def test_icon_state_accessors_and_toggle_cover_both_bars():
    widget = _icons_widget()
    widget.set_icon_state = MagicMock(side_effect=lambda key, state: ChatInput.set_icon_state(widget, key, state))

    assert ChatInput.get_icon_state(widget, "a") is False
    assert ChatInput.toggle_icon_state(widget, "a") is True
    assert widget._icon_meta["a"]["active"] is True
    assert ChatInput.toggle_icon_state(widget, "r") is True
    assert widget._icon_meta_right["r"]["active"] is True
    assert ChatInput.toggle_icon_state(widget, "missing") is False


def test_set_icon_tooltip_updates_base_or_alt_metadata():
    widget = _icons_widget()
    ChatInput.set_icon_tooltip(widget, "a", "base")
    ChatInput.set_icon_tooltip(widget, "a", "alt", for_alt=True)
    assert widget._icon_meta["a"]["tooltip"] == "base"
    assert widget._icon_meta["a"]["alt_tooltip"] == "alt"
    assert widget._apply_icon_visual.call_count == 2


def test_set_icon_callback_replaces_existing_connections():
    widget = _icons_widget()
    callback = MagicMock()
    ChatInput.set_icon_callback(widget, "a", callback)
    button = widget._icons["a"]
    button.clicked.disconnect.assert_called_once_with()
    button.clicked.connect.assert_called_once_with(callback)


def test_get_icon_button_prefers_left_then_right():
    widget = _icons_widget()
    assert ChatInput.get_icon_button(widget, "a") is widget._icons["a"]
    assert ChatInput.get_icon_button(widget, "r") is widget._icons_right["r"]
    assert ChatInput.get_icon_button(widget, "missing") is None


def test_effective_lines_handles_margin_and_invalid_line_height():
    widget = SimpleNamespace()
    assert ChatInput._effective_lines(widget, 100, 20, 10) == 4.0
    assert ChatInput._effective_lines(widget, 5, 20, 10) == 1.0
    assert ChatInput._effective_lines(widget, 100, 0, 10) == 1.0


def test_should_shrink_to_min_uses_line_spacing_and_document_margin():
    document = SimpleNamespace(documentMargin=lambda: 4.0)
    widget = SimpleNamespace(_line_spacing=lambda: 16, document=lambda: document)
    assert ChatInput._should_shrink_to_min(widget, 28) is True
    assert ChatInput._should_shrink_to_min(widget, 29) is False


def _history_widget(history=None, current="draft", limit=30):
    obj = SimpleNamespace(
        _history=list(history or []),
        _history_limit=limit,
        _history_index=-1,
        _history_active=False,
        _history_saved_current="",
        toPlainText=MagicMock(return_value=current),
        _set_text_and_move_end=MagicMock(),
    )
    obj._history_begin = lambda: ChatInput._history_begin(obj)
    obj._history_end = lambda restore_saved=True: ChatInput._history_end(obj, restore_saved)
    obj._normalize_history_text = lambda text: ChatInput._normalize_history_text(obj, text)
    obj.history_push = lambda text: ChatInput.history_push(obj, text)
    return obj


def test_history_begin_snapshots_current_text_once():
    widget = _history_widget(["one", "two"], current="draft")
    ChatInput._history_begin(widget)
    assert widget._history_active is True
    assert widget._history_saved_current == "draft"
    assert widget._history_index == 2

    widget.toPlainText.return_value = "changed"
    ChatInput._history_begin(widget)
    assert widget._history_saved_current == "draft"


def test_history_navigation_moves_older_then_restores_draft_past_newest():
    widget = _history_widget(["one", "two"], current="draft")
    ChatInput._history_navigate(widget, -1)
    assert widget._history_index == 1
    widget._set_text_and_move_end.assert_called_with("two")

    ChatInput._history_navigate(widget, -1)
    assert widget._history_index == 0
    widget._set_text_and_move_end.assert_called_with("one")

    ChatInput._history_navigate(widget, 1)
    assert widget._history_index == 1
    widget._set_text_and_move_end.assert_called_with("two")

    ChatInput._history_navigate(widget, 1)
    assert widget._history_active is False
    assert widget._history_index == -1
    widget._set_text_and_move_end.assert_called_with("draft")


def test_history_push_trims_deduplicates_and_ignores_empty():
    widget = _history_widget(["one"], limit=3)
    ChatInput.history_push(widget, " one ")
    ChatInput.history_push(widget, "")
    ChatInput.history_push(widget, "two")
    ChatInput.history_push(widget, "three")
    ChatInput.history_push(widget, "four")
    assert widget._history == ["two", "three", "four"]


def test_history_clear_resets_all_navigation_state():
    widget = _history_widget(["one", "two"])
    widget._history_index = 1
    widget._history_active = True
    widget._history_saved_current = "draft"
    ChatInput.history_clear(widget)
    assert widget._history == []
    assert widget._history_index == -1
    assert widget._history_active is False
    assert widget._history_saved_current == ""


def test_effectively_empty_strips_whitespace_and_fails_safe():
    widget = SimpleNamespace(toPlainText=MagicMock(return_value="  \n\t"))
    assert ChatInput._is_effectively_empty(widget) is True
    widget.toPlainText.return_value = "x"
    assert ChatInput._is_effectively_empty(widget) is False
    widget.toPlainText.side_effect = RuntimeError("gone")
    assert ChatInput._is_effectively_empty(widget) is True


@pytest.mark.parametrize('pending_height', [0, 40])
@pytest.mark.parametrize('text, doc_height, current, window_height, expected, fit', [
    ('short draft', 20, 400, 1200, 105, False),
    ('pasted long draft', 900, 150, 1200, 420, False),
    ('pasted long draft', 900, 150, 800, 320, False),
    ('', 20, 400, 1200, 105, False),
    ('remaining text', 160, 400, 1200, 200, True),
    ('long remaining text', 900, 420, 1200, None, True),
])
def test_auto_height_fits_draft_and_caps_growth(text, doc_height, current, window_height, expected, fit, pending_height):
    splitter = MagicMock()
    splitter.sizes.return_value = [1000-current, current]
    container = MagicMock()
    container.height.return_value = current
    container.minimumSizeHint.return_value.height.return_value = 105
    container.minimumHeight.return_value = 0
    widget = SimpleNamespace(
        _auto_updating=False, _splitter_resize_in_progress=False,
        _user_adjusting_splitter=False, _auto_max_ratio=0.4,
        _pending_fit_content=fit,
        window=SimpleNamespace(height=lambda: window_height, ui=SimpleNamespace(nodes={
            "input.pending": SimpleNamespace(active=bool(pending_height), editor_height=current),
        })),
        _get_main_splitter=lambda: splitter,
        _find_container_in_splitter=lambda s: (container, 1),
        hasFocus=lambda: True,
        _document_content_height=lambda: doc_height,
        height=lambda: current,
        viewport=lambda: SimpleNamespace(height=lambda: current-40),
        viewportMargins=lambda: SimpleNamespace(top=lambda: 10, bottom=lambda: 28),
        frameWidth=lambda: 1,
        _min_input_widget_height=lambda h: 105,
        _is_effectively_empty=lambda: not text.strip(),
    )
    ChatInput._update_auto_height(widget, force=fit, minimize_if_single=fit)
    container.setMaximumHeight.assert_called_once_with(max(current if pending_height else 105,
                                                         min(420, int(window_height*.4))))
    if expected is None:
        splitter.setSizes.assert_not_called()
    else:
        target = max(expected, current) if pending_height else expected
        if target == current:
            splitter.setSizes.assert_not_called()
        else:
            assert splitter.setSizes.call_args.args[0][1] == target


def test_completed_mention_does_not_trigger_picker_after_spaces():
    from PySide6.QtWidgets import QApplication, QTextEdit
    from PySide6.QtGui import QTextCharFormat
    app = QApplication.instance() or QApplication([])
    class Editor(QTextEdit):
        MENTION_ID_PROP = ChatInput.MENTION_ID_PROP
        MENTION_KIND_PROP = ChatInput.MENTION_KIND_PROP
        MENTION_VALUE_PROP = ChatInput.MENTION_VALUE_PROP
        MENTION_LABEL_PROP = ChatInput.MENTION_LABEL_PROP
        _collect_mention_groups = ChatInput._collect_mention_groups
        _find_mention_trigger = ChatInput._find_mention_trigger
        _cursor_selected_text = staticmethod(ChatInput._cursor_selected_text)
    editor = Editor()
    cursor = editor.textCursor()
    cursor.insertText('text ')
    fmt = QTextCharFormat()
    fmt.setProperty(editor.MENTION_ID_PROP, 'm1')
    cursor.insertText('@arnie.png', fmt)
    cursor.insertText('  ', QTextCharFormat())
    editor.setTextCursor(cursor)
    assert editor._find_mention_trigger() is None
    cursor.insertText('@', QTextCharFormat())
    editor.setTextCursor(cursor)
    assert editor._find_mention_trigger() is not None
    # Formatting may be cleared; the completed label and separator still
    # terminate the query, including when ordinary text follows it.
    from pygpt_net.ui.widget.textarea.mention import MentionEntry
    editor._mention_entries = [MentionEntry('attachment', 'arnie.png', 'arnie.png')]
    for text in ('text @arnie.png ', 'text @arnie.png xyz', 'text @unknown.bin anything'):
        editor.setPlainText(text)
        cursor = editor.textCursor()
        cursor.movePosition(type(cursor).MoveOperation.End)
        editor.setTextCursor(cursor)
        assert editor._find_mention_trigger() is None


@pytest.mark.parametrize('hide_blacklisted', [True, False])
def test_workdir_mention_blacklist_visibility_flag(tmp_path, monkeypatch, hide_blacklisted):
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.input.WORKDIR_MENTIONS_HIDE_BLACKLISTED', hide_blacklisted)
    (tmp_path / 'nested').mkdir()
    for name in ('note.txt', 'nested/program.EXE', 'nested/private.txt'):
        (tmp_path / name).write_text('text')
    core = MagicMock()
    core.config.get.side_effect = lambda key, default=None: ' .exe, BIN ' if key == 'llama.idx.excluded.ext' else 'chat'
    core.attachments.get_all.return_value = {}
    core.attachments.get_from_meta_ctx.return_value = []
    core.filesystem.get_data_dir.return_value = str(tmp_path)
    core.filesystem.make_local.side_effect = lambda path, ctx=None: path
    core.idx.indexing.is_allowed.side_effect = lambda path: not path.endswith('private.txt')
    widget = SimpleNamespace(window=SimpleNamespace(core=core), MENTION_SCAN_LIMIT=5000)
    entries = ChatInput._build_mention_entries(widget)
    expected = ['note.txt'] if hide_blacklisted else ['note.txt', 'nested/private.txt', 'nested/program.EXE']
    assert [entry.label for entry in entries] == expected
    if not hide_blacklisted:
        core.idx.indexing.is_allowed.assert_not_called()


def test_attachment_button_direct_upload_flag(monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.input.ATTACHMENT_BUTTON_OPEN_MENTIONS', False)
    widget = SimpleNamespace(window=MagicMock())
    ChatInput.action_add_attachment(widget)
    widget.window.controller.attachment.open_add.assert_called_once_with()


def test_attachment_button_popup_defaults_to_upload_without_changing_input(monkeypatch):
    from PySide6.QtWidgets import QTextEdit
    from pygpt_net.ui.widget.textarea.mention import MentionPopup, MentionEntry
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.input.ATTACHMENT_BUTTON_OPEN_MENTIONS', True)
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)

    class Editor(QTextEdit):
        action_add_attachment = ChatInput.action_add_attachment
        _refresh_mention_popup = ChatInput._refresh_mention_popup
        _accept_mention_entry = ChatInput._accept_mention_entry
        def mousePressEvent(self, event):
            ChatInput._dismiss_mention_popup(self)
            super().mousePressEvent(event)

    editor = Editor()
    editor.window = MagicMock()
    editor.window.controller.attachment.open_add.return_value = [
        SimpleNamespace(name='uploaded.txt', path='/tmp/uploaded.txt'),
    ]
    editor._mention_loading = False
    editor._mention_button_cursor = None
    editor._get_mention_source_key = lambda: 'source'
    editor._build_mention_entries = MagicMock(return_value=[])
    editor._get_conversation_mention_entry = lambda query: None
    editor._find_mention_trigger = lambda: None
    editor._mention_popup = MentionPopup(editor)
    editor._mention_popup.selected.connect(editor._accept_mention_entry)
    editor.setPlainText('Existing prompt')
    editor.resize(600, 500)
    from PySide6.QtWidgets import QPushButton
    button = QPushButton('+', editor)
    button.setGeometry(20, 420, 30, 30)
    editor._icons_right = {'attach': button}
    editor.show()
    editor.setFocus()
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()
    try:
        editor.action_add_attachment()
        assert editor._mention_popup.isVisible()
        assert editor._mention_popup.current_entry().kind == 'upload'
        editor._build_mention_entries.assert_called_once_with(include_workdir=False)
        from PySide6.QtCore import QPoint
        assert editor._mention_popup.pos() + QPoint(0, editor._mention_popup.height()) == button.mapToGlobal(QPoint(0, 0))
        assert editor.toPlainText() == 'Existing prompt'
        editor.window.controller.attachment.open_add.assert_not_called()
        editor._mention_popup.choose_current()
        editor.window.controller.attachment.open_add.assert_called_once_with()
        assert editor.toPlainText() == 'Existing prompt'
        assert editor._mention_button_cursor is None
        editor.action_add_attachment()
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        QTest.mouseClick(editor.viewport(), Qt.LeftButton, pos=QPoint(10, 10))
        assert not editor._mention_popup.isVisible()
        editor._refresh_mention_popup()
        assert not editor._mention_popup.isVisible()
    finally:
        editor._mention_popup.close()
        editor.close()



def test_button_mention_entries_do_not_access_workdir():
    core = MagicMock()
    core.attachments.get_all.return_value = {}
    core.attachments.get_from_meta_ctx.return_value = []
    widget = SimpleNamespace(window=SimpleNamespace(core=core))
    assert ChatInput._build_mention_entries(widget, include_workdir=False) == []
    core.filesystem.get_data_dir.assert_not_called()
    core.filesystem.make_local.assert_not_called()
    core.idx.indexing.is_allowed.assert_not_called()


def test_button_library_uses_upload_order_not_filename_or_modification_time():
    core = MagicMock()
    core.attachments.get_all.return_value = {
        'old': SimpleNamespace(name='a-current-old.txt', path='/old', extra={}),
        'new': SimpleNamespace(name='z-current-new.txt', path='/new', extra={}),
    }
    core.attachments.get_from_meta_ctx.return_value = [
        SimpleNamespace(name='a-history-old.txt', path='/history-old', extra={}),
        SimpleNamespace(name='z-history-new.txt', path='/history-new', extra={}),
    ]
    widget = SimpleNamespace(window=SimpleNamespace(core=core))
    entries = ChatInput._build_mention_entries(widget, include_workdir=False)
    assert [entry.label for entry in entries] == [
        'z-current-new.txt', 'a-current-old.txt', 'z-history-new.txt', 'a-history-old.txt',
    ]


def test_sketch_action_opens_painter_via_shared_tab_method():
    from pygpt_net.core.tabs.tab import Tab
    from pygpt_net.ui.widget.textarea.mention import MentionEntry
    widget = SimpleNamespace(window=MagicMock(), _mention_popup=MagicMock())
    ChatInput._accept_mention_entry(widget, MentionEntry('sketch', 'Sketch', ''))
    widget.window.controller.tabs.open_or_activate.assert_called_once_with(Tab.TAB_TOOL, 'painter')
    widget._mention_popup.hide.assert_called_once()
    assert widget._mention_button_cursor is None
    assert widget._mention_dismissed



def test_upload_from_typed_at_still_inserts_mention(monkeypatch):
    from pygpt_net.ui.widget.textarea.mention import MentionEntry
    from pygpt_net.core.text.mentions import KIND_ATTACHMENT
    cursor = MagicMock()
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.input.QTextCursor', MagicMock(return_value=cursor))
    widget = SimpleNamespace(
        _mention_button_cursor=None, _mention_popup=MagicMock(),
        _find_mention_trigger=lambda: (0, 1, ''), window=MagicMock(),
        document=MagicMock(), setTextCursor=MagicMock(), setFocus=MagicMock(),
        _insert_mention_cursor=MagicMock(), _insert_plain_cursor=MagicMock(),
        _refresh_mention_formats=MagicMock(), _schedule_auto_resize=MagicMock(),
    )
    widget.window.controller.attachment.open_add.return_value = [SimpleNamespace(name='uploaded.txt', path='/tmp/uploaded.txt')]
    ChatInput._accept_mention_entry(widget, MentionEntry('upload', 'Files and folders', ''))
    widget._insert_mention_cursor.assert_called_once_with(cursor, MentionEntry(KIND_ATTACHMENT, 'uploaded.txt', 'uploaded.txt'))
    cursor.removeSelectedText.assert_called_once()
