from pygpt_net.tools.base import BaseTool

class ExampleTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.id = "example_tool"
        self.has_tab = False
