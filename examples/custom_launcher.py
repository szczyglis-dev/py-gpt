#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# PyGPT custom launcher tutorial                     #
# Website: https://pygpt.net                         #
# Docs: https://pygpt.readthedocs.io/en/latest/      #
# GitHub: https://github.com/szczyglis-dev/py-gpt    #
# MIT License                                        #
# Updated: 2026-08-19                                #
# ================================================== #

"""Run PyGPT with custom extension instances.

`pygpt_net.app.run()` registers all built-in components first and then registers
objects supplied in the keyword-argument lists below. This file is therefore a
convenient integration point for private/company extensions without modifying
PyGPT's own package.
"""

# If you run this file directly from the PyGPT source tree without installing
# `pygpt-net`, uncomment this block. The repository layout is expected to be:
#
#   py-gpt/
#     src/pygpt_net/
#     examples/custom_launcher.py
#
# import sys
# from pathlib import Path
# sys.path.insert(0, str((Path(__file__).resolve().parent / "../src").resolve()))

try:
    from pygpt_net.app import run
except ImportError as exc:
    raise ImportError(
        "PyGPT is not importable. Install the package or uncomment the source-tree "
        "sys.path block at the top of examples/custom_launcher.py."
    ) from exc

# Local example modules live next to this launcher, therefore direct imports are
# appropriate when executing `python3 examples/custom_launcher.py`.
from example_agent import ExampleAgent
from example_audio_input import ExampleAudioInput
from example_audio_output import ExampleAudioOutput
from example_data_loader import ExampleDataLoader
from example_llm import ExampleLlm
from example_plugin import Plugin as ExamplePlugin
from example_tool import ExampleTool
from example_vector_store import ExampleVectorStore
from example_web_search import ExampleWebSearchEngine


def main():
    """Create extension instances and start the application once."""

    # Plugin: receives app/model events and can expose commands callable by models.
    plugins = [
        ExamplePlugin(),
    ]

    # LLM wrapper: used by LlamaIndex and, when implemented, embeddings.
    # This is different from the native Chat API provider path.
    llms = [
        ExampleLlm(),
    ]

    # Vector-store backend used by the LlamaIndex indexing subsystem.
    vector_stores = [
        ExampleVectorStore(),
    ]

    # File/web readers used when PyGPT indexes external data.
    loaders = [
        ExampleDataLoader(),
    ]

    # Providers displayed in Audio Input / Audio Output plugin settings.
    audio_input = [
        ExampleAudioInput(),
    ]
    audio_output = [
        ExampleAudioOutput(),
    ]

    # Search-engine backend used by the Web Search plugin.
    web = [
        ExampleWebSearchEngine(),
    ]

    # Agent workflow/provider shown in agent-type choices.
    agents = [
        ExampleAgent(),
    ]

    # GUI/application tool registered in the Tools subsystem.
    tools = [
        ExampleTool(),
    ]

    # `run()` owns the application lifecycle and blocks until PyGPT exits.
    # Call it only once.
    run(
        plugins=plugins,
        llms=llms,
        vector_stores=vector_stores,
        loaders=loaders,
        audio_input=audio_input,
        audio_output=audio_output,
        web=web,
        agents=agents,
        tools=tools,
    )


if __name__ == "__main__":
    main()
