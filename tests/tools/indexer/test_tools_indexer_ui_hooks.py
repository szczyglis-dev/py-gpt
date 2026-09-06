from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.tools.indexer.ui.dialogs import DialogBuilder
from pygpt_net.tools.indexer.ui.web import WebTab


def test_indexer_dialog_builder_hook_idx_change_updates_active_index_without_check():
    indexer = MagicMock()
    tools = MagicMock(); tools.get.return_value = indexer
    obj = SimpleNamespace(window=SimpleNamespace(tools=tools))

    DialogBuilder.hook_idx_change(obj, "idx", "docs", None)

    tools.get.assert_called_once_with("indexer")
    indexer.set_current_idx.assert_called_once_with("docs", check=False)


def test_indexer_web_loader_hook_hides_all_groups_and_shows_selected_group():
    option_a = MagicMock(); option_b = MagicMock()
    config_a = MagicMock(); config_b = MagicMock()
    options_label = MagicMock(); config_label = MagicMock(); config_help = MagicMock()
    nodes = {
        "tool.indexer.web.loader.option_group": {"webpage": option_a, "sitemap": option_b},
        "tool.indexer.web.loader.config_group": {"webpage": config_a, "sitemap": config_b},
        "tool.indexer.web.options.label": options_label,
        "tool.indexer.web.config.label": config_label,
        "tool.indexer.web.config.help": config_help,
    }
    obj = SimpleNamespace(
        window=SimpleNamespace(ui=SimpleNamespace(nodes=nodes)),
        params_widget=MagicMock(),
        params_scroll=MagicMock(),
    )

    WebTab.hook_loader_change(obj, "loader", "sitemap", None)

    option_a.hide.assert_called_once_with(); option_b.hide.assert_called_once_with()
    option_b.show.assert_called_once_with()
    config_a.hide.assert_called_once_with(); config_b.hide.assert_called_once_with()
    config_b.show.assert_called_once_with()
    options_label.hide.assert_called_once_with(); options_label.show.assert_called_once_with()
    config_label.hide.assert_called_once_with(); config_label.show.assert_called_once_with()
    config_help.hide.assert_called_once_with(); config_help.show.assert_called_once_with()
    obj.params_widget.adjustSize.assert_called_once_with()
    obj.params_scroll.update.assert_called_once_with()


def test_indexer_web_loader_hook_keeps_labels_hidden_for_unknown_loader():
    option = MagicMock(); config = MagicMock()
    options_label = MagicMock(); config_label = MagicMock(); config_help = MagicMock()
    nodes = {
        "tool.indexer.web.loader.option_group": {"webpage": option},
        "tool.indexer.web.loader.config_group": {"webpage": config},
        "tool.indexer.web.options.label": options_label,
        "tool.indexer.web.config.label": config_label,
        "tool.indexer.web.config.help": config_help,
    }
    obj = SimpleNamespace(
        window=SimpleNamespace(ui=SimpleNamespace(nodes=nodes)),
        params_widget=MagicMock(),
        params_scroll=MagicMock(),
    )

    WebTab.hook_loader_change(obj, "loader", "missing", None)

    option.show.assert_not_called(); config.show.assert_not_called()
    options_label.show.assert_not_called(); config_label.show.assert_not_called(); config_help.show.assert_not_called()
