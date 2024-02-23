#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.24 01:00:00                  #
# ================================================== #

# PyGPT custom launcher example.

# Uncomment these three lines below if you want to run the launcher directly from the source code,
# without installing the `pygpt_net` package:

# import sys
# from pathlib import Path
# sys.path.insert(0, str((Path(__file__).parent / '../src').resolve()))


from pygpt_net.app import run  # <-- import the "run" function from the app

from example_plugin import Plugin as ExamplePlugin
from example_llm import ExampleLlm
from example_vector_store import ExampleVectorStore
from example_data_loader import ExampleDataLoader
from example_audio_input import ExampleAudioInput
from example_audio_output import ExampleAudioOutput
from example_web_search import ExampleWebSearchEngine

"""
PyGPT can be extended with:

    - Custom plugins
    - Custom LLMs wrappers
    - Custom vector store providers
    - Custom data loaders
    - Custom audio input providers
    - Custom audio output providers
    - Custom web search engine providers

    - You can pass custom plugin instances, LLMs wrappers, vector store providers and more to the launcher.
    - This is useful if you want to extend PyGPT with your own plugins, vectors storage, LLMs or other data providers.
    
    First, create a custom launcher file, for example, "my_launcher.py," and register your extensions in it.

    To register custom plugins create custom launcher, e.g. "my_launcher.py" and:

    - Pass a list with the plugin instances as 'plugins' keyword argument.

    To register custom LLMs wrappers:

    - Pass a list with the LLMs wrappers instances as 'llms' keyword argument.

    To register custom vector store providers:

    - Pass a list with the vector store provider instances as 'vector_stores' keyword argument.

    To register custom data loaders:

    - Pass a list with the data loader instances as 'loaders' keyword argument.

    To register custom audio input providers:

    - Pass a list with the audio input provider instances as 'audio_input' keyword argument.

    To register custom audio output providers:

    - Pass a list with the audio output provider instances as 'audio_output' keyword argument.

    To register custom web providers:

    - Pass a list with the web provider instances as 'web' keyword argument.

    Example:
    --------
    ::

        # custom_launcher.py

        from pygpt_net.app import run
        from plugins import CustomPlugin, OtherCustomPlugin
        from llms import CustomLLM
        from vector_stores import CustomVectorStore
        from loaders import CustomLoader
        from audio_input import CustomAudioInput
        from audio_output import CustomAudioOutput
        from web import CustomWebSearch

        plugins = [
            CustomPlugin(),
            OtherCustomPlugin(),
        ]
        llms = [
            CustomLLM(),
        ]
        vector_stores = [
            CustomVectorStore(),
        ]
        loaders = [
            CustomLoader(),
        ]
        audio_input = [
            CustomAudioInput(),
        ]
        audio_output = [
            CustomAudioOutput(),
        ]
        web = [
            CustomWebSearch(),
        ]

        run(
            plugins=plugins,
            llms=llms,
            vector_stores=vector_stores,
            loaders=loaders,
            audio_input=audio_input,
            audio_output=audio_output,
            web=web
        )

"""

# Working example:

# 1. Prepare instances of your custom plugins, LLMs, vector stores, data loaders and rest of providers:

plugins = [
    ExamplePlugin(),  # add your custom plugin instances here
]
llms = [
    ExampleLlm(),  # add your custom LLM wrappers instances here
]
vector_stores = [
    ExampleVectorStore(),  # add your custom vector store instances here
]
loaders = [
    ExampleDataLoader(),  # add your custom data loader instances here
]
audio_input = [
    ExampleAudioInput(),  # add your custom audio input provider instances here
]
audio_output = [
    ExampleAudioOutput(),  # add your custom audio output provider instances here
]
web = [
    ExampleWebSearchEngine(),  # add your custom web search engine provider instances here
]

# 2. Register example plugins, LLM wrappers, vector stores, data loaders and rest of providers using the run function:

run(
    plugins=plugins,  # pass the list with the plugin instances
    llms=llms,  # pass the list with the LLM provider instances
    vector_stores=vector_stores,  # pass the list with the vector store instances
    loaders=loaders,  # pass the list with the data loader instances
    audio_input=audio_input,  # pass the list with the audio input instances
    audio_output=audio_output,  # pass the list with the audio output instances
    web=web,  # pass the list with the web search engine instances
)

if __name__ == '__main__':
    run()

# 3. Run the app using this custom launcher instead of the default one:

"""
    $ source venv/bin/activate
    $ python3 custom_launcher.py
"""
