#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.15 00:00:00                  #
# ================================================== #

from pygpt_net.launcher import Launcher

# plugins
from pygpt_net.plugin.voice_control import Plugin as VoiceControlPlugin
from pygpt_net.plugin.audio_output import Plugin as AudioOutputPlugin
from pygpt_net.plugin.audio_input import Plugin as AudioInputPlugin
from pygpt_net.plugin.cmd_api import Plugin as CmdApiPlugin
from pygpt_net.plugin.cmd_code_interpreter import Plugin as CmdCodeInterpreterPlugin
from pygpt_net.plugin.cmd_custom import Plugin as CmdCustomCommandPlugin
from pygpt_net.plugin.cmd_files import Plugin as CmdFilesPlugin
from pygpt_net.plugin.cmd_history import Plugin as CtxHistoryPlugin
from pygpt_net.plugin.cmd_mouse_control import Plugin as CmdMousePlugin
from pygpt_net.plugin.cmd_serial import Plugin as CmdSerialPlugin
from pygpt_net.plugin.cmd_web import Plugin as CmdWebPlugin
from pygpt_net.plugin.crontab import Plugin as CrontabPlugin
from pygpt_net.plugin.extra_prompt import Plugin as ExtraPromptPlugin
from pygpt_net.plugin.experts import Plugin as ExpertsPlugin
from pygpt_net.plugin.idx_llama_index import Plugin as IdxLlamaIndexPlugin
from pygpt_net.plugin.openai_dalle import Plugin as OpenAIDallePlugin
from pygpt_net.plugin.openai_vision import Plugin as OpenAIVisionPlugin
from pygpt_net.plugin.real_time import Plugin as RealTimePlugin
from pygpt_net.plugin.agent import Plugin as AgentPlugin

# agents (Llama-index)
from pygpt_net.provider.agents.openai import OpenAIAgent
from pygpt_net.provider.agents.openai_assistant import OpenAIAssistantAgent
from pygpt_net.provider.agents.planner import PlannerAgent
from pygpt_net.provider.agents.react import ReactAgent

# LLM wrapper providers (langchain, llama-index, embeddings)
from pygpt_net.provider.llms.anthropic import AnthropicLLM
from pygpt_net.provider.llms.azure_openai import AzureOpenAILLM
from pygpt_net.provider.llms.hugging_face import HuggingFaceLLM
from pygpt_net.provider.llms.google import GoogleLLM
from pygpt_net.provider.llms.ollama import OllamaLLM
from pygpt_net.provider.llms.openai import OpenAILLM

# vector store providers (llama-index)
from pygpt_net.provider.vector_stores.chroma import ChromaProvider
from pygpt_net.provider.vector_stores.elasticsearch import ElasticsearchProvider
from pygpt_net.provider.vector_stores.pinecode import PinecodeProvider
from pygpt_net.provider.vector_stores.redis import RedisProvider
from pygpt_net.provider.vector_stores.simple import SimpleProvider

# data loader providers (llama-index)
from pygpt_net.provider.loaders.file_csv import Loader as CsvLoader
from pygpt_net.provider.loaders.file_docx import Loader as DocxLoader
from pygpt_net.provider.loaders.file_epub import Loader as EpubLoader
from pygpt_net.provider.loaders.file_excel import Loader as ExcelLoader
from pygpt_net.provider.loaders.file_html import Loader as HtmlLoader
from pygpt_net.provider.loaders.file_image_vision import Loader as ImageVisionLoader
from pygpt_net.provider.loaders.file_ipynb import Loader as IPYNBLoader
from pygpt_net.provider.loaders.file_json import Loader as JsonLoader
from pygpt_net.provider.loaders.file_markdown import Loader as MarkdownLoader
from pygpt_net.provider.loaders.file_pdf import Loader as PdfLoader
from pygpt_net.provider.loaders.file_video_audio import Loader as VideoAudioLoader
from pygpt_net.provider.loaders.file_xml import Loader as XmlLoader
from pygpt_net.provider.loaders.web_bitbucket import Loader as BitbucketRepoLoader
from pygpt_net.provider.loaders.web_chatgpt_retrieval import Loader as ChatGptRetrievalLoader
from pygpt_net.provider.loaders.web_database import Loader as DatabaseLoader
from pygpt_net.provider.loaders.web_github_issues import Loader as GithubIssuesLoader
from pygpt_net.provider.loaders.web_github_repo import Loader as GithubRepoLoader
from pygpt_net.provider.loaders.web_google_calendar import Loader as GoogleCalendarLoader
from pygpt_net.provider.loaders.web_google_docs import Loader as GoogleDocsLoader
from pygpt_net.provider.loaders.web_google_drive import Loader as GoogleDriveLoader
from pygpt_net.provider.loaders.web_google_gmail import Loader as GoogleGmailLoader
from pygpt_net.provider.loaders.web_google_keep import Loader as GoogleKeepLoader
from pygpt_net.provider.loaders.web_google_sheets import Loader as GoogleSheetsLoader
from pygpt_net.provider.loaders.web_microsoft_onedrive import Loader as MicrosoftOneDriveLoader
from pygpt_net.provider.loaders.web_rss import Loader as RssLoader
from pygpt_net.provider.loaders.web_sitemap import Loader as SitemapLoader
from pygpt_net.provider.loaders.web_twitter import Loader as TwitterLoader
from pygpt_net.provider.loaders.web_page import Loader as WebPageLoader
from pygpt_net.provider.loaders.web_yt import Loader as YouTubeLoader

