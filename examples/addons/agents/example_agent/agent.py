"""Runnable Custom-agents provider example.

The example reuses PyGPT's working LlamaIndex ``ModeAgent('base')`` runtime and
supplies its own provider identity plus a small, editable option schema. This is
a practical starting point when you want a Custom-agents Add-on without
reimplementing the entire agent runtime.
"""

from pygpt_net.provider.agents.llama_index.modes import ModeAgent


class ExampleAgent(ModeAgent):
    def __init__(self):
        super().__init__("base")
        self.id = "example_agent"
        self.name = "External tutorial agent"

    def get_options(self):
        # ModeAgent's workflow asks for options in a section named ``base``.
        # Declaring defaults here makes the example self-contained and also
        # exposes the fields in the Custom-agent preset editor.
        return {
            "base": {
                "label": "Agent",
                "options": {
                    "prompt": {
                        "type": "textarea",
                        "label": "System prompt",
                        "description": "Default prompt used by the tutorial agent.",
                        "default": (
                            "You are the external PyGPT tutorial agent. Help the "
                            "user accurately and keep the response concise."
                        ),
                    },
                    "allow_local_tools": {
                        "type": "bool",
                        "label": "Allow local tools",
                        "default": True,
                    },
                    "allow_remote_tools": {
                        "type": "bool",
                        "label": "Allow remote tools",
                        "default": True,
                    },
                },
            }
        }
