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
