#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.10 00:00:00                  #
# ================================================== #

import importlib
import pytest
from unittest.mock import Mock, MagicMock
import datetime
import os
from types import SimpleNamespace

module = importlib.import_module("pygpt_net.core.idx.indexing")
Indexing = module.Indexing
class DocumentFake:
    def __init__(self, text='', metadata=None):
        self.text = text
        self.metadata = metadata or {}
        self.id_ = f"doc_{abs(hash(text)) % (10**8)}"

class FakeDirectoryReader:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
    def load_data(self):
        return [DocumentFake(text='dirfile', metadata={})]

def make_window(store=None):
    store = {} if store is None else store
    class ConfigFake:
        def __init__(self, s):
            self.s = s
        def get(self, key):
            return self.s.get(key)
        def has(self, key):
            return key in self.s
        def get_user_dir(self, key):
            return self.s.get('user_dir_' + key, '/tmp')
        def is_compiled(self):
            return self.s.get('is_compiled', False)
    config = ConfigFake(store)
    idx = SimpleNamespace()
    idx.log = Mock()
    idx.metadata = SimpleNamespace()
    idx.metadata.append_file_metadata = Mock()
    idx.metadata.append_web_metadata = Mock()
    storage = SimpleNamespace()
    storage.remove_document = Mock()
    storage.get_ctx_idx = Mock(return_value=Mock(insert=Mock(), delete_ref_doc=Mock()))
    storage.store_ctx_idx = Mock()
    idx.storage = storage
    files = SimpleNamespace()
    files.get_id = Mock(return_value='fileid')
    files.exists = Mock(return_value=False)
    files.get_doc_id = Mock(return_value=None)
    idx.files = files
    idx.ctx = SimpleNamespace()
    idx.ctx.exists = Mock(return_value=False)
    idx.ctx.get_doc_id = Mock(return_value=None)
    external = SimpleNamespace()
    external.exists = Mock(return_value=False)
    external.get_doc_id = Mock(return_value=None)
    external.set_indexed = Mock()
    idx.external = external
    llm_ns = SimpleNamespace()
    llm_ns.get_service_context = Mock(return_value=(None, None))
    idx.llm = llm_ns
    idx.get_current_store = Mock(return_value='store_1')
    debug = SimpleNamespace()
    debug.log = Mock()
    platforms = SimpleNamespace()
    platforms.is_snap = Mock(return_value=False)
    packer = SimpleNamespace()
    packer.is_archive = Mock(return_value=False)
    packer.unpack = Mock(return_value=None)
    filesystem = SimpleNamespace()
    filesystem.packer = packer
    db = SimpleNamespace()
    db.get_db = Mock(return_value=None)
    models = SimpleNamespace()
    models.from_defaults = Mock(return_value=SimpleNamespace())
    controller = SimpleNamespace()
    controller.idx = SimpleNamespace()
    controller.idx.is_stopped = Mock(return_value=False)
    core_ctx = SimpleNamespace()
    core_ctx.idx = SimpleNamespace()
    core_ctx.idx.set_meta_as_indexed = Mock()
    window = SimpleNamespace()
    window.core = SimpleNamespace(config=config, idx=idx, debug=debug, platforms=platforms, filesystem=filesystem, db=db, models=models)
    window.controller = controller
    window.core.ctx = core_ctx
    return window

@pytest.fixture
def window():
    return make_window()

@pytest.fixture(autouse=True)
def patch_module(monkeypatch):
    monkeypatch.setattr(module, 'Document', DocumentFake)
    monkeypatch.setattr(module, 'SimpleDirectoryReader', FakeDirectoryReader)
    return None

@pytest.fixture
def indexing(window):
    return Indexing(window=window)

def test_register_loader_file_and_web(monkeypatch, indexing, window):
    loader = SimpleNamespace()
    loader.allow_compiled = False
    loader.id = 'tloader'
    loader.extensions = ['txt']
    loader.type = ['file', 'web']
    loader.attach_window = Mock()
    loader.set_args = Mock()
    loader.instructions = [{'cmd1': 'do1'}]
    loader.init_args = {'k': 'v'}
    loader.args = {}
    loader.init_args_types = {'k': 'str'}
    loader.init_args_labels = {'k': 'lbl'}
    loader.init_args_desc = {'k': 'desc'}
    window.core.config.s = {'is_compiled': False}
    indexing.register_loader(loader)
    assert 'tloader' in indexing.data_providers
    assert indexing.loaders['file']['txt'] is loader
    assert indexing.loaders['web']['tloader'] is loader
    assert indexing.external_instructions.get('cmd1') == 'do1'
    assert 'tloader' in indexing.external_config

