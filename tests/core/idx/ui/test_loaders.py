from types import SimpleNamespace
from unittest.mock import MagicMock

from pygpt_net.core.idx.ui.loaders import Loaders


def _node(value):
    node = MagicMock()
    node.text.return_value = value
    return node


def test_handle_options_converts_loader_args_and_config_values(monkeypatch):
    monkeypatch.setattr("pygpt_net.core.idx.ui.loaders.trans", lambda key, **kwargs: key)
    select = SimpleNamespace(get_value=lambda: "demo")
    indexing = SimpleNamespace(
        get_external_instructions=lambda: {"demo": {"args": {
            "count": {"type": "int"},
            "ratio": {"type": "float"},
            "enabled": {"type": "bool"},
            "tags": {"type": "list"},
            "mapping": {"type": "dict"},
        }}},
        get_external_config=lambda: {"demo": {
            "limit": {"type": "int"},
        }},
    )
    nodes = {
        "opt.demo.count": _node("3"),
        "opt.demo.ratio": _node("1.5"),
        "opt.demo.enabled": _node("true"),
        "opt.demo.tags": _node("a,b"),
        "opt.demo.mapping": _node('{"x": 1}'),
        "cfg.demo.limit": _node("9"),
    }
    window = SimpleNamespace(
        core=SimpleNamespace(idx=SimpleNamespace(indexing=indexing), debug=SimpleNamespace(log=MagicMock())),
        ui=SimpleNamespace(nodes=nodes, dialogs=SimpleNamespace(alert=MagicMock())),
    )

    ok, loader, params, config = Loaders(window).handle_options(select, "opt", "cfg")

    assert ok is True
    assert loader == "demo"
    assert params == {"count": 3, "ratio": 1.5, "enabled": True, "tags": ["a", "b"], "mapping": {"x": 1}}
    assert config == {"limit": 9}


def test_handle_options_returns_false_without_selected_loader():
    select = SimpleNamespace(get_value=lambda: "")
    ok, loader, params, config = Loaders(SimpleNamespace()).handle_options(select, "opt", "cfg")
    assert (ok, loader, params, config) == (False, "", {}, {})


def test_handle_options_reports_conversion_errors(monkeypatch):
    warning = MagicMock()
    monkeypatch.setattr("pygpt_net.core.idx.ui.loaders.QMessageBox.warning", warning)
    monkeypatch.setattr("pygpt_net.core.idx.ui.loaders.trans", lambda key, **kwargs: key)
    select = SimpleNamespace(get_value=lambda: "demo")
    indexing = SimpleNamespace(
        get_external_instructions=lambda: {"demo": {"args": {"count": {"type": "int"}}}},
        get_external_config=lambda: {},
    )
    debug = SimpleNamespace(log=MagicMock())
    alert = MagicMock()
    window = SimpleNamespace(
        core=SimpleNamespace(idx=SimpleNamespace(indexing=indexing), debug=debug),
        ui=SimpleNamespace(nodes={"opt.demo.count": _node("nope")}, dialogs=SimpleNamespace(alert=alert)),
    )

    ok, _, params, _ = Loaders(window).handle_options(select, "opt", "cfg")

    assert ok is False
    assert params == {}
    debug.log.assert_called_once()
    alert.assert_not_called()
    warning.assert_called_once()


def test_required_fields_reject_whitespace_and_focus_input(monkeypatch):
    warning = MagicMock()
    monkeypatch.setattr("pygpt_net.core.idx.ui.loaders.QMessageBox.warning", warning)
    monkeypatch.setattr("pygpt_net.core.idx.ui.loaders.trans", lambda key, **kwargs: key)
    node = _node('   ')
    indexing = SimpleNamespace(
        get_external_instructions=lambda: {'demo': {'args': {}}},
        get_external_config=lambda: {'demo': {'token': {'type': 'str', 'required': True}}},
    )
    window = SimpleNamespace(
        core=SimpleNamespace(idx=SimpleNamespace(indexing=indexing), debug=SimpleNamespace(log=MagicMock())),
        ui=SimpleNamespace(nodes={'cfg.demo.token': node}, dialogs=SimpleNamespace(alert=MagicMock())),
    )
    assert Loaders(window).handle_options(SimpleNamespace(get_value=lambda: 'demo'), 'opt', 'cfg')[0] is False
    node.setFocus.assert_called_once()
    warning.assert_called_once()
    assert isinstance(warning.call_args.args[2], str)
    window.ui.dialogs.alert.assert_not_called()
    window.core.debug.log.assert_not_called()


