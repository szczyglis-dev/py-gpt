import pytest

from pygpt_net.core.text.mentions import KIND_FILE_CONTEXT
from pygpt_net.ui.widget.textarea.mention import MentionEntry, MentionPopup


@pytest.mark.parametrize('query, expected', [
    ('', ['folder/deeper/other.txt', 'folder/note.txt', 'root.txt']),
    ('folder/', ['folder/deeper/other.txt', 'folder/note.txt']),
    ('folder\\', ['folder/deeper/other.txt', 'folder/note.txt']),
    ('note', ['folder/note.txt']),
    ('folder/deeper/', ['folder/deeper/other.txt']),
])
def test_workdir_lists_files_with_paths_and_never_directory_rows(monkeypatch, query, expected):
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    popup = MentionPopup()
    try:
        popup.set_entries([
            MentionEntry(KIND_FILE_CONTEXT, 'folder/', '%workdir%/data/folder/', True),
            MentionEntry(KIND_FILE_CONTEXT, 'folder/deeper/', '%workdir%/data/folder/deeper/', True),
            MentionEntry(KIND_FILE_CONTEXT, 'folder/note.txt', '%workdir%/data/folder/note.txt'),
            MentionEntry(KIND_FILE_CONTEXT, 'folder/deeper/other.txt', '%workdir%/data/folder/deeper/other.txt'),
            MentionEntry(KIND_FILE_CONTEXT, 'root.txt', '%workdir%/data/root.txt'),
        ])
        popup.apply_filter(query)
        entries = [popup.list.item(i).data(popup.ROLE_ENTRY) for i in range(popup.list.count())]
        files = [entry for entry in entries if entry and entry.kind == KIND_FILE_CONTEXT]
        assert [entry.label for entry in files] == expected
        assert not any(entry.is_dir for entry in files)
    finally:
        popup.close()


@pytest.mark.parametrize('show_filetypes', [True, False])
def test_icons_belong_to_entries_and_filetypes_have_fallback(monkeypatch, show_filetypes):
    from PySide6.QtGui import QIcon
    from pygpt_net.core.text.mentions import KIND_ATTACHMENT, KIND_CONVERSATION
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.WORKDIR_MENTIONS_SHOW_FILETYPE_ICONS', show_filetypes)
    popup = MentionPopup()
    try:
        popup.set_entries([
            MentionEntry(KIND_CONVERSATION, 'Conversation', '123'),
            MentionEntry(KIND_ATTACHMENT, 'Attachment', 'note.txt'),
            MentionEntry(KIND_FILE_CONTEXT, 'known.TXT', '%workdir%/data/known.TXT'),
            MentionEntry(KIND_FILE_CONTEXT, 'unknown.unrecognized', '%workdir%/data/unknown.unrecognized'),
        ])
        icons = {}
        for i in range(popup.list.count()):
            item = popup.list.item(i)
            if item.data(popup.ROLE_HEADER):
                assert item.icon().isNull()
                continue
            entry = item.data(popup.ROLE_ENTRY)
            icons[entry.label if entry.kind == KIND_FILE_CONTEXT else entry.kind] = item.icon()
        expected = {'sketch': ':/icons/brush.svg', 'upload': ':/icons/attachment.svg', KIND_CONVERSATION: ':/icons/chat1.svg', KIND_ATTACHMENT: ':/icons/upload.svg'}
        if show_filetypes:
            expected.update({'known.TXT': ':/filetypes/txt.svg', 'unknown.unrecognized': ':/filetypes/default.svg'})
        else:
            assert icons['known.TXT'].isNull()
            assert icons['unknown.unrecognized'].isNull()
        for key, path in expected.items():
            actual = icons[key].pixmap(16, 16)
            assert not actual.isNull(), path
            assert actual.toImage() == QIcon(path).pixmap(16, 16).toImage()
    finally:
        popup.close()


def test_button_library_limit_preserves_newest_order_only_for_button(monkeypatch):
    from pygpt_net.core.text.mentions import KIND_ATTACHMENT
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.ATTACHMENT_BUTTON_LIBRARY_LIMIT', 2)
    popup = MentionPopup()
    entries = [MentionEntry(KIND_ATTACHMENT, name, name) for name in ('z-new.txt', 'b-middle.txt', 'a-old.txt')]
    def labels():
        return [entry.label for i in range(popup.list.count())
                if (entry := popup.list.item(i).data(popup.ROLE_ENTRY)) and entry.kind == KIND_ATTACHMENT]
    try:
        popup.set_entries(entries, from_attachment_button=True)
        assert labels() == ['z-new.txt', 'b-middle.txt']
        popup.set_entries(entries)
        assert labels() == ['a-old.txt', 'b-middle.txt', 'z-new.txt']
    finally:
        popup.close()


