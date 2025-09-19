#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.19 00:00:00                  #
# ================================================== #

import os
import builtins
import io
import platform

import pygpt_net.icons_rc

from .utils import set_env

# app env
set_env("PYGPT_APP_ENV", "prod", allow_overwrite=True) # dev | prod

# debug
# set_env("QTWEBENGINE_REMOTE_DEBUGGING", 9222)
# set_env("QT_LOGGING_RULES", "*.debug=true")
# set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--enable-logging=stderr", True)
# set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--v=1", True)
# set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--renderer-process-limit=1", True)
# set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--process-per-site", "", True)
# set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--enable-precise-memory-info", "", True)
# set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--js-flags=--expose-gc", "", True)

# by default, optimize for low-end devices
set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--enable-low-end-device-mode", True)
set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--enable-gpu-rasterization", True)
set_env("QTWEBENGINE_CHROMIUM_FLAGS", "--ignore-gpu-blocklist", True)

# disable warnings
set_env("TRANSFORMERS_NO_ADVISORY_WARNINGS", 1)
set_env("QT_LOGGING_RULES", "qt.multimedia.ffmpeg=false;qt.qpa.fonts=false", allow_overwrite=True)

if platform.system() == 'Windows':
    set_env("QT_MEDIA_BACKEND", "windows")

_original_open = builtins.open

def open_wrapper(file, mode='r', *args, **kwargs):
    """
    Patch for `builtins.open` - issue #116
    Prevents attempts to open the .env file in the /home directory
    within a Snapcraft environment when executing `dotenv.load_dotenv()`.
    """
    path = str(file)
    if ("SNAP" in os.environ
            and "SNAP_NAME" in os.environ
            and os.environ["SNAP_NAME"] == "pygpt"):
        if path == '.env' or path.endswith('/.env'):
            if 'b' in mode:
                return io.BytesIO(b"")
            else:
                return io.StringIO("")
    return _original_open(file, mode, *args, **kwargs)

builtins.open = open_wrapper

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
from pygpt_net.plugin.cmd_system import Plugin as CmdSystemPlugin
from pygpt_net.plugin.cmd_web import Plugin as CmdWebPlugin
from pygpt_net.plugin.crontab import Plugin as CrontabPlugin
from pygpt_net.plugin.extra_prompt import Plugin as ExtraPromptPlugin
from pygpt_net.plugin.experts import Plugin as ExpertsPlugin
from pygpt_net.plugin.idx_llama_index import Plugin as IdxLlamaIndexPlugin
from pygpt_net.plugin.openai_dalle import Plugin as OpenAIDallePlugin
from pygpt_net.plugin.openai_vision import Plugin as OpenAIVisionPlugin
from pygpt_net.plugin.real_time import Plugin as RealTimePlugin
from pygpt_net.plugin.agent import Plugin as AgentPlugin
from pygpt_net.plugin.mailer import Plugin as MailerPlugin
from pygpt_net.plugin.google import Plugin as GooglePlugin
from pygpt_net.plugin.twitter import Plugin as TwitterPlugin
from pygpt_net.plugin.facebook import Plugin as FacebookPlugin
from pygpt_net.plugin.telegram import Plugin as TelegramPlugin
from pygpt_net.plugin.slack import Plugin as SlackPlugin
from pygpt_net.plugin.github import Plugin as GithubPlugin
from pygpt_net.plugin.bitbucket import Plugin as BitbucketPlugin
from pygpt_net.plugin.server import Plugin as ServerPlugin
from pygpt_net.plugin.tuya import Plugin as TuyaPlugin
from pygpt_net.plugin.wikipedia import Plugin as WikipediaPlugin
from pygpt_net.plugin.mcp import Plugin as MCPPlugin
from pygpt_net.plugin.wolfram import Plugin as WolframPlugin
from pygpt_net.plugin.osm import Plugin as OSMPlugin

