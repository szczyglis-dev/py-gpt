# Example Custom-agent provider

This `agent` Add-on is runnable immediately because it subclasses PyGPT's existing LlamaIndex `ModeAgent("base")` workflow and changes its provider identity/default prompt. It demonstrates how an external agent is registered in the **Custom agents** provider registry.

## Try it

Install and restart PyGPT, create/select a Custom agents preset using **External tutorial agent**, and run a simple task. The normal base workflow remains functional while the external provider controls its defaults.

For a completely new runtime, subclass `BaseAgent` directly and implement `get_agent()`/`run()` according to the Add-ons API reference.
