from pygpt_net.provider.vector_stores.base import BaseStore

class ExampleVectorStore(BaseStore):
    def __init__(self):
        super().__init__()
        self.id = "example_vector_store"
        self.prefix = "external_example_"
