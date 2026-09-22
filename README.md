# PyGPT - Desktop AI Assistant

[![pygpt](https://snapcraft.io/pygpt/badge.svg)](https://snapcraft.io/pygpt)

Release: **2.8.28** | build: **2026-09-22** | Python: **>=3.10, <3.14**

> Official website: https://pygpt.net | [Documentation](https://pygpt.readthedocs.io) | [Discord](https://pygpt.net/discord)
> 
> Get it from: [PyPi](https://pypi.org/project/pygpt-net) | [Snap Store](https://snapcraft.io/pygpt) | [Microsoft Store](https://apps.microsoft.com/detail/XP99R4MX3X65VQ) | [AppImage](https://github.com/szczyglis-dev/py-gpt/releases)
> 
> Compiled version for Linux and Windows: [Download](https://pygpt.net/#download) (64-bit)
> 
> Donate: [Buy Me A Coffee](https://www.buymeacoffee.com/szczyglis) | [GitHub Sponsors](https://github.com/sponsors/szczyglis-dev) | [PayPal](https://pygpt.net/donate/paypal)

## Overview

**PyGPT** is an open-source desktop AI assistant for `Linux`, `Windows` and `macOS`. It supports models from `OpenAI` (`GPT-6 Astra`, `GPT-5.6`, `GPT-4`, etc.), `Google Gemini`, `Anthropic Claude`, `xAI Grok`, `Perplexity / Sonar`, `DeepSeek`, plus models available through `HuggingFace`, `LlamaIndex`, OpenAI-compatible APIs, and local `Ollama` installations such as `DeepSeek`, `Qwen`, `gpt-oss`, `Gemma`, `Mistral`, `Llama`, and others.

Beyond chat, PyGPT includes **Chat with Agents** with Chat, Orchestrator and Swarm workflows, Agent Skills, plugins and MCP connectors, RAG, files and attachments, Python/IPython and system tools, web search, vision and camera input, image and video generation, Computer use, realtime voice, speech input/output, memory, automation, and external integrations. Models can use local and remote tools, work with files, call APIs, and control the desktop or browser when enabled.

**Screenshots** (version `2.8.23`, build `2026-09-17`):

Dark theme:
![v2_main](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_main.png)

Light theme:
![v2_light](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_light.png)

You can download compiled 64-bit versions for Windows and Linux here: https://pygpt.net/#download

## Features

- Desktop AI assistant for `Linux`, `Windows` and `macOS`, written in Python.
- Runs as a local desktop application with a ChatGPT-like conversational interface.
- Work modes include Chat, Chat with Agents, Realtime + audio, Research, Completion, Image and Video generation, Computer use, Experts, Autonomous mode, plus legacy Agent modes.
- Supports `OpenAI GPT-6 Astra`, `GPT-5.6`, `GPT-4`, `Google Gemini`, `Anthropic Claude`, `xAI Grok`, `DeepSeek V3/R1`, `Perplexity / Sonar`, and models available through `LlamaIndex` and `Ollama`, including `DeepSeek`, `Qwen`, `gpt-oss`, `Gemma`, `Mistral`, `Llama`, and others.
- Integrated `LlamaIndex` RAG for files, webpages, Google/GitHub data, media, images, conversation history, and formats such as `txt`, `pdf`, `csv`, `html`, `md`, `docx`, `json`, `epub`, `xlsx`, and `xml`.
- Built-in vector-store support with automatic file, database-context, and data embedding.
- Image generation with models such as `gpt-image`, `Imagen`, `Gemini`, and `Nano Banana`.
- Video generation with models such as `Veo3` and `Sora2`.
- Web search via `DuckDuckGo`, `Google`, and `Microsoft Bing`.
- Speech synthesis via `OpenAI`, `Microsoft Azure`, `Google Cloud / GenAI`, `Eleven Labs`, and `xAI`.
- Speech recognition via `OpenAI Whisper` (API or local), `Google / Google Cloud / GenAI`, `Microsoft Bing`, and `xAI Grok Voice`.
- Extensible plugin system with `Files I/O`, `Python interpreter`, `Web search`, `Google`, `Facebook`, `X/Twitter`, `Slack`, `Telegram`, `GitHub`, `MCP`, and more.
- Model Context Protocol (MCP) support.
- Built-in **MCP Connectors** manager with catalog browsing and import from Claude, Codex, OpenClaw, Cursor, VS Code, OpenCode, MCPorter, and generic JSON/TOML/YAML configurations.
- **Chat with Agents** multi-agent workflows with Chat, Orchestrator, and Swarm runtimes.
- Project-specific `AGENTS.md` rules for the main Chat with Agents agent.
- Portable `SKILL.md`-based **Agent Skills** with GitHub/local import, catalog browsing, per-profile enable/disable, and on-demand loading.
- Built-in **Python/OS** tool for real-time Python, IPython, and system command execution.
- Camera capture for real-time image input in Chat and other supported modes.
- Image analysis with vision-capable models.
- Accessibility features including keyboard shortcuts, voice control, and spoken descriptions of on-screen actions.
- Conversation history with short- and long-term memory support.
- Integrated calendar, day notes, and conversation search by date.
- Tool and command execution through plugins, including filesystem, Python/OS, and system commands.
- User-defined custom commands and scripts exposed as tools.
- Built-in Crontab / Task scheduler.
- File and attachment upload, download, organization, and processing.
- Reopen and continue previous conversations, with optional **experimental** advanced context handling for very long chats.
- Editable prompt and model presets for reusable configurations.
- Desktop UI designed for direct, practical use.
- Built-in notepad.
- Built-in painter / drawing tool.
- Node-based Agent Builder (Legacy) for older agent modes.
- Multi-language interface support.
- No prior AI-model experience required.
- Extensive configuration options.
- Theme support.
- Real-time code syntax highlighting.
- Built-in token usage estimation and reporting.
- **Open source**; source code is available on `GitHub`.
- Uses the user's own provider API keys.
- and many more.

PyGPT is free and open source. Cloud providers use your own API credentials; local models such as those served through `Ollama` do not require external API keys. Additional credentials may be required for specific providers and integrations.

# Installation

## Prebuilt binaries (Windows / Linux)

**[Download PyGPT](https://pygpt.net/#download)**

Prebuilt 64-bit packages are the simplest way to run PyGPT:

- **Windows 10/11:** MSI installer.
- **Linux:** prebuilt archive; requires `GLIBC >= 2.35`.
- **macOS:** use the PyPI or source installation below.

## Microsoft Store (Windows)

PyGPT is also available from Microsoft Store:

[![Get it from Microsoft Store](https://get.microsoft.com/images/en-us%20dark.svg)](https://apps.microsoft.com/detail/XP99R4MX3X65VQ)

## AppImage (Linux)

**[Download the latest AppImage from GitHub Releases](https://github.com/szczyglis-dev/py-gpt/releases)**

Make it executable before the first run:

```bash
chmod +x ./PyGPT-X.X.X-x86_64.AppImage
```

Optional incremental updates are available through [AppImageUpdate](https://github.com/AppImage/AppImageUpdate):

```bash
appimageupdatetool ./PyGPT-X.X.X-x86_64.AppImage
```

## Snap Store (Linux)

Install from Snap Store:

```commandline
sudo snap install pygpt
```

Update an existing installation with:

```commandline
sudo snap refresh pygpt
```

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/pygpt)

Optional Snap interfaces are required only for the corresponding features.

Camera:

```commandline
sudo snap connect pygpt:camera
```

Microphone:

```commandline
sudo snap connect pygpt:audio-record :audio-record
sudo snap connect pygpt:alsa
```

Audio output:

```commandline
sudo snap connect pygpt:audio-playback
sudo snap connect pygpt:alsa
```

Docker sandbox:

```commandline
sudo snap connect pygpt:docker-executables docker:docker-executables
sudo snap connect pygpt:docker docker:docker-daemon
```

## PyPI (pip)

Requires Python `>=3.10, <3.14`. A virtual environment is recommended:

```commandline
python3 -m venv venv
source venv/bin/activate
```

Install and run PyGPT:

```commandline
pip install pygpt-net
pygpt
```

## Running from GitHub source code

Clone the repository and install the requirements in a virtual environment:

```commandline
git clone https://github.com/szczyglis-dev/py-gpt.git
cd py-gpt
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 run.py
```

### Poetry

Poetry can be used instead of `pip`:

```commandline
git clone https://github.com/szczyglis-dev/py-gpt.git
cd py-gpt
pip install poetry
poetry env use python3.10
poetry shell
poetry install
poetry run python3 run.py
```

For Poetry `>=2.0`, activate the environment with:

```commandline
poetry env use python3.10
poetry env activate
```

**Tip:** You can use `PyInstaller` to create a compiled version of the application (required version `6.4.0`).

### Troubleshooting

If you have a problems with `xcb` plugin with newer versions of PySide on Linux, e.g. like this:

```commandline
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. 
Reinstalling the application may fix this problem.
```

...then install `libxcb`:

```commandline
sudo apt install libxcb-cursor0
```

If you have a problems with audio on Linux, then try to install `portaudio19-dev` and/or `libasound2`:

```commandline
sudo apt install portaudio19-dev
```

```commandline
sudo apt install libasound2
sudo apt install libasound2-data 
sudo apt install libasound2-plugins
```

**Problems with GLIBC on Linux**

If you encounter error: 

```commandline
Error loading Python lib libpython3.10.so.1.0: dlopen: /lib/x86_64-linux-gnu/libm.so.6: version GLIBC_2.35 not found (required by libpython3.10.so.1.0)
```
when trying to run the compiled version for Linux, try updating GLIBC to version `2.35`, or use a newer operating system that has at least version `2.35` of GLIBC.

**Snap and AppArmor permission denied**

Snap installs AppArmor profiles for each application by default. The profile for PyGPT is created at:

`/var/lib/snapd/apparmor/profiles/snap.pygpt.pygpt`

The application should work with the default profile; however, if you encounter errors like:

`PermissionError: [Errno 13] Permission denied: '/etc/httpd/conf/mime.types'`

add the appropriate access rules to the profile file, for example:

```
# /var/lib/snapd/apparmor/profiles/snap.pygpt.pygpt

...

/etc/httpd/conf/mime.types r
```

and reload the profiles.

Alternatively, you can try removing snap and reinstalling it:

`sudo snap remove --purge pygpt`

`sudo snap install pygpt`


**Access to a microphone and audio in Windows version:**

If you have a problems with audio or a microphone in the non-binary PIP/Python version on Windows, check to see if FFmpeg is installed. If it's not, install it and add it to the PATH. You can find a tutorial on how to do this here: https://phoenixnap.com/kb/ffmpeg-windows. The binary version already includes FFmpeg.

**Windows and VC++ Redistributable**

On Windows, the proper functioning requires the installation of the `VC++ Redistributable`, which can be found on the Microsoft website:

https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist

The libraries from this environment are used by `PySide6` - one of the base packages used by PyGPT. 
The absence of the installed libraries may cause display errors or completely prevent the application from running.

It may also be necessary to add the path `C:\path\to\venv\Lib\python3.x\site-packages\PySide6` to the `PATH` variable.

**WebEngine/Chromium renderer and OpenGL problems**

If you have a problems with `WebEngine / Chromium` renderer you can try to disable OpenGL hardware acceleration with command line arguments:

``` ini
python3 run.py --disable-gpu=1
```

You can also manually disable hardware acceleration by editing config file - open the `%WORKDIR%/config.json` config file in editor and set the following options:

``` json
"render.open_gl": false,
```

## Other requirements

For API-based models, an internet connection and the appropriate provider API key are required. Models from OpenAI, Google, Anthropic, and xAI require API keys for their respective providers. Local models, such as those served through Ollama, do not require external API keys.

## Troubleshooting and diagnostics

See [Debugging and Logging](#debugging-and-logging) for logging and diagnostic options.


# Quick Start

## Setting-up API Key(s)

You can configure API keys for various providers, such as OpenAI, Anthropic, Google, xAI, Perplexity, OpenRouter, and more. This flexibility allows you to use different providers based on your needs.

During the initial setup, configure your API keys within the application.

To do so, navigate to the menu:

`Config -> Settings -> API Keys`

Here, you can add or manage API keys for any supported provider.

![v2_api_keys](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_api_keys.png)

**Configuring Provider**

1. **Select the Provider:** Choose a tab with provider.
2. **Enter the API Key:** Paste the corresponding API key for the selected provider.

**Example**

- **OpenAI:** Obtain your API key by registering on the OpenAI website: https://platform.openai.com and navigating to https://platform.openai.com/account/api-keys.
- **Anthropic, Google, xAPI, Perplexity, OpenRouter, etc.:** Follow similar steps on their respective platforms.

For a local or other OpenAI-compatible model, you can configure credentials per model in
   ``Config -> Models -> Editor`` using ``API base`` and ``API key``. This avoids having to
   reuse the global OpenAI endpoint/API key for that model.

**Note:** The ability to use models or services depends on your access level with the respective provider. If you wish to use custom API endpoints or local APIs that do not require API keys, simply enter any value into the API key field to bypass prompts about an empty key.

**Adding a custom OpenAI-compatible provider**

PyGPT includes built-in support for many popular model providers. If the provider you want to use is not available in the default provider list, you can add it manually under `Settings -> Custom providers`. The only requirement is that it exposes an OpenAI-compatible API.

# Modes

## Chat

In **PyGPT**, this mode lets you chat with models such as `GPT-6 Astra`, `GPT-5.6`, `Claude`, `Gemini`, `Grok`, `Sonar (Perplexity)`, `DeepSeek`, and many others, including local models running through `Ollama`.

The Chat mode supports regular conversations as well as more advanced tasks, including calling tools, executing Python code, using external integrations through MCP, searching the web, uploading and analyzing attachments, working with images, and generating new images. Depending on the selected model and enabled tools, it can also perform multi-step tasks that combine several of these capabilities in a single conversation.

PyGPT, in this and other modes, can use native SDKs provided by popular AI providers such as OpenAI, Google, Anthropic, and xAI. It also supports OpenAI-compatible `Chat Completions API` endpoints, custom providers, and providers available through LlamaIndex integrations. Both cloud-based and locally hosted models are supported, allowing PyGPT to work with a wide range of commercial, self-hosted, and local AI backends.

Currently built-in native clients:

- Anthropic SDK
- OpenAI SDK
- Google GenAI SDK
- xAI SDK

The main window is divided into several sections: tabs at the top, the main chat area in the center, the user input at the bottom, conversation history on the left, and the Toolbox with additional tools and options on the right. PyGPT also supports split-screen mode, allowing you to work with multiple conversations side by side.

![v2_mode_chat](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_mode_chat.png)

At the bottom of the chat window, PyGPT also shows an estimated number of tokens that will be sent to the model, as well as the number of tokens used for each generated response.

**Attachments:** You can attach and upload files from the input area. See [Files and Attachments](#files-and-attachments) for supported formats and attachment modes.

![attachment](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/attachment.png)


**RAG:** At the bottom of the toolbox, use the **RAG** selector to choose an index for additional context. When a valid index is selected, Chat is routed from the normal native/OpenAI-compatible SDK path to the LlamaIndex RAG runtime automatically. Select `---` to use the normal Chat provider path. See [Indexing and RAG](#indexing-and-rag) for RAG modes, indexing, project indexes, vector stores, and retrieval configuration.

![rag](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/rag.png)

**Vision:** If the selected model is multimodal and supports image input, vision is available natively by default. For models without native vision support, enable the `Vision (inline)` plugin to automatically route image analysis through a configured vision-capable model.

Images can be analyzed in real time from attachments, the camera enabled from the `Audio / Video` menu, or screenshots captured directly from the application. You can also use the built-in drawing tool to quickly sketch, annotate images, add arrows and markings, and send the result directly for analysis.

![v3_vision_chat](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v3_vision_chat.png)

**Image generation:** If you want to generate images directly in chat, enable the `Image generation (inline)` plugin in the Plugins menu. The plugin allows you to generate images in Chat mode.

For supported models/providers, you can alternatively enable the provider-side image-generation remote tool in `Config -> Settings -> Remote Tools`. When available, this lets the model generate images natively without the inline plugin.

## Chat with Agents

**Chat with Agents** is PyGPT's multi-agent work mode for tasks that benefit from delegation, parallel execution, tool use, verification, and specialist workers. It uses a dedicated runtime built on LlamaIndex agent workflows and is separate from the older `Agent (LlamaIndex)` and `Agent (OpenAI)` modes, as well as from the separate `Autonomous mode`.

The **Workflow** selector below the system prompt lets you choose how the agent workflow operates. The default is **Chat**.

### Agent workflows

- **Chat** - the default mode. The primary agent responds directly and can delegate tasks to workers when useful.
- **Orchestrator** - coordinates specialist workers for structured, multi-step tasks. The default limit is `16` workers; set **Max workers (Chat / Orchestrator)** to `0` for no limit.
- **Swarm** - launches the number of workers requested by the user and reports aggregate progress. Swarm has no built-in worker-count limit.

> **Warning:** Large swarms can generate high API/token usage and many concurrent tool operations. Use a reasonable worker count, especially when tools can modify files or execute commands.


### Agent Workflows

Open `Config -> Agent Workflows...` or use the settings icon in the Chat with Agents toolbox. The built-in **Chat**, **Orchestrator**, and **Swarm** profiles cannot be deleted; their prompts can be customized while their runtime type remains fixed.

Use **New** to create a custom profile and choose **Primary agent**, **Orchestrator**, or **Swarm** as its runtime. Custom profiles use only the prompt you provide. **From defaults** loads the built-in prompt for the selected runtime as a starting point. Older custom profiles without a runtime setting continue to use **Orchestrator**.

### Agent Workflow monitor

The built-in **Agent Workflow** tool shows the active Chat with Agents run as a tree/timeline with agents, status changes and tool calls. Open it from `Tools -> Agent Workflow` or pin it in an output tab. A new top-level run clears the previous view automatically.

### Project rules with AGENTS.md

Before processing the user input, the top-level Chat with Agents main agent checks for `%workdir%/AGENTS.md` in the active conversation's data workdir. If the file exists and is not empty, its UTF-8 content is appended to the main system prompt as additional project rules. The path follows the conversation/project that started the run, including a custom project data workdir.

`AGENTS.md` is read once per run and is not persisted to conversation history. A symlink that resolves outside the active workdir is ignored. The rules apply only to the top-level **Chat with Agents** main agent; they are not automatically injected into workers or Experts.

### Tools and provider capabilities

Chat with Agents can use both local and provider-side capabilities:

- **Local tools** from enabled PyGPT plugins can be made available to the primary agent/orchestrator and workers.
- **Remote tools** exposed by the selected provider can be made available when supported by the provider/model and enabled in PyGPT.
- Local and remote tools can be enabled or disabled independently in the Chat with Agents preset with **Allow local tools** and **Allow remote tools**.
- Models with native function calling use it when available; the runtime can fall back to a ReAct agent for compatible models without native function calling.

Local plugin execution is integrated with the normal PyGPT command/tool system, so enabled plugins can provide filesystem access, Python interpreter, system commands, web search, custom commands, integrations, and other capabilities according to their own configuration and security restrictions.

### Settings

Agent-related application settings are organized under `Settings -> Agents and experts`. The **Chat with Agents** section contains settings for this workflow. **Show full tool-chain in Chat with Agents** is disabled by default; when enabled, the final response stores and displays the complete chain of normal tool calls executed during the workflow, with a separate expandable Request/Response pair for each call. Internal orchestration and worker-management calls are not included.

**Display full agent workflow** is disabled by default. When enabled, completed Chat with Agents turns keep the full visible sequence of persisted agent partial responses in the chat, followed by the final response, both immediately after completion and after reloading the conversation. When disabled, completed turns are collapsed to the authoritative final response only. This option affects UI rendering only and does not change database storage or the separate model-facing history policy below.

**Restore full workflow history on next request** controls what is sent back to the main agent from completed Chat with Agents turns on later requests. It is enabled by default for backward compatibility. When enabled, PyGPT restores the full persisted workflow, including intermediate main-agent output and worker results, which can improve continuity and accuracy but uses more input tokens. When disabled, only the final response from each completed turn is restored. The complete workflow remains stored in the database and available to the UI, but omitting it from model-facing history saves tokens at the cost of less detailed workflow context. The live history token estimate and Advanced Context Handling checkpoint sizing/snapshots use the same policy.

The same section also exposes worker-count and iteration limits used by the Chat with Agents runtime:

- **Max iterations (Chat / Orchestrator)** - maximum number of main-agent iterations in Chat and Orchestrator modes. Default: `48`.
- **Max workers (Chat / Orchestrator)** - maximum number of worker agents that can be created in Chat and Orchestrator workflows. Default: `16`; set `0` for unlimited. This setting does not limit Swarm size.
- **Max iterations (Swarm)** - maximum number of main-agent/orchestrator iterations in Swarm mode. Default: `4096`.
- **Worker max iterations** - maximum number of iterations for each worker agent, regardless of the selected Chat with Agents mode. Default: `24`.

For all four limits, `0` means **unlimited**. The three iteration settings control internal agent reasoning/tool-call cycles, not user conversation turns; the worker limit controls how many worker agents may be created in a Chat or Orchestrator workflow. Raising or removing these limits can substantially increase API usage, token consumption, execution time, and the number of tool operations. **Swarm** keeps its separately declared worker count and is not constrained by the Chat/Orchestrator worker limit.

Settings kept only for older agent implementations are separated into the **Options** tab. **Display full agent output in chat view** controls rendering of full output from legacy agent modes, while **Display a tray notification when the goal is achieved** controls legacy agent completion notifications. These options do not control the Chat with Agents tool-chain display.

### RAG, attachments and artifacts

If a valid index is selected in the preset, Chat with Agents exposes it as a RAG query tool. User attachments and extracted attachment context are shared with the workflow, and image attachments are also passed as native image input when the selected model supports images. Files, images, URLs and attachments produced by workers or provider-side tools are collected by the runtime and propagated to the main response.

### Memory and worker lifecycle

The user-facing primary agent or orchestrator keeps hidden conversation memory across turns in the current conversation/preset, subject to the normal PyGPT token-window limits. For completed Chat with Agents turns, **Restore full workflow history on next request** determines whether later requests receive the full stored workflow or only the final response. Worker memory inside the active workflow is runtime-local and can be retained when the same worker is reused during that workflow.

The worker-management model depends on the selected mode:

- **Chat** delegates individual tasks to workers through the primary agent, without exposing the full orchestration lifecycle as the main interaction pattern.
- **Orchestrator** uses explicit worker-management operations to create, update, run, inspect, wait for, stop, and remove workers, and finalizes the workflow only after required worker activity has been resolved.
- **Swarm** extends the orchestrator flow with swarm initialization and aggregate swarm status. It tracks the requested number of workers, numbers them for status output, and reports collective progress while they are running.

### Recommended use cases

Use **Chat** for general agent conversations and tasks where delegation is occasional. Use **Orchestrator** for controlled multi-step work such as coding, file operations, research with independent verification, RAG-assisted analysis, implementation plus testing, or workflows combining several tools. Use **Swarm** when a task genuinely benefits from many parallel, independent workers and you intentionally want to control the swarm size yourself.

### Agent Skills

PyGPT supports portable **Agent Skills** built around `SKILL.md`, with optional scripts, references and assets. Skills can be imported from GitHub, local files/folders, `.skill`, ZIP or TAR packages.

Use the **Skills** menu to browse, install, enable, disable and remove skills. In **Chat with Agents**, enabled skills are loaded on demand so their full instructions do not have to be included in every prompt.

Skills do not bypass normal tool permissions or sandbox/security rules. Review third-party instructions and executable files before using them.

See the **Agent Skills** documentation for supported formats, resources and runtime behavior.

## Realtime + audio

This mode provides native, low-latency voice conversations with **OpenAI Realtime**, **Google Gemini Live**, and **xAI Grok** real-time models. Audio is streamed directly between PyGPT and the selected provider without the regular audio input/output plugins.

The audio toolbox provides two options for controlling voice turns:

- **Auto (VAD)** - enables automatic voice activity detection. While you speak, microphone audio is streamed to the active real-time model/provider, which detects when speech starts and when you stop speaking. The turn is then committed automatically and the model can respond without requiring you to manually stop the recording.
- **Loop** - automatically starts microphone recording again after the model finishes playing its audio response. This enables continuous back-and-forth voice conversation without having to click the microphone button before every next turn. When used together with **Auto (VAD)**, each new turn can start automatically and end automatically when you stop speaking.


## Research

**Research** is a provider-aware mode designed for models and APIs specialized in web research, information gathering, and deep-research workflows. It is intended for tasks that require searching multiple sources, collecting and comparing information, and producing more comprehensive, source-grounded answers.

Depending on the selected model and provider, PyGPT can use Perplexity Sonar research models as well as other provider-specific research paths, including Google Deep Research through the **Interactions API**. The exact workflow, available tools, and research capabilities depend on the selected provider and model.

> **Current limitation:** Regular tool calls are temporarily disabled in **Research** mode. RAG can still be selected, but support is provider/model-dependent and may not work correctly with some research models or provider-specific research APIs. Verify the response when indexed RAG context is required.

## Completion

An older mode of operation that allows working in the standard text completion mode. However, it allows for a bit more flexibility with the text by enabling you to initiate the entire discussion in any way you like.

Similar to chat mode, on the right-hand side of the interface, there are convenient presets. These allow you to fine-tune instructions and swiftly transition between varied configurations and pre-made prompt templates.

Additionally, this mode offers options for labeling the AI and the user, making it possible to simulate dialogues between specific characters - for example, you could create a conversation between Batman and the Joker, as predefined in the prompt. This feature presents a range of creative possibilities for setting up different conversational scenarios in an engaging and exploratory manner.


## Image and video generation

**PyGPT** enables quick and easy image and video generation using models such as `gpt-image`, `Imagen`, `Gemini`, `Nano Banana`, and `Grok` for images, as well as `Veo` and `Sora` for video.

Generating images and videos works similarly to a chat conversation: you provide a prompt, the selected model generates the requested media, and PyGPT downloads, saves, and displays the result in the application. In `Image and video` mode, you can either send a raw prompt directly to the model or ask PyGPT to prepare and optimize the prompt for you.

![v3_img](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v3_img.png)

To generate images directly inside a chat, enable **Image generation (inline)** in the Plugins menu.

For supported models/providers, you can also enable remote image generation in `Config -> Settings -> Remote Tools`. If enabled, image generation is available natively in supported work modes without the inline plugin.

**Tip:** To use `Imagen` models you must enable `Use Vertex AI` in `Config -> Settings -> API Keys -> Google -> Advanced options`.

### Remix, Edit, or Extend

To remix or extend from a previous image or video instead of creating a new one from scratch, enable the `Remix/Extend` option checkbox in the toolbox. The last generated image or video in the current context will be used as a reference for your prompt, allowing you to request changes to the generated content. If the `Remix/Extend` option is enabled, uploading an image attachment as a reference will not take effect.

### Raw mode

There is an option for switching prompt generation mode.

If **Raw Mode** is enabled, a model will receive the prompt exactly as you have provided it.
If **Raw Mode** is disabled, a model will generate the best prompt for you based on your instructions.

### Image storage

Generated images and videos are automatically saved to the working directory, under the `img` or `video` folder depending on the media type. You can also quickly save generated media to another location, open a preview, view it in full size, or remove it when it is no longer needed.

By default, images are stored in the base-profile `img` directory. If **Store images, captures, and uploads in the workdir data directory** is enabled, generated images are stored under the active `data` workdir instead, including a custom project data workdir when one is active.

## Computer use

> **WARNING: Computer use can give the model full control of your computer.** The model can move the mouse, type, click, open applications, read visible content, and perform actions with your user permissions. Use this mode only for tasks you trust and supervise sensitive operations.

Computer use lets supported models operate the desktop or browser through mouse and keyboard actions. PyGPT uses the selected provider's native `Computer use` capability when supported by the current model (OpenAI, Google, or Anthropic), combined with the built-in `Mouse and keyboard` integration.

**Example of use:**

```Click on the Start Menu to open it, search for the Notepad in the list, and run it.```

You can change the environment in which the navigation mode operates by using the list at the bottom of the toolbox.

**Available Environments:**

- Browser
- Linux
- Windows
- Mac

You can run this mode in a browser sandbox powered by `Playwright` (https://playwright.dev/). The Playwright package and at least one browser engine must be installed in an environment accessible to PyGPT. For example, to install Chromium:

```bash
pip install playwright
playwright install chromium
```

You can install another supported engine instead with `playwright install firefox` or `playwright install webkit`.

Then open `Plugins -> Settings -> Mouse and keyboard -> Sandbox (Playwright)` and configure the sandbox:

- set `Engine` to the installed browser engine, for example `chromium`;
- leave `Browsers directory` empty when using Playwright's default browser location, or set it to the custom directory where the Playwright browsers are installed;
- optionally configure `Headless mode`, browser arguments, home URL and viewport size.

Finally, enable the `Sandbox` switch in the Computer use toolbox when you want Computer use to run inside the Playwright browser sandbox.


**Tip:** DO NOT enable the `Mouse and keyboard` plugin in Computer use mode—it is already connected to Computer use mode "in the background."


## Experts

**Experts** lets you define reusable, specialized agents as presets and delegate tasks to them from a normal conversation. Experts are powered by regular agents from the same **Agents v2 runtime** that powers **Chat with Agents**. There is no separate legacy execution engine for an Expert.

Each enabled Expert is exposed to the current conversation as a regular `expert_call` tool. The main model can call it in exactly the same way as other tools: it selects an Expert, passes an instruction, waits for the agent to complete the task, and receives the Expert's final response directly as the tool result.

In **Experts** mode, the main conversation follows the normal **Chat** tool flow. Enabled local tools from plugins and supported remote provider tools remain available according to the usual Chat configuration, while `expert_call` adds the ability to delegate work to specialized agents.

Each Expert uses its own preset configuration, including its model/provider, system prompt, local and remote tool permissions, and optional RAG index. Because Experts run on the same runtime as **Chat with Agents**, they use the same agent and tool infrastructure. Each Expert also keeps an isolated hidden child context inside the parent conversation, so repeated calls to the same Expert can retain that Expert's own conversation memory without mixing it with the memory of other Experts.

### How to use Experts

1. Switch to **Experts** mode and create or edit an Expert preset. Give it a clear ID/name and specialized instructions, then enable it.
2. Start a conversation in **Experts** mode, or enable the **Experts (inline)** plugin to make the same Experts available in another supported chat mode.
3. Ask the model to use the Expert in natural language. For example:

```bash
Ask the Python programmer expert to review this code and suggest a fix.
```

The main model can then invoke `expert_call` automatically, use the returned result in its own answer, and call other tools or Experts if the task requires it. You do not need to manually start a separate Expert session. Defining and enabling the Expert is enough for it to become available to the model.

Experts can be activated or deactivated from the preset list using the RMB context menu and the `Enable/Disable` actions. Only enabled Experts are exposed through `expert_call`.

The **Experts (inline)** plugin does not implement a separate Expert engine. It exposes the same `expert_call` tool in supported chat modes and executes the selected Expert through the same **Chat with Agents / Agents v2** runtime.

## Autonomous mode

**Autonomous mode** is a single-agent loop for tasks that should continue across multiple model passes without requiring a new user message after every step. The same model keeps working on the original request, reviews the accumulated result, performs additional useful work or verification, and continues until the run is stopped by its configured rules. It does not create or orchestrate worker agents.

The current implementation is **Chat-backed**. Autonomous requests use the same bridge, provider routing, API selection, native tool/function-call settings, and normal tool execution flow as standard `Chat`. 

Autonomous uses the same global **RAG** selector shown at the bottom of the toolbox. If no index is selected, it follows normal Chat routing. Selecting a valid index routes the run through the LlamaIndex RAG runtime with that index. Select `---` to keep normal Chat routing.

**Run controls**

- **Max run steps (iterations)** limits the number of autonomous model passes. Set it to `0` for an unlimited loop. Tool calls and their results are handled inside the normal tool flow and do not represent a separate user turn.
- **Auto-stop** allows the agent to terminate the run early when it determines that the original goal is complete, or when a run-control condition requires stopping. When Auto-stop is disabled, the agent is not given the internal completion-control tool; the loop is then governed by the configured run limit or a manual/application stop.
- **Always continue** keeps the run open-ended and instructs the agent to continue exploring useful in-scope refinements instead of voluntarily finishing. Enabling it automatically disables Auto-stop and ignores the configured iteration limit, so the run continues until it is stopped externally.
- **Dynamic continuous prompt** is enabled by default. After each completed pass, PyGPT makes a hidden, tool-free call to the same selected model and uses it as a judge. The judge receives the original user input plus a configurable tail of recent Autonomous Assistant responses, then returns a focused instruction for the next pass. The generated instruction is shown in the live conversation as a localized `Judge:` pseudo-input, but it is not stored or handled as a new user turn. If the judge call fails or returns an empty result, PyGPT falls back to the normal static continuation prompt.
- **Responses to judge** controls how many recent Autonomous Assistant responses are sent with the original user input to that judge. The default is `3`; set it to `0` to include all Assistant responses produced since the current user input. Tool rounds inside one Autonomous provider pass are grouped as one response for this limit.
- **Auto-stop** and **Always continue** are mutually exclusive. Enabling either one immediately disables the other; both may also be disabled.

When the run limit is set to `0`, PyGPT shows an infinite-loop confirmation because an unattended run can generate substantial API usage, token consumption, and repeated tool actions.

**WARNING:** Autonomous execution can perform repeated tool calls and external actions. Review enabled plugins and remote tools before starting a long or unlimited run, especially when file access, code/system execution, web actions, or other side effects are available.


## Agent (LlamaIndex)

**Legacy mode — not recommended. Use the newer and more advanced `Chat with Agents` mode instead.**

This mode provides the older LlamaIndex-based agent workflows.

Includes built-in agents (Workflow):

- FunctionAgent
- ReAct
- Structured Planner (sub-tasks)
- Supervisor + worker


You can create your own types (workflows/patterns) using the built-in visual node-based editor found in the `Tools -> Agent Builder (Legacy)`.

You can also create your own agent by creating a new provider that inherits from `pygpt_net.provider.agents.base`.

**Tools and Plugins**  

In this mode, all commands from active plugins are available (commands from plugins are automatically converted into tools for the agent on-the-fly).

**RAG - using indexes**  

If an index is selected in the agent preset, a tool for reading data from the index is automatically added to the agent, creating a RAG automatically.

This legacy mode supports text input only; multimodal input is not available.

**Loop / Evaluate Mode**

You can run the agent in autonomous mode, in a loop, and with evaluation of the current output. When you enable the `Loop / Evaluate` checkbox, after the final response is given, the quality of the answer will be rated on a percentage scale of `0% to 100%` by another agent. If the response receives a score lower than the one expected (set using a slider at the bottom right corner of the screen, with a default value `75%`), a prompt will be sent to the agent requesting improvements and enhancements to the response.

Setting the expected (required) score to `0%` means that the response will be evaluated every time the agent produces a result, and it will always be prompted to self-improve its answer. This way, you can put the agent in an autonomous loop, where it will continue to operate until it succeeds.

You can choose between two methods of evaluation:

- By the percentage of tasks completed
- By the accuracy (score) of the final response

You can set the limit of steps in such a loop by going to `Settings -> Agents and experts -> Agents -> Max evaluation steps in loop`. The default value is `3`, meaning the agent will only make three attempts to improve or correct its answer. If you set the limit to zero, there will be no limit, and the agent can operate in this mode indefinitely (watch out for tokens!).

You can change the prompts used for evaluating the response in `Settings -> Prompts -> Agent: response evaluation in loop [LlamaIndex]`. Here, you can adjust it to suit your needs, for example, by defining more or less critical feedback for the responses received.

## Agent (OpenAI)

**Legacy mode — not recommended. Use the newer and more advanced `Chat with Agents` mode instead.**

This mode provides the older agent workflows built on the `openai-agents` library integrated into the application:

https://github.com/openai/openai-agents-python

It allows running agents for OpenAI models and models compatible with the OpenAI API.

In this mode, you can use pre-configured Experts in Expert mode presets - they will be launched as agents (in the `openai_agents_experts` type, which allows launching one main agent and subordinate agents to which queries will be appropriately directed).

**Agent types (workflows/patterns):**

- `Agent with experts` - uses attached experts as sub-agents
- `Agent with experts + feedback` - uses attached experts as sub-agents + feedback agent in a loop
- `Agent with feedback` - single agent + feedback agent in a loop
- `Planner` - planner agent, 3 sub-agents inside: planner, base agent + feedback
- `Research bot` - researcher, 3 sub-agents inside: planner, searcher and writer as base agent
- `Simple agent` - a single agent.
- `Evolve` - in each generation (cycle), the best response from a given parent agent is selected; in the next generation, the cycle repeats.
- `B2B` - bot-to-bot communication, involving two bots interacting with each other while keeping a human in the loop.
- `Supervisor + Worker` - one agent (supervisor) acts as a bridge between the user and the second agent (worker). The user provides a query to the supervisor, who then sends instructions to the worker until the task is completed by the worker.

You can create your own types (workflows/patterns) using the built-in visual node-based editor found in the `Tools -> Agent Builder (Legacy)`.

There are also predefined presets added as examples:

- `Coder`
- `Experts agent`
- `Planner`
- `Researcher`
- `Simple agent`
- `Writer with Feedback`
- `2 bots`
- `Supervisor + worker`

In the Agents (OpenAI) mode, all remote tools are available for the base agent according to the configuration in the Config -> Settings -> Remote tools menu.

Remote tools for experts can be selected separately for each expert in the preset configuration.

Local tools (from plugins) are available for agents and experts according to the enabled plugins, as in other modes.

In agents with feedback and plans, tools can be allowed in a preset configuration for each agent. They also have separate prompts that can be configured in presets.

**Description of how different types of agents work:**

Below is a pattern for how different types of agents work. You can use these patterns to create agents for different tasks by modifying the appropriate prompts in the preset for the specific task.

**Simple Agent**
- The agent completes its task and then stops working.

**Agent with Feedback**
- The first agent answers a question.
- The second agent (feedback) evaluates the answer and, if necessary, goes back to the first agent to enforce corrections.
- The cycle repeats until the feedback agent is satisfied with the evaluation.

**Agent with Experts**
- The agent completes the assigned task on its own or delegates it to the most suitable expert (another agent).

**Agent with Experts + Feedback**
- The first agent answers a question or delegates it to the most suitable expert.
- The second agent (feedback) evaluates and, if necessary, goes back to the first agent to enforce corrections.
- The cycle repeats until the feedback agent is satisfied with the evaluation.

**Research Bot**
- The first agent (planner) prepares a list of phrases to search.
- The second agent (search) finds information based on the phrases and creates a summary.
- The third agent (writer) prepares a report based on the summary.

**Planner**
- The first agent (planner) breaks down a task into sub-tasks and sends the list to the second agent.
- The second agent performs the task based on the prepared task list.
- The third agent, responsible for feedback, evaluates, requests corrections if needed, and sends the request back to the first agent. The cycle repeats.

**Evolve**
- You select the number of agents (parents) to operate in each generation (iteration).
- Each agent prepares a separate answer to a question.
- The best agent (producing the best answer) in a generation is selected by the next agent (chooser).
- Another agent (feedback) verifies the best answer and suggests improvements.
- A request for improving the best answer is sent to a new pair of agents (new parents).
- From this new pair, the best answer is selected again in the next generation, and the cycle repeats.

**B2B**
- A human provides a topic for discussion.
- Bot 1 generates a response and sends it to Bot 2.
- Bot 2 receives the response from Bot 1 as input, provides an answer, and sends the response back to Bot 1 as its input. This cycle repeats.
- The human can interrupt the loop at any time and update the entire discussion.

**Supervisor + Worker**

- A human provides a query to the Supervisor.
- The Supervisor prepares instructions for the Worker and sends them to the Worker.
- The Worker completes the task and returns the result to the Supervisor.
- If the task is completed, the Supervisor returns the result to the user. If not, the Supervisor sends another instruction to the Worker to complete the task or asks the user if there are any questions.
- The cycle repeats until the task is completed.

**Tip:** Experts can be assigned and used in these legacy agent workflows where supported.

**Limitations:**

- When the `Computer use` tool is selected for an expert or when the `computer-use` model is chosen, all other tools will not be available for that model.



# Indexing and RAG

PyGPT uses **LlamaIndex** and a vector store to provide persistent Retrieval-Augmented Generation (RAG) over indexed files, external data, and conversation history. Indexing and retrieval are configured in `Settings -> Indexes / RAG`.

## Using RAG in Chat

At the bottom of the Chat toolbox, use the **RAG** selector to choose the index that should provide additional context. Selecting `---` keeps the normal Chat provider path. When a valid index is selected, PyGPT routes the request through the LlamaIndex RAG runtime automatically, using the selected model through its LlamaIndex provider wrapper.

The **RAG mode** option in `Settings -> Indexes / RAG -> Chat` controls how the selected index is used:

- **Chat** retrieves relevant indexed context and generates a normal conversational answer with the selected model.
- **Query the Index Only** sends the prompt through the index query path without the normal conversational chat flow.
- **Retrieve Only** returns retrieved index context without generating the normal chat response.

The separate **Chat mode** setting controls the LlamaIndex chat-engine mode used when **RAG mode** is set to **Chat**.

When the **Tools** switch is enabled in RAG-backed Chat, PyGPT uses native tool calls whenever the current model/provider path supports them. If native tool calls are unavailable, it can fall back to a LlamaIndex ReAct agent. The ReAct fallback is non-streaming; normal native tool-call paths can stream.

RAG is also available in other supported workflows. The exact execution path depends on the mode: for example, Completion uses its LlamaIndex completion path, while Chat with Agents exposes the selected index as a RAG tool.

## Indexing files for RAG

To use persistent RAG, first index (embed) the files or external data you want to query. Embedding transforms document content into vectors stored in the selected vector store.

To index files, copy or upload them into the active `data` directory and use **Index all** or `RMB -> Embed into index` in the Files view. You can also use the Indexer tool or supported plugins. The active data directory is normally `<profile workdir>/data`; when the current conversation belongs to a project with a custom data workdir, that project directory is used instead.

If you're unfamiliar with embeddings and how they work, see:

https://stackoverflow.blog/2023/11/09/an-intuitive-introduction-to-text-embeddings/

For a visualization from OpenAI's page:

![vectors](https://github.com/szczyglis-dev/py-gpt/assets/61396542/4bbb3860-58a0-410d-b5cb-3fbfadf1a367)

Source: https://cdn.openai.com/new-and-improved-embedding-model/draft-20221214a/vectors-3.svg

## Querying single files

You can query an individual file on the fly with the `query_file` command from the **Files I/O** plugin. A temporary in-memory index is created for that query; it is not persisted as a normal index unless the plugin is configured to index read files automatically. A similar command is available for querying web and external content through LlamaIndex.

For example, if `data/my_cars.txt` contains `My car is red.`, you can ask the model to query that file for the car color and receive `Red` as the result. Enable the **Tools** switch when using tool commands from plugins.

## Index types

PyGPT uses three related index concepts:

- **Configured indexes** are the normal persistent indexes listed in `Settings -> Indexes / RAG -> General -> Indexes`. They can contain files, external data, and indexed conversation context.
- **Project indexes** are isolated persistent indexes created automatically for projects. They are shown to the user as **Current project** and are not added to the normal configured index list.
- **Temporary indexes** are created in memory for operations such as querying a single attachment or using the Files I/O `query_file` tool. They are not persisted as normal indexes.

**Important:** Removing an item from the normal **Indexes** list removes only its configuration entry. It does not delete the already stored vector data. Use **Clear and truncate** when you want to permanently remove index data.

## Supported data

Built-in file loaders include CSV, Epub, XLSX, HTML, IPYNB, images, JSON, Markdown, PDF, plain text, video/audio, DOCX, and XML. Built-in web/external loaders include Bitbucket, ChatGPT Retrieval Plugin, GitHub Issues and repositories, Google Calendar/Docs/Drive/Gmail/Keep/Sheets, Microsoft OneDrive, RSS, SQL databases, sitemaps, Twitter/X posts, webpages, and YouTube transcriptions.

Additional loader arguments can be configured in `Settings -> Indexes / RAG -> Data loaders`. Custom loaders can also be registered by extensions.

## File indexing

The **File indexing** tab controls how files and directories are embedded into persistent indexes. The main options include recursive directory indexing, replacement of old versions during re-indexing, excluded extensions, stop-on-error behavior, and custom metadata for file and web/external documents.

The Files view is project-aware. If the active conversation belongs to a project with a custom data workdir, the view uses that directory as its filesystem root; outside projects, or when **Use shared workdir** is enabled, it uses the shared `<profile workdir>/data` directory.

When the current conversation belongs to a project, **Current project** is available as a runtime index target. Selecting it indexes the file or directory into the isolated index for that project. The project's filesystem data workdir and its isolated vector index are separate concepts: changing the data workdir does not move, rename, or rebuild the project's vector index.

## Context indexing

LlamaIndex is integrated with the context database, so stored conversation history can also be indexed and used as RAG context. **Context indexing** is configured separately from file indexing.

The **Conversation auto-indexing** setting has three modes:

- **Off** - disables automatic conversation-context indexing.
- **Auto-index all conversations** - enables automatic context indexing for conversations both inside and outside projects.
- **Auto-index only in projects** - enables automatic context indexing only for conversations assigned to projects.

The **Enable auto-indexing in modes** setting further limits which work modes may trigger automatic context indexing.

### Global context indexes

**Indexes for global auto-indexing** is a multi-select list. One or more normal configured indexes can be selected. The global selection is used outside projects and for project conversations when **Use isolated index per project** is disabled.

### Isolated project indexes

**Use isolated index per project** is enabled by default. When enabled, each project uses its own isolated index. PyGPT exposes it in the UI as **Current project** and internally resolves it to a project-specific ID such as `proj_<project_id>`. These project indexes are created and updated on demand and are not added to the normal **Indexes** list.

Project context indexing is incremental. PyGPT tracks the last indexed conversation item and continues from that point on subsequent updates.

Project indexes follow the project lifecycle:

- **Update project index** continues indexing from the last indexed item.
- **Truncate project index** permanently removes that project's index data and resets its indexing state.
- Deleting a project also removes its isolated project index when it exists.
- Duplicating a project creates/rebuilds an isolated index for the duplicate only when the source project already had one.

## Using the current project index

The active project index can be used from multiple places:

- In a supported mode such as **Chat**, select **Current project** in the **RAG** selector at the bottom of the toolbox.
- In the **Files** tab, use `RMB -> Embed into index -> Current project` for a file or directory.
- In the **RAG (inline)** plugin, enable **Use project index if in use** to query the active project's isolated index automatically.
- In the **Files I/O** plugin, enable **Use project index if in use** so persistent file indexing performed by the plugin targets the active project instead of the configured global file index.

Outside a project, the virtual **Current project** target is unavailable and normal configured indexes are used.

## Attachments and temporary RAG

Attachments can provide additional context independently of the persistent RAG index selected in the toolbox. In attachment **RAG** mode, PyGPT creates or uses a temporary vector index for the attachment. This temporary context is scoped to the conversation/attachment flow and does not automatically become part of the selected persistent index.

## Vector stores

Available vector stores provided by LlamaIndex include:

- ChromaVectorStore
- ElasticsearchStore
- PineconeVectorStore
- QdrantVectorStore
- RedisVectorStore
- SimpleVectorStore

Configure the selected backend in `Settings -> Indexes / RAG -> Vector Store`. Provider-specific connection arguments can be supplied through the Vector Store `**kwargs` setting when required.

## Embeddings

Embedding configuration is shared by persistent file indexing, conversation context indexing, and attachment RAG. Configure it in `Settings -> Indexes / RAG -> Embeddings`. Provider credentials and endpoints are normally inherited from the provider's global configuration.

## Token and usage notes

Indexing uses the configured embedding provider and can generate API usage and token costs. Re-indexing large file collections or conversation histories may generate many embedding requests.

When **RAG mode** is **Chat**, retrieved context is added to the model-facing request. Large retrieved context plus plugin/tool instructions can approach the model's context limit. Disable unused plugins/tools or reduce retrieval scope if you encounter token-limit errors.

**Warning:** Monitor embedding and model usage with the selected provider, especially when indexing or re-indexing large data sets.


# MCP Connectors

PyGPT includes an **MCP Connectors** manager for importing and managing Model Context Protocol server configurations. Open **Config -> MCP... -> Connectors...**.

You can import from GitHub, local files or folders, including common Claude, Codex, OpenClaw, Cursor, VS Code, OpenCode, MCPorter, JSON, TOML and YAML formats. Imported connectors are disabled until you enable them.

Enabled connectors use the regular **MCP** plugin for discovery and execution. Review commands, URLs, credentials, environment variables and working directories before enabling third-party configurations.

See the **MCP Connectors** documentation for supported formats and advanced configuration.

# Context and memory

## Short and long-term memory

**PyGPT** features a continuous chat mode that maintains a long context of the ongoing dialogue. It preserves the entire conversation history and automatically appends it to each new message (prompt) you send to the AI. Additionally, you have the flexibility to revisit past conversations whenever you choose. The application keeps a record of your chat history, allowing you to resume discussions from the exact point you stopped.

## Advanced context handling (experimental)

> **Experimental:** Advanced context handling changes how long model-facing histories are compacted and continued. Keep it disabled if you need the legacy history-selection behavior, and verify important long-running workflows when enabling it for production work.

Enable it in `Config -> Settings -> Context -> Advanced handling -> Enable advanced context handling`. When the unsummarized model-facing conversation approaches the configured threshold, PyGPT compacts older completed turns into conversation-scoped continuation notes and keeps a newer verbatim tail. The complete chat history remains stored in SQLite; only the history sent to the model is trimmed.

Continuation notes are stored in `memory_ctx`, one row per conversation, and are separate from the Memory plugin's global/project long-term memory. They preserve compact state such as goals, constraints, decisions, completed work, important findings and pending work. `memory_ctx_get`, `memory_ctx_add` and `memory_ctx_replace` can read or maintain these notes. In Chat with Agents, the main agent also uses persistent bounded rolling memory backed by the same conversation notes, while worker rolling summaries stay runtime-local.

The main settings are **Checkpoint threshold (%)** (default `75`), **Context tail after checkpoint (%)** (default `45`), and **Maximum continuation note characters** (default `24000`). Model-aware token limits and safety reserves are also applied at runtime.

## Handling multiple contexts

On the left side of the application interface, there is a panel that displays a list of saved conversations. You can save numerous contexts and switch between them with ease. This feature allows you to revisit and continue from any point in a previous conversation. **PyGPT** automatically generates a summary for each context, akin to the way `ChatGPT` operates and gives you the option to modify these titles itself.

## Projects and project data workdirs

Conversations can be organized into projects. By default, projects use the shared profile `data` directory. When creating a project, leave **Use shared workdir** enabled to keep this behavior, or disable it and select a custom directory for that project. For an existing project, use `RMB -> Edit` to change its name or data workdir. Hovering a project item in the context list shows the effective data workdir.

A project workdir overrides **only the logical `data` directory** used by conversations in that project. It does not replace the profile/application workdir. Files such as `config.json`, `models.json`, `db.sqlite`, logs and other profile-level directories such as `tmp`, `cache`, `css`, `locale` and fonts continue to use the base profile workdir. Conversations outside projects, and projects with **Use shared workdir** enabled, use the normal `<profile workdir>/data` directory.

The project data directory is resolved at runtime. The **Files** tab, **Files I/O**, **Python interpreter**, filesystem-aware tools and Docker sandboxes use the data root that belongs to the current conversation. In Docker, the active host data directory is exposed as `/mnt/data`. The internal `tmp` directory always remains in the base profile workdir. `img`, `capture` and `upload` follow a custom project data workdir only when **Store images, captures, and uploads in the workdir data directory** is enabled; otherwise they remain in their normal base-profile locations.

## Clearing history

You can clear the entire memory (all contexts) by selecting the menu option:

``` ini
File -> Clear history...
```

## Context storage

On the application side, the context is stored in the `SQLite` database located in the base profile/application workdir (`db.sqlite`). A project data-workdir override does not move this database.


### Tool call storage

Tool requests and results can contain large payloads, for example file contents, generated data, or long command output. These payloads can significantly increase the size of the context database. Their persistence can be configured in:

```ini
Config -> Settings -> Context -> Tools -> Store tool calls in database
```

The available modes are:

- `Do not store` - tool calls and results are used normally during the live request, but are not written to durable history.
- `Store truncated` - keeps the tool-call structure for history and UI rendering, but recursively truncates every stored string value in tool input/output to 20 characters and appends `....`. Object keys and nesting are preserved.
- `Store full input/output` - stores complete tool requests and results, matching the previous behavior. This is the default for backward compatibility.

The storage policy applies to all modes that use tools, including Chat (with or without RAG), legacy Agents, and Chat with Agents. It affects only durable database persistence.

**Restore tool calls in runtime** controls whether completed tool calls/results from earlier turns are replayed to the model while the current conversation remains active in memory. It is enabled by default and is independent from the database storage mode. Disabling it removes completed tool protocol from later runtime turns, but does not interrupt the tool-call/result sequence that is currently in progress.

By default, historical tool calls and results loaded from the database are not replayed to the model on later turns. To restore persisted tool protocol after reloading a conversation, enable **Restore tool calls from history** in `Settings -> Context -> Tools`. This option applies only to history restored from the database, requires **Store full input/output**, and is ignored when tool calls are not stored or are stored truncated.

Once a conversation begins, a title for the chat is generated and displayed on the list to the left. This process is similar to `ChatGPT`, where the subject of the conversation is summarized, and a title for the thread is created based on that summary. You can change the name of the thread at any time.

# Files And Attachments

## Uploading attachments

**Using Your Own Files as Additional Context in Conversations**

You can use your own files (for example, to analyze them) during any conversation. You can do this in two ways: by indexing (embedding) your files in a vector database and selecting that index through the **RAG** selector in a supported conversation, or by adding a file attachment (the attachment file will only be available during the conversation in which it was uploaded).

**Attachments**

**PyGPT** makes it simple for users to upload files and send them to the model for tasks like analysis, similar to attaching files in `ChatGPT`. There's a separate `Attachments` tab next to the text input area specifically for managing file uploads. 

**Tip:** Project-wide attachment sharing is optional. Enable `Settings -> Files and attachments -> General -> Make attachments available in the whole project` to make attachments added in one chat available to all chats in the same project. The option is disabled by default; when disabled, attachments remain available only in the chat where they were added.

![v2_file_input](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_file_input.png)

### Mentioning attachments, workdir files, and conversations

Type `@` in the message input to open a scrollable mention picker. Current attachments are listed first, followed by files and directories from the active data workdir. Continue typing after `@` to filter the list; Backspace updates the matches. Select an item with the mouse or with the arrow keys plus `Enter`/`Tab`; `Esc` closes the popup. Selected mentions are rendered with a distinct color in the input and in conversation history, and directories are shown with a trailing `/`.

To reference another saved conversation, type its exact numeric context ID, for example `@123`. If that context exists in the local context database, the picker shows a **Chat history** section with the conversation title. After selection, PyGPT displays the title as the mention label while retaining the numeric ID internally so the same database context can be resolved reliably.

At send time, a conversation mention is resolved through the Chat history backend even when the optional **Chat history (inline)** plugin is disabled. The history summarizer receives the **current user request** and extracts only information from the referenced conversation that is relevant to that request. This is query-focused retrieval/summarization rather than a generic summary or a full copy of the previous conversation. Long conversations are split according to the selected summarizer model's context window, processed newest-first, and their query-focused extracts are recursively reduced to one bounded result. The summarizer model and summary budget can be configured in the Chat history plugin settings.

The model-facing request receives the retrieved context in a structured block such as `<conversation id="123" title="Previous title">...relevant context...</conversation>`. The stored conversation and the UI continue to show the compact `@Previous title` mention instead of the expanded block.

For attachments and workdir paths, mentions remain UI references rather than special syntax sent to the model. Before sending, a normal attachment mention becomes its plain filename and a workdir file/directory mention becomes its portable path, for example `%workdir%/data/docs/spec.md`. When a mentioned attachment is an image that is actually sent as image input, PyGPT replaces the filename only in the runtime provider prompt with `Attached Image #N`, where `N` follows the image-attachment order used for the multimodal request. The stored conversation and UI still keep the original attachment name.

**Important:** mentioning a workdir file does not automatically read the file into the prompt. It identifies the exact file or directory the user means. The model still needs an available file tool, RAG/index access, or another supported mechanism to inspect the content. Attachment mentions continue to follow the normal attachment-processing rules. Conversation-ID mentions are different: PyGPT explicitly retrieves query-focused context from the referenced conversation database entry before the request is sent.

You can use attachments to provide additional context to the conversation. By default, uploaded files are processed locally using loaders from LlamaIndex and can be converted into text and/or indexed in the vector store. You can upload any file format supported by the application through LlamaIndex. Supported formats include:

Text-based types:

- CSV files (csv)
- Epub files (epub)
- Excel .xlsx spreadsheets (xlsx)
- HTML files (html, htm)
- IPYNB Notebook files (ipynb)
- JSON files (json)
- Markdown files (md)
- PDF documents (pdf)
- Plain-text files (txt and etc.)
- Word .docx documents (docx)
- XML files (xml)

Media-types:

- Image (using vision) (jpg, jpeg, png, gif, bmp, tiff, webp)
- Video/audio (mp4, avi, mov, mkv, webm, mp3, mpeg, mpga, m4a, wav)

Archives:

- zip
- tar, tar.gz, tar.bz2

### Native file upload

In the `Attachments` tab you can enable **Prefer native file upload when supported**. This option is disabled by default.

When enabled, PyGPT will try to upload each supported attachment directly through the selected provider's native file API instead of reading the file locally and appending its extracted content to the prompt. Native upload is used only when it is supported by the current provider, model, file type, and file size. The native upload path is available for supported OpenAI, Google Gemini, Anthropic, and xAI configurations.

For a file that is successfully sent natively, native upload overrides the selected attachment context mode (`Full context`, `RAG`, or `Summary`) for that file. If native upload is unavailable or fails, PyGPT automatically falls back to the standard local attachment processing, so existing attachment behavior is preserved.

Archive files such as ZIP and TAR are unpacked locally first. Their contents are then handled individually: supported files can be uploaded natively, while unsupported files use the normal local-processing fallback. Attachments sent through the native path are marked with the `(Native)` suffix in the uploaded attachments list.

**Note:** Native upload sends the original file content to the selected API provider. Provider-specific file type, size, model, retention, and availability limits may apply.

**Tip:** To see native-upload activity in the console, enable `Settings -> Debug -> Log attachments usage to console`. Native upload messages are printed only when attachment logging is enabled.

### Attachment context modes

The content from the uploaded attachments will be used in the current conversation and will be available throughout (per context). There are 3 modes available for working with additional context from attachments:

- `Full context`: Provides best results. This mode attaches the entire content of the read file to the user's prompt. This process happens in the background and may require a large number of tokens if you uploaded extensive content.

- `RAG`: The indexed attachment will only be queried in real-time using LlamaIndex. This operation does not require any additional tokens, but it may not provide access to the full content of the file 1:1.

- `Summary`: When queried, an additional query will be generated in the background and executed by a separate model to summarize the content of the attachment and return the required information to the main model. You can change the model used for summarization in the settings under the `Files and attachments` section.

In the `RAG` and `Summary` mode, you can enable an additional setting by going to `Settings -> Files and attachments -> RAG -> Use history in RAG query`. This allows for better preparation of queries for RAG. When this option is turned on, the entire conversation context is considered, rather than just the user's last query. This allows for better searching of the index for additional context. In the `RAG limit` option, you can set a limit on how many recent entries in a discussion should be considered (`0 = no limit, default: 3`).

**Important**: When using `Full context` mode, the entire content of the file is included in the prompt, which can result in high token usage each time. If you want to reduce the number of tokens used, instead use the `RAG` option, which will only query the indexed attachment in the vector database to provide additional context.

**Images as Additional Context**

Files such as jpg, png, and similar images are a special case. By default, images are not used as additional context; they are analyzed in real-time using a vision model. If you want to use them as additional context instead, you must enable the "Allow images as additional context" option in the settings: `Files and attachments -> Allow images as additional context`.

**Uploading larger files and auto-index**

To use the `RAG` mode, the file must be indexed in the vector database. This occurs automatically at the time of upload if the `Auto-index on upload` option in the `Attachments` tab is enabled. When uploading large files, such indexing might take a while - therefore, if you are using the `Full context` option, which does not use the index, you can disable the `Auto-index` option to speed up the upload of the attachment. In this case, it will only be indexed when the `RAG` option is called for the first time, and until then, attachment will be available in the form of `Full context` and `Summary`.

**Embeddings**

When using RAG to query attachments, the documents are indexed into a temporary vector store. The query model is configured in `Config -> Settings -> Files and attachments -> RAG -> Model for RAG queries`. Embedding configuration is shared with the rest of RAG under `Config -> Settings -> Indexes / RAG -> Embeddings`.

`Default embedding models` maps each model provider to its default embedding model and is used for file indexing, conversation-context indexing, and attachments. For attachment RAG, PyGPT first tries the mapping that matches the RAG query model's provider; if no mapping is available, it falls back to the global `Embeddings provider` and its default model. Credentials and endpoints are inherited from the selected provider's normal global settings, including runtime custom providers. `Global embeddings provider **kwargs` and `Global embeddings provider ENV vars` in **Advanced** are optional overrides and normally remain empty. `Embeddings timeout` controls embedding request timeout and defaults to 60 seconds.

## Downloading files

**PyGPT** automatically downloads and saves files created by the model in the active `data` workdir. Outside projects, and in projects that use the shared workdir, this is the normal `<profile workdir>/data` directory. A project can instead define its own data workdir; when a conversation from that project is active, the **Files** tab displays that directory and file-producing tools use it automatically.

The active `data` directory is also where the application stores files generated locally by the AI, such as code files and other model outputs. You can execute code from these files, read them back into the conversation, and index them with LlamaIndex. The project override applies only to this logical data root; it does not move profile-level paths such as `tmp`, configuration files, the database or other application directories.

The `Files I/O` and `Python interpreter` plugins use the same runtime-resolved data workdir as the active conversation. In Docker sandboxes this directory is mounted as `/mnt/data`. If **Store images, captures, and uploads in the workdir data directory** is enabled, `img`, `capture` and `upload` storage follows the active data workdir as well. When the option is disabled, those directories remain in their normal base-profile locations. `tmp` always remains in the base profile workdir.

To allow the model to manage files or execute Python code, enable the `Tools` switch together with the required plugins:

![v2_code_execute](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_code_execute.png)

# Presets

## What is preset?

Presets in **PyGPT** are templates for quickly switching between reusable conversation/model configurations. A preset can store the selected model and mode availability, system prompt, names/personalization fields, optional RAG index, and mode-specific options such as tool permissions or remote tools. The exact fields shown in the preset editor depend on the selected mode. Presets can be used with built-in providers, custom providers, local models, and LlamaIndex-backed workflows.

The application lets you create as many presets as needed and easily switch among them. Additionally, you can clone an existing preset, which is useful for creating variations based on previously set configurations and experimentation.

![v2_preset](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_preset.png)

## Example usage

The application includes several sample presets that help you become acquainted with the mechanism of their use.

# Profiles

You can create multiple profiles for an app and switch between them. Each profile uses its own configuration, settings, context history, and a separate folder for user files. This allows you to set up different environments and quickly switch between them, changing the entire setup with just one click.

The app lets you create new profiles, edit existing ones, and duplicate current ones.

To create a new profile, select the option from the menu: `Config -> Profile -> New Profile...`

To edit saved profiles, choose the option from the menu: `Config -> Profile -> Edit Profiles...`

To switch to a created profile, pick the profile from the menu: `Config -> Profile -> [Profile Name]`

Each profile uses its own user directory (workdir). You can link a newly created or edited profile to an existing workdir with its configuration. This is the profile/application workdir. A project's custom workdir is different: it overrides only the runtime `data` directory for conversations in that project and does not replace the profile workdir.

The name of the currently active profile is shown as (Profile Name) in the window title.

### Importing and exporting profiles

Use `File -> Export profile...` to save the active profile as a ZIP archive. You can include the **Database**, **Config files**, **Files**, and optionally the shared **Workdir data/** directory. Temporary files, caches, logs, and project data stored outside the profile workdir are not included.

Use `File -> Import profile...` to restore an exported archive as a new profile. Choose which available sections to import, provide a unique profile name, and select its workdir.

# Models

## Built-in models

PyGPT has a preconfigured list of models (as of 2026-09-11):

```markdown
- `claude-fable-5` (Anthropic)
- `claude-fable-5-1` (Anthropic)
- `claude-haiku-4-5` (Anthropic)
- `claude-opus-4-5` (Anthropic)
- `claude-opus-5` (Anthropic)
- `claude-sonnet-4-5` (Anthropic)
- `claude-sonnet-5` (Anthropic)
- `deepseek-v4-flash` (DeepSeek)
- `deepseek-v4-pro` (DeepSeek)
- `gemini-2.5-computer-use-preview-10-2025` (Google)
- `gemini-2.5-flash` (Google)
- `gemini-2.5-flash-image` (Google)
- `gemini-2.5-flash-native-audio-latest` (Google, real-time)
- `gemini-2.5-pro` (Google)
- `gemini-3-flash-preview` (Google)
- `gemini-3-pro-image` (Google)
- `gemini-3.1-flash-image` (Google)
- `gemini-3.1-flash-lite-image` (Google)
- `gemini-3.1-flash-live-preview` (Google, real-time)
- `gemini-3.1-pro-preview` (Google)
- `gemini-3.5-flash` (Google)
- `gemini-3.5-flash-lite` (Google)
- `gemini-3.6-flash` (Google)
- `gemini-3.7-flash` (Google)
- `gemini-flash-latest` (Google)
- `gemini-pro-latest` (Google)
- `imagen-4.0-generate-001` (Google)
- `nano-banana-pro-preview` (Google)
- `veo-3.1-fast-generate-preview` (Google)
- `veo-3.1-generate-preview` (Google)
- `veo-3.1-lite-generate-preview` (Google)
- `openai/gpt-oss-120b:novita` (HuggingFace Router)
- `openai/gpt-oss-20b:novita` (HuggingFace Router)
- `deepseek-r1:8b` (Ollama)
- `gemma4:e4b` (Ollama)
- `gpt-oss:120b` (Ollama)
- `gpt-oss:20b` (Ollama)
- `llama2-uncensored` (Ollama)
- `llama3.1` (Ollama)
- `llama4:scout` (Ollama)
- `mistral-small3.2:latest` (Ollama)
- `nemotron-3.5-lightning:30b` (Ollama)
- `qwen3.5:9b` (Ollama)
- `qwen3.6:27b` (Ollama)
- `SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M` (Ollama)
- `gpt-3.5-turbo` (OpenAI)
- `gpt-3.5-turbo-instruct` (OpenAI)
- `gpt-4` (OpenAI)
- `gpt-4-turbo` (OpenAI)
- `gpt-4o` (OpenAI)
- `gpt-4o-mini` (OpenAI)
- `gpt-5.3-codex` (OpenAI)
- `gpt-5.6-luna` (OpenAI)
- `gpt-5.6-sol` (OpenAI)
- `gpt-5.6-terra` (OpenAI)
- `gpt-6-astra` (OpenAI)
- `gpt-image-1.5` (OpenAI)
- `gpt-image-2` (OpenAI)
- `gpt-image-2.5-flare` (OpenAI)
- `gpt-image-2.5-sunburst` (OpenAI)
- `gpt-realtime` (OpenAI, real-time)
- `gpt-realtime-2.1` (OpenAI, real-time)
- `gpt-realtime-2.1-mini` (OpenAI, real-time)
- `o1` (OpenAI)
- `o1-pro` (OpenAI)
- `o3` (OpenAI)
- `o3-mini` (OpenAI)
- `o3-pro` (OpenAI)
- `o4-mini` (OpenAI)
- `sora-2` (OpenAI)
- `sora-2-pro` (OpenAI)
- `sonar` (Perplexity)
- `sonar-deep-research` (Perplexity)
- `sonar-pro` (Perplexity)
- `sonar-reasoning-pro` (Perplexity)
- `grok-2-vision` (xAI)
- `grok-3-mini` (xAI)
- `grok-3-mini-fast` (xAI)
- `grok-4.3` (xAI)
- `grok-4.5` (xAI)
- `grok-4.6` (xAI)
- `grok-imagine-image` (xAI)
- `grok-imagine-image-quality-latest` (xAI)
- `grok-imagine-video` (xAI)
- `grok-imagine-video-1.5` (xAI)
```

All models are specified in the configuration file `models.json`, which you can customize.
This file is located in the base profile/application workdir and is not affected by a project data-workdir override. You can add models for built-in providers, OpenAI-compatible/custom providers, `Ollama`, and LlamaIndex-backed workflows.

For normal LlamaIndex use, no model-specific API key, endpoint, model name, `**kwargs` or `ENV` block is required. PyGPT resolves the LlamaIndex model from the model ID/provider and reuses the provider's normal global credentials and endpoint. This also applies to runtime custom providers. The optional LlamaIndex fields in the model's **Advanced** section are overrides only: add `**kwargs` or `ENV` values when you intentionally need provider-specific parameters or want to override the inherited configuration. The model importer therefore does not need to create LlamaIndex `args`/`env` entries for ordinary models.

You can import new models by manually editing `models.json` or by using the model importer in the `Config -> Models -> Import` menu.

**Tip:** The models on the list are sorted by provider, not by manufacturer. A model from a particular manufacturer may be available through different providers (e.g., OpenAI models can be provided by the `OpenAI API` or by `OpenRouter`). If you want to use a specific model through a particular provider, you need to configure the provider in `Config -> Models -> Edit`, or import it directly via `Config -> Models -> Import`.

**Tip**: Anthropic and Deepseek API providers use VoyageAI for embeddings (persistent and attachment RAG), so you must also configure the Voyage API key if you want to use embeddings from these providers.

## Adding a custom model

You can add your own models. See the section `Extending PyGPT / Adding a new model` for more info.

There is built-in support for those LLM providers:

- `Anthropic`
- `Azure OpenAI` (native SDK)
- `Deepseek API`
- `Eden AI`
- `Forge`
- `Google` (native SDK)
- `HuggingFace API`
- `HuggingFace Router` (wrapper for OpenAI compatible ChatCompletions)
- `LiteLLM`
- `Local models` (OpenAI API compatible)
- `Mistral AI`
- `Ollama`
- `OpenAI` (native SDK)
- `OpenRouter`
- `Perplexity`
- `xAI` (native SDK)

## Custom providers (OpenAI-compatible)

Add OpenAI Chat Completions-compatible providers in:

`Config -> Settings -> Custom providers`

Configure the provider name, API base URL and optional API key. After saving, the provider is available in the Models Editor and `Config -> Models -> Import`.

Normal Chat uses the OpenAI-compatible Chat Completions API. LlamaIndex-backed flows reuse the same provider endpoint and credentials automatically. Per-model API base/key values can still override the provider defaults.

## How to use local or other models

### DeepSeek, Qwen, gpt-oss, Gemma, Mistral, Llama, and other local models

How to use locally installed DeepSeek, Qwen, gpt-oss, Gemma, Mistral, Llama, and other models:

1) Choose the `Chat` working mode.

2) On the models list, select, edit, import, or add a model with the `ollama` provider. The model ID should match the name served by Ollama. No LlamaIndex `model_name` entry in Advanced `**kwargs` is required; PyGPT uses the model ID automatically.

3) Download and install Ollama from here: https://github.com/ollama/ollama

For example, on Linux:

```curl -fsSL https://ollama.com/install.sh | sh```

4) Run the model locally on your machine. For example, on Linux:

```ollama run gemma4:e4b```

5) Return to PyGPT and select the correct model from models list to chat with selected model using Ollama running locally.

**Example available models**

- `gemma4:e4b`
- `qwen3.5:9b`
- `qwen3.6:27b`
- `llama4:scout`
- `mistral-small3.2`
- `deepseek-r1:8b`
- `SpeakLeash/bielik-11b-v3.0-instruct:Q4_K_M`

etc.

You can add more models by editing the models list.

**Real-time importer**

You can also import models in real-time from a running Ollama instance using the `Config -> Models -> Import...` tool.

**Custom Ollama endpoint**

The default endpoint for Ollama is: http://localhost:11434

You can change it globally by setting the environment variable `OLLAMA_API_BASE` in `Settings -> General -> Advanced -> Application environment`.

The global value is automatically reused by Ollama LlamaIndex LLM and embedding wrappers. If one model must use a different endpoint, you can override it for that model in `Config -> Models -> Edit -> Advanced -> [LlamaIndex] ENV Vars` with `OLLAMA_API_BASE`.


**List of all models supported by Ollama**

https://ollama.com/library

https://github.com/ollama/ollama

**Using local embeddings**

Refer to: https://docs.llamaindex.ai/en/stable/examples/embeddings/ollama_embedding/

You can use an Ollama instance for embeddings. Open `Config -> Settings -> Indexes / RAG -> Embeddings`, select `ollama` as the global `Embeddings provider`, and set the Ollama embedding model in `Default embedding models` for the `ollama` provider.

The Ollama endpoint is inherited from the global `OLLAMA_API_BASE` configuration, so it does not need to be repeated in embedding `**kwargs`. `Global embeddings provider **kwargs` and `Global embeddings provider ENV vars` are available in the Embeddings **Advanced** group only for optional overrides. The common `Embeddings timeout` setting applies to embedding requests and defaults to 60 seconds.

### Other providers and LlamaIndex-based modes

PyGPT can route the same model differently depending on the selected work mode and provider integration. In normal `Chat`, built-in providers can use their native SDKs when enabled, while local or third-party services can use OpenAI-compatible endpoints. RAG-backed Chat and other workflows that rely on LlamaIndex use the model's configured LlamaIndex provider/wrapper; provider-specific agent runtimes can use their own integration path.

Configure provider credentials/endpoints once in `Config -> Settings -> API Keys` or, for runtime OpenAI-compatible providers, in `Config -> Settings -> Custom providers`. LlamaIndex-backed modes reuse those global settings automatically and use the selected model ID as the model name. Model-level LlamaIndex `**kwargs` and `ENV` can remain empty.

Use the model's **Advanced** LlamaIndex fields only when you need an explicit provider-specific override or extra constructor parameter. For `Local models (OpenAI API compatible)`, prefer the per-model `API base` and `API key` fields when only one model needs a different connection.

Embeddings follow the same rule. Configure the global embedding provider and provider-to-model mappings in `Config -> Settings -> Indexes / RAG -> Embeddings`. API keys and endpoints are inherited from the selected provider's global configuration; `Global embeddings provider **kwargs` and `Global embeddings provider ENV vars` are optional Advanced overrides. DeepSeek and Anthropic use the configured VoyageAI key for their default Voyage embedding integration.

# Plugins

## Overview

**PyGPT** can be enhanced with plugins that add tools, integrations, automation, multimodal features, and additional context directly to conversations.

The following plugins are currently available:

- `API calls` - connects models to external services through user-defined API endpoints, request methods, parameters, and payloads.

- `Audio input` - adds speech recognition and microphone input using providers such as OpenAI Whisper, local Whisper, Google, Bing, and xAI Grok Voice.

- `Audio output` - enables speech synthesis for every received response using providers such as OpenAI, Microsoft Azure, Google, Eleven Labs, and xAI.

- `Autonomous mode` - runs an autonomous multi-step conversation loop inside standard chat modes and can cooperate with other enabled plugins to complete tasks.

- `Bitbucket` - connects to Bitbucket Cloud for repository, file, issue, pull request, workspace, and account operations.

- `Chat history (inline)` - gives models access to saved conversation history and calendar day notes, including reading, searching, creating, and updating stored entries.

- `Crontab / Task scheduler` - lets models create and manage scheduled prompts and tasks using cron-based schedules.

- `Custom commands` - exposes user-defined system commands and scripts as callable tools with configurable arguments and execution rules.

- `Experts (inline)` - exposes enabled Expert presets through the regular `expert_call` tool in supported chat modes; Experts run as regular agents on the same Agents v2 runtime used by Chat with Agents.

- `Extra system prompt` - automatically appends reusable custom instructions or additional context to the active system prompt.

- `Facebook` - connects to the Facebook Graph API for working with pages, posts, photos, and related account information.

- `Files I/O` - gives models controlled access to local files and directories for reading, writing, copying, moving, downloading, searching, and indexing data.

- `GitHub` - connects to GitHub for repository, file, issue, pull request, code search, and account operations.

- `Google` - integrates Gmail, Drive, Calendar, Contacts, Keep, Docs, Maps, Colab, and YouTube so models can work with Google services from conversations.

- `Image generation (inline)` - adds image generation and editing directly to conversations using a separately configured image model without requiring a mode change.

- `Mailer` - provides email access through configured mail services, including sending and reading messages where supported.

- `MCP` - connects models to external Model Context Protocol servers and exposes discovered remote tools through stdio, SSE, or Streamable HTTP transports.

- `Memory (inline)` - provides compact global/per-project long-term memory, raw keyed memory, and conversation-scoped continuation notes (`memory_ctx`) used to preserve important state across long-context rollovers.

- `Mouse and keyboard` - lets models control the mouse and keyboard, capture screenshots, and interact with the desktop or supported sandbox environment.

- `OpenStreetMap` - adds geocoding, place search, routing, and map utilities based on OpenStreetMap services.

- `Python interpreter` - lets models execute Python or IPython code on the host, in the built-in uv-managed CPython sandbox, or in Docker, with mutually exclusive standard-Python/IPython tool sets and project-aware file access.

- `RAG (inline)` - adds RAG and LlamaIndex retrieval to standard conversations, allowing models to use indexed files, project indexes, and stored context as additional knowledge.

- `Real time` - appends the current date and/or time to system prompts so models can receive up-to-date local time context.

- `Serial port / USB` - gives models access to configured serial and USB devices for reading data and sending commands.

- `Server (SSH/FTP)` - connects to remote servers through SSH, SFTP, or FTP for command execution, file transfers, and filesystem operations.

- `Slack` - connects to Slack workspaces for reading conversations, managing messages, working with users, and transferring files.

- `System (OS)` - executes system commands on the host, in the built-in uv-managed sandbox, or in Docker, with project-aware runtime paths.

- `Telegram` - connects to Telegram bots or user accounts for messaging, chat access, contacts, media, and file transfers.

- `Tuya (IoT)` - connects to Tuya Cloud so models can inspect, search, and control supported smart-home and IoT devices.

- `TwelveLabs` - adds video understanding and multimodal embeddings using TwelveLabs Pegasus and Marengo models.

- `Vision (inline)` - provides a fallback vision model for chats where the selected model does not support image input; models with native vision handle images directly.

- `Voice control (inline)` - lets spoken commands trigger configured PyGPT actions directly while a conversation is active.

- `Web search` - adds real-time web search, webpage retrieval, crawling, and external-content indexing using supported search providers and LlamaIndex loaders.

- `Wikipedia` - provides Wikipedia search, article lookup, summaries, geographic discovery, and random-page access.

- `Wolfram Alpha` - adds computational knowledge, symbolic and numeric mathematics, unit conversions, matrix operations, and generated plots through Wolfram Alpha.

- `X/Twitter` - connects to X for searching and reading posts, publishing content, managing interactions, bookmarks, and media.

**Tip:** Inline plugins work independently of the `Tools` switch in the toolbox. Once enabled, they remain active throughout the conversation and can provide their functionality automatically when applicable.

## API calls

The API calls plugin turns user-defined HTTP endpoints into model-callable tools. Configure GET/POST parameters, JSON templates, headers and placeholders to connect a conversation to your own REST APIs.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#api-calls

## Audio input

The Audio input plugin captures microphone audio and converts speech to text for chat input and voice commands. It supports OpenAI Whisper, local Whisper, Google, Google Cloud, Google GenAI, Bing and xAI Grok Voice, with configurable device, language and recognition behavior.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#audio-input

## Audio output

The Audio output plugin reads model responses aloud. Choose OpenAI, Azure, Google Cloud, Google GenAI, ElevenLabs or xAI TTS and configure the provider-specific voice, model, language and credentials.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#audio-output

## Autonomous mode

**WARNING: Use autonomous mode with caution.** Long or unlimited runs can make repeated API requests and tool calls, including actions with side effects.

The Autonomous mode plugin adds the same iterative autonomous loop to supported standard chat modes. Instead of simulating a conversation with itself, the model keeps working on the original user request across successive passes: it can perform another action, inspect tool results, verify earlier work, refine the result, and continue until the run-control rules stop it. It can cooperate with other enabled plugins, so tools such as web search, Files I/O, Python interpreter, image generation, and other integrations remain available through the normal PyGPT tool flow.

The **Iterations** option limits the number of autonomous passes; `0` means unlimited. **Auto-stop** lets the model finish the run early when the goal is complete. **Always continue** is mutually exclusive with Auto-stop: enabling it disables Auto-stop and makes the loop open-ended, ignoring the normal iteration limit until the run is stopped externally.

**Dynamic continuous prompt** is enabled by default. After every completed pass, a hidden, tool-free call to the same selected model acts as a judge and produces the next continuation instruction from the original user input plus a recent tail of Autonomous Assistant responses. The judge instruction is shown in the live conversation as a localized `Judge:` pseudo-input, without creating another user turn. **Responses to judge** defaults to `3`; set it to `0` to send all Assistant responses produced since that user input. If the judge call fails, the plugin falls back to the static continuation prompt.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#autonomous-mode

## Bitbucket

The Bitbucket plugin exposes Bitbucket Cloud repositories, files, issues, pull requests, workspaces and account information as tools. Authentication can use an App Password or bearer token.

- Retrieve details about the authenticated user.
- Get information about a specific user.
- List available workspaces.
- List repositories in a workspace.
- Get details about a specific repository.
- Create a new repository.
- Delete an existing repository.
- Retrieve contents of a file in a repository.
- Upload a file to a repository.
- Delete a file from a repository.
- List issues in a repository.
- Create a new issue.
- Comment on an existing issue.
- Update details of an issue.
- List pull requests in a repository.
- Create a new pull request.
- Merge an existing pull request.
- Search for repositories.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#bitbucket

## Chat history (inline)

The Chat history (inline) plugin lets the model search and read saved conversations and work with calendar day notes, including creating and updating notes.

Example prompts:

```Show me today's note.```

```Save a new note for today.```

```Update today's note with...```

```Show me yesterday's conversations.```

```Show me the contents of conversation ID 123.```

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#chat-history-inline

## Crontab / Task scheduler

The Crontab / Task scheduler plugin lets the model create, inspect and manage scheduled prompts and tasks using cron expressions.

![v2_crontab](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_crontab.png)

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#crontab-task-scheduler

## Custom commands

The Custom commands plugin turns your own shell commands, scripts and applications into model-callable tools. Each command can define its arguments, usage instruction and execution rules; a tutorial command is included as an example:

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#custom-commands

## Experts (inline)

The Experts (inline) plugin makes enabled Expert presets available in supported chat modes through the regular `expert_call` tool. When the current model delegates a task, the selected Expert is executed as a regular agent by the same **Agents v2 runtime** used by **Chat with Agents**, and its final response is returned directly as the tool result.

Use **Experts** mode to define, configure, enable, or disable Expert presets. Once an Expert is enabled, you can simply ask for it by name in the conversation, for example: `Ask the Python programmer expert to review this code.` The model can then call `expert_call` automatically.

See the `Work modes -> Experts` section for more details.

## Extra system prompt

The Extra system prompt plugin appends selected reusable instructions or context to the active system prompt, making the same guidance available on every request.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#extra-system-prompt

## Facebook

The Facebook plugin exposes Facebook Graph API operations for pages, posts and media, including publishing, deleting and uploading content. Authentication uses OAuth2.

- Retrieving basic information about the authenticated user.
- Listing all Facebook pages the user has access to.
- Setting a specified Facebook page as the default.
- Retrieving a list of posts from a Facebook page.
- Creating a new post on a Facebook page.
- Deleting a post from a Facebook page.
- Uploading a photo to a Facebook page.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#facebook

## Files I/O

The Files I/O plugin gives the model file and directory tools for reading, writing, copying, moving, downloading, searching and indexing content on the local filesystem. The effective read/write scope is controlled in `Config -> Settings -> Security -> General`. Disabling the filesystem restrictions allows access outside the active data directory, including the host filesystem, so enable broader access only when required and only for trusted workflows.

Plugin capabilities include:

- Sending files as attachments
- Reading files
- Appending to files
- Writing files
- Deleting files and directories
- Listing files and directories
- Creating directories
- Downloading files
- Copying files and directories
- Moving (renaming) files and directories
- Reading file info
- Indexing files and directories using LlamaIndex
- Querying files using LlamaIndex
- Searching for files and directories

If a file being created (with the same name) already exists, a prefix including the date and time is added to the file name.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#files-i-o

## GitHub

The GitHub plugin exposes repositories, files, issues, pull requests, searches and account operations through the GitHub API. Authenticate with a Personal Access Token or OAuth Device Flow.

- Retrieve details about your GitHub profile.
- Get information about a specific GitHub user.
- List repositories for a user or organization.
- Retrieve details about a specific repository.
- Create a new repository.
- Delete an existing repository.
- Retrieve the contents of a file in a repository.
- Upload or update a file in a repository.
- Delete a file from a repository.
- List issues in a repository.
- Create a new issue in a repository.
- Add a comment to an existing issue.
- Close an existing issue.
- List pull requests in a repository.
- Create a new pull request.
- Merge an existing pull request.
- Search for repositories based on a query.
- Search for issues based on a query.
- Search for code based on a query.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#github

## Google (Gmail, Drive, Calendar, Contacts, YT, Keep, Docs, Maps, Colab)

The Google plugin exposes Gmail, Drive, Calendar, Contacts, Keep, Docs, Maps, Colab and YouTube tools so the model can work with Google data and services from a conversation.

- **Gmail**
  - Listing recent emails from Gmail.
  - Listing all emails from Gmail.
  - Searching emails in Gmail.
  - Retrieving email details by ID in Gmail.
  - Sending an email via Gmail.
  
- **Google Calendar**
  - Listing recent calendar events.
  - Listing today's calendar events.
  - Listing tomorrow's calendar events.
  - Listing all calendar events.
  - Retrieving calendar events by a specific date.
  - Adding a new event to the calendar.
  - Deleting an event from the calendar.
  
- **Google Keep**
  - Listing notes from Google Keep.
  - Adding a new note to Google Keep.
  
- **Google Drive**
  - Listing files from Google Drive.
  - Finding a file in Google Drive by its path.
  - Downloading a file from Google Drive.
  - Uploading a file to Google Drive.
  
- **YouTube**
  - Retrieving information about a YouTube video.
  - Retrieving the transcript of a YouTube video.
  
- **Google Contacts**
  - Listing contacts from Google Contacts.
  - Adding a new contact to Google Contacts.
  
- **Google Docs**
  - Creating a new document.
  - Retrieving a document.
  - Listing documents.
  - Appending text to a document.
  - Replacing text in a document.
  - Inserting a heading in a document.
  - Exporting a document.
  - Copying from a template.
  
- **Google Maps**
  - Geocoding an address.
  - Reverse geocoding coordinates.
  - Getting directions between locations.
  - Using the distance matrix.
  - Text search for places.
  - Finding nearby places.
  - Generating static map images.
  
- **Google Colab**
  - Listing notebooks.
  - Creating a new notebook.
  - Adding a code cell.
  - Adding a markdown cell.
  - Getting a link to a notebook.
  - Renaming a notebook.
  - Duplicating a notebook.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#google-gmail-drive-calendar-contacts-yt-keep-docs-maps-colab

## Image generation (inline)

The Image generation (inline) plugin adds an `image` tool to chats so the current model can delegate image creation or editing to the image-generation model configured in the plugin. It works independently of the global `Tools` switch.

By default, the plugin appends a short image-generation instruction to the system prompt so the current model knows when and how to use the `image` tool. You can disable this behavior with `Append image prompt to system prompt` while keeping the image tool available.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#image-generation-inline

## Mailer

The Mailer plugin provides email tools for sending messages and accessing configured mailbox operations. Configure the mail server, account credentials and individual mail tools in the plugin settings.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#mailer

## MCP (Model Context Protocol)

The MCP (Model Context Protocol) plugin connects PyGPT to Model Context Protocol servers over stdio, Streamable HTTP or SSE, discovers their tools and exposes allowed tools to the model.

To configure MCP connections, open `Config -> MCP...` or use `Plugins -> Settings -> MCP`. For easier setup and management, use [MCP Connectors](#mcp-connectors) from `Config -> MCP... -> Connectors...` to browse, import and manage connector definitions. See the [MCP Connectors](#mcp-connectors) section for more details.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#mcp

## Memory (inline)

The Memory (inline) plugin gives the model persistent memory beyond normal chat history. It supports three separate mechanisms:

- **Compact long-term memory** — one global memory outside projects and one isolated memory per project. It can be updated automatically with the configured memory model and is intended for durable reusable state rather than routine chat details.
- **Keyed memory** — raw key/value records stored exactly as supplied. Keys are isolated between global and per-project scope and are retrieved explicitly with `memory_key_*` tools.
- **Conversation continuation notes** — compact `memory_ctx` notes tied to exactly one conversation. They are separate from global/project memory and are intended to preserve goals, constraints, decisions, completed work, important findings and pending work across context-window trimming.

The Memory (inline) plugin works independently of the global `Tools` switch. Its compact-memory options include the update model, maximum memory size, refinement of manual `memory_add`, automatic attachment of global/project memory, and optional searching of keyed-memory content. Auto-attach applies only to compact global/project memory; keyed records and conversation notes are not automatically appended by those plugin options.

Conversation-note tools are `memory_ctx_get()`, `memory_ctx_add(text)` and `memory_ctx_replace(text)`. With **experimental Advanced context handling**, PyGPT core can maintain the same conversation notes automatically during checkpoints. In Chat with Agents those core context tools remain available when advanced handling is enabled even if the optional Memory plugin is disabled.

For full configuration details and the complete `memory_*`, `memory_key_*`, and `memory_ctx_*` tool reference, see:

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#memory-inline

## Mouse and keyboard

**WARNING: Use this plugin with caution - allowing all options gives the model full control over the mouse and keyboard**

The Mouse and keyboard plugin gives the model desktop interaction tools for pointer movement, clicks, scrolling, keyboard input and screenshots. It can also provide the browser interaction backend used by Computer use.

Plugin capabilities include:

- Get mouse cursor position
- Control mouse cursor position
- Control mouse clicks
- Control mouse scroll
- Control the keyboard (pressing keys, typing text)
- Making screenshots

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#mouse-and-keyboard

## OpenStreetMap

The OpenStreetMap plugin provides geocoding, place search, routing and map/tile utilities through OpenStreetMap-related services:

- Forward and reverse geocoding via Nominatim
- Search with optional near/bbox filters
- Routing via OSRM (driving, walking, cycling)
- Generate openstreetmap.org URL (center/zoom or bbox; optional marker)
- Utility helpers: open an OSM website URL centered on a point; download a single XYZ tile

Images are saved under `data/openstreetmap/` in the user data directory.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#openstreetmap

## Python interpreter

The Python interpreter plugin gives the model and the Python/OS tool a Python/IPython runtime for code execution, package use and shell commands, with host, built-in and Docker backends.

### Executing code

The Python interpreter plugin provides local Python execution for model-generated code and for code started manually from the **Python/OS** window. It uses the active conversation's runtime `data` workdir, so project-specific data workdirs are handled automatically. Execution can run directly on the host or through the selected sandbox backend.

The **Use IPython** option selects which Python tool set is exposed to the model. It is enabled by default:

- with **Use IPython** enabled, the model receives only `ipython_exec`, `ipython_sys_exec`, and `ipython_kernel_restart`;
- with **Use IPython** disabled, the model receives only `python_exec`, `python_exec_file`, and `python_sys_exec`.

The two execution tool sets are never exposed together. The HTML Canvas tools `html_render_output` and `html_get_output` are independent of this selection.

**IPython:** IPython is the recommended execution mode because it keeps kernel state between calls and supports iterative workflows, data analysis, and IPython magic/shell syntax such as `!pip install <package_name>`. Use `ipython_exec` for Python code and `ipython_sys_exec` for shell/system commands in the same runtime environment.

**Standard Python:** `python_exec` executes Python code directly and accepts only the `code` argument. PyGPT manages the temporary script path internally. Use `python_exec_file(path)` only when an existing Python file should be executed. `python_sys_exec` runs shell/system commands in the same selected host or sandbox runtime as standard Python.

**Sandbox:** The **Sandbox** selector is available at the beginning of the plugin's **General** tab. **Disabled** runs Python/IPython directly on the host and is unsafe for untrusted code. **Built-in sandbox** uses a separate uv-managed CPython environment and does not require Docker; it isolates the Python environment from PyGPT itself, but it is not a filesystem/network security boundary. **Docker** requires Docker to be installed and running and provides the strongest isolation of the available options. In both sandbox modes, the active conversation's `data` workdir is used as the runtime working directory; Docker exposes it as `/mnt/data`, while the built-in sandbox uses the host path.

**Built-in packages:** Add persistent packages in `Plugins -> Settings -> Python interpreter -> Built-in sandbox`, one requirement per line. Package-list changes rebuild the environment on the next use; use `Tools -> Sandbox / Docker` to rebuild it immediately. Packages installed manually with `pip` are removed by a rebuild unless they are also listed there.

**Docker permissions:** The stock Docker images run as the unprivileged `pygpt` user by default, with passwordless `sudo` available when elevated privileges are required. Separate **Run as root** options are available for the IPython and standard-Python Docker runtimes.

Docker installation: [Docker Engine](https://docs.docker.com/engine/install/) | [Docker Desktop](https://docs.docker.com/desktop/)

**Tip: connecting Docker in the Snap version**:

To use the Docker sandbox in the Snap version, connect PyGPT to the Docker daemon:

```commandline
sudo snap connect pygpt:docker-executables docker:docker-executables
```

````commandline
sudo snap connect pygpt:docker docker:docker-daemon
````

**Python/OS window:** PyGPT includes the **Python/OS** tool for real-time Python and IPython execution. Click the `<>` icon above the input field, use `Tools -> Python / OS`, or open it in a split/output tab. Plugin code input/output is mirrored there when **Connect to the Python/OS window** is enabled. The same **Use IPython** setting controls manual execution from this window, so the UI and the model-facing tool set use the same interpreter mode.

![v2_interpreter_icon](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_interpreter_icon.png)

![v2_python](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_python.png)

**Tip:** Remember to enable the `Tools` switch to allow tools from plugins to be executed.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#python-interpreter

## RAG (inline)

The RAG (inline) plugin lets standard chats query configured LlamaIndex indexes and inject retrieved context when needed. It can use the active project index automatically and also configures the image model used by the vision data loader.

When **Use project index if in use** is enabled (default), the plugin automatically queries the isolated **Current project** index whenever the active conversation belongs to a project. Outside a project it uses the configured regular index or indexes.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#rag-inline

## Real time

The Real time plugin adds the current date, time or both to the system prompt, giving models explicit access to the local current time for each request.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#real-time

## Serial port / USB

The Serial port / USB plugin lets the model exchange text or raw bytes with configured serial devices, such as Arduino boards and other controllers.

**Tip:** in Snap version you must connect the interface first: https://snapcraft.io/docs/serial-port-interface

You can send commands to, for example, an Arduino or any other controllers using the serial port for communication.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#serial-port-usb

## Server (SSH/FTP)

The Server (SSH/FTP) plugin provides remote command execution and file management over SSH, SFTP and FTP, including directory operations and file transfers.

For security reasons, the model will not see any credentials, only the server name and port fields (see the docs)

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#server-ssh-ftp

## Slack

The Slack plugin exposes workspace conversations, messages, users and file transfer operations through the Slack Web API. Authentication uses OAuth2.

- Retrieving a list of users.
- Listing all conversations.
- Accessing conversation history.
- Retrieving conversation replies.
- Opening a conversation.
- Posting a message in a chat.
- Deleting a chat message.
- Uploading files to Slack.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#slack

## System (OS)

The System (OS) plugin gives the model a `sys_exec` tool for running shell commands in the active data workdir. Commands can run on the host, in the built-in uv-managed environment, or in Docker.

- **Disabled** executes `sys_exec` directly on the host and is unsafe for untrusted commands.
- **Built-in sandbox** executes commands in a separate uv-managed CPython environment and does not require Docker. It separates the command environment from PyGPT's own Python installation, but it is not a filesystem/network security boundary.
- **Docker** executes `sys_exec` inside the Docker sandbox. Docker must be installed and running; this backend provides the strongest isolation of the available options.

When Docker is selected, the active conversation's runtime `data` directory is mounted as `/mnt/data` and used as the command working directory. Project-specific data workdirs are mapped automatically. The stock Docker image runs as the unprivileged `pygpt` user by default and provides passwordless `sudo`; **Run as root** can be enabled when required.

`sys_exec` input/output is mirrored to the Python/OS window when **Connect to the Python/OS window** is enabled. **Auto-append CWD to sys_exec** uses the active host data workdir in host mode and `/mnt/data` in Docker mode.

**Built-in packages:** Configure the System / OS environment in `Plugins -> Settings -> System (OS) -> Built-in sandbox`, one requirement per line. Changes rebuild the environment on the next use; use `Tools -> Sandbox / Docker` for an immediate rebuild.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#system-os

## Telegram

The Telegram plugin provides messaging, chat, contact, media and file tools for Telegram bots and user accounts through the Bot API and Telethon.

- Sending text messages to a chat or channel.
- Sending photos with an optional caption to a chat or channel.
- Sending documents or files to a chat or channel.
- Retrieving information about a specific chat or channel.
- Polling for updates in bot mode.
- Downloading files using a file identifier.
- Listing contacts in user mode.
- Listing recent dialogs or chats in user mode.
- Retrieving recent messages from a specific chat or channel in user mode.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#telegram

## Tuya (IoT)

The Tuya (IoT) plugin lets the model list, inspect, search and control supported smart-home devices connected through Tuya Cloud.

* Provide your Tuya Cloud Client ID, Client Secret, and linked App Account UID to enable communication; access/refresh tokens and the device cache are managed automatically.
* Access and list all smart devices connected to your Tuya app account.
* Retrieve detailed information about each device, including its status and supported functions.
* Effortlessly search for devices by their names using cached data for quick access.
* Control devices by turning them on or off, toggle states, and set specific device parameters.
* Send custom commands to devices for more advanced control.
* Read sensor values and normalize them for easy interpretation.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#tuya-iot

## TwelveLabs

The TwelveLabs plugin brings native video understanding to PyGPT through the [TwelveLabs](https://twelvelabs.io) API. The model can analyze videos with the `Pegasus` model and create multimodal embeddings with the `Marengo` model.

* Analyze a video and answer a prompt about it (summary, description, Q&A) from a public video URL or an already-indexed `video_id` (`tl_analyze_video`, Pegasus).
* Create a multimodal text embedding that lives in the same vector space as Marengo video embeddings, useful for text-to-video search (`tl_embed_text`, Marengo).
* Configure the Pegasus and Marengo model names, default max tokens, temperature, and request timeout.

Provide your API key in the plugin settings, or set the `TWELVELABS_API_KEY` environment variable. Defaults are `pegasus1.5` for analysis, `marengo3.0` for embeddings, 2048 max tokens, temperature 0.2, and a 300-second request timeout. You can grab a free API key at https://twelvelabs.io — there is a generous free tier.

## Vision (inline)

Models with native image input can analyze images directly in Chat; **Vision (inline) is not needed for them**. Use this plugin only as a fallback when the selected chat model does not support vision. In that case, image attachments, screenshots and camera captures are routed through the separately configured image-capable Chat model.

The fallback model list is filtered by `Chat` + image-input capability and can use any supported provider.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#vision-inline

## Voice control (inline)

The Voice control (inline) plugin recognizes spoken PyGPT actions while you are in a conversation. An optional magic prefix can be required before a spoken action is treated as a voice command.

See the `Accessibility` section for more details.

## Web search

The Web search plugin gives the model live web search, page retrieval and crawling tools using DuckDuckGo, Google Custom Search or Microsoft Bing. Retrieved web content can also be passed into LlamaIndex-based workflows where supported.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#web-search

## Wikipedia

The Wikipedia plugin provides article search, summaries, full-page lookup, title suggestions, geographic discovery and random-page tools with configurable language handling.

* Set your preferred language for Wikipedia queries.
* Retrieve and check the current language setting.
* Explore a list of supported languages.
* Search for articles using keywords or get suggestions for queries.
* Obtain summaries and detailed page content.
* Discover articles by geographic location or randomly.
* Open articles directly in your web browser.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#wikipedia

## Wolfram Alpha

Provides computational knowledge via Wolfram Alpha: short answers, full JSON pods, numeric and symbolic math (solve, derivatives, integrals), unit conversions, matrix operations, and plots rendered as images. Images are saved under `data/wolframalpha/` in the user data directory.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#wolfram-alpha

## X/Twitter

The X/Twitter plugin exposes X tools for reading and searching posts, publishing, replying, quoting, likes, reposts, bookmarks and media uploads. Authentication uses OAuth2.

- Retrieve user details by providing their username.
- Fetch user information using their unique ID.
- Access recent tweets from a specific user.
- Search for recent tweets using specific keywords or hashtags.
- Create a new tweet and post it on the platform.
- Remove an existing tweet from your profile.
- Reply to a specific tweet with a new comment.
- Quote a tweet while adding your own comments or thoughts.
- Like a tweet to show appreciation or support.
- Remove a like from a previously liked tweet.
- Retweet a tweet to share it with your followers.
- Undo a retweet to remove it from your profile.
- Hide a specific reply to a tweet.
- List all bookmarked tweets for easy access.
- Add a tweet to your bookmarks for later reference.
- Remove a tweet from your bookmarks.
- Upload media files such as images or videos for tweeting.
- Set alternative text for uploaded media for accessibility.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#x-twitter

# Creating Your Own Plugins

PyGPT can be extended with custom plugins, models, LLM wrappers, vector stores, data loaders, audio providers, web providers, and agents.

For implementation guides, launcher examples, plugin APIs, and complete code samples, see the full documentation:

https://pygpt.readthedocs.io/en/latest/extending.html

# Functions, commands and tools

PyGPT supports native API tool/function calls as well as its internal prompt-based command/tool system. Commands exposed by enabled plugins can be called by compatible models when the `Tools` switch is enabled. Native API tool calls can be enabled in `Config -> Settings -> Prompts`, and model-level support is controlled by the `Tool calls` option in the Models Editor.

Custom commands and API function schemas can be used together and are translated by PyGPT when required.

For command syntax, JSON schemas, custom command examples, and complete tool-call integration examples, see:

https://pygpt.readthedocs.io/en/latest/functions.html

# Tools

PyGPT features several useful tools, including:

- Notepad
- Painter
- Calendar
- Indexer
- Media Player
- Image viewer
- Text editor
- Transcribe audio/video files
- OpenAI Vector Stores
- Google Vector Stores
- Python/OS
- HTML/JS Canvas (built-in HTML renderer)
- Translator
- Web Browser (Chromium)
- Agent Workflow
- Agent Builder (Legacy)

![v2_tool_menu](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_tool_menu.png)


## Notepad

The application has a built-in notepad, divided into several tabs. This can be useful for storing information in a convenient way, without the need to open an external text editor. The content of the notepad is automatically saved whenever the content changes.

![v2_notepad](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_notepad.png)

## Painter

Using the `Painter` tool, you can create quick sketches and submit them to the model for analysis. You can also edit opened from disk or captured from camera images, for example, by adding elements like arrows or outlines to objects. Additionally, you can capture screenshots from the system - the captured image is placed in the drawing tool and attached to the query being sent.

![v2_draw](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_draw.png)

To capture the screenshot just click on the `Ask with screenshot` option in a tray-icon dropdown:

![v2_screenshot](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_screenshot.png)

## Calendar

Using the calendar, you can go back to selected conversations from a specific day and add daily notes. After adding a note, it will be marked on the list, and you can change the color of its label by right-clicking and selecting `Set label color`. By clicking on a particular day of the week, conversations from that day will be displayed.

![v2_calendar](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_calendar.png)


## Indexer


This tool allows indexing of local files or directories and external web content to a vector database, which can then be selected through the **RAG** selector in Chat and other supported workflows. Using this tool, you can manage local indexes and add new data with built-in `LlamaIndex` integration.

![v2_tool_indexer](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_tool_indexer.png)

## Media Player


A simple video/audio player that allows you to play video files directly from within the app.


## Image Viewer


A simple image browser that lets you preview images directly within the app.


## Text Editor


A simple text editor that enables you to edit text files directly within the app.


## Transcribe Audio/Video Files


An audio transcription tool with which you can prepare a transcript from a video or audio file. It will use a speech recognition plugin to generate the text from the file.


## OpenAI / Google Vector Stores


Remote vector stores management.


## Python/OS


This tool allows you to run Python code directly from within the app. It is integrated with the `Python interpreter` plugin. **Use IPython** selects IPython (default) or standard Python, while **Sandbox** selects host execution (**Disabled**), the **Built-in sandbox** based on a uv-managed CPython environment, or **Docker**. Docker provides the strongest isolation; the built-in sandbox separates the execution environment from PyGPT itself and does not require Docker, but it is not a filesystem/network security boundary. In Docker mode the active conversation data workdir is available as `/mnt/data`.

Docker installation: [Docker Engine](https://docs.docker.com/engine/install/) | [Docker Desktop](https://docs.docker.com/desktop/)

## HTML/JS Canvas

Allows to render HTML/JS code in HTML Canvas (built-in renderer based on Chromium). To use it, just ask the model to render the HTML/JS code in built-in browser (HTML Canvas). Tool is integrated with the `Python interpreter` plugin.

## Translator

Enables translation between multiple languages using an AI model.

## Web Browser

A built-in web browser based on Chromium, allowing you to open webpages directly within the app. **SECURITY NOTICE:** For your protection, avoid using the built-in browser for sensitive or critical tasks. It is intended for basic use only.

## Agent Workflow

**Agent Workflow** is a live, human-readable monitor for `Chat with Agents` / Agents v2. It displays the primary agent or orchestrator and worker agents as a hierarchy with timestamped status updates, agent turns, worker creation, task progress, and tool execution. Tool calls provide expandable input/output details, while each agent has a **Details** panel with available runtime information such as its system prompt, instruction, task, input, model/provider, language, and preset.

Open it from `Tools -> Agent Workflow` as a dialog, or pin it to an output tab from the tab context menu. The default configuration includes an Agent Workflow tab in the second output column. When the first actual Chat with Agents run starts after the user sends input in a profile, PyGPT reveals this tab and expands split-screen once. Merely selecting Chat with Agents does not trigger it; after that first-run introduction has been recorded, later runs and mode changes do not alter the user's layout automatically.

![agent_workflow_tool](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v3_workflow.png)


The view is runtime-only and does not replace conversation history or Debug workflow logging. Every new top-level agent run clears the previous workflow automatically. Use **Clear view** to clear it manually.

## Agent Builder (Legacy)

**Legacy modes only:** Agent Builder is used by the legacy `Agent (LlamaIndex)` and `Agent (OpenAI)` workflows. It is not used by the modern `Chat with Agents` mode.

To launch Agent Builder, navigate to:

`Tools -> Agent Builder (Legacy)`

![nodes](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/nodes.png)

This tool allows you to create workflows for agents using a node editor, without writing any code. You can add a new agent type, and it will appear in the list of presets.

To add a new element, right-click on the editor grid and select `Add` to insert a new node.

**Types of Nodes:**

- **Start**: The starting point for agents (user input).
- **Agent**: A single agent with customizable default parameters, such as system instructions and tool usage. These settings can be overridden in the preset.
- **Memory**: Shared memory between agents (shared Context).
- **End**: The endpoint, returning control to the user.

Agents with connected shared memory share it among themselves. Agents without shared memory only receive the latest output from the previous agent.

The first agent in the sequence always receives the full context passed by the user.

Connecting agents and memory is done using node connections via slots. To connect slots, simply drag from the input port to the output port (Ctrl + mouse button removes a connection).

**Node Editor Navigation:**

- **Right-click**: Add node, undo, redo, clear
- **Middle-click + drag**: Pan view
- **Ctrl + Mouse wheel**: Zoom
- **Left-click a port**: Create connection
- **Ctrl + Left-click a port**: Rewire or detach connection
- **Right-click or DELETE a node/connection**: Remove node/connection

**Tip:** Enable agent debugging in `Settings -> Debug -> Log Agents usage to console` to log the full workflow to the console.

Workflows built with this tool are compatible with the legacy `Agent (OpenAI)` and `Agent (LlamaIndex)` modes.

**Notes:** Multi-branch agent flows automatically receive an internal routing instruction that tells the current agent which downstream route can be selected.

For the complete routing schema, injected system-instruction example, and Agent Builder details, see:

https://pygpt.readthedocs.io/en/latest/tools.html#agent-builder-legacy

**INFO:** Agent Builder is a legacy tool for the older agent modes.


# Token usage calculation

## Input tokens

The application features a token calculator. It attempts to forecast the number of tokens that 
a particular query will consume and displays this estimate in real time. This gives you improved 
control over your token usage. The app provides detailed information about the tokens used for the user's prompt, 
the system prompt, any additional data, and those used within the context (the memory of previous entries).

**Remember that these are only approximate calculations and do not include, for example, the number of tokens consumed by some plugins. You can find the exact number of tokens used on provider's website.**

![v2_tokens1](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_tokens1.png)

## Total tokens

After receiving a response from the model, the application displays the actual total number of tokens used for the query (received from the API).

![v2_tokens2](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_tokens2.png)


# Accessibility

PyGPT includes beta accessibility features and voice control, including options that can assist blind and visually impaired users.

In the `Config / Accessibility` menu, you can turn on accessibility features such as:


- activating voice control

- translating actions and events on the screen with audio speech

- setting up keyboard shortcuts for actions.


**Using voice control**

Voice control can be turned on in two ways: globally, through settings in `Config -> Accessibility`, and by using the `Voice control (inline)` plugin. Both options let you use the same voice commands, but they work a bit differently - the global option allows you to run commands outside of a conversation, anywhere, while the plugin option lets you execute commands directly during a conversation – allowing you to interact with the model and execute commands at the same time, within the conversation.

In the plugin (inline) option, you can also turn on a special trigger word that will be needed for content to be recognized as a voice command. You can set this up by going to `Plugins -> Settings -> Voice control (inline)`:

```bash
Magic prefix for voice commands
```

**Tip:** When the voice control is enabled via a plugin, simply provide commands while providing the content of the conversation by using the standard `Microphone` button.


**Enabling voice control globally**


Turn on the voice control option in `Config / Accessibility`:


```bash
Enable voice control (using the microphone)
```

Once you enable this option, an `Voice Control` button will appear at the bottom right corner of the window. When you click on this button, the microphone will start listening; clicking it again stops listening and starts recognizing the voice command you said. You can cancel voice recording at any time with the `ESC` key. You can also set a keyboard shortcut to turn voice recording on/off.


Voice command recognition works based on a model, so you don't have to worry about saying things perfectly.


**Here's a list of commands you can ask for by voice:**

- Get the current application status
- Exit the application
- Enable audio output
- Disable audio output
- Enable audio input
- Disable audio input
- Add a memo to the calendar
- Clear memos from calendar
- Read the calendar memos
- Enable the camera
- Disable the camera
- Capture image from camera
- Create a new context
- Go to the previous context
- Go to the next context
- Go to the latest context
- Focus on the input
- Send the input
- Clear the input
- Get current conversation info
- Get available commands list
- Stop executing current action
- Clear the attachments
- Read the last conversation entry
- Read the whole conversation
- Rename current context
- Search for a conversation
- Clear the search results
- Send the message to input
- Append message to current input without sending it
- Switch to chat mode
- Switch to the next mode
- Switch to the previous mode
- Switch to the next model
- Switch to the previous model
- Add note to notepad
- Clear notepad contents
- Read current notepad contents
- Switch to the next preset
- Switch to the previous preset
- Switch to the chat tab
- Switch to the calendar tab
- Switch to the draw (painter) tab
- Switch to the files tab
- Switch to the notepad tab
- Switch to the next tab
- Switch to the previous tab
- Start listening for voice input
- Stop listening for voice input
- Toggle listening for voice input

More commands coming soon.

Just ask for an action that matches one of the descriptions above. These descriptions are also known to the model, and relevant commands are assigned to them. When you voice a command that fits one of those patterns, the model will trigger the appropriate action.


For convenience, you can enable a short sound to play when voice recording starts and stops. To do this, turn on the option:


```bash
Audio notification for microphone listening start/stop
```

To enable a sound notification when a voice command is recognized and command execution begins, turn on the option:


```bash
Audio notification for voice command execution
```

For voice translation of on-screen events and information about completed commands via speech synthesis, you can turn on the option:

```bash
Use voice synthesis to describe events on the screen.
```
![v2_access](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_access.png)

# Configuration

## Settings

Application settings are available from:

```ini
Config -> Settings...
```

![v2_settings](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_settings.png)

The current top-level Settings sections are: **General**, **API Keys**, **Layout**, **Files and attachments**, **Chats**, **Remote tools**, **Models**, **Prompts**, **Images and video**, **Vision and camera**, **Audio**, **Indexes / RAG**, **Agents and experts**, **Accessibility**, **Security**, **Personalize**, **Custom providers**, **Updates**, and **Debug**. Several sections use additional tabs; the current layout includes:

- **API Keys:** OpenAI, Google, Anthropic, Hugging Face, DeepSeek, xAI, Azure OpenAI, Perplexity, Mistral AI, Voyage AI, OpenRouter, Forge, Eden AI
- **Layout:** General, Code syntax
- **Files and attachments:** General, RAG
- **Chats:** List, Render, Options
- **Context:** General, Tools, Advanced handling
- **Remote tools:** OpenAI, Google, Anthropic, xAI
- **Images and video:** Image, Video
- **Vision and camera:** Camera
- **Audio:** Devices, Options, Cache
- **Indexes / RAG:** General, Vector Store, Chat, Embeddings, File indexing, Context indexing, Data loaders, Clear and truncate
- **Agents and experts:** Chat with Agents, Agents, Autonomous, Options
- **Security:** General, Computer use, Linux, Windows, macOS

For the complete configuration options reference, including descriptions and default values for all settings, see:

https://pygpt.readthedocs.io/en/latest/configuration.html#settings

## JSON files

The configuration is stored in JSON files for easy manual modification outside of the application. 
These configuration files are located in the user's work directory within the following subdirectory:

``` ini
{HOME_DIR}/.config/pygpt-net/
```

## Manual configuration

PyGPT stores its configuration and user data in the working directory, which by default is:

```ini
{HOME_DIR}/.config/pygpt-net/
```

Configuration files such as `config.json` and `models.json` can also be edited manually.

A project's custom workdir does **not** replace this profile/application workdir. It overrides only the logical `data` directory for conversations assigned to that project. The **Files** tab, file tools and Docker `/mnt/data` mapping follow the active project data directory at runtime, while `tmp`, configuration, database, cache, CSS, locale, fonts and logs remain in the base profile workdir.

For the complete manual configuration reference, including configuration files and workdir contents, see:

https://pygpt.readthedocs.io/en/latest/configuration.html#manual-configuration

## Setting the Working Directory Using Command Line Arguments

To set the base profile/application working directory using a command-line argument, use:

```
python3 ./run.py --workdir="/path/to/workdir"
```
or, for the binary version:

```
pygpt.exe --workdir="/path/to/workdir"
```

This command-line option changes the entire profile/application workdir. It is different from a project's custom data workdir, which changes only the logical `data` directory for that project.

## Translations / Locale

PyGPT supports custom translations and profile-specific themes. Locale files use the `.ini` format and are loaded automatically by the application.

Custom themes use a directory-per-theme layout under `%workdir%/css/<theme-id>/`, with optional `app.css`, `app.xml`, and `chat.css` files. New custom theme IDs can end in `-dark` or `-light` to define their runtime Dark/Light compatibility; the suffix is omitted from the normal menu title. Unsuffixed custom IDs default to Dark. A user theme can use the same ID as a built-in theme to override/extend it while keeping the built-in compatibility type. Custom fonts can also be placed in the PyGPT working directory.

For the complete translation, locale, CSS override, and custom font reference, see:

https://pygpt.readthedocs.io/en/latest/configuration.html#translations-locale

## Data Loaders

**Configuring data loaders**

In the `Settings -> Indexes / RAG -> Data loaders` section you can define additional keyword arguments passed to data loader instances.

PyGPT includes built-in loaders for common file types and external/web content. In most cases, LlamaIndex loaders are used internally. You can also develop and register your own custom loader.

**Tip:** To index external data or web content, you can use the `Web search` plugin and ask the model to index a supported resource, such as a webpage or YouTube video. The appropriate data loader is selected automatically when possible.

For the complete list of built-in data loaders, supported parameters, defaults, and configuration details, see:

https://pygpt.readthedocs.io/en/latest/configuration.html#configuration-data-loaders


## Vector stores

**Available vector stores** (provided by `LlamaIndex`):

```
- ChromaVectorStore
- ElasticsearchStore
- PinecodeVectorStore
- QdrantVectorStore
- RedisVectorStore
- SimpleVectorStore
```

You can configure selected vector store by providing config options like `api_key`, etc. in `Settings -> Indexes / RAG -> Vector Store`. 

Arguments provided here (on list: `Vector Store (**kwargs)` in `Advanced settings` will be passed to selected vector store provider. You can check keyword arguments needed by selected provider on LlamaIndex API reference page: 

https://docs.llamaindex.ai/en/stable/api_reference/storage/vector_store.html

Which keyword arguments are passed to providers?

For `ChromaVectorStore` and `SimpleVectorStore` all arguments are set by PyGPT and passed internally (you do not need to configure anything).

For other providers you can provide these arguments:

**ElasticsearchStore**

Keyword arguments for ElasticsearchStore(`**kwargs`):

- `index_name` (default: current index ID, already set, not required)
- any other keyword arguments provided on list

**PinecodeVectorStore**

Keyword arguments for Pinecone(`**kwargs`):

- `api_key`
- index_name (default: current index ID, already set, not required)

**QdrantVectorStore**

Keyword arguments for QdrantVectorStore(`**kwargs`):

- `url` - str, default: `http://localhost:6333`
- `api_key` - str, default: `None` (for Qdrant Cloud)
- `collection_name` (default: current index ID, already set, not required)
- any other keyword arguments provided on list

**RedisVectorStore**

Keyword arguments for RedisVectorStore(`**kwargs`):

- `index_name` (default: current index ID, already set, not required)
- any other keyword arguments provided on list

You can extend list of available providers by creating custom provider and registering it on app launch.

Use `Settings -> Indexes / RAG -> Chat -> RAG mode` to choose between normal RAG-backed Chat, querying the index only, or retrieval only.

### Adding custom vector stores and data loaders

You can create a custom vector store provider or data loader for your data and develop a custom launcher for the application. 

See the section `Extending PyGPT / Adding a custom Vector Store provider` for more details.

# Updates

### Updating PyGPT

**PyGPT** comes with an integrated update notification system. When a new version with additional features is released, you'll receive an alert within the app. 

To get the new version, simply download it and start using it in place of the old one. All your custom settings like configuration, presets, indexes, and past conversations will be kept and ready to use right away in the new version.

# Debugging and Logging

Most diagnostic options are available in `Config -> Settings -> Debug`. PyGPT writes application logs to `%workdir%/app.log`, and the log level can be set to `ERROR`, `WARNING`, `INFO`, or `DEBUG`. For startup troubleshooting, `--debug=1` forces `INFO` logging and `--debug=2` forces `DEBUG` logging.

Additional switches can log conversation processing, events, plugin usage, **API inputs**, **API outputs**, **tool calls/results**, attachments, image/video generation, LlamaIndex activity, Realtime sessions, legacy API paths, and agent workflows. For `Chat with Agents`, you can choose either a concise workflow trace or **Log Chat with Agents (verbose mode, full output)**. API/tool/full-agent traces can include prompts, paths, history, tool parameters/results, retrieved context, and other sensitive data; known API secrets are masked by the API-input logger.

Enable `Show debug menu` to expose developer tools such as the live Logger/console, DB Viewer, application-state inspectors, Chromium diagnostics, and WebEngine DevTools. If a compiled build crashes or fails during startup, launch it from a terminal so stdout/stderr and Python/Qt diagnostics remain visible.

For the complete debugging reference, Logger commands, DB Viewer details, compiled-build instructions, and all diagnostic switches, see the [Debugging and Logging documentation](https://pygpt.readthedocs.io/en/latest/debug.html).

# Extending PyGPT

PyGPT can also load custom themes directly from the active profile workdir. Put a theme in `%workdir%/css/<theme-id>/`; supported per-theme files are `app.css`, `app.xml`, and `chat.css`. New custom IDs should use a `-dark` or `-light` suffix to declare runtime compatibility, e.g. `my_custom-dark` becomes **My Custom** and `paper-light` becomes **Paper** in the menu. The suffix remains part of the stored theme ID. If both variants of one base name exist, they are shown as **(Dark)** / **(Light)**. Unsuffixed new custom IDs default to Dark. Reusing a built-in ID such as `ocean` overrides/extends that theme and preserves its built-in Dark/Light type. The runtime type controls qt-material behavior, platform fixes, widgets, renderer compatibility, and fallback assets. The global `data/css/app.css` is always the native UI base, `data/css/chat.css` is the chat base for both Standard and Wide layouts, and `chat.wide.css` is appended only for Wide. See the documentation section **Extending PyGPT -> Custom themes and styles** for the full load order and examples.

PyGPT can be extended with custom models, plugins, LLM wrappers, vector stores, data loaders, audio input/output providers, web providers, and custom agents. Extension components can be registered through a custom launcher.

The repository also contains ready-to-use examples in the `examples` directory.

For complete Python examples, event handling, custom model configuration, provider interfaces, launcher code, and extension API reference, see:

https://pygpt.readthedocs.io/en/latest/extending.html

# DISCLAIMER

This application is not officially associated with OpenAI. The author shall not be held liable for any damages 
resulting from the use of this application. It is provided "as is," without any form of warranty. 
Users are reminded to be mindful of token usage - always verify the number of tokens utilized by the model on 
the API website and engage with the application responsibly. Activating plugins, such as Web search,
may consume additional tokens that are not displayed in the main window. 

**Always monitor your actual token usage on the OpenAI, Google, Anthropic, xAI, etc. websites.**

---

# CHANGELOG

## Recent changes:

**2.8.28 (2026-09-22)**

- Integrated **Chat with Files** into the standard **Chat** mode. RAG is now available across all supported modes.
- Added a **Judge** mode to **Autonomous**, providing improved response evaluation and continuation guidance after each step.
- Added support for defining preinstalled packages in the built-in **Python Interpreter** and **System / OS** sandboxes.
- Added an option to manually rebuild the built-in sandbox virtual environment.
- Optimized Python command execution.
- Other fixes and improvements.

**2.8.27 (2026-09-20)**

- Added a built-in sandboxed Python interpreter running in its own virtual environment, managed by `uv`, available as the default third sandbox option in the Python Interpreter and System / OS plugins. It allows Python code to be executed without requiring Python to be installed on the host system and without using Docker, as the interpreter is bundled and managed directly by PyGPT. See the documentation: Plugins -> Python Interpreter.
- Fixed HTML / Canvas base directory handling for relative paths and local assets.
- UI and CSS fixes, refinements, and visual improvements.

**2.8.26 (2026-09-20)**

- Refactored, improved, and simplified CSS/QSS handling. Overriding and customizing CSS and QSS is now much easier - see the **Extending PyGPT** section in the documentation.
- Fixed and optimized RAG retrieval for improved reliability and performance.
- Fixed the splitter resize policy and improved layout resizing behavior.

**2.8.25 (2026-09-19)**

- Added support for **Agent Skills**, including importing from GitHub, local files, and formats compatible with Claude, Codex, OpenClaw, and other supported ecosystems. Added a dedicated **Skills** management interface for browsing, installing, enabling, disabling, and removing skills.
- Added support for **Claude/Codex-style Connectors**, integrated with the MCP plugin. Connectors can be imported from GitHub, local files, Claude, Codex, OpenClaw, Cursor, VS Code, OpenCode, MCPorter, and compatible JSON, TOML, and YAML definitions. Connector management is available under **Config → MCP → Connectors**.
- Added new application themes: **Matrix, Gray, Mint, Flare, Ocean, Sun, and Retro**.
- Refactored theme/CSS assets into a directory-per-theme layout and added profile-level custom themes/overrides from `%workdir%/css`, including runtime `-dark` / `-light` compatibility classification for custom themes.
- Added **Full Screen mode (F11)** and support for a frameless window layout.
- Optimized message sending from the chat input by moving pre-send preparation tasks to asynchronous workers, reducing UI blocking before requests are sent.
- Various **UI fixes, layout improvements, workflow fixes, and usability refinements** across the application.

**2.8.24 (2026-09-18)**

- Added **Import profile...** and **Export profile...** options to the **File** menu, allowing complete profiles to be exported and imported, including the database, configuration, files, and application data.
- Added an automatic prompt-injection guard in **Settings -> Security -> Auto-prevent prompt injections**.
- Moved the model selector to the input field.
- Added a clock to the Calendar.
- Added subdirectory lookup support for `@mentions`.
- Added runtime switching to the Agent Workflows editor.
- Removed the **Edit JSON configs** option.
- Improved the chat input field.
- Added a loader to the Docker builder.
- Integrated system notifications with **Chat with Agents**.
- The input field is now hidden in non-chat tabs.
- Added date and time headers above chat input blocks.
- Added support for referencing other conversations from the database using `@mentions` with conversation IDs, e.g. `What were we talking about in chat @123?`
- Added various CSS, layout, and UI improvements.

# Credits and links

**Official website:** <https://pygpt.net>

**Documentation:** <https://pygpt.readthedocs.io>

**Support and donate:** <https://pygpt.net/#donate>

**GitHub:** <https://github.com/szczyglis-dev/py-gpt>

**Discord:** <https://pygpt.net/discord>

**Snap Store:** <https://snapcraft.io/pygpt>

**Microsoft Store:** <https://apps.microsoft.com/detail/XP99R4MX3X65VQ>

**PyPI:** <https://pypi.org/project/pygpt-net>

**Author:** Marcin Szczygliński (Poland, EU)

**Contact:** <info@pygpt.net>

**License:** MIT License

# Special thanks

GitHub's community:
- [@atharvaHJoshi](https://github.com/atharvaHJoshi)

- [@ba2512005](https://github.com/ba2512005)

- [@BillionShields](https://github.com/BillionShields)

- [@gfsysa](https://github.com/gfsysa)

- [@glinkot](https://github.com/glinkot)

- [@kaneda2004](https://github.com/kaneda2004)

- [@KingOfTheCastle](https://github.com/KingOfTheCastle)

- [@linnflux](https://github.com/linnflux)

- [@LittleBallOfPurr](https://github.com/LittleBallOfPurr)

- [@lukasz-pekala](https://github.com/lukasz-pekala)

- [@mohit-twelvelabs](https://github.com/mohit-twelvelabs)

- [@moritz-t-w](https://github.com/moritz-t-w)

- [@MVS-source](https://github.com/MVS-source)

- [@oleksii-honchar](https://github.com/oleksii-honchar)

- [@RheagalFire](https://github.com/RheagalFire)

- [@robertnama](https://github.com/robertnama)

- [@WildGreenRose](https://github.com/WildGreenRose)

- [@yf007](https://github.com/yf007)

- [@Yiiii0](https://github.com/Yiiii0)

## Third-party libraries

Full list of external libraries used in this project is located in the [requirements.txt](https://github.com/szczyglis-dev/py-gpt/blob/master/requirements.txt) file in the main folder of the repository.

All used SVG icons are from `Material Design Icons` provided by Google:

https://github.com/google/material-design-icons

https://fonts.google.com/icons

Monaspace fonts provided by GitHub: https://github.com/githubnext/monaspace

Code of the LlamaIndex offline loaders integrated into app is taken from LlamaHub: https://llamahub.ai

Awesome ChatGPT Prompts (used in templates): https://github.com/f/awesome-chatgpt-prompts/

Code syntax highlight powered by: https://highlightjs.org

Markdown parsing powered by: https://github.com/markdown-it/markdown-it

LaTeX support by: https://katex.org

Playwright: https://playwright.dev/