# agents (Llama-index)
# from pygpt_net.provider.agents.llama_index.legacy.openai import OpenAIAgent
from pygpt_net.provider.agents.llama_index.legacy.openai_assistant import OpenAIAssistantAgent
# from pygpt_net.provider.agents.llama_index.legacy.planner import PlannerAgent
from pygpt_net.provider.agents.llama_index.planner_workflow import PlannerAgent as PlannerWorkflowAgent
from pygpt_net.provider.agents.llama_index.openai_workflow import OpenAIAgent as OpenAIWorkflowAgent
# from pygpt_net.provider.agents.llama_index.legacy.react import ReactAgent
from pygpt_net.provider.agents.llama_index.react_workflow import ReactWorkflowAgent
from pygpt_net.provider.agents.llama_index.codeact_workflow import CodeActAgent
from pygpt_net.provider.agents.llama_index.supervisor_workflow import SupervisorAgent as LlamaSupervisorAgent
from pygpt_net.provider.agents.openai.agent import Agent as OpenAIAgentsBase
from pygpt_net.provider.agents.openai.agent_with_experts import Agent as OpenAIAgentsExperts
from pygpt_net.provider.agents.openai.agent_with_experts_feedback import Agent as OpenAIAgentsExpertsFeedback
from pygpt_net.provider.agents.openai.agent_with_feedback import Agent as OpenAIAgentFeedback
from pygpt_net.provider.agents.openai.bot_researcher import Agent as OpenAIAgentBotResearcher
from pygpt_net.provider.agents.openai.agent_planner import Agent as OpenAIAgentPlanner
from pygpt_net.provider.agents.openai.evolve import Agent as OpenAIAgentsEvolve
from pygpt_net.provider.agents.openai.agent_b2b import Agent as OpenAIAgentsB2B
from pygpt_net.provider.agents.openai.supervisor import Agent as OpenAIAgentSupervisor

# LLM wrapper providers (langchain, llama-index, embeddings)
from pygpt_net.provider.llms.anthropic import AnthropicLLM
from pygpt_net.provider.llms.azure_openai import AzureOpenAILLM
from pygpt_net.provider.llms.deepseek_api import DeepseekApiLLM
from pygpt_net.provider.llms.google import GoogleLLM
# from pygpt_net.provider.llms.hugging_face import HuggingFaceLLM
from pygpt_net.provider.llms.hugging_face_api import HuggingFaceApiLLM
from pygpt_net.provider.llms.hugging_face_router import HuggingFaceRouterLLM
from pygpt_net.provider.llms.local import LocalLLM
from pygpt_net.provider.llms.mistral import MistralAILLM
from pygpt_net.provider.llms.ollama import OllamaLLM
from pygpt_net.provider.llms.openai import OpenAILLM
from pygpt_net.provider.llms.perplexity import PerplexityLLM
from pygpt_net.provider.llms.x_ai import xAILLM
from pygpt_net.provider.llms.open_router import OpenRouterLLM

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
from pygpt_net.provider.audio_input.google_genai import GoogleGenAIAudioInput
from pygpt_net.provider.audio_input.bing_speech_recognition import BingSpeechRecognition
from pygpt_net.provider.audio_output.openai_tts import OpenAITextToSpeech
from pygpt_net.provider.audio_output.ms_azure_tts import MSAzureTextToSpeech
from pygpt_net.provider.audio_output.google_tts import GoogleTextToSpeech
from pygpt_net.provider.audio_output.google_genai_tts import GoogleGenAITextToSpeech
from pygpt_net.provider.audio_output.eleven_labs import ElevenLabsTextToSpeech

# web search engine providers
from pygpt_net.provider.web.google_custom_search import GoogleCustomSearch
from pygpt_net.provider.web.microsoft_bing import MicrosoftBingSearch
from pygpt_net.provider.web.duckduck_search import DuckDuckGoSearch

# tools
from pygpt_net.tools.indexer import IndexerTool
from pygpt_net.tools.audio_transcriber import AudioTranscriber as AudioTranscriberTool
from pygpt_net.tools.code_interpreter import CodeInterpreter as CodeInterpreterTool
from pygpt_net.tools.image_viewer import ImageViewer as ImageViewerTool
from pygpt_net.tools.media_player import MediaPlayer as MediaPlayerTool
from pygpt_net.tools.text_editor import TextEditor as TextEditorTool
from pygpt_net.tools.html_canvas import HtmlCanvas as HtmlCanvasTool
from pygpt_net.tools.translator import Translator as TranslatorTool
# from pygpt_net.tools.agent_builder import AgentBuilder as AgentBuilderTool

