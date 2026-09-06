from unittest.mock import MagicMock

from pygpt_net.core.idx.types.ctx import Ctx


def test_ctx_delegates_crud_operations_to_provider():
    provider = MagicMock()
    provider.append_ctx_meta.return_value = 11
    provider.is_meta_indexed.return_value = True
    provider.get_ctx_updated_ts.return_value = 123
    provider.get_meta_doc_id.return_value = "doc-1"
    provider.update_ctx_meta.return_value = True
    ctx = Ctx(provider=provider)

    assert ctx.append("store", "idx", 7, "doc-1") == 11
    provider.append_ctx_meta.assert_called_once_with(store_id="store", idx="idx", meta_id=7, doc_id="doc-1")

    assert ctx.exists("store", "idx", 7) is True
    provider.is_meta_indexed.assert_called_once_with(store_id="store", idx="idx", meta_id=7)

    assert ctx.get_updated_ts("store", "idx", 7) == 123
    provider.get_ctx_updated_ts.assert_called_once_with("store", "idx", 7)

    assert ctx.get_doc_id("store", "idx", 7) == "doc-1"
    provider.get_meta_doc_id.assert_called_once_with(store_id="store", idx="idx", meta_id=7)

    assert ctx.update("store", "idx", 7, "doc-2") is True
    provider.update_ctx_meta.assert_called_once_with(store_id="store", idx="idx", meta_id=7, doc_id="doc-2")

    ctx.remove("store", "idx", 7)
    provider.remove_ctx_meta.assert_called_once_with(store_id="store", idx="idx", meta_id=7)

    ctx.truncate("store", "idx")
    provider.truncate_ctx.assert_called_once_with(store_id="store", idx="idx")
