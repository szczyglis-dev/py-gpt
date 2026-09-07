from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QSizePolicy

from pygpt_net.ui.base.config_dialog import BaseConfigDialog


def _window():
    placeholder = MagicMock()
    return SimpleNamespace(
        ui=SimpleNamespace(nodes={}),
        controller=SimpleNamespace(config=SimpleNamespace(placeholder=SimpleNamespace(apply=placeholder))),
        core=SimpleNamespace(
            config=SimpleNamespace(get_user_dir=MagicMock(return_value="/work/data"))
        ),
    )


def test_build_widgets_maps_supported_types_and_respects_excluded():
    window = _window()
    dialog = BaseConfigDialog(window)
    options = {
        "text": {"type": "text"},
        "secret": {"type": "text", "secret": True},
        "slider": {"type": "int", "slider": True},
        "textarea": {"type": "textarea"},
        "bool": {"type": "bool"},
        "bool_list": {"type": "bool_list"},
        "dict": {"type": "dict"},
        "combo": {"type": "combo"},
        "skip": {"type": "text"},
        "unknown": {"type": "other"},
    }

    constructors = {
        "OptionInput": MagicMock(side_effect=lambda *a: MagicMock(name="input")),
        "PasswordInput": MagicMock(side_effect=lambda *a: MagicMock(name="password")),
        "OptionSlider": MagicMock(side_effect=lambda *a: MagicMock(name="slider")),
        "OptionTextarea": MagicMock(side_effect=lambda *a: MagicMock(name="textarea")),
        "OptionCheckbox": MagicMock(side_effect=lambda *a: MagicMock(name="checkbox")),
        "OptionCheckboxList": MagicMock(side_effect=lambda *a: MagicMock(name="checkbox_list")),
        "OptionDict": MagicMock(side_effect=lambda *a: MagicMock(name="dict")),
        "OptionCombo": MagicMock(side_effect=lambda *a: MagicMock(name="combo")),
    }
    size_policy = SimpleNamespace(Expanding="EXPANDING", Preferred="PREFERRED", Fixed="FIXED")
    with patch.multiple("pygpt_net.ui.base.config_dialog", **constructors), \
         patch("pygpt_net.ui.base.config_dialog.QSizePolicy", size_policy):
        widgets = dialog.build_widgets("settings", options, excluded={"skip"}, stretch=True)

    assert set(widgets) == {"text", "secret", "slider", "textarea", "bool", "bool_list", "dict", "combo"}
    constructors["OptionInput"].assert_called_once_with(window, "settings", "text", options["text"])
    constructors["PasswordInput"].assert_called_once_with(window, "settings", "secret", options["secret"])
    constructors["OptionSlider"].assert_called_once_with(window, "settings", "slider", options["slider"])
    widgets["textarea"].setMinimumHeight.assert_called_once_with(150)
    widgets["textarea"].setSizePolicy.assert_called_once_with("EXPANDING", "EXPANDING")
    widgets["dict"].setMinimumHeight.assert_called_once_with(200)
    widgets["combo"].fit_to_content.assert_called_once()
    assert window.controller.config.placeholder.apply.call_count == 3


def test_trans_or_not_shortens_unknown_dictionary_label():
    dialog = BaseConfigDialog(_window())
    with patch("pygpt_net.ui.base.config_dialog.trans", side_effect=lambda value: value):
        assert dialog.trans_or_not("dictionary.some_value") == "Some_value"
        assert dialog.trans_or_not("plain") == "plain"
    with patch("pygpt_net.ui.base.config_dialog.trans", return_value="Translated"):
        assert dialog.trans_or_not("plain") == "Translated"


def test_add_description_translates_placeholder_and_expands_workdir():
    dialog = BaseConfigDialog(_window())
    with patch("pygpt_net.ui.base.config_dialog.trans", return_value="Path: %WORKDIR%"), \
         patch("pygpt_net.ui.base.config_dialog.trans_placeholder_apply", side_effect=lambda value: value), \
         patch("pygpt_net.ui.base.config_dialog.DescLabel", side_effect=lambda value: ("desc", value)):
        result = dialog.add_description("desc.key")

    assert result == ("desc", "Path: /work/data")
    dialog.window.core.config.get_user_dir.assert_called_once_with("data")


