from pygpt_net.provider.llms.base import BaseLLM

class ExampleLLM(BaseLLM):
    def __init__(self):
        super().__init__()
        self.id = "example_llm"
        self.name = "External example LLM"
        self.description = "Example registration only; implement provider methods before real use."
        self.type = []
