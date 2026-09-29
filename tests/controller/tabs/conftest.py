from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.controller.tabs import Tabs
from pygpt_net.core.tabs.tab import Tab


class FakeTabWidget:
    def __init__(self, count=0, current=0):
        self._count = int(count)
        self._current = int(current)
        self._texts = {}
        self._tooltips = {}
        self.active = False
        self.setCurrentIndex = MagicMock(side_effect=self._set_current)
        self.setTabText = MagicMock(side_effect=lambda idx, text: self._texts.__setitem__(int(idx), text))
        self.setTabToolTip = MagicMock(side_effect=lambda idx, text: self._tooltips.__setitem__(int(idx), text))
        self.set_active = MagicMock(side_effect=self._set_active)

    def _set_current(self, idx):
        self._current = int(idx)

    def _set_active(self, state):
        self.active = bool(state)

    def count(self):
        return self._count

    def currentIndex(self):
        return self._current

    def set_count(self, count):
        self._count = int(count)
        if self._count == 0:
            self._current = -1
        elif self._current < 0 or self._current >= self._count:
            self._current = 0

    def tabText(self, idx):
        return self._texts.get(int(idx), "")

    def tabToolTip(self, idx):
        return self._tooltips.get(int(idx), "")


class FakeSplitter:
    def __init__(self, sizes=None, widgets=None, root_index=1):
        self._sizes = list(sizes or [500, 200])
        self._widgets = list(widgets or [MagicMock(), MagicMock()])
        self._root_index = root_index
        self.setSizes = MagicMock(side_effect=self._set_sizes)

    def _set_sizes(self, sizes):
        self._sizes = list(sizes)

    def sizes(self):
        return list(self._sizes)

    def count(self):
        return len(self._sizes)

    def indexOf(self, _root):
        return self._root_index

    def widget(self, idx):
        return self._widgets[idx]


def make_tab(pid=1, idx=0, column_idx=0, type=Tab.TAB_CHAT, data_id=None, tool_id=None, title="Chat"):
    tab = Tab(
        pid=pid,
        idx=idx,
        column_idx=column_idx,
        type=type,
        data_id=data_id,
        tool_id=tool_id,
        title=title,
        tooltip=title,
    )
    return tab


@pytest.fixture
def tabs_env():
    widgets = {
        0: FakeTabWidget(count=0, current=-1),
        1: FakeTabWidget(count=0, current=-1),
    }

    core_tabs = MagicMock()
    core_tabs.NUM_COLS = 2
    core_tabs.pids = {}
    core_tabs.titles = {
        Tab.TAB_CHAT: "output.tab.chat",
        Tab.TAB_NOTEPAD: "output.tab.notepad",
        Tab.TAB_TOOL: "output.tab.tool",
    }

    def get_by_pid(pid):
        return core_tabs.pids.get(pid)

    def get_by_index(idx, column_idx=0):
        for tab in core_tabs.pids.values():
            if tab is not None and tab.idx == idx and tab.column_idx == column_idx:
                return tab
        return None

    def first_by_type(type_):
        candidates = [
            tab for tab in core_tabs.pids.values()
            if tab is not None and tab.type == type_
        ]
        candidates.sort(key=lambda tab: (tab.column_idx, tab.idx, tab.pid))
        return candidates[0] if candidates else None

    core_tabs.get_tab_by_pid.side_effect = get_by_pid
    core_tabs.get_tab_by_index.side_effect = get_by_index
    core_tabs.get_first_by_type.side_effect = first_by_type

    config_values = {
        "layout.split": False,
        "render.plain": False,
        "mode": "chat",
    }
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: config_values.get(key, default)

    output = MagicMock()
    output.has_request.return_value = False
    output.render_pids = {}
    core_ctx = MagicMock()
    core_ctx.output = output
    core_ctx.get_current.return_value = None

    core = SimpleNamespace(tabs=core_tabs, config=config, ctx=core_ctx)

    split_node = MagicMock()
    split_node.box = MagicMock()
    input_container = MagicMock()
    input_root = MagicMock()
    input_root.minimumSizeHint.return_value.height.return_value = 120
    input_root.sizeHint.return_value.height.return_value = 140

    layout = MagicMock()
    layout.get_tabs_by_idx.side_effect = lambda idx: widgets.get(int(idx))
    layout.columns = [MagicMock(), MagicMock()]

    splitter = FakeSplitter(sizes=[500, 200])
    ui = SimpleNamespace(
        layout=layout,
        nodes={
            "layout.split": split_node,
            "input.container": input_container,
            "input.root": input_root,
            "output": {},
            "output_plain": {},
        },
        splitters={
            "columns": MagicMock(),
            "main.output": splitter,
        },
        dialog={"rename": MagicMock()},
        dialogs=MagicMock(),
    )

    controller_ui = MagicMock()
    controller_ui.splitter_output_size_input = None
    controller = SimpleNamespace(
        dialogs=SimpleNamespace(debug=MagicMock()),
        notepad=MagicMock(),
        ctx=MagicMock(),
        ui=controller_ui,
        audio=MagicMock(),
        chat=SimpleNamespace(render=MagicMock()),
        calendar=MagicMock(),
        camera=MagicMock(),
        plugins=MagicMock(),
    )

    window = SimpleNamespace(
        core=core,
        controller=controller,
        ui=ui,
        dispatch=MagicMock(),
        tools=MagicMock(),
    )
    tabs = Tabs(window)
    controller.tabs = tabs

    def install(*items):
        core_tabs.pids = {tab.pid: tab for tab in items}
        for col in (0, 1):
            column_tabs = sorted(
                [tab for tab in items if tab.column_idx == col],
                key=lambda tab: tab.idx,
            )
            widgets[col].set_count(len(column_tabs))
            if column_tabs and widgets[col].currentIndex() < 0:
                widgets[col]._current = 0
            for tab in column_tabs:
                widgets[col]._texts[tab.idx] = tab.title or ""
                widgets[col]._tooltips[tab.idx] = tab.tooltip or ""
        return items

    return SimpleNamespace(
        tabs=tabs,
        window=window,
        core_tabs=core_tabs,
        config=config,
        config_values=config_values,
        core_ctx=core_ctx,
        output=output,
        widgets=widgets,
        layout=layout,
        splitter=splitter,
        install=install,
        make_tab=make_tab,
    )
