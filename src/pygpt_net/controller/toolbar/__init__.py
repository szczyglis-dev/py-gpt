"""Navigation actions for the persistent left toolbar."""
from pygpt_net.core.tabs.tab import Tab


class Toolbar:
    def __init__(self, window=None):
        self.window = window

    def home(self):
        return self.window.controller.tabs.open_or_activate(Tab.TAB_CHAT, create=False)

    def files(self):
        return self.window.controller.tabs.open_or_activate(Tab.TAB_FILES)

    def painter(self):
        return self.window.controller.tabs.open_or_activate(Tab.TAB_TOOL_PAINTER)
