"""Runnable external plugin example for PyGPT.

The example demonstrates the parts most plugin authors need in practice:
configuration options, model-callable commands, mutable application events and
returning command results to the active conversation.
"""

from pygpt_net.core.events import Event
from pygpt_net.plugin.base.plugin import BasePlugin


class ExamplePlugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.id = "example_plugin"
        self.name = "Example developer plugin"
        self.description = "Tutorial plugin with settings, tools and event hooks."
        self.prefix = "ExamplePlugin"
        self.type = ["cmd"]
        self.allowed_cmds = ["example_echo", "example_add"]

        # A normal plugin option. PyGPT persists the value in the active profile.
        self.add_option(
            "uppercase",
            type="bool",
            value=False,
            label="Uppercase echo result",
            description="Convert example_echo output to upper case.",
        )

        # A model-callable command. add_cmd() creates the schema used by both
        # PyGPT command syntax and native provider function/tool calling.
        self.add_cmd(
            "example_echo",
            instruction="Echo text through the external example plugin.",
            params=[
                {
                    "name": "text",
                    "type": "str",
                    "description": "Text to return.",
                    "required": True,
                }
            ],
            enabled=True,
            label="Echo tool",
            description="Allow the model to call example_echo.",
        )
        self.add_cmd(
            "example_add",
            instruction="Add two numbers and return the numeric result.",
            params=[
                {"name": "a", "type": "float", "description": "First number", "required": True},
                {"name": "b", "type": "float", "description": "Second number", "required": True},
            ],
            enabled=True,
            label="Add numbers tool",
            description="Allow the model to call example_add.",
        )

    def handle(self, event: Event, *args, **kwargs):
        # Publish command schemas when PyGPT asks enabled plugins for tools.
        if event.name in (Event.CMD_SYNTAX, Event.CMD_SYNTAX_INLINE):
            for name in self.allowed_cmds:
                if self.has_cmd(name):
                    event.data.setdefault("cmd", []).append(self.get_cmd(name))
            return

        # Execute commands sent by the model.
        if event.name in (Event.CMD_EXECUTE, Event.CMD_INLINE):
            self._execute(event)
            return

        # Demonstrate a harmless mutable event hook. This makes the plugin easy
        # to observe while developing without changing normal user text.
        if event.name == Event.POST_PROMPT_END:
            value = str(event.data.get("value") or "")
            note = "The external example_plugin add-on is enabled."
            if note not in value:
                event.data["value"] = (value + "\n\n" + note).strip()

        if event.name == Event.PLUGIN_SETTINGS_CHANGED:
            self.log("Plugin settings were saved.")

    def _execute(self, event: Event):
        for item in event.data.get("commands", []):
            cmd = item.get("cmd")
            if cmd not in self.allowed_cmds or not self.has_cmd(cmd):
                continue

            # Mark the tool phase as active in the same way built-in plugins do.
            self.cmd_prepare(event.ctx, [item])
            params = item.get("params") or {}
            try:
                if cmd == "example_echo":
                    result = str(params.get("text", ""))
                    if self.get_option_value("uppercase"):
                        result = result.upper()
                elif cmd == "example_add":
                    result = float(params.get("a", 0)) + float(params.get("b", 0))
                else:
                    continue

                self.reply(
                    {
                        "request": {"cmd": cmd, "params": params},
                        "result": result,
                    },
                    event.ctx,
                )
            except Exception as exc:
                self.reply(
                    {
                        "request": {"cmd": cmd, "params": params},
                        "result": f"Example plugin error: {exc}",
                    },
                    event.ctx,
                )
            return