def test_register_loader_blocked_on_compiled(indexing, window):
    loader = SimpleNamespace()
    loader.allow_compiled = False
    loader.id = 'block'
    loader.extensions = []
    loader.type = ['file']
    loader.attach_window = Mock()
    window.core.config.s = {'is_compiled': True}
    window.core.platforms.is_snap.return_value = False
    indexing.register_loader(loader)
    window.core.idx.log.assert_called()
    assert loader.id not in indexing.data_providers

def test_get_loader_and_data_providers(indexing):
    dummy = object()
    indexing.data_providers['x'] = dummy
    assert indexing.get_loader('x') is dummy
    assert indexing.get_loader('no') is None
    assert indexing.get_data_providers()['x'] is dummy

def test_update_loader_args_appends_config(monkeypatch, indexing, window):
    loader = SimpleNamespace()
    loader.id = 'webid'
    loader.set_args = Mock()
    loader.init_args_types = {}
    indexing.data_providers[loader.id] = loader
    indexing.loaders['web'][loader.id] = loader
    window.core.config.s = {'llama.hub.loaders.args': []}
    monkeypatch.setattr(module, 'pack_arg', lambda v, t: v)
    indexing.update_loader_args('webid', {'a': '1', 'b': '2'})
    loader.set_args.assert_called()
    cfg = window.core.config.get('llama.hub.loaders.args')
    found = [it for it in cfg if it['loader'] == 'web_webid' and it['name'] in ('a', 'b')]
    assert len(found) == 2

def test_reload_loaders_calls_register(monkeypatch, indexing):
    indexing.data_providers = {'p': object()}
    called = []
    def fake_register(x):
        called.append(x)
    monkeypatch.setattr(indexing, 'register_loader', fake_register)
    indexing.reload_loaders()
    assert len(called) == 1
    window = indexing.window
    window.core.idx.log.assert_called()

def test_external_getters(indexing):
    indexing.external_instructions = {'a': 1}
    indexing.external_config = {'b': 2}
    assert indexing.get_external_instructions() == {'a': 1}
    assert indexing.get_external_config() == {'b': 2}

def test_get_online_loader(window, indexing):
    window.core.config.s = {'llama.hub.loaders': [{'ext': 'jpg,png', 'loader': 'imgloader'}]}
    assert indexing.get_online_loader('jpg') == 'imgloader'
    assert indexing.get_online_loader('txt') is None

def test_get_loader_arguments(monkeypatch, window, indexing):
    window.core.config.s = {'llama.hub.loaders.args': [{'loader': 'file_test', 'name': 'a', 'value': '1'}]}
    monkeypatch.setattr(module, 'parse_args', lambda data: {'a': '1'})
    assert indexing.get_loader_arguments('test', 'file') == {'a': '1'}

def test_is_excluded_and_paths(window, indexing, tmp_path):
    indexing.loaders['file']['md'] = object()
    window.core.config.s = {'llama.idx.excluded.force': False, 'llama.idx.excluded.ext': 'exe,bin', 'user_dir_data': str(tmp_path)}
    assert indexing.is_excluded('md') is False
    assert indexing.is_excluded('exe') is True
    data_dir = window.core.config.get_user_dir('data')
    excluded_path = os.path.join(data_dir, '.interpreter.output.py')
    assert indexing.is_excluded_path(excluded_path) is True
    normal_path = os.path.join(data_dir, 'other.py')
    assert indexing.is_excluded_path(normal_path) is False

def test_is_allowed_dir_and_file(window, indexing, tmp_path):
    d = tmp_path / 'd'
    d.mkdir()
    assert indexing.is_allowed(str(d)) is True
    f = tmp_path / 'f.txt'
    f.write_text('x')
    indexing.loaders['file']['txt'] = object()
    window.core.config.s = {'llama.idx.excluded.force': False}
    assert indexing.is_allowed(str(f)) is True

