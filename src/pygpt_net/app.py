#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.28 22:00:00                  #
# ================================================== #

from pygpt_net.launcher import Launcher

# plugins
from pygpt_net.plugin.audio_output import Plugin as AudioOutputPlugin
from pygpt_net.plugin.audio_input import Plugin as AudioInputPlugin
from pygpt_net.plugin.cmd_api import Plugin as CmdApiPlugin
from pygpt_net.plugin.cmd_code_interpreter import Plugin as CmdCodeInterpreterPlugin
from pygpt_net.plugin.cmd_custom import Plugin as CmdCustomCommandPlugin
from pygpt_net.plugin.cmd_files import Plugin as CmdFilesPlugin
from pygpt_net.plugin.cmd_history import Plugin as CtxHistoryPlugin
from pygpt_net.plugin.cmd_serial import Plugin as CmdSerialPlugin
from pygpt_net.plugin.cmd_web import Plugin as CmdWebPlugin
from pygpt_net.plugin.crontab import Plugin as CrontabPlugin
from pygpt_net.plugin.extra_prompt import Plugin as ExtraPromptPlugin
from pygpt_net.plugin.idx_llama_index import Plugin as IdxLlamaIndexPlugin
from pygpt_net.plugin.openai_dalle import Plugin as OpenAIDallePlugin
from pygpt_net.plugin.openai_vision import Plugin as OpenAIVisionPlugin
from pygpt_net.plugin.real_time import Plugin as RealTimePlugin
from pygpt_net.plugin.agent import Plugin as AgentPlugin

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
from pygpt_net.provider.loaders.file_csv import Loader as CsvLoader  # file: CSV
from pygpt_net.provider.loaders.file_docx import Loader as DocxLoader  # file: DOCX
from pygpt_net.provider.loaders.file_epub import Loader as EpubLoader  # file: EPUB
from pygpt_net.provider.loaders.file_excel import Loader as ExcelLoader  # file: Excel
from pygpt_net.provider.loaders.file_json import Loader as JsonLoader  # file: JSON
from pygpt_net.provider.loaders.file_markdown import Loader as MarkdownLoader  # file: Markdown
from pygpt_net.provider.loaders.file_pdf import Loader as PdfLoader  # file: PDF
from pygpt_net.provider.loaders.file_xml import Loader as XmlLoader  # file: XML
from pygpt_net.provider.loaders.web_rss import Loader as RssLoader  # web: RSS feed
from pygpt_net.provider.loaders.web_sitemap import Loader as SitemapLoader  # web: Sitemap XML
from pygpt_net.provider.loaders.web_page import Loader as WebPageLoader  # web: Webpages
from pygpt_net.provider.loaders.web_yt import Loader as YouTubeLoader  # web: YouTube

# audio providers
from pygpt_net.provider.audio_input.openai_whisper import OpenAIWhisper
from pygpt_net.provider.audio_input.google_speech_recognition import GoogleSpeechRecognition
from pygpt_net.provider.audio_input.google_cloud_speech_recognition import GoogleCloudSpeechRecognition
from pygpt_net.provider.audio_input.bing_speech_recognition import BingSpeechRecognition
from pygpt_net.provider.audio_output.openai_tts import OpenAITextToSpeech
from pygpt_net.provider.audio_output.ms_azure_tts import MSAzureTextToSpeech
from pygpt_net.provider.audio_output.google_tts import GoogleTextToSpeech
from pygpt_net.provider.audio_output.eleven_labs import ElevenLabsTextToSpeech

# web search providers
from pygpt_net.provider.web.google_custom_search import GoogleCustomSearch
from pygpt_net.provider.web.microsoft_bing import MicrosoftBingSearch


def run(**kwargs):
    """
    PyGPT launcher.

    :param kwargs: keyword arguments for launcher

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

    First, create a custom launcher file, for example, "custom_launcher.py," and register your extensions in it.

    To register custom plugins create custom launcher, e.g. "custom_launcher.py" and:

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
    # initialize app launcher
    launcher = Launcher()
    launcher.init()

    # register audio providers
    launcher.add_audio_input(OpenAIWhisper())
    launcher.add_audio_input(GoogleSpeechRecognition())
    launcher.add_audio_input(GoogleCloudSpeechRecognition())
    launcher.add_audio_input(BingSpeechRecognition())
    launcher.add_audio_output(OpenAITextToSpeech())
    launcher.add_audio_output(MSAzureTextToSpeech())
    launcher.add_audio_output(GoogleTextToSpeech())
    launcher.add_audio_output(ElevenLabsTextToSpeech())

    # register custom audio providers
    providers = kwargs.get('audio_input', None)
    if isinstance(providers, list):
        for provider in providers:
            launcher.add_audio_input(provider)

    providers = kwargs.get('audio_output', None)
    if isinstance(providers, list):
        for provider in providers:
            launcher.add_audio_output(provider)

    # register web providers
    launcher.add_web(GoogleCustomSearch())
    launcher.add_web(MicrosoftBingSearch())

    # register custom web providers
    providers = kwargs.get('web', None)
    if isinstance(providers, list):
        for provider in providers:
            launcher.add_web(provider)

    # register base plugins
    launcher.add_plugin(AgentPlugin())
    launcher.add_plugin(RealTimePlugin())
    launcher.add_plugin(ExtraPromptPlugin())
    launcher.add_plugin(AudioInputPlugin())
    launcher.add_plugin(AudioOutputPlugin())
    launcher.add_plugin(CmdWebPlugin())
    launcher.add_plugin(CmdFilesPlugin())
    launcher.add_plugin(CmdCodeInterpreterPlugin())
    launcher.add_plugin(CmdCustomCommandPlugin())
    launcher.add_plugin(CmdApiPlugin())
    launcher.add_plugin(CmdSerialPlugin())
    launcher.add_plugin(CtxHistoryPlugin())
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
    launcher.add_loader(XmlLoader())
    launcher.add_loader(RssLoader())
    launcher.add_loader(SitemapLoader())
    launcher.add_loader(WebPageLoader())
    launcher.add_loader(YouTubeLoader())

    # register custom data loaders (llama-index)
    loaders = kwargs.get('loaders', None)
    if isinstance(loaders, list):
        for loader in loaders:
            launcher.add_loader(loader)

    # run app
    launcher.run()
    

if __name__ == '__main__':
    run()
