from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.sandbox.preparer import BuiltinSandboxPreparer


@pytest.mark.parametrize("manual", [False, True])
def test_finished_closes_loader_and_shows_success_with_environment_path(monkeypatch, manual):
    monkeypatch.setattr(
        "pygpt_net.core.sandbox.preparer.trans", lambda key: "Success! Environment built.")
    window = MagicMock()
    preparer = SimpleNamespace(
        plugin=SimpleNamespace(window=window),
        _request={"manual": manual},
        _close_loader=MagicMock(),
        _finish_state=MagicMock(),
    )
    runtime = SimpleNamespace(venv_root=Path("/tmp/sandbox/python"))

    BuiltinSandboxPreparer._finished(preparer, runtime)

    preparer._close_loader.assert_called_once_with()
    preparer._finish_state.assert_called_once_with()
    message = "Success! Environment built.\n\n/tmp/sandbox/python"
    window.ui.dialogs.alert.assert_called_once_with(message)
    window.update_status.assert_called_once_with(message)
