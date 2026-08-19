# PyGPT extension examples

This directory contains small, runnable examples showing the extension points exposed by the current PyGPT launcher and runtime.

The examples are intentionally simple. They are meant to be copied, renamed, and adapted rather than used as production implementations unchanged.

Full documentation: https://pygpt.readthedocs.io/en/latest/

## What is included

- `custom_launcher.py` - registers all custom extension types and starts PyGPT.
- `example_plugin.py` - plugin options, events, commands/tools, and command replies.
- `example_tool.py` - a custom GUI tool with a Tools-menu action and dialog.
- `example_agent.py` - a custom agent provider based on the built-in OpenAI Agents implementation.
- `example_llm.py` - a LlamaIndex LLM + embeddings wrapper.
- `example_vector_store.py` - a LlamaIndex vector-store provider.
- `example_data_loader.py` - a file data loader and custom `BaseReader`.
- `example_audio_input.py` - speech-to-text provider.
- `example_audio_output.py` - text-to-speech provider using PyGPT's temporary audio-output helper.
- `example_web_search.py` - web search-engine provider.

## How registration works

`pygpt_net.app.run()` first registers PyGPT's built-in providers, plugins, tools, and agents. It then appends the lists supplied by a custom launcher:

- `plugins=[...]`
- `llms=[...]`
- `vector_stores=[...]`
- `loaders=[...]`
- `audio_input=[...]`
- `audio_output=[...]`
- `web=[...]`
- `agents=[...]`
- `tools=[...]`

During application initialization PyGPT attaches the main `window` or owning plugin to registered objects. Do not assume these references are available while your extension object's `__init__()` is still running unless the base class explicitly provides them.

Every extension ID must be unique. Reusing a built-in ID may replace or shadow a built-in provider in the corresponding registry.

## Running the examples

From an installed package:

```bash
python3 examples/custom_launcher.py
```

When running directly from the source tree without installing `pygpt-net`, uncomment the `sys.path` block at the top of `custom_launcher.py`.

## Important distinctions

### LLM wrappers vs. native Chat providers

The `llms=` extension point is used by PyGPT's LlamaIndex integration (Chat with Files / LlamaIndex agents) and embeddings. Normal Chat mode uses the configured API provider or an OpenAI-compatible endpoint directly.

For OpenAI-compatible/local models, per-model `API base` and `API key` can be configured in the Models Editor. These values are stored in `ModelItem.custom_api_endpoint` and `ModelItem.custom_api_key`; a custom LLM wrapper should explicitly honor them if that is appropriate for its backend.

### Plugins vs. Tools

A **plugin** participates in model/application events and can expose callable commands to models.

A **tool** is primarily an application/UI component registered in the Tools subsystem. A tool can provide menu actions, dialogs, tabs, lifecycle hooks, and event handling, but it is not automatically a callable model command.

### Temporary files

Application-managed temporary files belong under the workdir `tmp` directory. For audio output, use `BaseProvider.prepare_output_path()` instead of reusing a fixed output filename. This avoids clutter and file-lock problems.

## Source code as reference

The most useful built-in implementations live under:

- `pygpt_net.plugin.*`
- `pygpt_net.tools.*`
- `pygpt_net.provider.llms.*`
- `pygpt_net.provider.vector_stores.*`
- `pygpt_net.provider.loaders.*`
- `pygpt_net.provider.audio_input.*`
- `pygpt_net.provider.audio_output.*`
- `pygpt_net.provider.web.*`
- `pygpt_net.provider.agents.*`

The base interfaces are the source of truth for required method signatures.