# audio providers (input, output)
from pygpt_net.provider.audio_input.openai_whisper import OpenAIWhisper
from pygpt_net.provider.audio_input.openai_whisper_local import OpenAIWhisperLocal
from pygpt_net.provider.audio_input.google_speech_recognition import GoogleSpeechRecognition
from pygpt_net.provider.audio_input.google_cloud_speech_recognition import GoogleCloudSpeechRecognition
from pygpt_net.provider.audio_input.bing_speech_recognition import BingSpeechRecognition
from pygpt_net.provider.audio_output.openai_tts import OpenAITextToSpeech
from pygpt_net.provider.audio_output.ms_azure_tts import MSAzureTextToSpeech
from pygpt_net.provider.audio_output.google_tts import GoogleTextToSpeech
from pygpt_net.provider.audio_output.eleven_labs import ElevenLabsTextToSpeech

# web search engine providers
from pygpt_net.provider.web.google_custom_search import GoogleCustomSearch
from pygpt_net.provider.web.microsoft_bing import MicrosoftBingSearch

# tools
from pygpt_net.tools.indexer import IndexerTool
from pygpt_net.tools.audio_transcriber import AudioTranscriber as AudioTranscriberTool
from pygpt_net.tools.code_interpreter import CodeInterpreter as CodeInterpreterTool
from pygpt_net.tools.image_viewer import ImageViewer as ImageViewerTool
from pygpt_net.tools.media_player import MediaPlayer as MediaPlayerTool
from pygpt_net.tools.text_editor import TextEditor as TextEditorTool
from pygpt_net.tools.html_canvas import HtmlCanvas as HtmlCanvasTool

