from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.dialog.remote_store import RemoteStore


def _store():
    controller = MagicMock()
    controller.remote_store.DEFAULT_PROVIDER = "openai"
    return SimpleNamespace(
        dialog_id="remote_store",
        window=SimpleNamespace(
            ui=SimpleNamespace(models={}, nodes={}, config={}, dialog={}),
            core=SimpleNamespace(config=MagicMock()),
            controller=controller,
        ),
    )


def test_update_list_pairs_sets_rows_and_labels():
    s = _store()
    model = MagicMock()
    s.window.ui.models["list"] = model
    RemoteStore.update_list_pairs(s, "list", [("a", "A"), ("b", "B")])
    model.setRowCount.assert_called_once_with(2)
    assert model.setData.call_count == 2


def test_update_list_pairs_ignores_unknown_model():
    s = _store()
    RemoteStore.update_list_pairs(s, "missing", [("a", "A")])


def test_set_current_row_requires_node_and_model():
    s = _store()
    RemoteStore.set_current_row(s, "list", 2)
    node = MagicMock()
    model = MagicMock()
    index = object()
    model.index.return_value = index
    s.window.ui.nodes["list"] = node
    s.window.ui.models["list"] = model
    RemoteStore.set_current_row(s, "list", 2)
    node.setCurrentIndex.assert_called_once_with(index)


def test_set_provider_blocks_signals_while_selecting():
    s = _store()
    combo = MagicMock()
    combo.findData.return_value = 3
    combo.blockSignals.return_value = False
    s.window.ui.nodes["remote_store.provider.combo"] = combo
    RemoteStore.set_provider_in_ui(s, "google")
    combo.setCurrentIndex.assert_called_once_with(3)
    assert combo.blockSignals.call_args_list[0].args == (True,)
    assert combo.blockSignals.call_args_list[-1].args == (False,)


def test_provider_dependent_expire_days_visible_only_for_openai():
    s = _store()
    widget = MagicMock()
    s.window.ui.config = {"remote_store": {"expire_days": widget}}
    RemoteStore.sync_provider_dependent_ui(s, "openai")
    widget.setVisible.assert_called_with(True)
    RemoteStore.sync_provider_dependent_ui(s, "google")
    widget.setVisible.assert_called_with(False)


def test_provider_from_cfg_falls_back_to_default():
    s = _store()
    s.window.core.config.get.return_value = "missing"
    s.window.controller.remote_store.get_provider_keys.return_value = ["openai", "google"]
    assert RemoteStore._provider_from_cfg(s) == "openai"
    s.window.core.config.get.return_value = "google"
    assert RemoteStore._provider_from_cfg(s) == "google"


def test_update_title_only_when_dialog_exists():
    s = _store()
    dlg = MagicMock()
    s.window.ui.dialog["remote_store"] = dlg
    RemoteStore.update_title(s, "Stores")
    dlg.setWindowTitle.assert_called_once_with("Stores")
