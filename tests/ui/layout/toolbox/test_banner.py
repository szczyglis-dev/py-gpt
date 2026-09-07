from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.ui.layout.toolbox.banner import Banner, BannerWidget


def test_banner_setup_registers_widget_and_loaded_signal(qapp):
    window = MagicMock()
    window.core.banners.get_default_path.return_value = "/tmp/default.png"
    window.ui.nodes = {}
    builder = Banner(window)

    with patch("pygpt_net.ui.layout.toolbox.banner.BannerWidget") as cls:
        widget = cls.return_value
        result = builder.setup()

    assert result is widget
    assert window.ui.nodes["toolbox.banner"] is widget
    cls.assert_called_once_with(width=256, height=36, default_path="/tmp/default.png", parent=window)
    window.core.banners.loaded.connect.assert_called_once_with(widget.set_items)


def test_set_items_empty_stops_timer_and_shows_default():
    widget = SimpleNamespace(
        timer=MagicMock(), items=[1], current_index=9, _show_default=MagicMock(), _show_current=MagicMock()
    )
    BannerWidget.set_items(widget, None)
    assert widget.items == []
    assert widget.current_index == 0
    widget.timer.stop.assert_called_once()
    widget._show_default.assert_called_once()
    widget._show_current.assert_not_called()


def test_set_items_nonempty_resets_index_and_shows_current():
    widget = SimpleNamespace(
        timer=MagicMock(), items=[], current_index=9, _show_default=MagicMock(), _show_current=MagicMock()
    )
    items = [{"path": "a"}]
    BannerWidget.set_items(widget, items)
    assert widget.items == items
    assert widget.current_index == 0
    widget._show_current.assert_called_once()


def test_show_current_wraps_index_sets_metadata_and_minimum_duration():
    timer = MagicMock()
    widget = SimpleNamespace(
        items=[{"url": "https://example.test", "tooltip": "tip", "path": "a", "duration": 0.1}],
        current_index=4,
        current_url="",
        timer=timer,
        setToolTip=MagicMock(),
        setCursor=MagicMock(),
        unsetCursor=MagicMock(),
        _show_image=MagicMock(),
    )

    BannerWidget._show_current(widget)

    assert widget.current_index == 0
    assert widget.current_url == "https://example.test"
    widget.setToolTip.assert_called_once_with("tip")
    widget.setCursor.assert_called_once_with(Qt.PointingHandCursor)
    widget._show_image.assert_called_once_with("a")
    timer.start.assert_called_once_with(1000)


def test_show_current_invalid_duration_falls_back_to_thirty_seconds():
    widget = SimpleNamespace(
        items=[{"duration": "bad"}], current_index=0, current_url="", timer=MagicMock(),
        setToolTip=MagicMock(), setCursor=MagicMock(), unsetCursor=MagicMock(), _show_image=MagicMock(),
    )
    BannerWidget._show_current(widget)
    widget.timer.start.assert_called_once_with(30000)


def test_next_rotates_and_show_default_resets_state():
    widget = SimpleNamespace(items=[1, 2, 3], current_index=1, _show_current=MagicMock())
    BannerWidget._next(widget)
    assert widget.current_index == 2
    widget._show_current.assert_called_once()

    default_widget = SimpleNamespace(
        timer=MagicMock(), current_url="x", setToolTip=MagicMock(), unsetCursor=MagicMock(),
        default_path="/tmp/default.png", _show_image=MagicMock(),
    )
    with patch("pygpt_net.ui.layout.toolbox.banner.os.path.isfile", return_value=False):
        BannerWidget._show_default(default_widget)
    assert default_widget.current_url == ""
    default_widget._show_image.assert_called_once_with(None)


def test_show_image_missing_path_only_stops_movie_and_clears():
    widget = SimpleNamespace(_stop_movie=MagicMock(), clear=MagicMock())
    with patch("pygpt_net.ui.layout.toolbox.banner.os.path.isfile", return_value=False):
        BannerWidget._show_image(widget, "/missing")
    widget._stop_movie.assert_called_once()
    widget.clear.assert_called_once()


def test_stop_movie_stops_deletes_and_clears_reference():
    movie = MagicMock()
    widget = SimpleNamespace(_movie=movie)
    BannerWidget._stop_movie(widget)
    movie.stop.assert_called_once()
    movie.deleteLater.assert_called_once()
    assert widget._movie is None


def test_left_click_opens_current_url_in_browser():
    event = MagicMock()
    event.button.return_value = Qt.LeftButton
    widget = SimpleNamespace(current_url="https://example.test")

    with patch("pygpt_net.ui.layout.toolbox.banner.webbrowser.open") as open_browser:
        BannerWidget.mousePressEvent(widget, event)

    open_browser.assert_called_once_with("https://example.test", new=2)
    event.accept.assert_called_once()