def test_forms_refresh_locale_and_dialog_rebuild_preserves_values(monkeypatch, qt_application):
    from PySide6.QtWidgets import QWidget, QVBoxLayout
    from pygpt_net.ui.widget.dialog.url import UrlDialog
    from pygpt_net.core.idx.ui import loaders as module
    import pygpt_net.utils as utils
    monkeypatch.setattr(utils, "locale", SimpleNamespace(get=lambda key, domain=None: key))
    window = QWidget()
    window.controller = MagicMock()
    window.controller.config.placeholder.apply_by_id.return_value = [{'web_demo': 'Demo'}]
    window.core = MagicMock()
    window.core.idx.indexing.get_external_instructions.return_value = {
        'demo': {'args': {'source': {'type': 'str', 'label': 'options.source.label',
                                   'description': 'options.source.desc', '_locale_domain': 'loader.demo',
                                   'required': True}}}}
    window.core.idx.indexing.get_external_config.return_value = {
        'demo': {'enabled': {'type': 'bool', 'value': True},
                 'token': {'type': 'str', 'extra': {'secret': True}, 'value': ''}}}
    window.ui = SimpleNamespace(nodes={}, add_hook=MagicMock())
    service = Loaders(window)
    window.core.idx.ui.loaders = service
    translations = {'options.source.label': 'Source', 'options.source.desc': 'Source description'}
    monkeypatch.setattr(module, 'trans', lambda key, **kwargs: translations.get(key, key))
    dialog = UrlDialog(window)
    dialog.init()
    window.ui.nodes['dialog.url.loader'].set_value('demo')
    node = window.ui.nodes['dialog.url.loader.option.demo.source']
    node.setText('keep me')
    window.ui.nodes['dialog.url.loader.config.demo.enabled'].setText(False)
    window.ui.nodes['dialog.url.loader.config.demo.token'].setText('keep secret')
    assert node._loader_field[2].text() == 'Source *'
    translations['options.source.label'] = 'Źródło'
    service.update_locale()
    assert node._loader_field[2].text() == 'Źródło *'
    assert node.text() == 'keep me'
    dialog.init(rebuild=True)
    assert isinstance(dialog.layout(), QVBoxLayout)
    assert dialog.layout().count() == 4
    assert window.ui.nodes['dialog.url.loader'].get_value() == 'demo'
    replacement = window.ui.nodes['dialog.url.loader.option.demo.source']
    assert replacement.text() == 'keep me'
    assert replacement._loader_field[2].text() == 'Źródło *'
    assert window.ui.nodes['dialog.url.loader.config.demo.enabled'].text() == 'false'
    assert window.ui.nodes['dialog.url.loader.config.demo.token'].text() == 'keep secret'
    from pygpt_net.tools.indexer.ui.web import WebTab
    window.core.config.get.return_value = 'local'
    tab = WebTab(window)
    tab_widget = tab.setup()
    tab_node = window.ui.nodes['tool.indexer.web.loader.option.demo.source']
    tab_node.setText('index this')
    translations['options.source.label'] = 'Source'
    service.update_locale()
    assert replacement._loader_field[2].text() == 'Source *'
    assert tab_node._loader_field[2].text() == 'Source *'
    assert replacement.text() == 'keep me'
    assert tab_node.text() == 'index this'
    dialog.resize(800, 400)
    dialog.show()
    qt_application.processEvents()
    group = window.ui.nodes['dialog.url.loader.option_group']['demo']
    assert group.width() >= dialog.params_scroll.viewport().width() - 10
    dialog.close()
    dialog.deleteLater()
    tab_widget.deleteLater()
    window.deleteLater()


def test_typed_fields_mask_secrets_use_toggles_and_browse_files(monkeypatch, qt_application):
    import pygpt_net.utils as utils
    from PySide6.QtWidgets import QWidget, QLineEdit, QFileDialog
    from pygpt_net.ui.widget.anims.toggles import AnimToggle
    monkeypatch.setattr(utils, 'locale', SimpleNamespace(get=lambda key, domain=None: key))
    window = QWidget()
    window.controller = MagicMock()
    window.core = MagicMock()
    fields = {
        'token': {'type': 'str', 'extra': {'secret': True}, 'value': 'private'},
        'enabled': {'type': 'bool', 'value': False, 'required': True},
        'credentials': {'type': 'path', 'value': '/old.json'},
        'mapping': {'type': 'dict', 'value': {'x': 1}},
    }
    window.core.idx.indexing.get_external_config.return_value = {'demo': fields}
    window.core.idx.indexing.get_external_instructions.return_value = {'demo': {'args': {}}}
    window.core.config.get.return_value = []
    window.ui = SimpleNamespace(nodes={}, dialogs=SimpleNamespace(alert=MagicMock()))
    service = Loaders(window)
    inputs, groups = service.setup_loader_config()
    for key, node in inputs['demo'].items():
        window.ui.nodes['cfg.demo.' + key] = node
    token, enabled, path = (inputs['demo'][key] for key in ('token', 'enabled', 'credentials'))
    assert token.input.echoMode() == QLineEdit.Password
    assert token.text() == 'private'
    token.input.toggle_password_visibility()
    assert token.input.echoMode() == QLineEdit.Normal
    assert isinstance(enabled.input, AnimToggle)
    assert enabled.text() == 'false'
    enabled.setText('true')
    assert enabled.input.isChecked()
    enabled.setText(False)
    choose = MagicMock(return_value=('/new.json', ''))
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', choose)
    path.path_button.click()
    choose.assert_called_once()
    assert path.text() == '/new.json'
    choose.return_value = ('', '')
    path.path_button.click()
    assert path.text() == '/new.json'
    ok, _, _, config = service.handle_options(SimpleNamespace(get_value=lambda: 'demo'), 'opt', 'cfg')
    assert ok is True
    assert config == {'token': 'private', 'enabled': False, 'credentials': '/new.json', 'mapping': {'x': 1}}
    for group in groups.values():
        group.deleteLater()
    window.deleteLater()
