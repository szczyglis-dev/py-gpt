from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QPoint, QSize

from pygpt_net.tools.image_viewer.ui.dialogs import ImageViewerDialog


def _pixmap(width=100, height=50, null=False):
    pm = MagicMock()
    pm.width.return_value = width
    pm.height.return_value = height
    pm.isNull.return_value = null
    pm.cacheKey.return_value = 123
    return pm


def test_image_viewer_compute_fit_factor_preserves_aspect_ratio():
    obj = SimpleNamespace()
    assert ImageViewerDialog._compute_fit_factor(obj, QSize(400, 200), QSize(100, 100)) == 0.25
    assert ImageViewerDialog._compute_fit_factor(obj, QSize(100, 400), QSize(100, 100)) == 0.25
    assert ImageViewerDialog._compute_fit_factor(obj, QSize(0, 0), QSize(0, 0)) == 1.0


def test_image_viewer_has_image_and_can_drag_require_manual_oversized_pixmap():
    source_pm = _pixmap()
    source = MagicMock(); source.pixmap.return_value = source_pm
    displayed = MagicMock(); displayed.width.return_value = 300; displayed.height.return_value = 80
    obj = SimpleNamespace(
        source=source,
        pixmap=displayed,
        _zoom_mode="manual",
        _viewport_size=MagicMock(return_value=QSize(200, 100)),
        _has_image=MagicMock(return_value=True),
    )

    assert ImageViewerDialog._has_image(SimpleNamespace(source=source, pixmap=displayed)) is True
    assert ImageViewerDialog._can_drag(obj) is True

    obj._zoom_mode = "fit"
    assert ImageViewerDialog._can_drag(obj) is False
    obj._zoom_mode = "manual"; displayed.width.return_value = 150
    assert ImageViewerDialog._can_drag(obj) is False


def test_image_viewer_clamp_factor_respects_widget_dimensions_and_total_pixels():
    source_pm = _pixmap(width=10_000, height=10_000)
    source = MagicMock(); source.pixmap.return_value = source_pm
    obj = SimpleNamespace(
        source=source,
        _max_total_pixels=80_000_000,
        _max_widget_dim=32_768,
        _min_zoom=0.05,
    )

    assert ImageViewerDialog._clamp_factor_by_size(obj, 0.5) == 0.5
    clamped = ImageViewerDialog._clamp_factor_by_size(obj, 10.0)
    assert clamped < 10.0
    assert clamped > 0.0
    assert (10_000 * clamped) ** 2 <= 80_000_000 + 1


def test_image_viewer_clamp_factor_returns_original_without_valid_source():
    source = MagicMock(); source.pixmap.return_value = None
    obj = SimpleNamespace(source=source)
    assert ImageViewerDialog._clamp_factor_by_size(obj, 3.0) == 3.0


def test_image_viewer_set_scaled_pixmap_manual_resizes_and_refreshes_status():
    src = _pixmap(100, 50)
    source = MagicMock(); source.pixmap.return_value = src
    displayed_pm = MagicMock(); displayed_pm.cacheKey.return_value = 999
    pixmap = MagicMock(); pixmap.pixmap.return_value = displayed_pm
    obj = SimpleNamespace(
        source=source,
        pixmap=pixmap,
        scroll_area=MagicMock(),
        _zoom_mode="manual",
        _zoom_factor=1.0,
        _has_image=MagicMock(return_value=True),
        _clamp_factor_by_size=MagicMock(side_effect=lambda factor: factor),
        _refresh_statusbar=MagicMock(),
    )

    ImageViewerDialog._set_scaled_pixmap_by_factor(obj, 2.0)

    pixmap.setPixmap.assert_called_once_with(src)
    pixmap.setScaledContents.assert_called_once_with(True)
    pixmap.resize.assert_called_once_with(200, 100)
    obj._refresh_statusbar.assert_called_once_with()


def test_image_viewer_set_status_meta_normalizes_values_and_refreshes():
    obj = SimpleNamespace(
        _meta_index=0,
        _meta_total=0,
        _meta_img_size=QSize(),
        _meta_file_size="",
        _refresh_statusbar=MagicMock(),
    )

    ImageViewerDialog.set_status_meta(
        obj,
        index=-1,
        total=5,
        img_size=QSize(1920, 1080),
        file_size_str="2 MB",
    )

    assert obj._meta_index == 0
    assert obj._meta_total == 5
    assert obj._meta_img_size == QSize(1920, 1080)
    assert obj._meta_file_size == "2 MB"
    obj._refresh_statusbar.assert_called_once_with()


def test_image_viewer_current_zoom_and_displayed_size_follow_mode():
    shown = MagicMock(); shown.width.return_value = 640; shown.height.return_value = 360
    shown_pm = _pixmap(320, 180)
    shown.pixmap.return_value = shown_pm
    obj = SimpleNamespace(
        _zoom_mode="fit",
        _fit_factor=0.5,
        _zoom_factor=2.0,
        pixmap=shown,
    )

    assert ImageViewerDialog._current_zoom_percent(obj) == 50
    assert ImageViewerDialog._displayed_size(obj) == QSize(320, 180)

    obj._zoom_mode = "manual"
    assert ImageViewerDialog._current_zoom_percent(obj) == 200
    assert ImageViewerDialog._displayed_size(obj) == QSize(640, 360)


def test_image_viewer_refresh_statusbar_formats_all_metadata():
    obj = SimpleNamespace(
        lbl_index=MagicMock(),
        lbl_extra=MagicMock(),
        lbl_zoom=MagicMock(),
        lbl_resolution=MagicMock(),
        _meta_index=2,
        _meta_total=7,
        _meta_img_size=QSize(1920, 1080),
        _meta_file_size="3.2 MB",
        _displayed_size=MagicMock(return_value=QSize(960, 540)),
        _current_zoom_percent=MagicMock(return_value=50),
    )

    ImageViewerDialog._refresh_statusbar(obj)

    obj.lbl_index.setText.assert_called_once_with("2/7")
    obj.lbl_extra.setText.assert_called_once_with("960x540 px")
    obj.lbl_zoom.setText.assert_called_once_with("50%")
    obj.lbl_resolution.setText.assert_called_once_with("1920x1080 px | 3.2 MB")


def test_image_viewer_event_pos_supports_qpointf_style_and_legacy_pos():
    obj = SimpleNamespace()
    point = QPoint(4, 5)
    event = SimpleNamespace(position=MagicMock(return_value=SimpleNamespace(toPoint=MagicMock(return_value=point))))
    assert ImageViewerDialog._event_pos(obj, event) == point

    legacy = SimpleNamespace(pos=MagicMock(return_value=QPoint(8, 9)))
    assert ImageViewerDialog._event_pos(obj, legacy) == QPoint(8, 9)