def test_get_documents_dir_and_file_and_custom(monkeypatch, indexing, tmp_path, window):
    d = tmp_path / 'folder'
    d.mkdir()
    docs = [DocumentFake(text='a', metadata={})]
    monkeypatch.setattr(module, 'SimpleDirectoryReader', lambda *args, **kwargs: SimpleNamespace(load_data=Mock(return_value=docs)))
    res = indexing.get_documents(str(d))
    assert isinstance(res, list) and res[0].text == 'a'
    f = tmp_path / 'file.md'
    f.write_text('x')
    reader_obj = SimpleNamespace(load_data=Mock(return_value=[DocumentFake(text='file', metadata={})]))
    loader = SimpleNamespace()
    loader.get = Mock(return_value=reader_obj)
    indexing.loaders['file']['md'] = loader
    window.core.filesystem.packer.is_archive.return_value = False
    res2 = indexing.get_documents(str(f))
    assert res2[0].text == 'file'
    custom_reader = SimpleNamespace(load_data_custom=Mock(return_value=[DocumentFake(text='custom', metadata={})]))
    loader_custom = SimpleNamespace(get=Mock(return_value=custom_reader))
    indexing.loaders['file']['md'] = loader_custom
    res3 = indexing.get_documents(str(f), loader_kwargs={'opt': 1})
    assert res3[0].text == 'custom'

def test_read_text_and_read_web_content(monkeypatch, indexing):
    docs = [DocumentFake(text='t1'), DocumentFake(text='t2')]
    monkeypatch.setattr(indexing, 'get_documents', Mock(return_value=docs))
    text, docs_out = indexing.read_text_content('p')
    assert 't1' in text and len(docs_out) == 2
    monkeypatch.setattr(indexing, 'read_web', Mock(return_value=docs))
    text2, docs2 = indexing.read_web_content('u')
    assert 't2' in text2 and len(docs2) == 2

def test_read_web_success_and_error(monkeypatch, indexing, window):
    window.core.config.s = {}
    loader_provider = SimpleNamespace(get_external_id=Mock(return_value='uid'), prepare_args=Mock(return_value={'url': 'u'}))
    indexing.data_providers['webtype'] = loader_provider
    loader = SimpleNamespace(get=Mock(return_value=SimpleNamespace(load_data=Mock(return_value=[DocumentFake(text='w')]))))
    indexing.loaders['web']['webtype'] = loader
    docs = indexing.read_web('u', 'webtype', extra_args={})
    assert len(docs) == 1 and docs[0].text == 'w'
    bad_loader = SimpleNamespace(get=Mock(return_value=SimpleNamespace(load_data=Mock(side_effect=Exception('fail')))))
    indexing.loaders['web']['webtype'] = bad_loader
    window.core.debug.log.reset_mock()
    docs2 = indexing.read_web('u', 'webtype', extra_args={})
    assert docs2 == []

def test_prepare_document_sets_last_accessed():
    doc = DocumentFake(text='x', metadata={'creation_date': '2020', 'last_accessed_date': None})
    indexing = Indexing(window=make_window())
    indexing.prepare_document(doc)
    assert doc.metadata['last_accessed_date'] == '2020'

def test_index_files_single_and_error(monkeypatch, tmp_path, window):
    f = tmp_path / 'file.txt'
    f.write_text('x')
    indexing = Indexing(window=window)
    window.core.config.s = {'llama.idx.replace_old': True}
    doc = DocumentFake(text='t', metadata={})
    monkeypatch.setattr(indexing, 'get_documents', Mock(return_value=[doc]))
    fake_index = SimpleNamespace(insert=Mock())
    indexed, errors = indexing.index_files('idx', fake_index, str(f))
    assert str(f) in indexed and errors == []
    def fail_get(path):
        raise Exception('boom')
    monkeypatch.setattr(indexing, 'get_documents', fail_get)
    window.core.debug.log.reset_mock()
    _, errs = indexing.index_files('idx', fake_index, str(f))
    assert errs and 'boom' in errs[0]

