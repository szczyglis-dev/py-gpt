from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.assistant.batch import Batch


def _window():
    window = MagicMock()
    window.core.assistants.items = {}
    return window


def test_assistant_batch_import_requests_confirmation_unless_forced():
    window = _window()
    batch = Batch(window)

    with patch("pygpt_net.controller.assistant.batch.trans", return_value="confirm"):
        batch.import_assistants(force=False)

    window.ui.dialogs.confirm.assert_called_once_with(type="assistant.import", id="", msg="confirm")
    window.core.api.openai.assistants.importer.import_assistants.assert_not_called()

    window.ui.dialogs.confirm.reset_mock()
    batch.import_assistants(force=True)
    window.update_status.assert_called_with("Importing assistants...please wait...")
    window.core.api.openai.assistants.importer.import_assistants.assert_called_once_with()


def test_assistant_batch_handle_imported_refreshes_dependent_controllers():
    window = _window()
    batch = Batch(window)

    with patch("pygpt_net.controller.assistant.batch.trans", return_value="finished"):
        batch.handle_imported_assistants(4)

    window.controller.assistant.update.assert_called_once_with()
    window.controller.remote_store.update.assert_called_once_with()
    window.controller.assistant.files.update.assert_called_once_with()
    window.update_status.assert_called_once_with("OK. Imported assistants: 4.")
    window.ui.dialogs.alert.assert_called_once_with("finished")


def test_assistant_batch_handle_import_failed_logs_error_and_refreshes_assistants():
    window = _window()
    batch = Batch(window)
    error = RuntimeError("api")

    batch.handle_imported_assistants_failed(error)

    window.core.debug.log.assert_called_once_with(error)
    window.controller.assistant.update.assert_called_once_with()
    window.update_status.assert_called_once_with("Error importing assistants.")
    window.ui.dialogs.alert.assert_called_once_with(error)


def test_assistant_batch_remove_store_clears_only_matching_assistants():
    window = _window()
    a = SimpleNamespace(vector_store="store-1")
    b = SimpleNamespace(vector_store="store-2")
    window.core.assistants.items = {"a": a, "b": b, "missing": None}
    window.core.assistants.get_by_id.side_effect = lambda item_id: window.core.assistants.items[item_id]
    batch = Batch(window)

    batch.remove_store_from_assistants("store-1")

    assert a.vector_store is None
    assert b.vector_store == "store-2"
    window.core.assistants.save.assert_called_once_with()
    window.core.remote_store.openai.files.on_store_deleted.assert_called_once_with("store-1")


def test_assistant_batch_remove_all_stores_clears_every_existing_assistant():
    window = _window()
    a = SimpleNamespace(vector_store="store-1")
    b = SimpleNamespace(vector_store="store-2")
    window.core.assistants.items = {"a": a, "b": b}
    window.core.assistants.get_by_id.side_effect = lambda item_id: window.core.assistants.items[item_id]
    batch = Batch(window)

    batch.remove_all_stores_from_assistants()

    assert a.vector_store is None
    assert b.vector_store is None
    window.core.assistants.save.assert_called_once_with()
    window.core.remote_store.openai.files.on_all_stores_deleted.assert_called_once_with()


def test_assistant_batch_status_change_forwards_message_only():
    window = _window()
    batch = Batch(window)

    batch.handle_status_change("busy", "Working")

    window.update_status.assert_called_once_with("Working")
