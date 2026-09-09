from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from pygpt_net.ui.layout.toolbox.banner import Banner, BannerWidget


def test_banner_setup_registers_loaded_signal_without_creating_widget(qapp):
    window = MagicMock()
    window.ui.nodes = {}
    builder = Banner(window)
    layout = MagicMock()

    result = builder.setup(layout)

    assert result is None
    assert builder.layout is layout
    assert builder.widget is None
    assert "toolbox.banner" not in window.ui.nodes
    window.core.banners.loaded.connect.assert_called_once_with(builder.set_items)


def test_banner_set_items_creates_widget_lazily_and_inserts_it(qapp):
    window = MagicMock()
    window.ui.nodes = {}
    builder = Banner(window)
    layout = MagicMock()
    builder.setup(layout)

    with patch("pygpt_net.ui.layout.toolbox.banner.BannerWidget") as cls:
        widget = cls.return_value
        builder.set_items([{"path": "/tmp/banner.png"}])

    cls.assert_called_once_with(width=256, height=36, parent=window)
    assert builder.widget is widget
    assert window.ui.nodes["toolbox.banner"] is widget
    layout.insertWidget.assert_called_once_with(0, widget, 0, Qt.AlignTop | Qt.AlignRight)
    widget.set_items.assert_called_once_with([{"path": "/tmp/banner.png"}])


def test_banner_empty_items_remove_existing_widget(qapp):
    window = MagicMock()
    widget = MagicMock()
    window.ui.nodes = {"toolbox.banner": widget}
    layout = MagicMock()
    builder = Banner(window)
    builder.layout = layout
    builder.widget = widget

    builder.set_items([])

    widget.stop.assert_called_once_with()
    layout.removeWidget.assert_called_once_with(widget)
    widget.deleteLater.assert_called_once_with()
    assert builder.widget is None
    assert "toolbox.banner" not in window.ui.nodes


def test_set_items_empty_stops_widget():
    widget = SimpleNamespace(
        timer=MagicMock(),
        items=[1],
        current_index=9,
        stop=MagicMock(),
        _show_current=MagicMock(),
    )

    BannerWidget.set_items(widget, None)

    assert widget.items == []
    assert widget.current_index == 0
    widget.timer.stop.assert_called_once()
    widget.stop.assert_called_once_with()
    widget._show_current.assert_not_called()


def test_set_items_nonempty_resets_index_and_shows_current():
    widget = SimpleNamespace(
        timer=MagicMock(),
        items=[],
        current_index=9,
        stop=MagicMock(),
        _show_current=MagicMock(),
    )
    items = [{"path": "a"}]

    BannerWidget.set_items(widget, items)

    assert widget.items == items
    assert widget.current_index == 0
    widget.stop.assert_not_called()
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
        items=[{"duration": "bad"}],
        current_index=0,
        current_url="",
        timer=MagicMock(),
        setToolTip=MagicMock(),
        setCursor=MagicMock(),
        unsetCursor=MagicMock(),
        _show_image=MagicMock(),
    )
    BannerWidget._show_current(widget)
    widget.timer.start.assert_called_once_with(30000)


def test_next_rotates_and_stop_resets_state():
    widget = SimpleNamespace(items=[1, 2, 3], current_index=1, _show_current=MagicMock())
    BannerWidget._next(widget)
    assert widget.current_index == 2
    widget._show_current.assert_called_once()

    stopped_widget = SimpleNamespace(
        timer=MagicMock(),
        current_url="x",
        items=[1],
        setToolTip=MagicMock(),
        unsetCursor=MagicMock(),
        _stop_movie=MagicMock(),
        clear=MagicMock(),
    )
    BannerWidget.stop(stopped_widget)
    assert stopped_widget.current_url == ""
    assert stopped_widget.items == []
    stopped_widget.timer.stop.assert_called_once_with()
    stopped_widget.setToolTip.assert_called_once_with("")
    stopped_widget.unsetCursor.assert_called_once_with()
    stopped_widget._stop_movie.assert_called_once_with()
    stopped_widget.clear.assert_called_once_with()


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
