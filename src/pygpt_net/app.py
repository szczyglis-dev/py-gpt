#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.27 18:00:00                  #
# ================================================== #

from pygpt_net.launcher import Launcher

# plugins
from pygpt_net.plugin.audio_azure import Plugin as AudioAzurePlugin
from pygpt_net.plugin.audio_openai_tts import Plugin as AudioOpenAITTSPlugin
from pygpt_net.plugin.audio_openai_whisper import Plugin as AudioOpenAIWhisperPlugin
from pygpt_net.plugin.cmd_code_interpreter import Plugin as CmdCodeInterpreterPlugin
from pygpt_net.plugin.cmd_custom import Plugin as CmdCustomCommandPlugin
from pygpt_net.plugin.cmd_files import Plugin as CmdFilesPlugin
from pygpt_net.plugin.cmd_serial import Plugin as CmdSerialPlugin
from pygpt_net.plugin.cmd_web_google import Plugin as CmdWebGooglePlugin
from pygpt_net.plugin.crontab import Plugin as CrontabPlugin
from pygpt_net.plugin.idx_llama_index import Plugin as IdxLlamaIndexPlugin
from pygpt_net.plugin.openai_dalle import Plugin as OpenAIDallePlugin
from pygpt_net.plugin.openai_vision import Plugin as OpenAIVisionPlugin
from pygpt_net.plugin.real_time import Plugin as RealTimePlugin
from pygpt_net.plugin.self_loop import Plugin as SelfLoopPlugin

# LLMs wrappers providers (langchain, llama-index)
from pygpt_net.provider.llms.anthropic import AnthropicLLM
from pygpt_net.provider.llms.azure_openai import AzureOpenAILLM
from pygpt_net.provider.llms.hugging_face import HuggingFaceLLM
from pygpt_net.provider.llms.llama import Llama2LLM
from pygpt_net.provider.llms.ollama import OllamaLLM
from pygpt_net.provider.llms.openai import OpenAILLM

# vector stores providers (llama-index)
from pygpt_net.provider.vector_stores.chroma import ChromaProvider
from pygpt_net.provider.vector_stores.elasticsearch import ElasticsearchProvider
from pygpt_net.provider.vector_stores.pinecode import PinecodeProvider
from pygpt_net.provider.vector_stores.redis import RedisProvider
from pygpt_net.provider.vector_stores.simple import SimpleProvider

# data loaders providers (llama-index)
from pygpt_net.provider.loaders.csv import Loader as CsvLoader
from pygpt_net.provider.loaders.docx import Loader as DocxLoader
from pygpt_net.provider.loaders.epub import Loader as EpubLoader
from pygpt_net.provider.loaders.excel import Loader as ExcelLoader
from pygpt_net.provider.loaders.json import Loader as JsonLoader
from pygpt_net.provider.loaders.markdown import Loader as MarkdownLoader
from pygpt_net.provider.loaders.pdf import Loader as PdfLoader


def run(**kwargs):
    """
    PyGPT launcher.

    :param kwargs: keyword arguments for launcher

    Extending PyGPT with custom plugins, LLMs wrappers, vector stores and data loaders

    - You can pass custom plugin instances, LLMs wrappers and vector store providers to the launcher.
    - This is useful if you want to extend PyGPT with your own plugins, vectors storage and LLMs.

    To register custom plugins create custom launcher, e.g. "my_launcher.py" and:

    - Pass a list with the plugin instances as 'plugins' keyword argument.

    To register custom LLMs wrappers:

    - Pass a list with the LLMs wrappers instances as 'llms' keyword argument.

    To register custom vector store providers:

    - Pass a list with the vector store provider instances as 'vector_stores' keyword argument.

    To register custom data loaders:

    - Pass a list with the data loader instances as 'loaders' keyword argument.

    Example:
    --------
    ::

        # my_launcher.py

        from pygpt_net.app import run
        from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
        from my_llms import MyCustomLLM
        from my_vector_stores import MyCustomVectorStore
        from my_loaders import MyCustomLoader

        plugins = [
            MyCustomPlugin(),
            MyOtherCustomPlugin(),
        ]
        llms = [
            MyCustomLLM(),
        ]
        vector_stores = [
            MyCustomVectorStore(),
        ]
        loaders = [
            MyCustomLoader(),
        ]

        run(
            plugins=plugins,
            llms=llms,
            vector_stores=vector_stores,
            loaders=loaders
        )

    """
    # initialize app launcher
    launcher = Launcher()
    launcher.init()

    # register base plugins
    launcher.add_plugin(SelfLoopPlugin())
    launcher.add_plugin(RealTimePlugin())
    launcher.add_plugin(AudioAzurePlugin())
    launcher.add_plugin(AudioOpenAITTSPlugin())
    launcher.add_plugin(AudioOpenAIWhisperPlugin())
    launcher.add_plugin(CmdWebGooglePlugin())
    launcher.add_plugin(CmdFilesPlugin())
    launcher.add_plugin(CmdCodeInterpreterPlugin())
    launcher.add_plugin(CmdCustomCommandPlugin())
    launcher.add_plugin(CmdSerialPlugin())
    launcher.add_plugin(OpenAIDallePlugin())
    launcher.add_plugin(OpenAIVisionPlugin())
    launcher.add_plugin(IdxLlamaIndexPlugin())
    launcher.add_plugin(CrontabPlugin())

    # register custom plugins
    plugins = kwargs.get('plugins', None)
    if isinstance(plugins, list):
        for plugin in plugins:
            launcher.add_plugin(plugin)

    # register base langchain and llama-index LLMs
    launcher.add_llm(OpenAILLM())
    launcher.add_llm(AzureOpenAILLM())
    launcher.add_llm(AnthropicLLM())
    launcher.add_llm(HuggingFaceLLM())
    launcher.add_llm(Llama2LLM())
    launcher.add_llm(OllamaLLM())

    # register custom langchain and llama-index LLMs
    llms = kwargs.get('llms', None)
    if isinstance(llms, list):
        for llm in llms:
            launcher.add_llm(llm)

    # register base vector store providers (llama-index)
    launcher.add_vector_store(ChromaProvider())
    launcher.add_vector_store(ElasticsearchProvider())
    launcher.add_vector_store(PinecodeProvider())
    launcher.add_vector_store(RedisProvider())
    launcher.add_vector_store(SimpleProvider())

    # register custom vector store providers (llama-index)
    vector_stores = kwargs.get('vector_stores', None)
    if isinstance(vector_stores, list):
        for store in vector_stores:
            launcher.add_vector_store(store)

    # register base data loaders (llama-index)
    launcher.add_loader(CsvLoader())
    launcher.add_loader(DocxLoader())
    launcher.add_loader(EpubLoader())
    launcher.add_loader(ExcelLoader())
    launcher.add_loader(JsonLoader())
    launcher.add_loader(MarkdownLoader())
    launcher.add_loader(PdfLoader())

    # register custom data loaders (llama-index)
    loaders = kwargs.get('loaders', None)
    if isinstance(loaders, list):
        for loader in loaders:
            launcher.add_loader(loader)

    # run app
    launcher.run()
    

if __name__ == '__main__':
    run()
