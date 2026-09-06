from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pygpt_net.controller.lang.plugins import Plugins


def test_lang_plugins_apply_translates_enabled_plugin_and_refreshes_current_tab():
    window = MagicMock()
    plugin = MagicMock()
    plugin.use_locale = True
    plugin.setup.return_value = {
        "enabled": {"type": "bool"},
        "path": {"type": "text"},
    }
    disabled = MagicMock()
    disabled.use_locale = False
    window.core.plugins.plugins = {"demo": plugin, "disabled": disabled}

    desc = MagicMock()
    label = MagicMock()
    bool_widget = MagicMock()
    window.ui.nodes = {
        "plugin.settings.demo.desc": MagicMock(),
        "plugin.demo.enabled.label": label,
        "plugin.demo.enabled.desc": desc,
    }
    settings_tab = MagicMock()
    settings_tab.currentIndex.return_value = 3
    window.ui.tabs = {"plugin.settings": settings_tab}
    menu_item = MagicMock()
    window.ui.menu = {"plugins": {"demo": menu_item}}
    window.ui.config = {"plugin.demo": {"enabled": bool_widget}}
    window.controller.plugins.get_tab_idx.return_value = 1

    def tr(key, *args):
        if key == "enabled.tooltip":
            return "enabled.tooltip"
        return f"tr:{key}"

    with patch("pygpt_net.controller.lang.plugins.trans", side_effect=tr) as trans:
        Plugins(window).apply()

    window.controller.plugins.update_info.assert_called_once_with()
    trans.assert_any_call("", True, "plugin.demo")
    settings_tab.setTabText.assert_called_once_with(1, "tr:plugin.name")
    menu_item.setText.assert_called_once_with("tr:plugin.name")
    label.setText.assert_called_once_with("tr:enabled.label")
    desc.setText.assert_called_once_with("tr:enabled.description")
    desc.setToolTip.assert_called_once_with("tr:enabled.description")
    bool_widget.setText.assert_called_once_with("tr:enabled.label")
    bool_widget.box.setText.assert_called_once_with("tr:enabled.label")
    window.plugin_settings.update_list.assert_called_once_with("plugin.list", window.core.plugins.plugins)
    window.controller.plugins.set_by_tab.assert_called_once_with(3)
    disabled.setup.assert_not_called()
