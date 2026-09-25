from pygpt_net.provider.web.base import BaseProvider

class ExampleWeb(BaseProvider):
    def __init__(self):
        super().__init__()
        self.id = "example_web"
        self.name = "External example web"
        self.type = ["search_engine"]
    def search(self, query, limit=10, offset=0):
        return []
    def is_configured(self, cmds):
        return True
