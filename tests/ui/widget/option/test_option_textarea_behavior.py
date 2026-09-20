from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.option.textarea import OptionTextarea


def _widget(context_options=None):
    window = SimpleNamespace(core=SimpleNamespace(prompt=SimpleNamespace(
        template=SimpleNamespace(to_menu_options=MagicMock()),
        custom=SimpleNamespace(to_menu_options=MagicMock()),
    )))
    return SimpleNamespace(
        window=window,
        context_options=context_options or [],
        createStandardContextMenu=MagicMock(return_value=MagicMock()),
    )


def test_option_textarea_context_menu_adds_prompt_actions_only_when_enabled():
    widget = _widget(["prompt.template.paste"])
    event = MagicMock()
    event.globalPos.return_value = "p"

    OptionTextarea.contextMenuEvent(widget, event)

    menu = widget.createStandardContextMenu.return_value
    widget.window.core.prompt.template.to_menu_options.assert_called_once_with(menu, "editor")
    widget.window.core.prompt.custom.to_menu_options.assert_called_once_with(menu, "editor")
    menu.exec_.assert_called_once_with("p")


def test_option_textarea_context_menu_without_prompt_option_uses_plain_standard_menu():
    widget = _widget([])
    event = MagicMock()
    OptionTextarea.contextMenuEvent(widget, event)
    widget.window.core.prompt.template.to_menu_options.assert_not_called()
    widget.window.core.prompt.custom.to_menu_options.assert_not_called()
