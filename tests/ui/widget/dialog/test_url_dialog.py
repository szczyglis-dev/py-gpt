from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.dialog.url import UrlDialog


def _widget():
    opt_web = MagicMock()
    opt_other = MagicMock()
    cfg_web = MagicMock()
    cfg_other = MagicMock()
    options_label = MagicMock()
    config_label = MagicMock()
    config_help = MagicMock()
    nodes = {
        "dialog.url.loader.option_group": {"webpage": opt_web, "other": opt_other},
        "dialog.url.loader.config_group": {"webpage": cfg_web, "other": cfg_other},
        "dialog.url.options.label": options_label,
        "dialog.url.config.label": config_label,
        "dialog.url.config.help": config_help,
    }
    return SimpleNamespace(
        window=SimpleNamespace(ui=SimpleNamespace(nodes=nodes)),
        params_widget=MagicMock(),
        params_scroll=MagicMock(),
    ), (opt_web, opt_other, cfg_web, cfg_other, options_label, config_label, config_help)


def test_init_is_idempotent_after_initialization():
    widget = SimpleNamespace(initialized=True)
    assert UrlDialog.init(widget) is None


def test_loader_hook_shows_only_matching_option_and_config_groups():
    widget, items = _widget()
    opt_web, opt_other, cfg_web, cfg_other, options_label, config_label, config_help = items

    UrlDialog.hook_loader_change(widget, "web.loader", "webpage", "test")

    opt_web.hide.assert_called_once()
    opt_other.hide.assert_called_once()
    opt_web.show.assert_called_once()
    cfg_web.hide.assert_called_once()
    cfg_other.hide.assert_called_once()
    cfg_web.show.assert_called_once()
    options_label.hide.assert_called_once()
    options_label.show.assert_called_once()
    config_label.hide.assert_called_once()
    config_label.show.assert_called_once()
    config_help.hide.assert_called_once()
    config_help.show.assert_called_once()
    widget.params_widget.adjustSize.assert_called_once()
    widget.params_scroll.update.assert_called_once()


def test_loader_hook_hides_labels_when_loader_has_no_groups():
    widget, items = _widget()
    _, _, _, _, options_label, config_label, config_help = items

    UrlDialog.hook_loader_change(widget, "web.loader", "missing", "test")

    options_label.hide.assert_called_once()
    options_label.show.assert_not_called()
    config_label.hide.assert_called_once()
    config_label.show.assert_not_called()
    config_help.hide.assert_called_once()
    config_help.show.assert_not_called()