def test_sketch_action_follows_upload_and_keeps_upload_selected(monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    popup = MentionPopup()
    try:
        popup.set_entries([], from_attachment_button=True)
        assert popup.list.item(1).data(popup.ROLE_ENTRY).kind == 'upload'
        assert popup.list.item(2).data(popup.ROLE_ENTRY).kind == 'sketch'
        assert popup.current_entry().kind == 'upload'
    finally:
        popup.close()


def test_registered_readers_have_connect_header_and_configurable_icons(monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    popup = MentionPopup()
    try:
        popup.set_entries([MentionEntry('web_loader', 'Google Drive', 'google_drive'),
                           MentionEntry('web_loader', 'Database', 'database', icon=':/icons/attachment.svg')])
        headers = [popup.list.item(i).text() for i in range(popup.list.count()) if popup.list.item(i).data(popup.ROLE_HEADER)]
        assert headers[-1] == 'input.mentions.connect'
        readers = [popup.list.item(i) for i in range(popup.list.count()) if popup.list.item(i).data(popup.ROLE_ENTRY)
                   and popup.list.item(i).data(popup.ROLE_ENTRY).kind == 'web_loader']
        assert [item.text() for item in readers] == ['Database', 'Google Drive']
        assert all(not item.icon().pixmap(16, 16).isNull() for item in readers)
    finally:
        popup.close()


def test_button_library_paginates_all_attachments_in_batches_of_five(monkeypatch):
    from pygpt_net.core.text.mentions import KIND_ATTACHMENT
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    popup = MentionPopup()
    sources = [MentionEntry(KIND_ATTACHMENT, f'file-{i}', str(i), shared=i % 2 == 0,
                            attachment_id=str(i)) for i in range(12)]
    def entries():
        return [entry for i in range(popup.list.count())
                if (entry := popup.list.item(i).data(popup.ROLE_ENTRY))]
    def load_more():
        row = next(popup.list.item(i) for i in range(popup.list.count())
                   if popup.list.item(i).data(popup.ROLE_ENTRY)
                   and popup.list.item(i).data(popup.ROLE_ENTRY).kind == 'load_more')
        popup._activate_item(row)
    try:
        popup.set_project_state(True, True)
        popup.set_entries(sources, from_attachment_button=True)
        assert [e.value for e in entries() if e.kind == KIND_ATTACHMENT] == [str(i) for i in range(5)]
        more = next(popup.list.item(i) for i in range(popup.list.count())
                    if popup.list.item(i).data(popup.ROLE_ENTRY)
                    and popup.list.item(i).data(popup.ROLE_ENTRY).kind == 'load_more')
        from PySide6.QtCore import Qt
        assert more.textAlignment() == Qt.AlignCenter
        selected = []
        popup.selected.connect(selected.append)
        load_more()
        assert not selected
        assert [e.value for e in entries() if e.kind == KIND_ATTACHMENT] == [str(i) for i in range(10)]
        load_more()
        assert len([e for e in entries() if e.kind == KIND_ATTACHMENT]) == 12
        assert not any(e.kind == 'load_more' for e in entries())
        less = next(popup.list.item(i) for i in range(popup.list.count())
                    if popup.list.item(i).data(popup.ROLE_ENTRY)
                    and popup.list.item(i).data(popup.ROLE_ENTRY).kind == 'show_less')
        assert less.textAlignment() == Qt.AlignCenter
        popup.list.setCurrentItem(less)
        assert popup.choose_current()
        assert not selected
        assert len([e for e in entries() if e.kind == KIND_ATTACHMENT]) == 5
        assert any(e.kind == 'load_more' for e in entries())
        assert not any(e.kind == 'show_less' for e in entries())
        load_more()
        load_more()
        less = next(popup.list.item(i) for i in range(popup.list.count())
                    if popup.list.item(i).data(popup.ROLE_ENTRY)
                    and popup.list.item(i).data(popup.ROLE_ENTRY).kind == 'show_less')
        popup._activate_item(less)
        assert len([e for e in entries() if e.kind == KIND_ATTACHMENT]) == 5
        assert not selected
        popup.set_entries(sources, from_attachment_button=True)
        assert len([e for e in entries() if e.kind == KIND_ATTACHMENT]) == 5
        popup.set_entries(sources)
        assert len([e for e in entries() if e.kind == KIND_ATTACHMENT]) == 12
    finally:
        popup.close()


def test_library_bulk_state_includes_hidden_attachments(monkeypatch):
    from pygpt_net.core.text.mentions import KIND_ATTACHMENT
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    popup = MentionPopup()
    try:
        popup.set_project_state(True, True, library_enabled=False)
        popup.set_entries([MentionEntry(KIND_ATTACHMENT, str(i), str(i),
                                       active=i < 5, attachment_id=str(i)) for i in range(6)],
                          from_attachment_button=True)
        header = next(popup.list.item(i) for i in range(popup.list.count())
                      if popup.list.item(i).data(popup.ROLE_TOGGLE) == 'library')
        assert header.data(popup.ROLE_CHECKED) is False
        changed = []
        popup.library_share_changed.connect(changed.append)
        popup.show()
        click_toggle(popup, popup.list.row(header))
        assert changed == [True]
    finally:
        popup.close()


def click_toggle(popup, row):
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    from pygpt_net.ui.widget.textarea.mention import SharingDelegate
    item = popup.list.item(row)
    point = SharingDelegate.toggle_rect(popup.list.visualItemRect(item)).center()
    QTest.mouseClick(popup.list.viewport(), Qt.LeftButton, pos=point)


def test_empty_library_hides_header_and_sharing_label(monkeypatch):
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    popup = MentionPopup()
    try:
        popup.set_project_state(True, False)
        popup.set_entries([], from_attachment_button=True)
        assert popup.list.item(0).text() == "input.mentions.add_new"
        assert not popup.list.item(0).data(popup.ROLE_SHARING_LABEL)
        assert not any(popup.list.item(i).text() == "input.mentions.library"
                       for i in range(popup.list.count()))
        from pygpt_net.core.text.mentions import KIND_ATTACHMENT
        popup.set_entries([MentionEntry(KIND_ATTACHMENT, "file.txt", "file.txt")],
                          from_attachment_button=True)
        assert popup.list.item(0).data(popup.ROLE_SHARING_LABEL)
        assert any(popup.list.item(i).text() == "input.mentions.library"
                   for i in range(popup.list.count()))
        assert not popup.list.item(0).data(popup.ROLE_TOGGLE)
        assert all(not popup.list.itemWidget(popup.list.item(i)) for i in range(popup.list.count()))
        popup.set_project_state(False, False)
        popup.set_entries([])
        assert not popup.list.item(0).data(popup.ROLE_SHARING_LABEL)
    finally:
        popup.close()


def test_bulk_and_individual_toggles_do_not_select_files_and_include_inactive_rows(monkeypatch):
    from pygpt_net.core.text.mentions import KIND_ATTACHMENT
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    popup = MentionPopup()
    try:
        popup.set_project_state(True, True)
        popup.set_entries([MentionEntry(KIND_ATTACHMENT, "plans.txt", "plan", shared=True,
                                       active=False, attachment_id="source-id")], from_attachment_button=True)
        selected, bulk, individual = [], [], []
        popup.selected.connect(selected.append)
        popup.library_share_changed.connect(bulk.append)
        popup.attachment_share_changed.connect(lambda uid, active: individual.append((uid, active)))
        popup.show()
        library = next(i for i in range(popup.list.count()) if popup.list.item(i).data(popup.ROLE_TOGGLE) == "library")
        source = next(i for i in range(popup.list.count()) if popup.list.item(i).data(popup.ROLE_TOGGLE) == "source-id")
        click_toggle(popup, library)
        click_toggle(popup, source)
        assert bulk == [True] and individual == [("source-id", True)]
        assert selected == [] and popup.isVisible()
        popup.set_project_state(False, False)
        popup.set_entries([MentionEntry(KIND_ATTACHMENT, "plans.txt", "plan", attachment_id="source-id")])
        assert not any(popup.list.item(i).data(popup.ROLE_TOGGLE) for i in range(popup.list.count()))
    finally:
        popup.close()


def test_individual_toggle_rebuild_syncs_library_header_state(monkeypatch):
    from pygpt_net.core.text.mentions import KIND_ATTACHMENT
    monkeypatch.setattr('pygpt_net.ui.widget.textarea.mention.trans', lambda key: key)
    popup = MentionPopup()
    try:
        popup.set_project_state(True, False, library_enabled=True)
        popup.set_entries([MentionEntry(KIND_ATTACHMENT, "plans.txt", "plan", shared=True,
                                       active=True, attachment_id="file")])
        bulk = next(popup.list.item(i) for i in range(popup.list.count())
                    if popup.list.item(i).data(popup.ROLE_TOGGLE) == "library")
        popup.show()
        changes = []
        popup.attachment_share_changed.connect(lambda uid, active: changes.append((uid, active)))
        row = next(i for i in range(popup.list.count()) if popup.list.item(i).data(popup.ROLE_TOGGLE) == "file")
        click_toggle(popup, row)
        assert changes == [("file", False)]
        assert bulk.data(popup.ROLE_CHECKED) is True
        popup.set_project_state(True, False, library_enabled=True)
        popup.set_entries([MentionEntry(KIND_ATTACHMENT, "plans.txt", "plan", shared=True,
                                       active=False, attachment_id="file")])
        bulk = next(popup.list.item(i) for i in range(popup.list.count())
                    if popup.list.item(i).data(popup.ROLE_TOGGLE) == "library")
        assert bulk.data(popup.ROLE_CHECKED) is False
        # All files can be re-enabled even though project sharing is currently off.
        row = next(i for i in range(popup.list.count()) if popup.list.item(i).data(popup.ROLE_TOGGLE) == "file")
        click_toggle(popup, row)
        assert changes[-1] == ("file", True)
    finally:
        popup.close()
