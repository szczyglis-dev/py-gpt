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