def run(**kwargs):
    """
    PyGPT launcher.

    :param kwargs: keyword arguments for launcher

    PyGPT can be extended with:

    - Custom plugins
    - Custom LLM providers
    - Custom vector store providers
    - Custom data loaders
    - Custom audio input providers
    - Custom audio output providers
    - Custom web search engine providers
    - Custom tools
    - Custom agents

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
        from agents import CustomAgent

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
    launcher.add_audio_input(GoogleGenAIAudioInput())
    launcher.add_audio_input(BingSpeechRecognition())
    launcher.add_audio_output(OpenAITextToSpeech())
    launcher.add_audio_output(MSAzureTextToSpeech())
    launcher.add_audio_output(GoogleTextToSpeech())
    launcher.add_audio_output(GoogleGenAITextToSpeech())
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
    launcher.add_web(DuckDuckGoSearch())

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
    launcher.add_plugin(CmdSystemPlugin())
    launcher.add_plugin(CmdCustomCommandPlugin())
    launcher.add_plugin(CmdApiPlugin())
    launcher.add_plugin(CmdSerialPlugin())
    launcher.add_plugin(CmdMousePlugin())
    launcher.add_plugin(CtxHistoryPlugin())
    launcher.add_plugin(OpenAIDallePlugin())
    launcher.add_plugin(OpenAIVisionPlugin())
    launcher.add_plugin(IdxLlamaIndexPlugin())
    launcher.add_plugin(MailerPlugin())
    launcher.add_plugin(CrontabPlugin())
    launcher.add_plugin(GooglePlugin())
    launcher.add_plugin(TwitterPlugin())
    launcher.add_plugin(FacebookPlugin())
    launcher.add_plugin(TelegramPlugin())
    launcher.add_plugin(SlackPlugin())
    launcher.add_plugin(GithubPlugin())
    launcher.add_plugin(BitbucketPlugin())
    launcher.add_plugin(ServerPlugin())
    launcher.add_plugin(TuyaPlugin())
    launcher.add_plugin(WikipediaPlugin())
    launcher.add_plugin(MCPPlugin())
    launcher.add_plugin(WolframPlugin())
    launcher.add_plugin(OSMPlugin())

    # register custom plugins
    plugins = kwargs.get('plugins', None)
    if isinstance(plugins, list):
        for plugin in plugins:
            launcher.add_plugin(plugin)

    # register LLMs
    launcher.add_llm(OpenAILLM())
    launcher.add_llm(AzureOpenAILLM())
    launcher.add_llm(AnthropicLLM())
    launcher.add_llm(GoogleLLM())
    # launcher.add_llm(HuggingFaceLLM())
    launcher.add_llm(HuggingFaceApiLLM())
    launcher.add_llm(HuggingFaceRouterLLM())
    launcher.add_llm(LocalLLM())
    launcher.add_llm(MistralAILLM())
    launcher.add_llm(OllamaLLM())
    launcher.add_llm(DeepseekApiLLM())
    launcher.add_llm(PerplexityLLM())
    launcher.add_llm(xAILLM())
    launcher.add_llm(OpenRouterLLM())

    # register LLMs
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

    # register base agents
    # launcher.add_agent(OpenAIAgent())  # llama-index
    launcher.add_agent(OpenAIWorkflowAgent())  # llama-index
    launcher.add_agent(OpenAIAssistantAgent())  # llama-index
    # launcher.add_agent(PlannerAgent())  # llama-index
    launcher.add_agent(PlannerWorkflowAgent())  # llama-index
    # launcher.add_agent(ReactAgent())  # llama-index
    launcher.add_agent(ReactWorkflowAgent())  # llama-index
    launcher.add_agent(CodeActAgent())  # llama-index
    launcher.add_agent(LlamaSupervisorAgent())  # llama-index
    launcher.add_agent(OpenAIAgentsBase())  # openai-agents
    launcher.add_agent(OpenAIAgentsExperts())  # openai-agents
    launcher.add_agent(OpenAIAgentFeedback())  # openai-agents
    launcher.add_agent(OpenAIAgentPlanner())  # openai-agents
    launcher.add_agent(OpenAIAgentBotResearcher())  # openai-agents
    launcher.add_agent(OpenAIAgentsExpertsFeedback())  # openai-agents
    launcher.add_agent(OpenAIAgentsEvolve())  # openai-agents
    launcher.add_agent(OpenAIAgentsB2B())  # openai-agents
    launcher.add_agent(OpenAIAgentSupervisor())  # openai-agents

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
    launcher.add_tool(TranslatorTool())
    # launcher.add_tool(AgentBuilderTool())

    # register custom tools
    tools = kwargs.get('tools', None)
    if isinstance(tools, list):
        for tool in tools:
            launcher.add_tool(tool)

    # run the app
    launcher.run()
    

if __name__ == '__main__':
    run()
