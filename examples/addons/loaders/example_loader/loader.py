from pygpt_net.provider.loaders.base import BaseLoader

class ExampleLoader(BaseLoader):
    def __init__(self):
        super().__init__()
        self.id = "example_loader"
        self.name = "External example loader"
        self.extensions = ["example"]
        self.type = ["file"]