def test_index_files_recursive_dir_and_file(monkeypatch, tmp_path, window):
    root = tmp_path / 'root'
    sub = root / 'sub'
    sub.mkdir(parents=True)
    file1 = sub / 'a.txt'
    file1.write_text('x')
    indexing = Indexing(window=window)
    window.core.config.s = {'llama.idx.replace_old': True}
    doc = DocumentFake(text='t', metadata={})
    monkeypatch.setattr(indexing, 'get_documents', Mock(return_value=[doc]))
    fake_index = SimpleNamespace(insert=Mock())
    indexed, errors = indexing.index_files_recursive('idx', fake_index, str(root))
    assert any(str(file1) in k for k in indexed.keys())
    f = tmp_path / 'solo.txt'
    f.write_text('y')
    indexed2, errors2 = indexing.index_files_recursive('idx', fake_index, str(f))
    assert str(f) in indexed2

def test_db_methods_get_data_and_ids(monkeypatch, indexing, window):
    rows = [SimpleNamespace(_asdict=lambda: {'text': 't', 'input_ts': int(datetime.datetime.now().timestamp()), 'meta_id': 1, 'item_id': 2})]
    class Conn:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def execute(self, q):
            return SimpleNamespace(fetchall=lambda: rows)
    dbobj = SimpleNamespace(connect=Mock(return_value=Conn()))
    window.core.db.get_db = Mock(return_value=dbobj)
    docs = indexing.get_db_data_from_ts(0)
    assert isinstance(docs, list) and docs and 'ctx_id' in docs[0].metadata
    rows2 = [SimpleNamespace(_asdict=lambda: {'id': 5})]
    class Conn2:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def execute(self, q):
            return SimpleNamespace(fetchall=lambda: rows2)
    dbobj2 = SimpleNamespace(connect=Mock(return_value=Conn2()))
    window.core.db.get_db = Mock(return_value=dbobj2)
    ids = indexing.get_db_meta_ids_from_ts(0)
    assert ids == [5]
    rows3 = [SimpleNamespace(_asdict=lambda: {'text': 'x', 'input_ts': int(datetime.datetime.now().timestamp()), 'meta_id': 7, 'item_id': 8})]
    class Conn3:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def execute(self, q):
            return SimpleNamespace(fetchall=lambda: rows3)
    dbobj3 = SimpleNamespace(connect=Mock(return_value=Conn3()))
    window.core.db.get_db = Mock(return_value=dbobj3)
    docs2 = indexing.get_db_data_by_id(7, 0)
    assert docs2 and docs2[0].metadata['ctx_id'] == 7

def test_index_db_by_meta_id_and_from_ts(monkeypatch, indexing, window):
    doc = DocumentFake(text='d', metadata={})
    monkeypatch.setattr(indexing, 'get_db_data_by_id', Mock(return_value=[doc]))
    fake_index = SimpleNamespace(insert=Mock())
    window.core.idx.log = Mock()
    window.core.ctx.idx.set_meta_as_indexed = Mock()
    n, errs = indexing.index_db_by_meta_id('idx', fake_index, 1, 0)
    assert n == 1 and errs == []
    monkeypatch.setattr(indexing, 'get_db_meta_ids_from_ts', Mock(return_value=[2,3]))
    monkeypatch.setattr(indexing, 'index_db_by_meta_id', Mock(return_value=(1, [])))
    n2, errs2 = indexing.index_db_from_updated_ts('idx', fake_index, 0)
    assert n2 == 2

def test_index_url_and_index_urls(monkeypatch, indexing, window):
    provider = SimpleNamespace(get_external_id=Mock(return_value='uid'), prepare_args=Mock(return_value={'url':'u'}))
    loader_instance = SimpleNamespace(load_data=Mock(return_value=[DocumentFake(text='wx', metadata={})]))
    loader = SimpleNamespace(get=Mock(return_value=loader_instance))
    indexing.loaders['web']['wtype'] = loader
    indexing.data_providers['wtype'] = provider
    window.core.idx.metadata.append_web_metadata = Mock()
    window.core.idx.external.set_indexed = Mock()
    fake_index = SimpleNamespace(insert=Mock())
    window.core.config.s = {'llama.idx.replace_old': True}
    n, errs = indexing.index_url('idx', fake_index, 'http://x', type='wtype', extra_args=None, is_tmp=False)
    assert n == 1 and errs == []
    monkeypatch.setattr(indexing, 'remove_old_external', Mock(side_effect=Exception('fail')))
    n2, errs2 = indexing.index_url('idx', fake_index, 'http://x', type='wtype', extra_args={}, is_tmp=False)
    assert isinstance(errs2, list)
    monkeypatch.setattr(indexing, 'index_url', Mock(return_value=(1, [])))
    n3, errs3 = indexing.index_urls('idx', fake_index, ['u1', 'u2'], type='wtype')
    assert n3 == 2

