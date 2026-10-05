from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.controller.chat.attachment import Attachment
from pygpt_net.core.attachments.context import Context
from pygpt_net.core.text.mentions import KIND_FILE_CONTEXT, make_tag


def setup_context(tmp_path):
    window = MagicMock()
    window.core.filesystem.normalize_local_path.side_effect = lambda path, ctx=None: str(
        tmp_path / path.replace('%workdir%/data/', '')) if path.startswith('%workdir%/data/') else path
    window.core.tokens.from_str.return_value = 3
    window.core.config.get.side_effect = lambda key, default=None: '' if key == 'llama.idx.excluded.ext' else False
    window.core.idx.indexing.is_allowed.return_value = True
    context = Context(window)
    context.get_dir = MagicMock(return_value=str(tmp_path / 'stored'))
    context.is_verbose = lambda: False
    window.core.attachments.context = context
    attachment = Attachment(window)
    window.controller.chat.attachment = attachment
    meta = SimpleNamespace(id=1, group=None, additional_ctx=[], additional_ctx_current=[])
    return window, attachment, meta


def test_workdir_mention_reads_loader_at_send_and_appends_additional_context(tmp_path):
    source = tmp_path / 'note.txt'
    source.write_text('before')
    prompt = 'Read ' + make_tag(KIND_FILE_CONTEXT, '%workdir%/data/note.txt')
    window, attachment, meta = setup_context(tmp_path)
    source.write_text('latest content')
    window.core.idx.indexing.read_text_content.side_effect = lambda path, loader_kwargs: (Path(path).read_text(), [])
    assert attachment.upload_workdir_mentions(meta, prompt)
    assert len(meta.additional_ctx_current) == 1
    assert meta.additional_ctx_current == meta.additional_ctx
    window.core.idx.indexing.read_text_content.assert_called_once()
    ctx = SimpleNamespace(meta=meta)
    output = attachment.get_context(ctx, [], only_current=True)
    assert 'ADDITIONAL CONTEXT FROM ATTACHMENT(s)' in output
    assert 'latest content' in output
    window.core.attachments.native.upload.assert_not_called()


def test_workdir_duplicate_files_loaded_once_and_directories_stay_paths(tmp_path):
    source = tmp_path / 'note.txt'
    source.write_text('text')
    window, attachment, meta = setup_context(tmp_path)
    window.core.idx.indexing.read_text_content.return_value = ('text', [])
    mention = make_tag(KIND_FILE_CONTEXT, '%workdir%/data/note.txt')
    prompt = mention + mention + make_tag(KIND_FILE_CONTEXT, str(tmp_path))
    assert attachment.upload_workdir_mentions(meta, prompt)
    assert len(meta.additional_ctx_current) == 1
    assert not attachment.upload_workdir_mentions(meta, prompt)
    window.core.idx.indexing.read_text_content.assert_called_once()


def test_workdir_path_only_switch_does_not_read_files(tmp_path, monkeypatch):
    window, attachment, meta = setup_context(tmp_path)
    monkeypatch.setattr('pygpt_net.controller.chat.attachment.WORKDIR_MENTIONS_LOAD_CONTEXT', False)
    assert not attachment.upload_workdir_mentions(meta, make_tag(KIND_FILE_CONTEXT, 'missing.txt'))
    window.core.filesystem.normalize_local_path.assert_not_called()
    window.core.idx.indexing.read_text_content.assert_not_called()
    assert meta.additional_ctx == []


def test_missing_workdir_file_keeps_path(tmp_path):
    window, attachment, meta = setup_context(tmp_path)
    prompt = make_tag(KIND_FILE_CONTEXT, '%workdir%/data/missing.txt')
    assert not attachment.upload_workdir_mentions(meta, prompt)
    assert meta.additional_ctx == []
    window.core.idx.indexing.read_text_content.assert_not_called()


@pytest.mark.parametrize('blacklist, allowed', [(' .TXT, exe ', True), ('', False)])
def test_excluded_workdir_files_keep_path_without_reading(tmp_path, blacklist, allowed):
    source = tmp_path / 'note.TXT'
    source.write_text('text')
    window, attachment, meta = setup_context(tmp_path)
    window.core.config.get.side_effect = lambda key, default=None: blacklist if key == 'llama.idx.excluded.ext' else False
    window.core.idx.indexing.is_allowed.return_value = allowed
    prompt = make_tag(KIND_FILE_CONTEXT, str(source))
    assert not attachment.upload_workdir_mentions(meta, prompt)
    window.core.idx.indexing.read_text_content.assert_not_called()
    assert meta.additional_ctx_current == []
    from pygpt_net.core.text.mentions import to_model_text
    assert to_model_text(prompt) == str(source)


@pytest.mark.parametrize('failure', [PermissionError('denied'), ValueError('unsupported'), None])
def test_unreadable_workdir_file_keeps_path_and_next_file_loads(tmp_path, failure):
    first = tmp_path / 'first.txt'
    second = tmp_path / 'second.txt'
    first.write_text('first')
    second.write_text('second')
    window, attachment, meta = setup_context(tmp_path)
    window.core.idx.indexing.read_text_content.side_effect = [failure if failure else ('', []), ('second', [])]
    prompt = make_tag(KIND_FILE_CONTEXT, str(first)) + ' ' + make_tag(KIND_FILE_CONTEXT, str(second))
    assert attachment.upload_workdir_mentions(meta, prompt)
    assert [item['name'] for item in meta.additional_ctx_current] == ['second.txt']
    from pygpt_net.core.text.mentions import to_model_text
    assert to_model_text(prompt) == str(first) + ' ' + str(second)
