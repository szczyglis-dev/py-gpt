from pygpt_net.provider.agents.base import BaseAgent

class ExampleAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.id = "example_agent"
        self.name = "External example agent"
        self.type = "external_example"
        self.mode = "agent_llama"