def test_remove_old_methods(window, indexing):
    window.core.config.s = {'llama.idx.replace_old': True}
    window.core.idx.ctx.exists = Mock(return_value=True)
    window.core.idx.ctx.get_doc_id = Mock(return_value='doc123')
    window.core.idx.storage.remove_document = Mock()
    assert indexing.remove_old_meta_id('i', 1, force=False) is True
    window.core.idx.files.exists = Mock(return_value=True)
    window.core.idx.files.get_doc_id = Mock(return_value='docf')
    assert indexing.remove_old_file('i', 'fileid', force=False) is True
    window.core.idx.external.exists = Mock(return_value=True)
    window.core.idx.external.get_doc_id = Mock(return_value='doce')
    assert indexing.remove_old_external('i', 'content', 'type', force=False) is True

def test_index_document_calls_insert(monkeypatch, indexing):
    fake_index = SimpleNamespace(insert=Mock())
    monkeypatch.setattr(indexing, 'apply_rate_limit', Mock())
    doc = DocumentFake(text='z')
    indexing.index_document(fake_index, doc)
    fake_index.insert.assert_called_with(document=doc)

def test_index_attachment_and_web(monkeypatch, indexing, window):
    docs = [DocumentFake(text='a'), DocumentFake(text='b')]
    monkeypatch.setattr(indexing, 'get_documents', Mock(return_value=docs))
    window.core.idx.llm.get_service_context = Mock(return_value=(None, None))
    ctx_index = SimpleNamespace(insert=Mock())
    window.core.idx.storage.get_ctx_idx = Mock(return_value=ctx_index)
    ids = indexing.index_attachment('path', 'ipath', model=None, documents=None)
    assert isinstance(ids, list) and len(ids) == 2
    monkeypatch.setattr(indexing, 'get_webtype', Mock(return_value='wtype'))
    monkeypatch.setattr(indexing, 'read_web', Mock(return_value=docs))
    ids2 = indexing.index_attachment_web('http', 'ip2', model=None, documents=None)
    assert len(ids2) == 2

def test_get_webtype_and_remove_attachment(indexing, window):
    loader = SimpleNamespace(is_supported_attachment=Mock(return_value=True))
    indexing.data_providers['custom'] = loader
    t = indexing.get_webtype('http://x')
    assert t == 'custom'
    window.core.models.from_defaults = Mock(return_value=SimpleNamespace())
    window.core.idx.llm.get_service_context = Mock(return_value=(None, None))
    idxobj = SimpleNamespace(delete_ref_doc=Mock())
    window.core.idx.storage.get_ctx_idx = Mock(return_value=idxobj)
    res = indexing.remove_attachment('ip', 'docid')
    assert res is True

def test_apply_rate_limit_sleep_and_no_sleep(monkeypatch, indexing, window):
    window.core.config.s = {}
    indexing.last_call = None
    indexing.window.core.config.s['llama.idx.embeddings.limit.rpm'] = '0'
    indexing.apply_rate_limit()
    indexing.window.core.config.s['llama.idx.embeddings.limit.rpm'] = '2'
    now = datetime.datetime.now()
    indexing.last_call = now - datetime.timedelta(seconds=5)
    slept = {}
    def fake_sleep(sec):
        slept['val'] = sec
    monkeypatch.setattr(module.time, 'sleep', fake_sleep)
    indexing.apply_rate_limit()
    assert 'val' in slept

def test_stop_enabled_and_is_stopped(indexing, window):
    window.core.config.s = {'llama.idx.stop.error': True}
    assert indexing.stop_enabled() is True
    window.controller.idx.is_stopped = Mock(return_value=True)
    assert indexing.is_stopped() is True