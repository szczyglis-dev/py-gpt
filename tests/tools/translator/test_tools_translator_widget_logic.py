from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import Qt

from pygpt_net.tools.translator.ui.widgets import TextColumn, TextareaField, ToolWidget


def _column(lang, text):
    lang_select = MagicMock()
    lang_select.get_value.return_value = lang
    textarea = MagicMock()
    textarea.toPlainText.return_value = text
    return SimpleNamespace(lang_select=lang_select, textarea=textarea, on_load=MagicMock())


def _widget():
    left = _column("-", "hello")
    right = _column("pl", "cześć")
    model = MagicMock(); model.get_value.return_value = "gpt-test"
    signals = SimpleNamespace(
        translate=SimpleNamespace(emit=MagicMock()),
        save_config=SimpleNamespace(emit=MagicMock()),
    )
    return SimpleNamespace(
        left_column=left,
        right_column=right,
        model_select=model,
        tool=SimpleNamespace(signals=signals),
        loading=False,
        initialized=True,
        status=MagicMock(),
    )


def test_translator_widget_on_load_and_status_update():
    obj = _widget()
    ToolWidget.on_load(obj)
    obj.left_column.on_load.assert_called_once_with()

    ToolWidget.set_status(obj, "Ready")
    obj.status.setText.assert_called_once_with("Ready")


def test_translator_widget_translate_routes_left_and_right_languages():
    obj = _widget()

    ToolWidget.translate(obj, "left")
    obj.tool.signals.translate.emit.assert_called_once_with(
        "left", "gpt-test", "hello", "-", "pl"
    )

    obj.tool.signals.translate.emit.reset_mock()
    ToolWidget.translate(obj, "right")
    obj.tool.signals.translate.emit.assert_called_once_with(
        "right", "gpt-test", "cześć", "pl", "-"
    )


def test_translator_widget_translate_is_suppressed_during_load_or_before_init():
    obj = _widget()
    obj.loading = True
    ToolWidget.translate(obj, "left")
    obj.tool.signals.translate.emit.assert_not_called()

    obj.loading = False; obj.initialized = False
    ToolWidget.translate(obj, "left")
    obj.tool.signals.translate.emit.assert_not_called()


def test_translator_widget_load_config_updates_only_present_values_and_resets_loading():
    obj = _widget()
    config = {
        "model": "gpt-x",
        "language_left": "en",
        "language_right": "de",
        "content_left": "left text",
        "content_right": "right text",
    }

    ToolWidget.load_config(obj, config)

    assert obj.loading is False
    obj.model_select.set_value.assert_called_once_with("gpt-x")
    obj.left_column.lang_select.set_value.assert_called_once_with("en")
    obj.right_column.lang_select.set_value.assert_called_once_with("de")
    obj.left_column.textarea.setPlainText.assert_called_once_with("left text")
    obj.right_column.textarea.setPlainText.assert_called_once_with("right text")


def test_translator_widget_save_config_serializes_current_widget_values():
    obj = _widget()

    ToolWidget.save_config(obj)

    obj.tool.signals.save_config.emit.assert_called_once_with({
        "model": "gpt-test",
        "language_left": "-",
        "language_right": "pl",
        "content_left": "hello",
        "content_right": "cześć",
    })


def test_translator_widget_save_config_is_suppressed_while_loading():
    obj = _widget(); obj.loading = True
    ToolWidget.save_config(obj)
    obj.tool.signals.save_config.emit.assert_not_called()


def test_translator_widget_content_helpers_target_correct_column():
    obj = _widget()

    ToolWidget.set_content(obj, "L", "left")
    obj.left_column.textarea.setPlainText.assert_called_with("L")
    ToolWidget.set_content(obj, "R", "right")
    obj.right_column.textarea.setPlainText.assert_called_with("R")

    ToolWidget.replace_content(obj, "left", "RL")
    obj.left_column.textarea.setPlainText.assert_called_with("RL")
    ToolWidget.replace_content(obj, "right", "RR")
    obj.right_column.textarea.setPlainText.assert_called_with("RR")

    ToolWidget.append_content(obj, "left", "AL")
    obj.left_column.textarea.append.assert_called_once_with("AL")
    ToolWidget.append_content(obj, "right", "AR")
    obj.right_column.textarea.append.assert_called_once_with("AR")


