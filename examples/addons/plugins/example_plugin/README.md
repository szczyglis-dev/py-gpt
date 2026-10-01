# Example plugin

This is a complete external `plugin` Add-on. It demonstrates persistent plugin options, two model-callable commands (`example_echo` and `example_add`), command schema publication, command execution, replies returned to the current conversation, application event hooks, and a private `locale/` directory. The Add-on loader automatically binds that directory to `addon.example_plugin`; no locale registration code is needed.

## Try it

1. Install this directory with **Config -> Install Add-on...** and restart PyGPT.
2. Enable **Example developer plugin** in Plugins and enable Tools in a normal Chat.
3. Ask: `Use example_add to add 12.5 and 7.25.`
4. Open the plugin settings, enable **Uppercase echo result**, then ask the model to call `example_echo`.
5. Enable plugin/event debug logging while developing to see the event flow.

The key implementation points are `add_option()`, `add_cmd()`, `handle()`, `get_cmd()`, `cmd_allowed()` and `reply()`. See the Add-ons API documentation for the full `BasePlugin` method and event reference.
