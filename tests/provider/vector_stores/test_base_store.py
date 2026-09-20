#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.06 22:00:00                  #
# ================================================== #

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.provider.vector_stores.base import BaseStore


def _window(idx_dir="/tmp/idx"):
    config = SimpleNamespace(get_user_dir=MagicMock(return_value=idx_dir))
    return SimpleNamespace(core=SimpleNamespace(config=config))


def test_init_reads_window_and_initializes_state():
    window = object()

    store = BaseStore(window=window)

    assert store.window is window
    assert store.id is None
    assert store.prefix == ""
    assert store.indexes == {}


def test_attach_replaces_window():
    store = BaseStore(window=object())
    window = object()

    store.attach(window)

    assert store.window is window


def test_index_from_store_forwards_all_arguments():
    store = BaseStore()
    vector_store = object()
    storage_context = object()
    llm = object()
    embed_model = object()
    expected = object()

    with patch(
        "pygpt_net.provider.vector_stores.base.VectorStoreIndex.from_vector_store",
        return_value=expected,
    ) as from_vector_store:
        result = store.index_from_store(
            vector_store,
            storage_context=storage_context,
            llm=llm,
            embed_model=embed_model,
        )

    assert result is expected
    from_vector_store.assert_called_once_with(
        vector_store,
        storage_context=storage_context,
        llm=llm,
        embed_model=embed_model,
    )


def test_index_from_empty_uses_requested_embedding_model():
    store = BaseStore()
    embed_model = object()
    expected = object()

    with patch(
        "pygpt_net.provider.vector_stores.base.VectorStoreIndex",
        return_value=expected,
    ) as index_cls:
        result = store.index_from_empty(embed_model=embed_model)

    assert result is expected
    index_cls.assert_called_once_with([], embed_model=embed_model)


def test_get_path_uses_configured_idx_directory_and_prefix():
    window = _window("/var/lib/pygpt/idx")
    store = BaseStore(window=window)
    store.prefix = "vector-"

    assert store.get_path("abc") == "/var/lib/pygpt/idx/vector-abc"
    window.core.config.get_user_dir.assert_called_once_with("idx")


def test_exists_returns_false_without_id_without_touching_filesystem():
    store = BaseStore(window=_window())

    with patch("pygpt_net.provider.vector_stores.base.os.path.exists") as exists:
        assert store.exists() is False

    exists.assert_not_called()


def test_exists_checks_resolved_path():
    store = BaseStore(window=_window("/indexes"))

    with patch(
        "pygpt_net.provider.vector_stores.base.os.path.exists",
        return_value=True,
    ) as exists:
        assert store.exists("main") is True

    exists.assert_called_once_with("/indexes/main")


def test_create_is_base_noop():
    assert BaseStore().create("test") is None


def test_get_is_base_noop():
    assert BaseStore().get("test") is None


def test_store_is_base_noop():
    assert BaseStore().store("test") is None


def test_remove_clears_cached_index_and_removes_existing_directory():
    store = BaseStore(window=_window("/indexes"))
    store.indexes["main"] = object()

    with (
        patch("pygpt_net.provider.vector_stores.base.os.path.exists", return_value=True),
        patch("pygpt_net.provider.vector_stores.base.shutil.rmtree") as rmtree,
    ):
        assert store.remove("main") is True

    assert store.indexes["main"] is None
    rmtree.assert_called_once_with("/indexes/main")


def test_remove_does_not_create_cache_entry_or_delete_missing_directory():
    store = BaseStore(window=_window("/indexes"))

    with (
        patch("pygpt_net.provider.vector_stores.base.os.path.exists", return_value=False),
        patch("pygpt_net.provider.vector_stores.base.shutil.rmtree") as rmtree,
    ):
        assert store.remove("missing") is True

    assert "missing" not in store.indexes
    rmtree.assert_not_called()


def test_truncate_delegates_to_remove():
    store = BaseStore()
    store.remove = MagicMock(return_value=True)

    assert store.truncate("main") is True
    store.remove.assert_called_once_with("main")


def test_remove_document_uses_mock_embedding_and_persists_updated_index():
    store = BaseStore()
    index = MagicMock()
    store.get = MagicMock(return_value=index)
    store.store = MagicMock()

    with patch("pygpt_net.provider.vector_stores.base.MockEmbedding") as embedding_cls:
        embedding = object()
        embedding_cls.return_value = embedding

        assert store.remove_document("main", "doc-1") is True

    embedding_cls.assert_called_once_with(embed_dim=1)
    store.get.assert_called_once_with("main", embed_model=embedding)
    index.delete_ref_doc.assert_called_once_with("doc-1")
    store.store.assert_called_once_with(id="main", index=index)
