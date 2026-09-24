Introduction
=============

Overview
----------------

**PyGPT** is an open-source desktop AI assistant for ``Linux``, ``Windows`` and ``macOS``. It supports models from ``OpenAI`` (``GPT-6 Astra``, ``GPT-5.6``, ``GPT-4``, etc.), ``Google Gemini``, ``Anthropic Claude``, ``xAI Grok``, ``Perplexity / Sonar``, ``DeepSeek``, plus models available through ``HuggingFace``, ``LlamaIndex``, OpenAI-compatible APIs, and local ``Ollama`` installations such as ``DeepSeek``, ``Qwen``, ``gpt-oss``, ``Gemma``, ``Mistral``, ``Llama``, and others.

Beyond chat, PyGPT includes Agents with Chat, Orchestrator and Swarm workflows, Agent Skills, plugins and MCP connectors, RAG, files and attachments, Python/IPython and system tools, web search, vision and camera input, image and video generation, Computer use, realtime voice, speech input/output, memory, automation, and external integrations. Models can use local and remote tools, work with files, call APIs, and control the desktop or browser when enabled.

*Dark theme*

.. image:: images/v2_main.png
   :width: 800


*Light theme*

.. image:: images/v2_light.png
   :width: 800

Features
---------
* Desktop AI assistant for ``Linux``, ``Windows`` and ``macOS``, written in Python.
* Runs as a local desktop application with a ChatGPT-like conversational interface.
* Work modes include Chat, Agents, Realtime + audio, Research, Completion, Image and Video generation, Computer use, Experts, Autonomous mode, plus legacy Agent modes.
* Supports ``OpenAI GPT-6 Astra``, ``GPT-5.6``, ``GPT-4``, ``Google Gemini``, ``Anthropic Claude``, ``xAI Grok``, ``DeepSeek V3/R1``, ``Perplexity / Sonar``, and models available through ``LlamaIndex`` and ``Ollama``, including ``DeepSeek``, ``Qwen``, ``gpt-oss``, ``Gemma``, ``Mistral``, ``Llama``, and others.
* Integrated ``LlamaIndex`` RAG for files, webpages, Google/GitHub data, media, images, conversation history, and formats such as ``txt``, ``pdf``, ``csv``, ``html``, ``md``, ``docx``, ``json``, ``epub``, ``xlsx``, and ``xml``.
* Built-in vector-store support with automatic file, database-context, and data embedding.
* Image generation with models such as ``gpt-image``, ``Imagen``, ``Gemini``, and ``Nano Banana``.
* Video generation with models such as ``Veo3`` and ``Sora2``.
* Web search via ``DuckDuckGo``, ``Google``, ``Microsoft Bing`` and remote web search.
* Speech synthesis via ``OpenAI``, ``Microsoft Azure``, ``Google Cloud / GenAI``, ``Eleven Labs``, and ``xAI``.
* Speech recognition via ``OpenAI Whisper`` (API or local), ``Google / Google Cloud / GenAI``, ``Microsoft Bing``, and ``xAI Grok Voice``.
* Extensible plugin system with ``Files I/O``, ``Python interpreter``, ``Web search``, ``Google``, ``Facebook``, ``X/Twitter``, ``Slack``, ``Telegram``, ``GitHub``, ``MCP``, and more.
* Model Context Protocol (MCP) support.
* Built-in ``MCP Connectors`` manager with catalog browsing and import from Claude, Codex, OpenClaw, Cursor, VS Code, OpenCode, MCPorter, and generic JSON/TOML/YAML configurations.
* Agents multi-agent workflows with Chat, Orchestrator, and Swarm runtimes.
* Project-specific ``AGENTS.md`` rules for the main Agents agent.
* Portable ``SKILL.md``-based ``Agent Skills`` with GitHub/local import, catalog browsing, per-profile enable/disable, and on-demand loading.
* Built-in ``Python/OS`` tool for real-time Python, IPython, and system command execution.
* Built-in real-time ``Canvas`` with annotation support and web browser integration for interactive workflows.
* Camera capture for real-time image input in Chat and other supported modes.
* Image analysis with vision-capable models.
* Accessibility features including keyboard shortcuts, voice control, and spoken descriptions of on-screen actions.
* Conversation history with short- and long-term memory support.
* Integrated calendar, day notes, and conversation search by date.
* Tool and command execution through plugins, including filesystem, Python/OS, and system commands.
* User-defined custom commands and scripts exposed as tools.
* Built-in Crontab / Task scheduler.
* File and attachment upload, download, organization, and processing.
* Reopen and continue previous conversations, with optional experimental advanced context handling for very long chats.
* Editable prompt and model presets for reusable configurations.
* Desktop UI designed for direct, practical use.
* Built-in notepad.
* Built-in painter / drawing tool.
* Node-based Agent Builder (Legacy) for older agent modes.
* Multi-language interface support.
* No prior AI-model experience required.
* Extensive configuration options.
* Theme support.
* Real-time code syntax highlighting.
* Built-in token usage estimation and reporting.
* **Open source**; source code is available on ``GitHub``.
* Uses the user's own provider API keys.
* and many more.

PyGPT is free and open source. Cloud providers use your own API credentials; local models such as those served through ``Ollama`` do not require external API keys. Additional credentials may be required for specific providers and integrations.

.. note::
   This application is not officially associated with OpenAI. The author shall not be held liable for any damages 
   resulting from the use of this application. It is provided "as is," without any form of warranty. 
   Users are reminded to be mindful of token usage - always verify the number of tokens utilized by the model on 
   the API website and engage with the application responsibly. Activating plugins, such as Web search, 
   may consume additional tokens that are not displayed in the main window. 
   **Always monitor your actual token usage on the OpenAI, Google, Anthropic, etc. websites.**
