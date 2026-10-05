from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.controller.attachment.attachment import Attachment as AttachmentController
from pygpt_net.controller.chat.attachment import Attachment as ChatAttachment
from pygpt_net.core.attachments.context import Context
from pygpt_net.item.attachment import AttachmentItem


def test_selected_reader_opens_existing_dialog_with_correct_fields():
    window = MagicMock()
    dialog = MagicMock()
    select = MagicMock()
    window.ui.dialog = {'url': dialog}
    window.ui.nodes = {'dialog.url.loader': select}
    ctrl = AttachmentController(window)
    ctrl.open_add_url(loader_id='google_drive')
    select.set_value.assert_called_once_with('google_drive')
    dialog.hook_loader_change.assert_called_once_with(None, 'google_drive', None)
    dialog.show.assert_called_once()
    window.core.idx.indexing.read_web_content.assert_not_called()


def test_dialog_stores_reader_configuration_without_fetching_remote_data():
    window = MagicMock()
    window.ui.dialog = {'url': SimpleNamespace(current='', close=MagicMock())}
    window.ui.nodes = {'dialog.url.loader': MagicMock()}
    window.core.config.get.return_value = 'chat'
    window.core.idx.ui.loaders.handle_options.return_value = (True, 'database', {'query': 'select * from docs'}, {'uri': 'db'})
    provider = SimpleNamespace(name='Database', icon=':/icons/language.svg', get_external_id=lambda args: 'database-source')
    window.core.idx.indexing.get_loader.return_value = provider
    ctrl = AttachmentController(window)
    ctrl.update = MagicMock()
    ctrl.attach_url()
    kwargs = window.core.attachments.new.call_args.kwargs
    assert kwargs['type'] == AttachmentItem.TYPE_URL
    assert kwargs['extra'] == {'loader': 'database', 'loader_name': 'Database', 'loader_icon': ':/icons/language.svg',
                              'input_params': {'query': 'select * from docs'}, 'input_config': {'uri': 'db'}}
    window.core.idx.indexing.read_web_content.assert_not_called()
    ctrl.update.assert_called_once()


def test_web_context_is_read_at_send_and_appended_as_attachment(tmp_path):
    window = MagicMock()
    window.core.config.get.return_value = False
    window.core.tokens.from_str.return_value = 5
    context = Context(window)
    context.is_verbose = lambda: False
    context.get_dir = lambda *args, **kwargs: str(tmp_path / 'context')
    window.core.attachments.context = context
    window.core.idx.indexing.read_web_content.return_value = ('fresh remote context', [])
    ctrl = ChatAttachment(window)
    window.controller.chat.attachment = ctrl
    meta = SimpleNamespace(id=1, group=None, additional_ctx=[], additional_ctx_current=[])
    source = AttachmentItem(name='Database', path='database-source', type=AttachmentItem.TYPE_URL,
                            extra={'loader': 'database', 'input_params': {'query': 'docs'}, 'input_config': {'uri': 'db'}})
    assert ctrl.upload_web(source, meta, 'Question', False, 'chat')
    window.core.idx.indexing.update_loader_args.assert_called_once_with('database', {'uri': 'db'})
    window.core.idx.indexing.read_web_content.assert_called_once_with(url='', type='database', extra_args={'query': 'docs'}, raise_on_error=True)
    output = ctrl.get_context(SimpleNamespace(meta=meta), [], only_current=True)
    assert 'ADDITIONAL CONTEXT' in output and 'fresh remote context' in output
    assert source.consumed
    window.core.attachments.native.upload.assert_not_called()


def test_editing_connection_updates_existing_attachment():
    window = MagicMock()
    source = AttachmentItem(name='old', path='old', type=AttachmentItem.TYPE_URL)
    window.ui.dialog = {'url': SimpleNamespace(current='source', close=MagicMock())}
    window.ui.nodes = {'dialog.url.loader': MagicMock()}
    window.core.attachments.get_all.return_value = {'source': source}
    window.core.config.get.return_value = 'chat'
    window.core.idx.ui.loaders.handle_options.return_value = (True, 'database', {'query': 'new'}, {})
    window.core.idx.indexing.get_loader.return_value = SimpleNamespace(name='Database', icon='', get_external_id=lambda args: 'new-source')
    ctrl = AttachmentController(window)
    ctrl.update = MagicMock()
    ctrl.attach_url()
    assert source.path == 'new-source' and source.extra['input_params'] == {'query': 'new'}
    window.core.attachments.new.assert_not_called()


def test_empty_web_reader_result_does_not_create_url_only_context(tmp_path):
    import pytest
    window = MagicMock()
    window.core.config.get.return_value = False
    context = Context(window)
    context.is_verbose = lambda: False
    context.get_dir = lambda *args, **kwargs: str(tmp_path / 'context')
    window.core.attachments.context = context
    window.core.idx.indexing.read_web_content.return_value = ('', [])
    ctrl = ChatAttachment(window)
    meta = SimpleNamespace(id=1, group=None, additional_ctx=[], additional_ctx_current=[])
    source = AttachmentItem(path='https://youtu.be/F3uvhqiKrcI', type=AttachmentItem.TYPE_URL,
                            extra={'loader': 'youtube', 'input_params': {'url': 'https://youtu.be/F3uvhqiKrcI'}, 'input_config': {}})
    with pytest.raises(ValueError, match='returned no content'):
        ctrl.upload_web(source, meta, 'Question', False, 'chat')
    assert meta.additional_ctx == [] and not source.consumed