def test_translator_text_column_search_selects_found_language_and_clear_resets_search():
    lang_select = MagicMock()
    lang_input = MagicMock()
    text = MagicMock()
    text.find_lang_id_by_search_string.return_value = "de"
    obj = SimpleNamespace(
        window=SimpleNamespace(core=SimpleNamespace(text=text)),
        lang_select=lang_select,
        lang_input=lang_input,
        on_search=MagicMock(),
    )

    TextColumn.on_search(obj, "German")
    lang_select.set_value.assert_called_once_with("de")

    TextColumn.on_clear(obj)
    lang_input.clear.assert_called_once_with()
    obj.on_search.assert_called_once_with("")


def test_translator_text_column_search_ignores_auto_detect_and_missing_matches():
    text = MagicMock()
    lang_select = MagicMock()
    obj = SimpleNamespace(
        window=SimpleNamespace(core=SimpleNamespace(text=text)),
        lang_select=lang_select,
    )
    for result in (None, "-"):
        text.find_lang_id_by_search_string.return_value = result
        TextColumn.on_search(obj, "query")
    lang_select.set_value.assert_not_called()


def test_translator_textarea_action_clear_routes_by_column():
    translator = MagicMock()
    tools = MagicMock(); tools.get.return_value = translator
    obj = SimpleNamespace(id="left", window=SimpleNamespace(tools=tools))

    TextareaField.action_clear(obj)
    translator.clear_left.assert_called_once_with()

    obj.id = "right"
    TextareaField.action_clear(obj)
    translator.clear_right.assert_called_once_with()


def test_translator_textarea_audio_find_and_update_delegate():
    cursor = MagicMock(); cursor.selectedText.return_value = "selected"
    finder = MagicMock()
    window = SimpleNamespace(
        controller=SimpleNamespace(
            audio=MagicMock(),
            finder=MagicMock(),
        )
    )
    obj = SimpleNamespace(window=window, finder=finder, textCursor=MagicMock(return_value=cursor))

    TextareaField.audio_read_selection(obj)
    window.controller.audio.read_text.assert_called_once_with("selected")
    TextareaField.find_open(obj)
    window.controller.finder.open.assert_called_once_with(finder)
    TextareaField.on_update(obj)
    finder.clear.assert_called_once_with()


def test_translator_textarea_update_stylesheet_skips_identical_css():
    obj = SimpleNamespace(
        default_stylesheet="base;",
        styleSheet=MagicMock(return_value="base;extra;"),
        setStyleSheet=MagicMock(),
    )
    TextareaField.update_stylesheet(obj, "extra;")
    obj.setStyleSheet.assert_not_called()

    obj.styleSheet.return_value = "old"
    TextareaField.update_stylesheet(obj, "extra;")
    obj.setStyleSheet.assert_called_once_with("base;extra;")


def test_translator_textarea_ctrl_wheel_clamps_font_size_and_accepts_event():
    event = SimpleNamespace(
        modifiers=MagicMock(return_value=Qt.ControlModifier),
        angleDelta=MagicMock(return_value=SimpleNamespace(y=MagicMock(return_value=120))),
        accept=MagicMock(),
    )
    obj = SimpleNamespace(
        value=12,
        min_font_size=8,
        max_font_size=13,
        update_stylesheet=MagicMock(),
    )

    TextareaField.wheelEvent(obj, event)
    assert obj.value == 13
    obj.update_stylesheet.assert_called_once_with("QTextEdit { font-size: 13px };")
    event.accept.assert_called_once_with()

    obj.update_stylesheet.reset_mock(); obj.value = 13
    TextareaField.wheelEvent(obj, event)
    assert obj.value == 13
    obj.update_stylesheet.assert_not_called()
