from pygpt_net.plugin.base.plugin import BasePlugin

class ExamplePlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.id = "example_plugin"
        self.name = "External example plugin"
        self.description = "Loaded from the profile extensions directory."
        self.type = ["cmd"]
