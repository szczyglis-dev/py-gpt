from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.ui.widget.option.cmd import OptionCmd


def test_option_cmd_update_item_is_noop_for_read_only_params():
    widget = SimpleNamespace(params=MagicMock())

    assert OptionCmd.update_item(widget, 3, {"value": 7}) is None

    widget.params.update_item.assert_not_called()


def test_option_cmd_update_refreshes_locale():
    widget = SimpleNamespace(update_locale=MagicMock())

    assert OptionCmd.update(widget) is None

    widget.update_locale.assert_called_once_with()


def test_option_cmd_description_uses_child_provider_locale():
    from unittest.mock import patch
    from pygpt_net.plugin.filesystem import Plugin
    plugin = Plugin()
    for tool in ('python_exec', 'python_kernel_restart'):
        option = plugin.options['cmd.' + tool]
        assert option['description']
        widget = SimpleNamespace(plugin=plugin, option=option, cmd_id=tool)
        with patch('pygpt_net.ui.widget.option.cmd.trans', return_value='Przetłumaczony opis') as translate:
            assert OptionCmd._description(widget) == 'Przetłumaczony opis'
        translate.assert_called_once_with('cmd.' + tool + '.description', False, 'plugin.cmd_code_interpreter')


def test_tool_description_fits_wrapped_text_when_resized(qt_application):
    from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout
    from pygpt_net.ui.widget.element.labels import DescLabel

    window = QWidget()
    window.controller = MagicMock()
    window.ui = SimpleNamespace(nodes={}, groups={})
    plugin = SimpleNamespace(use_locale=False)
    option = {'id': 'cmd.shell_exec', 'description': 'A long description of shell execution. ' * 30,
              'value': {'enabled': True, 'instruction': 'Execute a command', 'params': []}}
    widget = OptionCmd(window, plugin, 'test', 'cmd.shell_exec', option)
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.addWidget(widget)
    ordinary = DescLabel(option['description'])
    layout.addWidget(ordinary)
    layout.addStretch()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(content)
    scroll.resize(480, 250)
    scroll.show()
    for width in (480, 280, 600):
        scroll.resize(width, 250)
        qt_application.processEvents()
        for label in (window.ui.nodes[widget.desc_key], ordinary):
            assert label.hasHeightForWidth()
            assert label.height() >= label.heightForWidth(label.width())
            assert label.height() > 40
    scroll.close()
    window.close()