def test_add_option_builds_label_and_description_rows():
    dialog = BaseConfigDialog(_window())
    widget = MagicMock()
    label_widget = MagicMock()
    desc_widget = MagicMock()
    layout = MagicMock()
    rows = MagicMock()

    size_policy = SimpleNamespace(Expanding="EXPANDING", Preferred="PREFERRED", Fixed="FIXED")
    with patch.object(dialog, "trans_or_not", return_value="Label"), \
         patch.object(dialog, "add_description", return_value=desc_widget), \
         patch("pygpt_net.ui.base.config_dialog.BaseLabel", return_value=label_widget), \
         patch("pygpt_net.ui.base.config_dialog.QHBoxLayout", return_value=layout), \
         patch("pygpt_net.ui.base.config_dialog.QVBoxLayout", return_value=rows), \
         patch("pygpt_net.ui.base.config_dialog.QSizePolicy", size_policy):
        result = dialog.add_option(widget, {"label": "foo", "description": "bar", "type": "textarea"})

    assert result is rows
    assert dialog.window.ui.nodes["foo.label"] is label_widget
    assert dialog.window.ui.nodes["foo.desc"] is desc_widget
    widget.setSizePolicy.assert_called_once_with("EXPANDING", "PREFERRED")
    layout.addWidget.assert_any_call(label_widget)
    layout.addWidget.assert_any_call(widget)
    rows.addWidget.assert_called_once_with(desc_widget)


def test_add_row_option_uses_title_and_urls_when_requested():
    dialog = BaseConfigDialog(_window())
    widget = MagicMock()
    title = MagicMock()
    urls = MagicMock()
    layout = MagicMock()

    with patch.object(dialog, "trans_or_not", return_value="Title"), \
         patch.object(dialog, "add_urls", return_value=urls), \
         patch("pygpt_net.ui.base.config_dialog.TitleLabel", return_value=title), \
         patch("pygpt_net.ui.base.config_dialog.QVBoxLayout", return_value=layout):
        result = dialog.add_row_option(widget, {"label": "foo", "extra": {"bold": True, "urls": ["https://x"]}})

    assert result is layout
    assert dialog.window.ui.nodes["foo.label"] is title
    layout.addWidget.assert_any_call(title)
    layout.addWidget.assert_any_call(widget)
    layout.addWidget.assert_any_call(urls)


def test_add_raw_option_wraps_description_and_urls():
    dialog = BaseConfigDialog(_window())
    widget = MagicMock()
    desc = MagicMock()
    urls = MagicMock()
    inner = MagicMock()
    rows = MagicMock()

    with patch.object(dialog, "add_description", return_value=desc), \
         patch.object(dialog, "add_urls", return_value=urls), \
         patch("pygpt_net.ui.base.config_dialog.QHBoxLayout", return_value=inner), \
         patch("pygpt_net.ui.base.config_dialog.QVBoxLayout", return_value=rows):
        result = dialog.add_raw_option(widget, {"label": "foo", "description": "desc", "extra": {"urls": "https://x"}})

    assert result is rows
    inner.addWidget.assert_any_call(widget)
    inner.addWidget.assert_any_call(urls)
    rows.addLayout.assert_called_once_with(inner)
    rows.addWidget.assert_called_once_with(desc)


def test_add_urls_accepts_dict_list_and_string():
    dialog = BaseConfigDialog(_window())
    for urls, expected in [
        ({"Docs": "https://docs"}, [("Docs", "https://docs")]),
        (["https://a", "https://b"], [("", "https://a"), ("", "https://b")]),
        ("https://one", [("", "https://one")]),
    ]:
        layout = MagicMock()
        widget = MagicMock()
        created = []
        with patch("pygpt_net.ui.base.config_dialog.QVBoxLayout", return_value=layout), \
             patch("pygpt_net.ui.base.config_dialog.QWidget", return_value=widget), \
             patch("pygpt_net.ui.base.config_dialog.UrlLabel", side_effect=lambda name, url: created.append((name, url)) or MagicMock()):
            assert dialog.add_urls(urls) is widget
        assert created == expected
        widget.setLayout.assert_called_once_with(layout)
        widget.setContentsMargins.assert_called_once_with(0, 0, 0, 0)


def test_add_line_configures_frame():
    dialog = BaseConfigDialog(_window())
    frame = MagicMock()
    with patch("pygpt_net.ui.base.config_dialog.QFrame", return_value=frame) as cls:
        result = dialog.add_line()
    assert result is frame
    frame.setFrameShape.assert_called_once_with(cls.HLine)
    frame.setFrameShadow.assert_called_once_with(cls.Sunken)
