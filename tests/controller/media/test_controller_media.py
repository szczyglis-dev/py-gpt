from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.controller.media.media import Media


def _media():
    window = MagicMock()
    window.ui.config = {
        "global": {
            "img_raw": MagicMock(),
            "img.remix": MagicMock(),
            "video.remix": MagicMock(),
        }
    }
    return Media(window), window


def test_media_setup_applies_persisted_options_and_registers_hooks_once():
    media, window = _media()
    values = {
        "img_raw": True,
        "img.remix": False,
        "video.remix": True,
        "img_variants": 3,
        "img_mode": "video",
        "img_resolution": "512x512",
        "video.aspect_ratio": "9:16",
        "video.resolution": "1080p",
        "video.duration": 12,
    }
    window.core.config.get.side_effect = lambda key, default=None: values.get(key, default)
    window.core.image.get_mode_option.return_value = {"mode": True}
    window.core.image.get_resolution_option.return_value = {"image": True}
    window.core.video.get_aspect_ratio_option.return_value = {"aspect": True}
    window.core.video.get_resolution_option.return_value = {"resolution": True}
    window.core.video.get_duration_option.return_value = {"duration": True}

    media.setup()

    window.ui.config["global"]["img_raw"].setChecked.assert_called_once_with(True)
    window.ui.config["global"]["img.remix"].setChecked.assert_called_once_with(False)
    window.ui.config["global"]["video.remix"].setChecked.assert_called_once_with(True)
    assert window.controller.config.apply_value.call_count == 7
    assert window.ui.add_hook.call_count == 7

    media.initialized = True
    window.ui.add_hook.reset_mock()
    media.setup()
    window.ui.add_hook.assert_not_called()


def test_media_reload_delegates_to_setup():
    media, _ = _media()
    media.setup = MagicMock()

    media.reload()

    media.setup.assert_called_once_with()


@pytest.mark.parametrize(
    "key,value,config_key,expected",
    [
        ("img_resolution", "1024x1024", "img_resolution", "1024x1024"),
        ("img_variants", "4", "img_variants", 4),
        ("img_mode", "video", "img_mode", "video"),
        ("video.aspect_ratio", "16:9", "video.aspect_ratio", "16:9"),
        ("video.resolution", "720p", "video.resolution", "720p"),
        ("video.duration", 8, "video.duration", 8),
    ],
)
def test_media_hook_update_persists_supported_values(key, value, config_key, expected):
    media, window = _media()

    media.hook_update(key, value, None)

    window.core.config.set.assert_called_once_with(config_key, expected)
    if key == "img_mode":
        window.controller.ui.mode.update.assert_called_once_with()


def test_media_hook_update_ignores_empty_values():
    media, window = _media()

    for key in (
        "img_resolution", "img_variants", "img_mode", "video.aspect_ratio",
        "video.resolution", "video.duration",
    ):
        media.hook_update(key, "", None)

    window.core.config.set.assert_not_called()


@pytest.mark.parametrize(
    "method,key,value",
    [
        ("enable_raw", "img_raw", True),
        ("disable_raw", "img_raw", False),
        ("enable_remix_image", "img.remix", True),
        ("disable_remix_image", "img.remix", False),
        ("enable_remix_video", "video.remix", True),
        ("disable_remix_video", "video.remix", False),
    ],
)
def test_media_enable_disable_methods_persist_and_save(method, key, value):
    media, window = _media()

    getattr(media, method)()

    window.core.config.set.assert_called_once_with(key, value)
    window.core.config.save.assert_called_once_with()


def test_media_toggle_methods_delegate_based_on_checkbox_state():
    media, window = _media()
    media.enable_raw = MagicMock()
    media.disable_raw = MagicMock()
    media.enable_remix_image = MagicMock()
    media.disable_remix_image = MagicMock()
    media.enable_remix_video = MagicMock()
    media.disable_remix_video = MagicMock()

    window.ui.config["global"]["img_raw"].isChecked.return_value = True
    media.toggle_raw()
    media.enable_raw.assert_called_once_with()

    window.ui.config["global"]["img.remix"].isChecked.return_value = False
    media.toggle_remix_image()
    media.disable_remix_image.assert_called_once_with()

    window.ui.config["global"]["video.remix"].isChecked.return_value = True
    media.toggle_remix_video()
    media.enable_remix_video.assert_called_once_with()


def test_media_get_mode_and_model_type_helpers():
    media, window = _media()
    window.core.config.get.side_effect = lambda key, default=None: "video" if key == "img_mode" else "m1"
    model = MagicMock()
    model.is_image_output.return_value = True
    model.is_video_output.return_value = False
    window.core.models.get.return_value = model

    assert media.get_mode() == "video"
    assert media.is_image_model() is True
    assert media.is_video_model() is False
    window.core.models.get.assert_called_with("m1")


def test_media_model_type_helpers_return_none_for_missing_model():
    media, window = _media()
    window.core.config.get.return_value = "missing"
    window.core.models.get.return_value = None

    assert media.is_image_model() is None
    assert media.is_video_model() is None


def test_media_play_video_delegates_to_player_tool():
    media, window = _media()
    player = MagicMock()
    window.tools.get.return_value = player

    media.play_video("/tmp/movie.mp4")

    window.tools.get.assert_called_once_with("player")
    player.play.assert_called_once_with("/tmp/movie.mp4")
