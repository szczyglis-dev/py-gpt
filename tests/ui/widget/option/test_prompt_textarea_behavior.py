from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.option.prompt import PromptTextarea


def _window(locked=False):
    node = SimpleNamespace(
        parent_id="preset",
        id="prompt",
        option={"value": "x"},
        toPlainText=MagicMock(return_value="hello"),
    )
    return SimpleNamespace(
        controller=SimpleNamespace(
            mode=SimpleNamespace(locked=locked),
            config=SimpleNamespace(input=SimpleNamespace(on_update=MagicMock())),
            ui=SimpleNamespace(update_tokens=MagicMock()),
        ),
        ui=SimpleNamespace(nodes={"preset.prompt": node}),
        core=SimpleNamespace(
            prompt=SimpleNamespace(
                template=SimpleNamespace(to_menu_options=MagicMock()),
                custom=SimpleNamespace(to_menu_options=MagicMock()),
            ),
            debug=SimpleNamespace(log=MagicMock()),
        ),
    )


def test_prompt_change_is_ignored_while_mode_is_locked():
    window = _window(locked=True)
    PromptTextarea.on_prompt_changed(SimpleNamespace(window=window))
    window.controller.config.input.on_update.assert_not_called()
    window.controller.ui.update_tokens.assert_not_called()


def test_prompt_change_updates_config_and_token_count():
    window = _window(locked=False)
    PromptTextarea.on_prompt_changed(SimpleNamespace(window=window))
    node = window.ui.nodes["preset.prompt"]
    window.controller.config.input.on_update.assert_called_once_with(
        "preset", "prompt", {"value": "x"}, "hello"
    )
    node.toPlainText.assert_called_once_with()
    window.controller.ui.update_tokens.assert_called_once_with()


def test_prompt_context_menu_adds_template_and_custom_options():
    window = _window()
    menu = MagicMock()
    event = MagicMock()
    event.globalPos.return_value = "global"
    widget = SimpleNamespace(window=window, createStandardContextMenu=MagicMock(return_value=menu))

    PromptTextarea.contextMenuEvent(widget, event)

    window.core.prompt.template.to_menu_options.assert_called_once_with(menu, "global")
    window.core.prompt.custom.to_menu_options.assert_called_once_with(menu, "global")
    menu.exec_.assert_called_once_with("global")


def test_prompt_context_menu_logs_extension_errors_and_still_opens_menu():
    window = _window()
    err = RuntimeError("boom")
    window.core.prompt.template.to_menu_options.side_effect = err
    menu = MagicMock()
    event = MagicMock()
    event.globalPos.return_value = "global"
    widget = SimpleNamespace(window=window, createStandardContextMenu=MagicMock(return_value=menu))

    PromptTextarea.contextMenuEvent(widget, event)

    window.core.debug.log.assert_called_once_with(err)
    menu.exec_.assert_called_once_with("global")
