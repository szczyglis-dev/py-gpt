from pygpt_net.core.types import image as mod


def test_scale_resolutions_multiplies_both_dimensions_and_preserves_order():
    assert mod._scale_resolutions(("10x20", "3x4"), 2) == ("20x40", "6x8")


def test_resolution_map_is_identity_mapping():
    assert mod._resolution_map(("1x2", "3x4")) == {"1x2": "1x2", "3x4": "3x4"}


def test_gemini_flash_resolution_sets_include_512_1k_2k_and_4k_variants():
    values = mod.IMAGE_AVAILABLE_RESOLUTIONS["gemini-3.1-flash-image"]
    assert "512x512" in values
    assert "1024x1024" in values
    assert "2048x2048" in values
    assert "4096x4096" in values
    assert len(values) == len(mod._GEMINI_31_FLASH_ALL)


def test_flash_lite_is_limited_to_1k_family():
    values = mod.IMAGE_AVAILABLE_RESOLUTIONS["gemini-3.1-flash-lite-image"]
    assert set(values) == set(mod._GEMINI_31_FLASH_1K)
    assert "2048x2048" not in values


def test_video_resolution_and_aspect_ratio_maps_are_identity_maps():
    assert mod.VIDEO_AVAILABLE_RESOLUTIONS["1080p"] == "1080p"
    assert mod.VIDEO_AVAILABLE_ASPECT_RATIOS["16:9"] == "16:9"


def test_model_version_at_least_parses_numbered_model_family():
    from pygpt_net.core.types.image import model_version_at_least

    assert model_version_at_least("openai/gpt-image-2", "gpt-image-", (2, 0)) is True
    assert model_version_at_least("gpt-image-2.1-preview", "gpt-image-", (2, 1)) is True
    assert model_version_at_least("gpt-image-1", "gpt-image-", (2, 0)) is False
    assert model_version_at_least("other-2", "gpt-image-", (2, 0)) is False


def test_get_future_image_resolutions_returns_forward_family_fallbacks_only():
    from pygpt_net.core.types.image import get_future_image_resolutions

    assert "3840x2160" in get_future_image_resolutions("gpt-image-3")
    assert "2048x2048" in get_future_image_resolutions("imagen-5.0")
    assert "4096x4096" in get_future_image_resolutions("gemini-4-pro-image")
    assert set(get_future_image_resolutions("grok-imagine-image-3")) == {"1k", "2k"}
    assert get_future_image_resolutions("gpt-image-1") is None
    assert get_future_image_resolutions("unknown") is None
