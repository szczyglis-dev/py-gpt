from types import SimpleNamespace
from unittest.mock import MagicMock

import pygpt_net.core.prompt.template as template_mod
from pygpt_net.core.prompt.base.gpt import Gpt
from pygpt_net.core.prompt.template import Template


def test_gpt_get_reads_existing_config_key_or_returns_empty():
    config = SimpleNamespace(has=MagicMock(side_effect=lambda key: key == "prompt.cmd"), get=MagicMock(return_value="SYSTEM"))
    window = SimpleNamespace(core=SimpleNamespace(config=config))
    gpt = Gpt(window)
    assert gpt.get("cmd") == "SYSTEM"
    assert gpt.get("missing") == ""
    config.has.assert_any_call("prompt.cmd")


def make_template(tmp_path):
    app = tmp_path / "app"; data = app / "data"; data.mkdir(parents=True)
    config = SimpleNamespace(get_app_path=MagicMock(return_value=str(app)))
    debug = SimpleNamespace(log=MagicMock())
    presets = SimpleNamespace(paste_prompt=MagicMock())
    window = SimpleNamespace(core=SimpleNamespace(config=config, debug=debug), controller=SimpleNamespace(presets=presets))
    return Template(window), data, window


def test_load_from_csv_skips_header_sorts_by_name_and_getters(tmp_path):
    tpl, data, _ = make_template(tmp_path)
    (data / "prompts.csv").write_text("act,prompt\nZulu,Z\nAlpha,A\n", encoding="utf-8")
    tpl.load_from_csv()
    assert [x["name"] for x in tpl.prompts.values()] == ["Alpha", "Zulu"]
    assert tpl.get_by_id(next(iter(tpl.prompts))) is not None
    assert tpl.get_all() is tpl.prompts
    assert tpl.loaded is True


def test_load_only_once_and_logs_errors(tmp_path, monkeypatch):
    tpl, _, window = make_template(tmp_path)
    tpl.load_from_csv = MagicMock(side_effect=OSError("boom"))
    tpl.load()
    assert tpl.loaded is True
    window.core.debug.log.assert_called_once()
    tpl.load()
    assert tpl.load_from_csv.call_count == 1


class Signal:
    def __init__(self): self.callback = None
    def connect(self, callback): self.callback = callback


class FakeAction:
    def __init__(self, text, parent):
        self.text = text; self.parent = parent; self.triggered = Signal(); self.tooltip = None
    def setToolTip(self, value): self.tooltip = value


class Menu:
    def __init__(self, name="root"):
        self.name = name; self.submenus = []; self.actions = []; self.separators = 0
    def addSeparator(self): self.separators += 1
    def addMenu(self, name):
        child = Menu(name); self.submenus.append(child); return child
    def addAction(self, action): self.actions.append(action)


def test_to_menu_options_groups_by_first_letter_and_binds_prompt_id(tmp_path, monkeypatch):
    tpl, _, window = make_template(tmp_path)
    tpl.prompts = {1: {"name": "Alpha", "prompt": "A"}, 2: {"name": "Beta", "prompt": "B"}}
    tpl.loaded = True
    monkeypatch.setattr(template_mod, "QAction", FakeAction)
    monkeypatch.setattr(template_mod, "trans", lambda key: "Templates")
    menu = Menu()
    tpl.to_menu_options(menu, parent="agent")
    assert menu.separators == 1
    submenu = menu.submenus[0]
    assert [m.name for m in submenu.submenus] == ["A", "B"]
    action = submenu.submenus[0].actions[0]
    assert action.tooltip == "A"
    action.triggered.callback()
    window.controller.presets.paste_prompt.assert_called_once_with(1, "agent")
