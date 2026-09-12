# PyGPT - Desktop AI Assistant

[![pygpt](https://snapcraft.io/pygpt/badge.svg)](https://snapcraft.io/pygpt)

Release: **2.8.16** | build: **2026-09-12** | Python: **>=3.10, <3.14**

> Official website: https://pygpt.net | [Documentation](https://pygpt.readthedocs.io) | [Discord](https://pygpt.net/discord)
> 
> Get it from: [PyPi](https://pypi.org/project/pygpt-net) | [Snap Store](https://snapcraft.io/pygpt) | [Microsoft Store](https://apps.microsoft.com/detail/XP99R4MX3X65VQ) | [AppImage](https://github.com/szczyglis-dev/py-gpt/releases)
> 
> Compiled version for Linux and Windows: [Download](https://pygpt.net/#download) (64bit)
> 
> Donate: [Buy Me A Coffee](https://www.buymeacoffee.com/szczyglis) | [GitHub Sponsors](https://github.com/sponsors/szczyglis-dev) | [PayPal](https://pygpt.net/donate/paypal)

## Overview

**PyGPT** is an **all-in-one desktop AI assistant** supporting models from `OpenAI` (`GPT-6 Astra`, `GPT-5.6`, `GPT-4`, `o1`, `o3`), `Google Gemini`, `Anthropic Claude`, `xAI Grok`, `Perplexity / Sonar`, `DeepSeek`, and models available through `HuggingFace`, `LlamaIndex`, OpenAI-compatible APIs, and local `Ollama` installations such as `Gemma 4`, `Qwen 3.6`, `Llama 4`, `Mistral Small 3.2`, `DeepSeek`, `Bielik`, `Nemotron`, and `gpt-oss`.

It supports chat, **Chat with Agents** and other agent workflows, completions, Chat with Files (via `LlamaIndex`), image and video generation, and image analysis. Models can work with files, run Python and system or custom commands, transfer files, call external APIs, and search the web with `DuckDuckGo`, `Google` and `Microsoft Bing`.

**PyGPT** also provides speech synthesis through `OpenAI`, `Microsoft Azure`, `Google Cloud / GenAI`, `Eleven Labs` and `xAI`, plus speech recognition with `OpenAI Whisper` (API or local), `Google / Google Cloud / GenAI`, `Bing` and `xAI Grok Voice`. It stores conversation history and memory, supports reusable presets, and can be extended with built-in or custom plugins for tools, automation and external integrations.

**Showcase** (mp4, version `2.8.3`, build `2026-08-16`):

https://github.com/user-attachments/assets/22972e34-dc9f-451d-ae64-23a91e945e97

**Screenshots** (version `2.8.4`, build `2026-08-16`):

Dark theme:
![v2_main](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_main.png)

Light theme:
![v2_light](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_light.png)

You can download compiled 64-bit versions for Windows and Linux here: https://pygpt.net/#download

## Features

- Desktop AI Assistant for `Linux`, `Windows` and `Mac`, written in Python.
- Works similarly to `ChatGPT`, but locally (on a desktop computer).
- 11 modes of operation: Chat, Chat with Files, Chat with Agents, Realtime + audio, Research, Completion, Image and Video generation, Experts, Computer use, plus legacy Agent and Autonomous modes.
- Supports multiple models like `OpenAI GPT-6 Astra`, `GPT-5.6`, `GPT-4`, `o1`, `o3`, `o4`, `Google Gemini`, `Anthropic Claude`, `xAI Grok`, `DeepSeek V3/R1`, `Perplexity / Sonar`, and any model accessible through `LlamaIndex` and `Ollama` such as `Gemma 4`, `Qwen 3.6`, `Llama 4`, `Mistral Small 3.2`, `DeepSeek`, `Bielik`, `Nemotron`, `gpt-oss`, etc.
- Chat with your own Files: integrated `LlamaIndex` support: chat with data such as: `txt`, `pdf`, `csv`, `html`, `md`, `docx`, `json`, `epub`, `xlsx`, `xml`, webpages, `Google`, `GitHub`, video/audio, images and other data types, or use conversation history as additional context provided to the model.
- Built-in vector databases support and automated files and data embedding.
- Image generation via models like `gpt-image`, `Imagen`, `Gemini`, and `Nano Banana`.
- Video generation via models like `Veo3` and `Sora2`.
- Internet access via `DuckDuckGo`, `Google` and `Microsoft Bing`.
- Speech synthesis via `OpenAI`, `Microsoft Azure`, `Google Cloud / GenAI`, `Eleven Labs` and `xAI` Text-To-Speech services.
- Speech recognition via `OpenAI Whisper` (API or local), `Google / Google Cloud / GenAI`, `Microsoft Bing` and `xAI Grok Voice`.
- Plugins support with built-in plugins like `Files I/O`, `Code interpreter (v2)`, `Web search`, `Google`, `Facebook`, `X/Twitter`, `Slack`, `Telegram`, `GitHub`, `MCP`, and many more.
- MCP support.
- Camera capture for real-time image analysis in Chat and other supported modes.
- Image analysis via vision models.
- Included support features for individuals with disabilities: customizable keyboard shortcuts, voice control, and translation of on-screen actions into audio via speech synthesis.
- Handles and stores the full context of conversations (short and long-term memory).
- Integrated calendar, day notes and search in contexts by selected date.
- Tools and commands execution (via plugins: access to the local filesystem, Python/OS, system commands execution, and more).
- Custom commands creation and execution.
- Crontab / Task scheduler included.
- Built-in **Python/OS** tool with real-time Python / IPython execution.
- Manages files and attachments with options to upload, download, and organize.
- Context history with the capability to revert to previous contexts (long-term memory).
- Allows you to easily manage prompts with handy editable presets.
- Provides an intuitive operation and interface.
- Includes a notepad.
- Includes simple painter / drawing tool.
- Includes an node-based Agents Builder.
- Includes **Chat with Agents**, an advanced orchestrated multi-agent mode with a user-facing Orchestrator and dynamically managed worker agents.
- Supports multiple languages.
- Requires no previous knowledge of using AI models.
- Fully configurable.
- Themes support.
- Real-time code syntax highlighting.
- Built-in token usage calculation.
- **Open source**; source code is available on `GitHub`.
- Utilizes the user's own API key.
- and many more.

The application is free, open-source, and runs on PCs with `Linux`, `Windows 10`, `Windows 11` and `Mac`. 
Full Python source code is available on `GitHub`.

PyGPT uses your own API credentials to connect to supported AI providers such as OpenAI, Google, Anthropic, xAI, Perplexity, Mistral, OpenRouter, and others. Depending on the selected model and provider, you may need an account and a valid API key for that service. Local models do not require external API credentials.
You can also use built-it LlamaIndex support to connect to other Large Language Models (LLMs), 
such as those on HuggingFace. Additional API keys may be required.

# Installation

## Binaries (Linux, Windows 10 and 11)

You can download compiled binary versions for `Linux` and `Windows` (10/11). 

**PyGPT** binaries require a PC with Windows 10, 11, or Linux. Simply download the installer or the archive with the appropriate version from the download page at https://pygpt.net, extract it, or install it, and then run the application. A binary version for Mac is not available, so you must run PyGPT from PyPi or from the source code on Mac. Currently, only 64-bit binaries are available.

Linux version requires `GLIBC` >= `2.35`.

## Microsoft Store (Windows)

For Windows 10/11, you can install **PyGPT** directly from Microsoft Store:

[![Get it from Microsoft Store](https://get.microsoft.com/images/en-us%20dark.svg)](https://apps.microsoft.com/detail/XP99R4MX3X65VQ)

Link to MS Store: https://apps.microsoft.com/detail/XP99R4MX3X65VQ

## AppImage (Linux)

You can download the latest **PyGPT** `AppImage` for Linux from the release page:

**Releases:** https://github.com/szczyglis-dev/py-gpt/releases

**Tip:** Remember to give execution permissions to the downloaded file:

```chmod +x ./PyGPT-X.X.X-x86_64.AppImage```

To manage future updates you can use `AppImageUpdate` tool:

You can download it from: https://github.com/AppImage/AppImageUpdate/releases

After downloading, run the following command in terminal:

```appimageupdatetool ./PyGPT-X.X.X-x86_64.AppImage```

## Snap Store (Linux)

You can install **PyGPT** directly from Snap Store:

```commandline
sudo snap install pygpt
```

To manage future updates use:

```commandline
sudo snap refresh pygpt
```

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/pygpt)

**Using camera:** to use camera in Snap version you must connect the camera with:

```commandline
sudo snap connect pygpt:camera
```

**Using microphone:** to use microphone in Snap version you must connect the microphone with:

```commandline
sudo snap connect pygpt:audio-record :audio-record
sudo snap connect pygpt:alsa
```

**Using audio output:** to use audio output in Snap version you must connect the audio with:

```commandline
sudo snap connect pygpt:audio-playback
sudo snap connect pygpt:alsa
```

**Connecting IPython in Docker in Snap version**:

To use IPython in the Snap version, you must connect PyGPT to the Docker daemon:

```commandline
sudo snap connect pygpt:docker-executables docker:docker-executables
```

````commandline
sudo snap connect pygpt:docker docker:docker-daemon
````

## PyPi (pip)

The application can also be installed from `PyPi` using `pip install`:

1. Create virtual environment:

```commandline
python3 -m venv venv
source venv/bin/activate
```

2. Install from PyPi:

``` commandline
pip install pygpt-net
```

3. Once installed run the command to start the application:

``` commandline
pygpt
```

## Running from GitHub source code

An alternative method is to download the source code from `GitHub` and execute the application using the Python interpreter (`>=3.10`, `<3.14`). 

### Install with pip

1. Clone git repository or download .zip file:

```commandline
git clone https://github.com/szczyglis-dev/py-gpt.git
cd py-gpt
```

2. Create a new virtual environment:

```commandline
python3 -m venv venv
source venv/bin/activate
```

3. Install requirements:

```commandline
pip install -r requirements.txt
```

4. Run the application:

```commandline
python3 run.py
```

### Install with Poetry

1. Clone git repository or download .zip file:

```commandline
git clone https://github.com/szczyglis-dev/py-gpt.git
cd py-gpt
```

2. Install Poetry (if not installed):

```commandline
pip install poetry
```

3. Create a new virtual environment that uses Python 3.10:

```commandline
poetry env use python3.10
poetry shell
```

or (Poetry >= 2.0):

```commandline
poetry env use python3.10
poetry env activate
```

4. Install requirements:

```commandline
poetry install
```

5. Run the application:

```commandline
poetry run python3 run.py
```

**Tip**: you can use `PyInstaller` to create a compiled version of
the application for your system (required version `6.4.0`).

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

**Access to camera in Snap version:**


```commandline
sudo snap connect pygpt:camera
```

**Access to microphone in Snap version:**

To use microphone in Snap version you must connect the microphone with:

```commandline
sudo snap connect pygpt:audio-record :audio-record
```

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

If you have a problems with `WebEngine / Chromium` renderer you can force the legacy mode by launching the app with command line arguments:

``` ini
python3 run.py --legacy=1
```

and to force disable OpenGL hardware acceleration:

``` ini
python3 run.py --disable-gpu=1
```

You can also manualy enable legacy mode by editing config file - open the `%WORKDIR%/config.json` config file in editor and set the following options:

``` json
"render.engine": "legacy",
"render.open_gl": false,
```

## Other requirements

For operation, an internet connection is needed (for API connectivity), a registered OpenAI account, 
and an active API key that must be input into the program. Local models served through Ollama do not require an OpenAI account or external API keys.

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
- **Anthropic, Google, etc.:** Follow similar steps on their respective platforms.

**Note:** The ability to use models or services depends on your access level with the respective provider. If you wish to use custom API endpoints or local APIs that do not require API keys, simply enter any value into the API key field to bypass prompts about an empty key.

# Work modes

## Chat

**+ Inline vision and image generation**

In **PyGPT**, this mode lets you chat with models such as `GPT-6 Astra`, `GPT-5.6`, `GPT-4`, `o1`, `o3`, `Claude`, `Gemini`, `Grok`, `Perplexity (Sonar)`, `DeepSeek`, and many others. PyGPT can use native SDKs from supported providers, including OpenAI, Google, Anthropic, and xAI, when enabled. It can also connect to providers and local services through OpenAI-compatible APIs, including `Responses API` and `ChatCompletions API` compatible endpoints where supported.

**Tip:** This mode uses the provider SDK directly. If there's no native client built into the app, models like Sonar or local Ollama models such as Qwen 3.6 and Gemma 4 are supported in Chat mode via LlamaIndex or OpenAI-compatible API endpoints. The app automatically switches to these endpoints when using non-OpenAI models. You can enable or disable the use of the native API SDK (per provider) in `Settings -> API Keys`. If the native SDK is disabled, the OpenAI SDK will be used via the compatible ChatCompletions API endpoint.

Currently built-in native clients:

- Anthropic SDK
- OpenAI SDK
- Google GenAI SDK
- xAI SDK

Local `Ollama` models and models from other configured providers are also supported.

The main part of the interface is a chat window where you see your conversations. Below it is a message box for typing. On the right side, you can set up or change the model and system prompt. You can also save these settings as presets to easily switch between models or tasks.

Above where you type your messages, the interface shows you the number of tokens your message will use up as you type it – this helps to keep track of usage. There is also a feature to attach and upload files in this area. Go to the `Files and Attachments` section for more information on how to use attachments.

![v2_mode_chat](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_mode_chat.png)

**Vision:** If you want to analyze photos from disk, screenshots, or camera captures and the currently selected model cannot accept image input, enable the `Vision (inline)` plugin in the Plugins menu. The plugin uses a separately configured image-capable Chat model only for the image-analysis turn. The fallback model can come from any supported provider (for example OpenAI, Google, Anthropic, xAI, OpenRouter, or another OpenAI-compatible provider), as long as the model is configured for Chat and image input.

![v3_vision_plugins](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v3_vision_plugins.png)

With this plugin, you can capture an image with your camera or attach an image and send it for analysis to discuss the photograph:

![v3_vision_chat](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v3_vision_chat.png)

**Image generation:** If you want to generate images directly in chat, enable the `Image generation (inline)` plugin in the Plugins menu. The plugin allows you to generate images in Chat mode.

For supported models/providers, you can alternatively enable the provider-side image-generation remote tool in `Config -> Settings -> Remote Tools`. When available, this lets the model generate images natively without the inline plugin.

![v3_img_chat](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v3_img_chat.png)

##  Chat with Files (LlamaIndex)

This mode enables chat interaction with your documents and entire context history through conversation. 
It seamlessly incorporates `LlamaIndex` into the chat interface, allowing for immediate querying of your indexed documents.

**Tip:** If you do not want to call tools/commands, disable the checkbox `+Tools`. It will speed up the response time when using local models. You can also enable the ReAct agent for tool calls in: `Settings -> Indexes / RAG -> Chat -> Use ReAct agent for Tool calls in Chat with Files mode`. Stream mode is disabled if the ReAct agent and `+Tools` checkbox are active.

**Querying single files**

You can also query individual files "on the fly" using the `query_file` command from the `Files I/O` plugin. This allows you to query any file by simply asking a question about that file. A temporary index will be created in memory for the file being queried, and an answer will be returned from it. A similar command is available for querying web and external content: `Directly query web content with LlamaIndex`.

**For example:**

If you have a file: `data/my_cars.txt` with content `My car is red.`

You can ask for: `Query the file my_cars.txt about what color my car is.`

And you will receive the response: `Red`.

Note: this command indexes the file only for the current query and does not persist it in the database. To store queried files also in the standard index you must enable the option `Auto-index readed files` in plugin settings. Remember to enable `+ Tools` checkbox to allow usage of tools and commands from plugins. 

**Using Chat with Files mode**

In this mode, you are querying the whole index, stored in a vector store database.
To start, you need to index (embed) the files you want to use as additional context.
Embedding transforms your text data into vectors. If you're unfamiliar with embeddings and how they work, check out this article:

https://stackoverflow.blog/2023/11/09/an-intuitive-introduction-to-text-embeddings/

For a visualization from OpenAI's page, see this picture:

![vectors](https://github.com/szczyglis-dev/py-gpt/assets/61396542/4bbb3860-58a0-410d-b5cb-3fbfadf1a367)

Source: https://cdn.openai.com/new-and-improved-embedding-model/draft-20221214a/vectors-3.svg

To index your files, copy or upload them into the active `data` directory and initiate indexing (embedding) by clicking the `Index all` button, or right-click on a file and select `Embed into index`. Normally this is `<profile workdir>/data`; if the current conversation belongs to a project with a custom data workdir, the project directory is used instead. Additionally, you have the option to utilize data from indexed files in any Chat mode by activating the `Chat with Files (RAG, inline)` plugin.

![v2_idx1](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_idx1.png)

After the file(s) are indexed (embedded in vector store), you can use context from them in chat mode:

![v2_idx2](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_idx2.png)

Built-in file loaders: 

**Files:**

- CSV files (csv)
- Epub files (epub)
- Excel .xlsx spreadsheets (xlsx)
- HTML files (html, htm)
- IPYNB Notebook files (ipynb)
- Image (vision) (jpg, jpeg, png, gif, bmp, tiff, webp)
- JSON files (json)
- Markdown files (md)
- PDF documents (pdf)
- Plain-text files (txt)
- Video/audio (mp4, avi, mov, mkv, webm, mp3, mpeg, mpga, m4a, wav)
- Word .docx documents (docx)
- XML files (xml)

**Web/external content:**

- Bitbucket
- ChatGPT Retrieval Plugin
- GitHub Issues
- GitHub Repository
- Google Calendar
- Google Docs
- Google Drive 
- Google Gmail
- Google Keep
- Google Sheets
- Microsoft OneDrive
- RSS
- SQL Database
- Sitemap (XML)
- Twitter/X posts
- Webpages (crawling any webpage content)
- YouTube (transcriptions)

You can configure data loaders in `Settings / Indexes / RAG / Data Loaders` by providing list of keyword arguments for specified loaders.
You can also develop and provide your own custom loader and register it within the application.

LlamaIndex is also integrated with the context database, so conversation history can be indexed and used as additional RAG context. Context indexing is configured separately from file indexing in `Settings -> Indexes / RAG -> Context indexing`.

### File, context, and project indexing

PyGPT separates file indexing from conversation-context indexing:

- **File indexing** indexes files and directories into a selected persistent vector index. Use `Settings -> Indexes / RAG -> File indexing`, the **Index all** action, or `Files -> RMB -> Embed into index`.
- **Context indexing** indexes stored conversation items from the context database. It is configured in `Settings -> Indexes / RAG -> Context indexing`.
- **Project indexes** are isolated runtime indexes associated with projects. They are created and resolved automatically and do not need to be added to the normal configured indexes list.

A project's **data workdir** and its **project index** are separate. The data workdir controls which filesystem directory the Files view and file tools use; the project index controls vector-store data. Changing the project data workdir does not move or rebuild the project index.

The **Conversation auto-indexing** setting has three modes:

- **Off** - disables automatic conversation-context indexing.
- **Auto-index all conversations** - enables automatic context indexing for conversations both inside and outside projects.
- **Auto-index only in projects** - enables automatic context indexing only for conversations assigned to projects.

The **Use isolated index per project** option controls where conversations inside projects are stored. When enabled, each project uses its own isolated index. PyGPT exposes it in the UI as **Current project** and internally resolves it to a project-specific ID such as `proj_<project_id>`. These project indexes are created and updated on demand and are not added to the normal `Indexes` list. When this option is disabled, project conversations use the global auto-indexing index or indexes selected in **Indexes for global auto-indexing**.

The **Enable auto-indexing in modes** setting further limits which work modes may trigger automatic context indexing. Project context indexing is incremental: PyGPT tracks the last indexed conversation item and continues from that point on subsequent updates.

Project-aware indexing is also available outside automatic context indexing:

- In **Chat with Files**, select **Current project** to query the active project's isolated index.
- In the **Files** tab, `RMB -> Embed into index -> Current project` indexes the selected file or directory into the active project.
- The **Chat with Files (RAG, inline)** and **Files I/O** plugins can automatically use the active project index when their **Use project index if in use** option is enabled (default: enabled).
- The project context menu provides **Update project index** and **Truncate project index** actions. Updating continues incrementally; truncating removes the project's index data and resets its indexing state.
- Deleting a project also removes its project index. Duplicating a project rebuilds a corresponding isolated index only when the source project had one.

Removing an entry from `Settings -> Indexes / RAG -> Indexes` removes only the configuration entry; it does **not** delete data already stored in the vector store. Use the **Clear and truncate** tab to permanently remove a selected index or all tracked project indexes.

**WARNING:** remember that when indexing content, API calls to the embedding model are used. Each indexing consumes additional tokens. Always control the number of tokens used on the provider's page.

**Tip:** Using the Chat with Files mode, you have default access to files manually indexed from the active `data` directory. For a project with a custom data workdir this means that project's directory; otherwise it is the shared profile `data` directory. You can also use additional context by attaching a file - such additional context from the attachment does not land in the main index, but only in a temporary one, available only for the given conversation.

**Token limit:** When you use `Chat with Files` in non-query mode, LlamaIndex adds extra context to the system prompt. If you use a plugins (which also adds more instructions to system prompt), you might go over the maximum number of tokens allowed. If you get a warning that says you've used too many tokens, turn off plugins you're not using or turn off the "+ Tools" option to reduce the number of tokens used by the system prompt.

**Available vector stores** (provided by `LlamaIndex`):

```
- ChromaVectorStore
- ElasticsearchStore
- PinecodeVectorStore
- QdrantVectorStore
- RedisVectorStore
- SimpleVectorStore
```

You can configure selected vector store by providing config options like `api_key`, etc. in `Settings -> LlamaIndex` window. See the section: `Configuration / Vector stores` for configuration reference.


**Configuring data loaders**

In the `Settings -> Indexes / RAG -> Data loaders` section you can define the additional keyword arguments to pass into data loader instance. See the section: `Configuration / Data Loaders` for configuration reference.


## Chat with Audio

This mode works like the Chat mode but with native support for audio input and output using a Realtime and Live APIs. In this mode, audio input and output are directed to and from the model directly, without the use of external plugins. This enables faster and better audio communication.

Currently, in beta. 

At this moment, only OpenAI real-time models (via the Realtime API) and Google Gemini real-time models (via the Live API) are supported.

## Research

**Research** is a provider-aware mode for models designed for web research and deep-research workflows. Depending on the selected model and provider, PyGPT can use Perplexity Sonar research models as well as other provider-specific research paths, including Google Deep Research through the **Interactions API**.

Configure the API key for the provider you want to use in `Config -> Settings -> API Keys`. For Perplexity models, see https://perplexity.ai.

**Google Remote MCP:** Google Remote MCP can be enabled in `Config -> Settings -> Remote Tools -> Google`. In the current PyGPT implementation it is available in **Research** mode through Google's Interactions API / Deep Research path. Configure MCP servers in **Remote MCP configuration** as a JSON object or list. Google currently supports Streamable HTTP MCP servers on this path; SSE servers are not supported.

## Completion

An older mode of operation that allows working in the standard text completion mode. However, it allows for a bit more flexibility with the text by enabling you to initiate the entire discussion in any way you like.

Similar to chat mode, on the right-hand side of the interface, there are convenient presets. These allow you to fine-tune instructions and swiftly transition between varied configurations and pre-made prompt templates.

Additionally, this mode offers options for labeling the AI and the user, making it possible to simulate dialogues between specific characters - for example, you could create a conversation between Batman and the Joker, as predefined in the prompt. This feature presents a range of creative possibilities for setting up different conversational scenarios in an engaging and exploratory manner.


## Image and video generation

**PyGPT** enables quick and easy image creation with image-generation models such as `gpt-image`, `Imagen`, `Gemini`, `Nano Banana`, and `Grok`, as well as video generation using models such as `Veo` and `Sora`.
Generating images and videos is akin to a chat conversation  -  a user's prompt triggers the generation, followed by downloading, saving to the computer, and displaying the image onscreen. You can send raw prompt to the model in `Image generation` mode or ask the model for the best prompt.

![v3_img](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v3_img.png)

Image generation using image models is also available in every mode via plugin `Image generation (inline)`. Just ask any model, in any mode, like e.g. GPT or Gemini to generate an image and it will do it inline, without need to mode change.

If you want to generate images directly in chat you must enable plugin **Image generation (inline)** in the Plugins menu.
Plugin allows you to generate images in Chat mode:

![v3_img_chat](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v3_img_chat.png)

For supported models/providers, you can also enable remote image generation in `Config -> Settings -> Remote Tools`. If enabled, image generation is available natively in supported work modes without the inline plugin.

To use `Imagen` models you must enable `Use Vertex AI` in `Config -> Settings -> API Keys -> Google -> Advanced options`.

### Remix, Edit, or Extend

To remix or extend from a previous image or video instead of creating a new one from scratch, enable the `Remix/Extend` option checkbox in the toolbox. The last generated image or video in the current context will be used as a reference for your prompt, allowing you to request changes to the generated content. If the `Remix/Extend` option is enabled, uploading an image attachment as a reference will not take effect.

### Raw mode

There is an option for switching prompt generation mode.

If **Raw Mode** is enabled, a model will receive the prompt exactly as you have provided it.
If **Raw Mode** is disabled, a model will generate the best prompt for you based on your instructions.

### Image storage

Once you've generated an image, you can easily save it anywhere on your disk by right-clicking on it. 
You also have the options to delete it or view it in full size in your web browser.

**Tip:** Use presets to save your prepared prompts. 
This lets you quickly use them again for generating new images later on.

The app keeps a history of all your prompts, allowing you to revisit any session and reuse previous 
prompts for creating new images.

Images are stored in the base-profile `img` directory by default. If **Store images, captures, and uploads in the workdir data directory** is enabled, generated images are stored under the active `data` workdir instead, including a custom project data workdir when one is active.


## Chat with Agents

**Chat with Agents** is PyGPT's multi-agent work mode for tasks that benefit from delegation, parallel execution, tool use, verification, and specialist workers. It uses a dedicated runtime built on LlamaIndex agent workflows and is separate from the older `Agent (LlamaIndex)`, `Agent (OpenAI)`, and `Agent (Autonomous)` modes.

The **Mode** selector below the system prompt lets you choose how the agent workflow operates. The default is **Chat**.

### Agent modes

- **Chat** - the default mode. A primary agent talks directly with the user, uses available tools, and can delegate selected tasks to background workers when useful. This is the best general-purpose option when you want a normal agent conversation with multi-agent assistance available on demand.
- **Orchestrator** - a dedicated orchestrator manages specialist workers in the background. It can create workers, assign or update their roles, run or reuse them, inspect their state, wait for results, stop them, and combine their work into the final response. Independent workers can run concurrently. This mode is useful for structured, multi-stage tasks where explicit coordination and verification are important. The Orchestrator runtime supports up to `16` workers.
- **Swarm** - the orchestrator launches a swarm containing the number of workers requested by the user. If the number of agents is not specified in the request, the orchestrator asks how many should be launched before starting the swarm. Workers are numbered and prefixed in status output, the orchestrator reports the swarm size when it starts, and it periodically provides an aggregated status showing how many agents are running and what they are doing. **Swarm does not impose a worker-count limit.**

> **Warning:** Use **Swarm** with care. This mode has no built-in limit on the number of agents that can be created. Requesting a large swarm can cause unexpectedly high API usage, token consumption, resource usage, many concurrent tool operations, and other unexpected effects. Start with a reasonable number of agents and supervise workflows that can modify files, execute code or system commands, or perform external actions.

### Tools and provider capabilities

Chat with Agents can use both local and provider-side capabilities:

- **Local tools** from enabled PyGPT plugins can be made available to the primary agent/orchestrator and workers.
- **Remote tools** exposed by the selected provider can be made available when supported by the provider/model and enabled in PyGPT.
- Local and remote tools can be enabled or disabled independently in the Chat with Agents preset with **Allow local tools** and **Allow remote tools**.
- Models with native function calling use it when available; the runtime can fall back to a ReAct agent for compatible models without native function calling.

Local plugin execution is integrated with the normal PyGPT command/tool system, so enabled plugins can provide filesystem access, Code interpreter (v2), system commands, web search, custom commands, integrations, and other capabilities according to their own configuration and security restrictions.

### Settings

Agent-related application settings are organized under `Settings -> Agents and experts`. The **Chat with Agents** section contains settings for this workflow. **Show full tool-chain in Chat with Agents** is disabled by default; when enabled, the final response stores and displays the complete chain of normal tool calls executed during the workflow, with a separate expandable Request/Response pair for each call. Internal orchestration and worker-management calls are not included.

The same section also exposes the iteration limits used by the Chat with Agents runtime:

- **Max iterations (Chat / Orchestrator)** - maximum number of main-agent iterations in Chat and Orchestrator modes. Default: `48`.
- **Max iterations (Swarm)** - maximum number of main-agent/orchestrator iterations in Swarm mode. Default: `4096`.
- **Worker max iterations** - maximum number of iterations for each worker agent, regardless of the selected Chat with Agents mode. Default: `24`.

For all three options, `0` means **unlimited**. These are agent execution iterations (reasoning/tool-call cycles), not user conversation turns. Raising or removing these limits can substantially increase API usage, token consumption, execution time, and the number of tool operations. In **Swarm**, an unlimited iteration setting can combine with the absence of a worker-count limit, so use it particularly carefully.

Settings kept only for older agent implementations are separated into the **Legacy** tab. **Display full agent output in chat view** controls rendering of full output from legacy agent modes, while **Display a tray notification when the goal is achieved** controls legacy agent completion notifications. These Legacy options do not control the Chat with Agents tool-chain display.

### RAG, attachments and artifacts

If a valid index is selected in the preset, Chat with Agents exposes it as a RAG query tool. User attachments and extracted attachment context are shared with the workflow, and image attachments are also passed as native image input when the selected model supports images. Files, images, URLs and attachments produced by workers or provider-side tools are collected by the runtime and propagated to the main response.

### Memory and worker lifecycle

The user-facing primary agent or orchestrator keeps hidden conversation memory across turns in the current conversation/preset, subject to the normal PyGPT token-window limits. Worker memory is runtime-local and can be retained when the same worker is reused during a workflow.

The worker-management model depends on the selected mode:

- **Chat** delegates individual tasks to workers through the primary agent, without exposing the full orchestration lifecycle as the main interaction pattern.
- **Orchestrator** uses explicit worker-management operations to create, update, run, inspect, wait for, stop, and remove workers, and finalizes the workflow only after required worker activity has been resolved.
- **Swarm** extends the orchestrator flow with swarm initialization and aggregate swarm status. It tracks the requested number of workers, numbers them for status output, and reports collective progress while they are running.

### Recommended use cases

Use **Chat** for general agent conversations and tasks where delegation is occasional. Use **Orchestrator** for controlled multi-step work such as coding, file operations, research with independent verification, RAG-assisted analysis, implementation plus testing, or workflows combining several tools. Use **Swarm** when a task genuinely benefits from many parallel, independent workers and you intentionally want to control the swarm size yourself.

## Experts

**Experts** lets you define reusable, specialized agents as presets and delegate tasks to them from a normal conversation. Experts are powered by regular agents from the same **Agents v2 runtime** that powers **Chat with Agents**. There is no separate legacy execution engine for an Expert.

Each enabled Expert is exposed to the current conversation as a regular `expert_call` tool. The main model can call it in exactly the same way as other tools: it selects an Expert, passes an instruction, waits for the agent to complete the task, and receives the Expert's final response directly as the tool result. The Expert response is not inserted back into the conversation as a synthetic user message or an `@expert says...` entry.

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

##  Computer use

This mode allows for autonomous computer control.

In this mode, the model takes control of the mouse and keyboard and can navigate within the user's environment. PyGPT uses the selected provider's native `Computer use` capability when supported by the current model (OpenAI, Google, or Anthropic), combined with the built-in `Mouse and keyboard` integration.

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


## Agent (LlamaIndex)

**Legacy mode — not recommended. Use the newer and more advanced `Chat with Agents` mode instead.**

This mode provides the older LlamaIndex-based agent workflows.

Includes built-in agents (Workflow):

- FunctionAgent
- ReAct
- Structured Planner (sub-tasks)
- CodeAct (connected to Code interpreter (v2) plugin)
- Supervisor + worker


You can create your own types (workflows/patterns) using the built-in visual node-based editor found in the `Tools -> Agents Builder`.

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

You can change the prompts used for evaluating the response in `Settings -> Prompts -> Agent: evaluation prompt in loop`. Here, you can adjust it to suit your needs, for example, by defining more or less critical feedback for the responses received.

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

You can create your own types (workflows/patterns) using the built-in visual node-based editor found in the `Tools -> Agents Builder`.

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

## Agent (Autonomous)

**Legacy mode — not recommended. Use the newer and more advanced `Chat with Agents` mode instead.**

`Agent (Autonomous)` is a legacy loop-based workflow that repeatedly runs a selected underlying mode and feeds the result into the next iteration. It is intended for unattended multi-step execution where the model can continue working toward a goal without requiring a new user message after every step.

Unlike `Chat with Agents`, this mode does not use the modern primary-agent/delegated-worker orchestration runtime. It is kept mainly for compatibility with older presets and workflows. Enabled plugins and tools remain available according to the capabilities of the selected underlying mode.

**WARNING:** Autonomous execution can perform repeated tool calls and external actions. Review the enabled plugins before starting a run, especially when file access, system commands, web actions, or other side effects are available.

The run can be limited to a fixed number of iterations. Setting the number of iterations to `0` enables an unlimited loop and can cause very high API usage, token consumption, and repeated tool operations.

When `Auto-stop` is enabled, the workflow attempts to stop after the goal has been reached. When `Always continue...` is enabled, PyGPT sends the continuation prompt and starts another iteration even if the previous result appears complete.

**Options**

The autonomous workflow is a virtual mode that executes another PyGPT mode internally. Select the underlying mode in:

```ini
Settings -> Agents and experts -> Autonomous -> Sub-mode for agents
```

The default sub-mode is `Chat`. If the selected sub-mode uses LlamaIndex/RAG, you can also choose the index in:

```ini
Settings -> Agents and experts -> Autonomous -> Index to use
```


# Context and memory

## Short and long-term memory

**PyGPT** features a continuous chat mode that maintains a long context of the ongoing dialogue. It preserves the entire conversation history and automatically appends it to each new message (prompt) you send to the AI. Additionally, you have the flexibility to revisit past conversations whenever you choose. The application keeps a record of your chat history, allowing you to resume discussions from the exact point you stopped.

## Handling multiple contexts

On the left side of the application interface, there is a panel that displays a list of saved conversations. You can save numerous contexts and switch between them with ease. This feature allows you to revisit and continue from any point in a previous conversation. **PyGPT** automatically generates a summary for each context, akin to the way `ChatGPT` operates and gives you the option to modify these titles itself.

You can disable context support in the settings by using the following option:

``` ini
Config -> Settings -> Use context 
```

## Projects and project data workdirs

Conversations can be organized into projects. By default, projects use the shared profile `data` directory. When creating a project, leave **Use shared workdir** enabled to keep this behavior, or disable it and select a custom directory for that project. For an existing project, use `RMB -> Edit` to change its name or data workdir. Hovering a project item in the context list shows the effective data workdir.

A project workdir overrides **only the logical `data` directory** used by conversations in that project. It does not replace the profile/application workdir. Files such as `config.json`, `models.json`, `db.sqlite`, logs and other profile-level directories such as `tmp`, `cache`, `css`, `locale` and fonts continue to use the base profile workdir. Conversations outside projects, and projects with **Use shared workdir** enabled, use the normal `<profile workdir>/data` directory.

The project data directory is resolved at runtime. The **Files** tab, **Files I/O**, **Code interpreter (v2)**, filesystem-aware tools and Docker sandboxes use the data root that belongs to the current conversation. In Docker, the active host data directory is exposed as `/data`. The internal `tmp` directory always remains in the base profile workdir. `img`, `capture` and `upload` follow a custom project data workdir only when **Store images, captures, and uploads in the workdir data directory** is enabled; otherwise they remain in their normal base-profile locations.

## Clearing history

You can clear the entire memory (all contexts) by selecting the menu option:

``` ini
File -> Clear history...
```

## Context storage

On the application side, the context is stored in the `SQLite` database located in the base profile/application workdir (`db.sqlite`). A project data-workdir override does not move this database.

Once a conversation begins, a title for the chat is generated and displayed on the list to the left. This process is similar to `ChatGPT`, where the subject of the conversation is summarized, and a title for the thread is created based on that summary. You can change the name of the thread at any time.

# Files And Attachments

## Uploading attachments

**Using Your Own Files as Additional Context in Conversations**

You can use your own files (for example, to analyze them) during any conversation. You can do this in two ways: by indexing (embedding) your files in a vector database, which makes them available all the time during a "Chat with Files" session, or by adding a file attachment (the attachment file will only be available during the conversation in which it was uploaded).

**Attachments**

**PyGPT** makes it simple for users to upload files and send them to the model for tasks like analysis, similar to attaching files in `ChatGPT`. There's a separate `Attachments` tab next to the text input area specifically for managing file uploads. 

**Tip:** Project-wide attachment sharing is optional. Enable `Settings -> Files and attachments -> Make attachments available in the whole project` to make attachments added in one chat available to all chats in the same project. The option is disabled by default; when disabled, attachments remain available only in the chat where they were added.

![v2_file_input](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_file_input.png)

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

In the `RAG` and `Summary` mode, you can enable an additional setting by going to `Settings -> Files and attachments -> Use history in RAG query`. This allows for better preparation of queries for RAG. When this option is turned on, the entire conversation context is considered, rather than just the user's last query. This allows for better searching of the index for additional context. In the `RAG limit` option, you can set a limit on how many recent entries in a discussion should be considered (`0 = no limit, default: 3`).

**Important**: When using `Full context` mode, the entire content of the file is included in the prompt, which can result in high token usage each time. If you want to reduce the number of tokens used, instead use the `RAG` option, which will only query the indexed attachment in the vector database to provide additional context.

**Images as Additional Context**

Files such as jpg, png, and similar images are a special case. By default, images are not used as additional context; they are analyzed in real-time using a vision model. If you want to use them as additional context instead, you must enable the "Allow images as additional context" option in the settings: `Files and attachments -> Allow images as additional context`.

**Uploading larger files and auto-index**

To use the `RAG` mode, the file must be indexed in the vector database. This occurs automatically at the time of upload if the `Auto-index on upload` option in the `Attachments` tab is enabled. When uploading large files, such indexing might take a while - therefore, if you are using the `Full context` option, which does not use the index, you can disable the `Auto-index` option to speed up the upload of the attachment. In this case, it will only be indexed when the `RAG` option is called for the first time, and until then, attachment will be available in the form of `Full context` and `Summary`.

**Embeddings**

When using RAG to query attachments, the documents are indexed into a temporary vector store. With multiple providers and models available, you can select the model used for querying attachments in: `Config -> Settings -> Files and Attachments`. You can also choose the embedding models for specified providers in `Config -> Settings -> Indexes / RAG -> Embeddings -> Default embedding providers for attachments` list. By default, when querying an attachment using RAG, the default embedding model and provider corresponding to the RAG query model will be used. If no default configuration is provided for a specific provider, the global embedding configuration will be used.

For example, if the RAG query model is `gpt-4o-mini`, then the default model for the provider `OpenAI` will be used. If the default model for `OpenAI` is not specified on the list, the global provider and model will be used.

## Downloading files

**PyGPT** automatically downloads and saves files created by the model in the active `data` workdir. Outside projects, and in projects that use the shared workdir, this is the normal `<profile workdir>/data` directory. A project can instead define its own data workdir; when a conversation from that project is active, the **Files** tab displays that directory and file-producing tools use it automatically.

The active `data` directory is also where the application stores files generated locally by the AI, such as code files and other model outputs. You can execute code from these files, read them back into the conversation, and index them with LlamaIndex. The project override applies only to this logical data root; it does not move profile-level paths such as `tmp`, configuration files, the database or other application directories.

The `Files I/O` and `Code interpreter (v2)` plugins use the same runtime-resolved data workdir as the active conversation. In Docker sandboxes this directory is mounted as `/data`. If **Store images, captures, and uploads in the workdir data directory** is enabled, `img`, `capture` and `upload` storage follows the active data workdir as well. When the option is disabled, those directories remain in their normal base-profile locations. `tmp` always remains in the base profile workdir.

![v2_file_output](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_file_input.png)

To allow the model to manage files or python code execution, the `+ Tools` option must be active, along with the above-mentioned plugins:

![v2_code_execute](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_code_execute.png)

# Presets

## What is preset?

Presets in **PyGPT** are essentially templates used to store and quickly apply different configurations. Each preset includes settings for the mode you want to use (such as chat, completion, or image generation), an initial system prompt, an assigned name for the AI, a username for the session, and the desired "temperature" for the conversation. A warmer "temperature" setting allows the AI to provide more creative responses, while a cooler setting encourages more predictable replies. These presets can be used across various modes and with models accessed via the `OpenAI API` or `LlamaIndex`.

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
- `deep-research-max-preview-04-2026` (Google)
- `deep-research-preview-04-2026` (Google)
- `deep-research-pro-preview-12-2025` (Google)
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
- `gpt-5.3-codex (high)` (OpenAI)
- `gpt-5.3-codex (low)` (OpenAI)
- `gpt-5.3-codex (medium)` (OpenAI)
- `gpt-5.3-codex (xhigh)` (OpenAI)
- `gpt-5.6-luna (high)` (OpenAI)
- `gpt-5.6-luna (low)` (OpenAI)
- `gpt-5.6-luna (medium)` (OpenAI)
- `gpt-5.6-sol (high)` (OpenAI)
- `gpt-5.6-sol (low)` (OpenAI)
- `gpt-5.6-sol (medium)` (OpenAI)
- `gpt-5.6-terra (high)` (OpenAI)
- `gpt-5.6-terra (low)` (OpenAI)
- `gpt-5.6-terra (medium)` (OpenAI)
- `gpt-6-astra (high)` (OpenAI)
- `gpt-6-astra (low)` (OpenAI)
- `gpt-6-astra (medium)` (OpenAI)
- `gpt-image-1` (OpenAI)
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
- `o3-mini (high)` (OpenAI)
- `o3-mini (low)` (OpenAI)
- `o3-mini (medium)` (OpenAI)
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
This file is located in the base profile/application workdir and is not affected by a project data-workdir override. You can add new models provided directly by `OpenAI API` (or compatible), `Google Gen AI API`, `Anthropic API`, `xAI API`, and those supported by `LlamaIndex` or `Ollama` to this file. Configuration for LlamaIndex in placed in `llama_index` key.

You can import new models by manually editing `models.json` or by using the model importer in the `Config -> Models -> Import` menu.

**Tip:** The models on the list are sorted by provider, not by manufacturer. A model from a particular manufacturer may be available through different providers (e.g., OpenAI models can be provided by the `OpenAI API` or by `OpenRouter`). If you want to use a specific model through a particular provider, you need to configure the provider in `Config -> Models -> Edit`, or import it directly via `Config -> Models -> Import`.

**Tip**: Anthropic and Deepseek API providers use VoyageAI for embeddings (Chat with Files and attachments RAG), so you must also configure the Voyage API key if you want to use embeddings from these providers.

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

You can add OpenAI Chat Completions-compatible providers at runtime without editing PyGPT source code or creating a custom launcher. Open:

`Config -> Settings -> Custom providers`

and add a row with:

- **Provider name** - the name shown in provider selectors.
- **API base URL** - the OpenAI-compatible API base, for example `https://example.com/v1`.
- **API key** - the provider API key. It may be left empty when the endpoint does not require authentication.

Custom providers are stored in `config.json` under the `api_custom_providers` key. After saving Settings, they are registered immediately and become available anywhere PyGPT uses the LLM provider registry, including the Models Editor and `Config -> Models -> Import`. The importer obtains the model list from the provider's OpenAI-compatible `/models` endpoint.

Models assigned to a custom provider use the native OpenAI Python SDK with the **Chat Completions API** in normal Chat mode. In **Chat with Files (LlamaIndex)** and LlamaIndex-based flows, PyGPT uses the LlamaIndex `OpenAILike` wrapper with the same API base URL and API key. Custom runtime providers intentionally use Chat Completions compatibility; they do not enable the OpenAI Responses API.

Once the provider is saved, import its models from `Config -> Models -> Import`, or create/edit a model manually and select the custom provider from the provider list. Model-specific `API base` / `API key` values in the Models Editor, when provided, override the custom provider values for that model.

## How to use local or other models

### Gemma 4, Qwen 3.6, Llama 4, Mistral, DeepSeek, Bielik, gpt-oss, and other local models

How to use locally installed Gemma 4, Qwen 3.6, Llama 4, DeepSeek, Mistral, Bielik, and other models:

1) Choose a working mode: `Chat` or `Chat with Files`.

2) On the models list - select, edit, or add a new model (with `ollama` provider). You can edit the model settings through the menu `Config -> Models -> Edit`, then configure the model parameters in the `advanced` section.

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

You can also change the "base_url" for a specific model in its configuration:

`Config -> Models -> Edit`, then in the `Advanced -> [LlamaIndex] ENV Vars` section add the variable:

NAME: `OLLAMA_API_BASE`
VALUE: `http://my_endpoint.com:11434`


**List of all models supported by Ollama**

https://ollama.com/library

https://github.com/ollama/ollama

**IMPORTANT:** Remember to define the correct model name in the **kwargs list in the model settings.

**Using local embeddings**

Refer to: https://docs.llamaindex.ai/en/stable/examples/embeddings/ollama_embedding/

You can use an Ollama instance for embeddings. Simply select the `ollama` provider in:

```Config -> Settings -> Indexes / RAG -> Embeddings -> Embeddings provider```

Define parameters like model name and Ollama base URL in the Embeddings provider **kwargs list, e.g.:

- name: `model_name`, value: `gemma4:e4b`, type: `str`

- name: `base_url`, value: `http://localhost:11434`, type: `str`

### Other providers and LlamaIndex-based modes

PyGPT can route the same model differently depending on the selected work mode and provider integration. In normal `Chat`, built-in providers can use their native SDKs when enabled, while local or third-party services can use OpenAI-compatible endpoints. `Chat with Files` and other non-Chat workflows that rely on LlamaIndex use the model's configured LlamaIndex provider/wrapper; provider-specific agent runtimes can use their own integration path.

For built-in providers, configure credentials in `Config -> Settings -> API Keys`. In most cases, LlamaIndex wrappers automatically reuse the corresponding provider key, so you do not need to duplicate credentials in model-specific environment variables. The model configuration normally only needs the correct provider and model name.

Use the model's `Advanced` fields only when you need provider-specific overrides, a custom endpoint, or additional LlamaIndex arguments. For `Local models (OpenAI API compatible)`, prefer the per-model `API base` and `API key` fields. Advanced LlamaIndex `**kwargs` and `ENV` values remain available for backend-specific options such as `context_window`, `is_chat_model`, or custom integration parameters.

Examples of built-in provider credential reuse include Google, Anthropic, xAI, Mistral AI, Perplexity, and HuggingFace. DeepSeek and Anthropic use the configured VoyageAI key for their default embeddings integration.

# Plugins

## Overview

**PyGPT** can be enhanced with plugins that add tools, integrations, automation, multimodal features, and additional context directly to conversations.

The following plugins are currently available:

- `API calls` - connects models to external services through user-defined API endpoints, request methods, parameters, and payloads.

- `Audio input` - adds speech recognition and microphone input using providers such as OpenAI Whisper, local Whisper, Google, Bing, and xAI Grok Voice.

- `Audio output` - adds text-to-speech output using providers such as OpenAI, Microsoft Azure, Google, Eleven Labs, and xAI.

- `Autonomous mode` - runs an autonomous multi-step conversation loop inside standard chat modes and can cooperate with other enabled plugins to complete tasks.

- `Bitbucket` - connects to Bitbucket Cloud for repository, file, issue, pull request, workspace, and account operations.

- `Chat with Files (RAG, inline)` - adds RAG and LlamaIndex retrieval to standard conversations, allowing models to use indexed files, project indexes, and stored context as additional knowledge.

- `Code interpreter (v2)` - lets models execute Python code locally or in a Docker sandbox, maintain IPython state, and work with files created during the conversation.

- `Context history (calendar, inline)` - gives models access to saved conversation history and calendar day notes, including reading, searching, creating, and updating stored entries.

- `Crontab / Task scheduler` - lets models create and manage scheduled prompts and tasks using cron-based schedules.

- `Custom commands` - exposes user-defined system commands and scripts as callable tools with configurable arguments and execution rules.

- `Experts (inline)` - exposes enabled Expert presets through the regular `expert_call` tool in supported chat modes; Experts run as regular agents on the same Agents v2 runtime used by Chat with Agents.

- `Facebook` - connects to the Facebook Graph API for working with pages, posts, photos, and related account information.

- `Files I/O` - gives models controlled access to local files and directories for reading, writing, copying, moving, downloading, searching, and indexing data.

- `GitHub` - connects to GitHub for repository, file, issue, pull request, code search, and account operations.

- `Google` - integrates Gmail, Drive, Calendar, Contacts, Keep, Docs, Maps, Colab, and YouTube so models can work with Google services from conversations.

- `Image generation (inline)` - adds image generation and editing directly to conversations using a separately configured image model without requiring a mode change.

- `Mailer` - provides email access through configured mail services, including sending and reading messages where supported.

- `Memory (inline)` - maintains compact database-backed long-term memory plus raw keyed memory, using a global scope outside projects and an isolated memory scope for each project.

- `MCP` - connects models to external Model Context Protocol servers and exposes discovered remote tools through stdio, SSE, or Streamable HTTP transports.

- `Mouse and keyboard` - lets models control the mouse and keyboard, capture screenshots, and interact with the desktop or supported sandbox environment.

- `OpenStreetMap` - adds geocoding, place search, routing, and map utilities based on OpenStreetMap services.

- `Real time` - appends the current date and/or time to system prompts so models can receive up-to-date local time context.

- `Serial port / USB` - gives models access to configured serial and USB devices for reading data and sending commands.

- `Server (SSH/FTP)` - connects to remote servers through SSH, SFTP, or FTP for command execution, file transfers, and filesystem operations.

- `Slack` - connects to Slack workspaces for reading conversations, managing messages, working with users, and transferring files.

- `Extra system prompt` - automatically appends reusable custom instructions or additional context to the active system prompt.

- `System (OS)` - provides access to the operating system and executes system commands through PyGPT's host or sandbox execution mechanisms.

- `Telegram` - connects to Telegram bots or user accounts for messaging, chat access, contacts, media, and file transfers.

- `Tuya (IoT)` - connects to Tuya Cloud so models can inspect, search, and control supported smart-home and IoT devices.

- `TwelveLabs` - adds video understanding and multimodal embeddings using TwelveLabs Pegasus and Marengo models.

- `Vision (inline)` - adds image analysis to supported chat modes by routing image input through a separately configured vision-capable model.

- `Voice control (inline)` - lets spoken commands trigger configured PyGPT actions directly while a conversation is active.

- `Web search` - adds real-time web search, webpage retrieval, crawling, and external-content indexing using supported search providers and LlamaIndex loaders.

- `Wikipedia` - provides Wikipedia search, article lookup, summaries, geographic discovery, and random-page access.

- `Wolfram Alpha` - adds computational knowledge, symbolic and numeric mathematics, unit conversions, matrix operations, and generated plots through Wolfram Alpha.

- `X/Twitter` - connects to X for searching and reading posts, publishing content, managing interactions, bookmarks, and media.

**Tip:** Inline plugins do not require the `+ Tools` option in the toolbox. Once enabled, they remain active throughout the conversation and can provide their functionality automatically when applicable.

## API calls

**PyGPT** lets you connect the model to the external services using custom defined API calls.

To activate this feature, turn on the `API calls` plugin found in the `Plugins` menu.

In this plugin you can provide list of allowed API calls, their parameters and request types. The model will replace provided placeholders with required params and make API call to external service.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#api-calls

## Audio input

The plugin facilitates speech recognition. OpenAI Whisper is the default provider; local Whisper, Google, Google Cloud, Google GenAI, Bing, and xAI Grok Voice providers are also available. It allows for voice commands to be relayed to the AI using your own voice. Whisper doesn't require any extra API keys or additional configurations; it uses the main OpenAI key. In the plugin's configuration options, you should adjust the volume level (min energy) at which the plugin will respond to your microphone. Once the plugin is activated, a new `Speak` option will appear at the bottom near the `Send` button  -  when this is enabled, the application will respond to the voice received from the microphone.

The plugin can be extended with other speech recognition providers.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#audio-input

## Audio output

The plugin lets you turn text into speech using OpenAI TTS or providers such as `Microsoft Azure`, `Google Cloud TTS`, `Google GenAI TTS`, `Eleven Labs`, and `xAI TTS`. You can add more text-to-speech providers to it too. `OpenAI TTS` does not require any additional API keys or extra configuration; it utilizes the main OpenAI key. 
Provider-specific credentials are required where applicable: Azure and Eleven Labs use plugin credentials, Google GenAI uses the Google API key from Settings, and xAI TTS uses the xAI API key from Settings. Configure voices, regions, and provider-specific options in the plugin settings.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#audio-output

## Autonomous mode

**WARNING: Please use autonomous mode with caution!** - this mode, when connected with other plugins, may produce unexpected results!

The plugin activates autonomous mode in standard chat modes, where AI begins a conversation with itself. 
You can set this loop to run for any number of iterations. The plugin also has an **Always continue** option (default: disabled) that forces another iteration even when the goal has already been reached. Throughout this sequence, the model will engage
in self-dialogue, answering his own questions and comments, in order to find the best possible solution, subjecting previously generated steps to criticism.

This mode is similar to `Auto-GPT` - it can be used to create more advanced inferences and to solve problems by breaking them down into subtasks that the model will autonomously perform one after another until the goal is achieved. The plugin is capable of working in cooperation with other plugins, thus it can utilize tools such as web search, access to the file system, or image generation.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#autonomous-mode

## Bitbucket

The Bitbucket plugin allows for seamless integration with the Bitbucket Cloud API, offering functionalities to manage repositories, issues, and pull requests. This plugin provides highly configurable options for authentication, cached convenience, and manages HTTP requests efficiently.

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

## Chat with Files (RAG, inline)

Plugin integrates `LlamaIndex` storage in any chat and provides additional knowledge into context. The plugin also provides the `Image model` setting used by the Image (vision) data loader when API mode is active (default: `gpt-4o`). Audio/video transcription is not configured here; it uses the provider selected in the `Audio input` plugin.

When **Use project index if in use** is enabled (default), the plugin automatically queries the isolated **Current project** index whenever the active conversation belongs to a project. Outside a project it uses the configured regular index or indexes.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#chat-with-files-rag-inline

## Code interpreter (v2)

### Executing Code

The plugin operates similarly to the `Code Interpreter` feature in `ChatGPT`, with the key difference that it works locally on the user's system. It allows for the execution of any Python code on the computer that the model may generate. When combined with the `Files I/O` plugin, it facilitates running code from files saved in the active `data` directory. For conversations in a project with a custom workdir, the project directory becomes the runtime data root; otherwise the shared `<profile workdir>/data` directory is used. Docker execution exposes the same active host directory as `/data`.

**IPython:** IPython is the recommended execution mode and offers significant improvements over the legacy Python workflow. IPython provides a robust environment for executing code within a kernel, allowing you to maintain the state of your session by preserving the results of previous commands. This feature is particularly useful for iterative development and data analysis, as it enables you to build upon prior computations without starting from scratch. Moreover, IPython supports the use of magic commands, such as `!pip install <package_name>`, which facilitate the installation of new packages directly within the session. This capability streamlines the process of managing dependencies and enhances the flexibility of your development environment. Overall, IPython offers a more efficient and user-friendly experience for executing and managing code.

To use IPython in sandbox mode, Docker must be installed on your system. The active conversation's runtime `data` workdir is mounted as `/data`; a custom project data workdir is therefore remapped automatically when that project is active.

You can find the installation instructions here: https://docs.docker.com/engine/install/

**Tip: connecting IPython in Docker in Snap version**:

To use IPython in the Snap version, you must connect PyGPT to the Docker daemon:

```commandline
sudo snap connect pygpt:docker-executables docker:docker-executables
```

````commandline
sudo snap connect pygpt:docker docker:docker-daemon
````

**Code interpreter:** PyGPT includes the **Python/OS** tool for real-time Python and IPython execution. Click the `<>` icon to open the Python/OS window. Plugin code input/output is mirrored there only when **Connect to the Python/OS window** is enabled (default: enabled). The window keeps 30 input/output blocks by default (`0` = unlimited), and **Always run code in a fresh kernel** is disabled by default.

![v2_python](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_python.png)

**Python/IPython environment:** Local IPython execution requires a working Python environment on the host system. If local execution fails because of Python, package, kernel, or environment issues, enable the Docker sandbox in the `Code interpreter (v2)` plugin settings. Docker provides an isolated and reproducible runtime and is the recommended fallback for problematic host environments.

Docker installation: [Docker Engine](https://docs.docker.com/engine/install/) | [Docker Desktop](https://docs.docker.com/desktop/)


**Tip:** always remember to enable the `+ Tools` option to allow execute commands from the plugins.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#code-interpreter-v2

## Context history (calendar, inline)

Provides access to context history database.
Plugin also provides access to reading and creating day notes.

Examples of use, you can ask e.g. for the following:

```Give me today day note```

```Save a new note for today```

```Update my today note with...```

```Get the list of yesterday conversations```

```Get contents of conversation ID 123```

etc.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#context-history-calendar-inline

## Crontab / Task scheduler

Plugin provides cron-based job scheduling - you can schedule tasks/prompts to be sent at any time using cron-based syntax for task setup.

![v2_crontab](https://github.com/szczyglis-dev/py-gpt/raw/master/docs/source/images/v2_crontab.png)

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#crontab-task-scheduler

## Custom commands

With the `Custom commands` plugin, you can integrate **PyGPT** with your operating system and scripts or applications. You can define an unlimited number of custom commands and instruct model on when and how to execute them. Configuration is straightforward, and **PyGPT** includes a simple tutorial command for testing and learning how it works:

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#custom-commands

## Experts (inline)

The plugin makes enabled Expert presets available in supported chat modes through the regular `expert_call` tool. When the current model delegates a task, the selected Expert is executed as a regular agent by the same **Agents v2 runtime** used by **Chat with Agents**, and its final response is returned directly as the tool result.

Use **Experts** mode to define, configure, enable, or disable Expert presets. Once an Expert is enabled, you can simply ask for it by name in the conversation, for example: `Ask the Python programmer expert to review this code.` The model can then call `expert_call` automatically.

See the `Work modes -> Experts` section for more details.

## Facebook

The plugin integrates with Facebook's Graph API to enable various actions such as managing pages, posts, and media uploads. It uses OAuth2 for authentication and supports automatic token exchange processes. 

- Retrieving basic information about the authenticated user.
- Listing all Facebook pages the user has access to.
- Setting a specified Facebook page as the default.
- Retrieving a list of posts from a Facebook page.
- Creating a new post on a Facebook page.
- Deleting a post from a Facebook page.
- Uploading a photo to a Facebook page.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#facebook

## Files I/O

The plugin allows for file management within the local filesystem. It enables the model to create, read, write and query files located in the active `data` workdir. Normally this is `<profile workdir>/data`; if the current conversation belongs to a project with **Use shared workdir** disabled, the project's configured directory is used instead. The plugin and its current-working-directory tool resolve this path dynamically for the conversation that invoked the operation.

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

The plugin provides seamless integration with GitHub, allowing various operations such as repository management, issue tracking, pull requests, and more through GitHub's API. This plugin requires authentication, which can be configured using a Personal Access Token (PAT) or OAuth Device Flow.

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

The plugin integrates with various Google services, enabling features such as email management, calendar events, contact handling, and document manipulation through Google APIs.

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

The plugin integrates image generation with any chat mode. Select the image-generation model in the plugin settings, enable the plugin, and ask the current model to create an image. The model can then call the plugin's `image` tool with a dedicated image prompt. The plugin does not require the `+ Tools` option to be enabled.

By default, the plugin appends a short image-generation instruction to the system prompt so the current model knows when and how to use the `image` tool. You can disable this behavior with `Append image prompt to system prompt` while keeping the image tool available.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#image-generation-inline

## Mailer

Enables the sending, receiving, and reading of emails from the inbox. Currently, only SMTP is supported. More options coming soon.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#mailer

## Memory (inline)

The **Memory (inline)** plugin provides a compact long-term memory cache stored in the local database. It uses one global memory outside projects and a separate memory for each project; when a conversation belongs to a project, the project-specific memory is used instead of the global one. It also provides a separate raw key/value store in the `memory_keys` table with the same global/project isolation. Because it is an inline plugin, it does not require the `+ Tools` option to be enabled.

After a completed conversation turn, Memory can update the active memory asynchronously using the configured model. The updater rewrites the memory as a compact canonical state: it keeps important durable information, merges related facts instead of accumulating duplicates, reconciles newer information with older entries, and drops routine or transient details. Global memory focuses on durable information about the user, while project memory keeps information relevant to that project.

**Options:**

- **Memory update model** - model used for automatic memory updates and, when enabled, for refining manual `memory_add` calls.
- **Maximum memory characters** - target memory size. Default: `15000` characters. A `300`-character safety margin is allowed before hard truncation.
- **Refine memory before adding** - applies only to manual `memory_add` calls. When enabled (default), the configured model merges the new information into the existing memory instead of appending raw text. Automatic end-of-context updates are always refined regardless of this option.
- **Auto attach memory to every conversation** - appends the active memory to the system prompt in `<context_memory>...</context_memory>`. Default: `False`.
- **Auto attach memory only in projects** - automatically attaches memory when the current conversation belongs to a project. Default: `True`.
- **Search memory key content** - controls `memory_key_search`. Key names are always searched with `LIKE '%query%'`; content is searched too only when this option is enabled. Default: `False`.

Keyed memory is stored raw and never summarized, merged, or rewritten by the memory-update LLM. Each key is unique inside its global/project scope. The auto-attach options apply only to the compact memory; keyed records are retrieved explicitly through the keyed-memory tools. Use keyed writes only for genuinely important information that should be preserved for later use, not routine or temporary details.

**Tools:**

- `memory_get` - reads the complete memory for the current scope. Enabled by default.
- `memory_add` - selectively adds an important, durable fact and can merge it with existing memory. Disabled by default.
- `memory_update` - replaces the complete memory content for the current scope. Disabled by default.
- `memory_clear` - clears the current memory only after explicit user confirmation. Enabled by default.
- `memory_key_get(key|keys)` - reads raw keyed-memory records by one key or a list of keys. Enabled by default.
- `memory_key_add(key, content)` - creates a new raw keyed record without overwriting an existing key or using an LLM. Enabled by default.
- `memory_key_append(key, content)` - appends raw content exactly as provided to an existing key, without an automatic separator or LLM processing. Enabled by default.
- `memory_key_update(key, content)` - replaces the raw content of an existing key. Enabled by default.
- `memory_key_list()` - returns only key names, without content. Enabled by default.
- `memory_key_search(query)` - returns matching raw records; always uses `LIKE '%query%'` on keys and optionally on content when **Search memory key content** is enabled. Enabled by default.
- `memory_key_remove(key|keys)` - removes one key or a list of keys from the current scope. Enabled by default.

Inside projects, keyed tools use only the current project's records and never fall back to global keyed memory. Outside projects, they use only global keyed records.

## MCP (Model Context Protocol)

With the `MCP` plugin, you can connect **PyGPT** to remote tools exposed by `Model Context Protocol` servers (stdio, Streamable HTTP, or SSE). The plugin discovers available tools on your configured servers and publishes them to the model as callable commands with proper parameter schemas. You can whitelist/blacklist tools per server. Tool discovery caching is enabled by default with a 300-second TTL.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#mcp

## Mouse and keyboard

**WARNING: Use this plugin with caution - allowing all options gives the model full control over the mouse and keyboard**

The plugin allows for controlling the mouse and keyboard by the model. With this plugin, you can send a task to the model, e.g., "open notepad, type something in it" or "open web browser, do search, find something."

Plugin capabilities include:

- Get mouse cursor position
- Control mouse cursor position
- Control mouse clicks
- Control mouse scroll
- Control the keyboard (pressing keys, typing text)
- Making screenshots

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#mouse-and-keyboard

## OpenStreetMap

Provides everyday mapping utilities using OpenStreetMap services:

- Forward and reverse geocoding via Nominatim
- Search with optional near/bbox filters
- Routing via OSRM (driving, walking, cycling)
- Generate openstreetmap.org URL (center/zoom or bbox; optional marker)
- Utility helpers: open an OSM website URL centered on a point; download a single XYZ tile

Images are saved under `data/openstreetmap/` in the user data directory.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#openstreetmap

## Real time

This plugin automatically adds the current date and time to each system prompt you send. 
You have the option to include just the date, just the time, or both.

When enabled, it quietly enhances each system prompt with current time information before sending it to model.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#real-time

## Serial port / USB

Provides commands for reading and sending data to USB ports.

**Tip:** in Snap version you must connect the interface first: https://snapcraft.io/docs/serial-port-interface

You can send commands to, for example, an Arduino or any other controllers using the serial port for communication.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#serial-port-usb

## Server (SSH/FTP)

The Server plugin provides integration for remote server management via SSH, SFTP, and FTP protocols. This plugin allows executing commands, transferring files, and managing directories on remote servers.

For security reasons, the model will not see any credentials, only the server name and port fields (see the docs)

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#server-ssh-ftp

## Slack

The Slack plugin integrates with the Slack Web API, enabling interaction with Slack workspaces through the application. This plugin supports OAuth2 for authentication, which allows for seamless integration with Slack services, enabling actions such as posting messages, retrieving users, and managing conversations.

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

The plugin provides access to the operating system and executes system commands. `sys_exec` input/output is mirrored to the Python/OS window when **Connect to the Python/OS window** is enabled (default: enabled). Docker sandbox execution is disabled by default; the stock sandbox runs as the unprivileged `pygpt` user by default, with passwordless `sudo` available when elevated commands are needed.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#system-os

## Extra system prompt

The plugin appends additional system prompts (extra data) from a list to every current system prompt. 
You can enhance every system prompt with extra instructions that will be automatically appended to the system prompt.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#extra-system-prompt

## Telegram

The plugin enables integration with Telegram for both bots and user accounts through the ``Bot API`` and the ``Telethon`` library respectively. It allows sending and receiving messages, managing chats, and handling updates.

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

The Tuya plugin integrates with Tuya's Smart Home platform, enabling seamless interactions with your smart devices via the Tuya Cloud API. This plugin provides a user-friendly interface to manage and control devices directly from your assistant.

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

The plugin adds image analysis to supported chat modes without relying on the deprecated standalone Vision mode. When an image attachment, screenshot, or camera capture is detected, the request is handled through Chat with the image-capable model configured in the plugin. This preserves the plugin's dedicated-model behavior while removing the dependency on the legacy Vision mode.

The plugin model list is filtered by capabilities (`Chat` + image input), not by provider, so supported models from OpenAI, Google, Anthropic, xAI, OpenRouter, local/OpenAI-compatible endpoints, and other configured providers can be selected. Native Google, Anthropic, and xAI SDK routing is respected when enabled; otherwise the configured OpenAI-compatible Chat endpoint is used where applicable.

**Tip:** The `+ Vision` label at the bottom of the Chat window is an availability indicator for inline image analysis. Image handling is automatic when compatible image content is supplied; there is no separate legacy Vision-mode switch to enable.

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#vision-inline

## Voice control (inline)

The plugin provides voice control command execution within a conversation. The optional **Magic prefix for voice commands** defaults to `Execute voice command`.

See the `Accessibility` section for more details.

## Web search

**PyGPT** lets you connect model to the internet and carry out web searches in real time as you make queries.

To activate this feature, turn on the `Web search` plugin found in the `Plugins` menu.

Web searches can use `DuckDuckGo`, `Google Custom Search Engine`, or `Microsoft Bing` and can be extended with other search engine providers. DuckDuckGo does not require an API key. The default provider is Google Custom Search; the plugin opens at most 3 URLs at once by default, fetches thumbnail images, and currently has SSL verification disabled for crawling by default. 

Documentation: https://pygpt.readthedocs.io/en/latest/plugins.html#web-search

## Wikipedia

The Wikipedia plugin allows for comprehensive interactions with Wikipedia, including language settings, article searching, summaries, and random article discovery. This plugin offers a variety of options to optimize your search experience.

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

The X/Twitter plugin integrates with the X platform, allowing for comprehensive interactions such as tweeting, retweeting, liking, media uploads, and more. This plugin requires OAuth2 authentication and offers various configuration options to manage API interactions effectively.

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

PyGPT supports native API tool/function calls as well as its internal prompt-based command/tool system. Commands exposed by enabled plugins can be called by compatible models when the `+ Tools` option is active. Native API tool calls can be enabled in `Config -> Settings -> Prompts`, and model-level support is controlled by the `Tool calls` option in the Models Editor.

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
- Agents Builder (beta)

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


This tool allows indexing of local files or directories and external web content to a vector database, which can then be used with the `Chat with Files` mode. Using this tool, you can manage local indexes and add new data with built-in `LlamaIndex` integration.

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


This tool allows you to run Python code directly from within the app. It is integrated with the `Code interpreter (v2)` plugin, ensuring that code generated by the model is automatically available from the interpreter. In the plugin settings, you can enable the execution of code in a Docker environment.

**Python/IPython environment:** Local IPython execution requires a working Python environment on the host system. If local execution fails because of Python, package, kernel, or environment issues, enable the Docker sandbox in the `Code interpreter (v2)` plugin settings. Docker provides an isolated and reproducible runtime and is the recommended fallback for problematic host environments.

Docker installation: [Docker Engine](https://docs.docker.com/engine/install/) | [Docker Desktop](https://docs.docker.com/desktop/)

## HTML/JS Canvas

Allows to render HTML/JS code in HTML Canvas (built-in renderer based on Chromium). To use it, just ask the model to render the HTML/JS code in built-in browser (HTML Canvas). Tool is integrated with the `Code interpreter (v2)` plugin.

## Translator

Enables translation between multiple languages using an AI model.

## Web Browser

A built-in web browser based on Chromium, allowing you to open webpages directly within the app. **SECURITY NOTICE:** For your protection, avoid using the built-in browser for sensitive or critical tasks. It is intended for basic use only.

# Agents Builder (beta)

**Legacy modes only:** Agents Builder is used by the legacy `Agent (LlamaIndex)` and `Agent (OpenAI)` workflows. It is not used by the modern `Chat with Agents` mode.

To launch the Agent Editor, navigate to:

`Tools -> Agents Builder`

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

For the complete routing schema, injected system-instruction example, and Agents Builder details, see:

https://pygpt.readthedocs.io/en/latest/tools.html#agents-builder-beta

**INFO:** Agents Builder is in beta.


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
- Switch to chat with files (llama-index) mode
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

The Settings window contains configuration for API providers, layout, files and attachments, chats, remote tools, models, prompts, media, RAG/indexes, agents, security, accessibility, updates, debugging, and other application features.

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

A project's custom workdir does **not** replace this profile/application workdir. It overrides only the logical `data` directory for conversations assigned to that project. The **Files** tab, file tools and Docker `/data` mapping follow the active project data directory at runtime, while `tmp`, configuration, database, cache, CSS, locale, fonts and logs remain in the base profile workdir.

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

PyGPT supports custom translations and user overrides for locale and CSS files. Locale files use the `.ini` format and are loaded automatically by the application.

Custom locale, CSS, and font files can also be placed in the PyGPT working directory to override the bundled resources.

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

You can configure selected vector store by providing config options like `api_key`, etc. in `Settings -> LlamaIndex` window. 

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

By default, you are using chat-based mode when using `Chat with Files`.
If you want to only query index (without chat) you can enable `Query index only (without chat)` option.

### Adding custom vector stores and data loaders

You can create a custom vector store provider or data loader for your data and develop a custom launcher for the application. 

See the section `Extending PyGPT / Adding a custom Vector Store provider` for more details.

# Updates

### Updating PyGPT

**PyGPT** comes with an integrated update notification system. When a new version with additional features is released, you'll receive an alert within the app. 

To get the new version, simply download it and start using it in place of the old one. All your custom settings like configuration, presets, indexes, and past conversations will be kept and ready to use right away in the new version.

# Debugging and Logging

Most diagnostic options are available in `Config -> Settings -> Debug`. PyGPT writes application logs to `%workdir%/app.log`, and the log level can be set to `ERROR`, `WARNING`, `INFO`, or `DEBUG`. For startup troubleshooting, `--debug=1` forces `INFO` logging and `--debug=2` forces `DEBUG` logging.

Additional switches can log conversation processing, events, plugin usage, attachments, image/video generation, LlamaIndex activity, Realtime sessions, legacy API paths, and agent workflows. For `Chat with Agents`, you can choose either a concise workflow trace or the full verbose flow. Full tracing can include prompts, tool arguments, retrieved context, and other sensitive data.

Enable `Show debug menu` to expose developer tools such as the live Logger/console, DB Viewer, application-state inspectors, Chromium diagnostics, and WebEngine DevTools. If a compiled build crashes or fails during startup, launch it from a terminal so stdout/stderr and Python/Qt diagnostics remain visible.

For the complete debugging reference, Logger commands, DB Viewer details, compiled-build instructions, and all diagnostic switches, see the [Debugging and Logging documentation](https://pygpt.readthedocs.io/en/latest/debug.html).

# Extending PyGPT

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

**2.8.16 (2026-09-12)**

- Experts are now full-featured agents, using the same agent runtime and capabilities as agents in Chat with Agents.
- Experts are now available as tools across all supported modes, allowing them to be invoked directly from anywhere in the application.

**2.8.15 (2026-09-11)**

- Renamed **Agents v2 (beta)** mode to **Chat with Agents**.
- Added 3 separate submodes to **Chat with Agents**:
  - **Chat** - allows natural conversation with the primary agent, with delegated agents used when needed.
  - **Orchestrator** - the previous Agents v2 behavior, where the primary agent acts only as an orchestrator for other agents.
  - **Swarm** - allows creating and running a dynamically defined group of specialized agents/workers in parallel in the background. Swarm mode can run continuously with a defined number of parallel agents.
- Added the ability to configure a custom working directory per project. Right-click a project in the project list and select a custom workdir.
- Added LLM provider fallbacks to **OpenAILike** when a model is not yet supported by the native LlamaIndex integrations for OpenAI, Google, Anthropic, or xAI.
- Added keyed memory storage to the **Memory** plugin.
- Fixed collection of used URLs and attachments in **Chat with Files**.

**2.8.14 (2026-09-10)**

- Security, stability, and provider fixes - PR [#208](https://github.com/szczyglis-dev/py-gpt/pull/208) by [@atharvaHJoshi](https://github.com/atharvaHJoshi).
- Fixed list selectors for vision models by removing checks for the deprecated vision mode.
- Fixed the halt and acknowledgement flow in Computer Use.
- Moved the native Perplexity LlamaIndex provider to the shared OpenAI-compatible wrapper.
- Fixed legacy beta headers for Anthropic in Chat with Files mode.
- Fixed support for remote tools and Computer Use in Chat with Files mode.
- Fixed race conditions and restart loops in the IPython plugin.
- Added splitter anchors to the CSS in the light theme.
- Added a new model: `gpt-image-2.5`.
- Added an **Insert date/time** option to the Notepad right-click menu.
- Added support for Completion-only mode with models and providers other than OpenAI `gpt-3.5-instruct`.
- Added support for local Jupyter/IPython in compiled builds.
- Set IPython’s default stdin to `DEVNULL` when running code with interactive input to prevent freezes.
- Added support for Computer Use in Realtime + Audio, Legacy Agents, and Autonomous modes.
- Various UI and CSS fixes.

**2.8.13 (2026-09-09)**

- Fixed issue with empty parameters in the Anthropic API remote tool for computer use.
- Added support for the use of computer use remote tool in Chat with Agents for Anthropic and Google.
- Added **OSINT v2** preset to Chat with Agents.
- Added a new plugin: **Memory (inline)**.
- Updated IPython Dockerfile: included default installation of pandas, matplotlib, scikit-learn, and other useful libraries.
- Integrated Google remote tool - MCP.
- Added validation for pasting large directory attachments.
- Enhanced CSS in chat view for better aesthetics.
- Improved handling of multiple tabs.
- Fixed issue with hiding date separators in context list view.
- Corrected profile switch components restoration.
- Other fixes.

**2.8.12 (2026-09-08)**

- Improved, extended, and fixed several bugs in the following modes: Chat, Realtime + Audio, Computer Use, Autonomous Agent, and Chat with Agents.
- Added new models: **GPT-6 Astra** and **Claude Fable 5.1**.
- Added a new remote tool in **Settings**: **Computer Use**, which allows you to control the computer in standard Chat mode.
- Added item limits, a **Show more** option, and collapsible items to the project list.
- Model responses are now split into partials and stored in the database.
- Fixed multi-column context handling.
- Fixed sandbox image URLs.
- Removed redundant tool input/output from message footers.
- Removed old and deprecated models.

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