def run(**kwargs):
    """
    PyGPT launcher.

    :param kwargs: keyword arguments for launcher

    PyGPT can be extended with:

    - Custom plugins
    - Custom LLM wrappers
    - Custom vector store providers
    - Custom data loaders
    - Custom audio input providers
    - Custom audio output providers
    - Custom web search engine providers
    - Custom tools

    - You can pass custom plugin instances, LLM wrappers, vector store providers and more to the launcher.
    - This is useful if you want to extend PyGPT with your own plugins, vector storage, LLMs, or other data providers.

    First, create a custom launcher file, for example, "custom_launcher.py," and register your extensions in it.

    To register a custom plugin - create the custom launcher, e.g. "custom_launcher.py" and:

    - Pass a list with the plugin instances as the 'plugins' keyword argument.

    To register a custom LLM wrapper:

    - Pass a list with the LLM wrapper instances as the 'llms' keyword argument.

    To register a custom vector store provider:

    - Pass a list with the vector store provider instances as the 'vector_stores' keyword argument.

    To register a custom data loader:

    - Pass a list with the data loader instances as the 'loaders' keyword argument.

    To register a custom audio input provider:

    - Pass a list with the audio input provider instances as the 'audio_input' keyword argument.

    To register a custom audio output provider:

    - Pass a list with the audio output provider instances as the 'audio_output' keyword argument.

    To register a custom web provider:

    - Pass a list with the web provider instances as the 'web' keyword argument.

    To register a custom agent:

    - Pass a list with the agent instances as the 'agents' keyword argument.

    To register a custom tool:

    - Pass a list with the tool instances as the 'tools' keyword argument.

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
        from tools import CustomTool

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
        agents = [
            CustomAgent(),
        ]
        tools = [
            CustomTool(),
        ]

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

    """
    # initialize app launcher
    launcher = Launcher()
    launcher.init()

    # register audio providers
    launcher.add_audio_input(OpenAIWhisper())
    launcher.add_audio_input(OpenAIWhisperLocal())
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

    # register base data loaders (llama-index)
    launcher.add_loader(CsvLoader())
    launcher.add_loader(DocxLoader())
    launcher.add_loader(EpubLoader())
    launcher.add_loader(ExcelLoader())
    launcher.add_loader(HtmlLoader())
    launcher.add_loader(ImageVisionLoader())
    launcher.add_loader(IPYNBLoader())
    launcher.add_loader(JsonLoader())
    launcher.add_loader(MarkdownLoader())
    launcher.add_loader(PdfLoader())
    launcher.add_loader(VideoAudioLoader())
    launcher.add_loader(XmlLoader())
    launcher.add_loader(RssLoader())
    launcher.add_loader(SitemapLoader())
    launcher.add_loader(BitbucketRepoLoader())
    launcher.add_loader(ChatGptRetrievalLoader())
    launcher.add_loader(DatabaseLoader())
    launcher.add_loader(GithubIssuesLoader())
    launcher.add_loader(GithubRepoLoader())
    launcher.add_loader(GoogleCalendarLoader())
    launcher.add_loader(GoogleDocsLoader())
    launcher.add_loader(GoogleDriveLoader())
    launcher.add_loader(GoogleGmailLoader())
    launcher.add_loader(GoogleKeepLoader())
    launcher.add_loader(GoogleSheetsLoader())
    launcher.add_loader(MicrosoftOneDriveLoader())
    launcher.add_loader(TwitterLoader())
    launcher.add_loader(WebPageLoader())
    launcher.add_loader(YouTubeLoader())

    # register custom data loaders (llama-index)
    loaders = kwargs.get('loaders', None)
    if isinstance(loaders, list):
        for loader in loaders:
            launcher.add_loader(loader)

    # register base plugins
    launcher.add_plugin(VoiceControlPlugin())
    launcher.add_plugin(AgentPlugin())
    launcher.add_plugin(RealTimePlugin())
    launcher.add_plugin(ExpertsPlugin())
    launcher.add_plugin(ExtraPromptPlugin())
    launcher.add_plugin(AudioInputPlugin())
    launcher.add_plugin(AudioOutputPlugin())
    launcher.add_plugin(CmdWebPlugin())
    launcher.add_plugin(CmdFilesPlugin())
    launcher.add_plugin(CmdCodeInterpreterPlugin())
    launcher.add_plugin(CmdCustomCommandPlugin())
    launcher.add_plugin(CmdApiPlugin())
    launcher.add_plugin(CmdSerialPlugin())
    launcher.add_plugin(CmdMousePlugin())
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
    launcher.add_llm(GoogleLLM())
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

    # register base llama-index agents
    launcher.add_agent(OpenAIAgent())
    launcher.add_agent(OpenAIAssistantAgent())
    launcher.add_agent(PlannerAgent())
    launcher.add_agent(ReactAgent())

    # register custom agents
    agents = kwargs.get('agents', None)
    if isinstance(agents, list):
        for agent in agents:
            launcher.add_agent(agent)

    # register base tools
    launcher.add_tool(IndexerTool())
    launcher.add_tool(MediaPlayerTool())
    launcher.add_tool(ImageViewerTool())
    launcher.add_tool(TextEditorTool())
    launcher.add_tool(AudioTranscriberTool())
    launcher.add_tool(CodeInterpreterTool())
    launcher.add_tool(HtmlCanvasTool())

    # register custom tools
    tools = kwargs.get('tools', None)
    if isinstance(tools, list):
        for tool in tools:
            launcher.add_tool(tool)

    # run the app
    launcher.run()
    

if __name__ == '__main__':
    run()
