from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.ui.dialog.snap import Snap


def test_setup_creates_all_snap_dialogs():
    window = SimpleNamespace(ui=SimpleNamespace(dialog={}))
    camera = MagicMock(); audio_in = MagicMock(); audio_out = MagicMock()
    with patch("pygpt_net.ui.dialog.snap.SnapDialogCamera", return_value=camera) as camera_cls, \
         patch("pygpt_net.ui.dialog.snap.SnapDialogAudioInput", return_value=audio_in) as input_cls, \
         patch("pygpt_net.ui.dialog.snap.SnapDialogAudioOutput", return_value=audio_out) as output_cls:
        Snap(window).setup()
    camera_cls.assert_called_once_with(window)
    input_cls.assert_called_once_with(window)
    output_cls.assert_called_once_with(window)
    assert window.ui.dialog == {
        "snap_camera": camera,
        "snap_audio_input": audio_in,
        "snap_audio_output": audio_out,
    }
