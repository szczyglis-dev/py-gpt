# PyGPT - Desktop AI Assistant

[![pygpt](https://snapcraft.io/pygpt/badge.svg)](https://snapcraft.io/pygpt)

Release: **2.4.15** | build: **2024.11.18** | Python: **>=3.10, <3.12**

> Official website: https://pygpt.net | Documentation: https://pygpt.readthedocs.io
> 
> Discord: https://pygpt.net/discord | Snap: https://snapcraft.io/pygpt | PyPi: https://pypi.org/project/pygpt-net
> 
> Compiled version for Linux (`zip`) and Windows 10/11 (`msi`) 64-bit: https://pygpt.net/#download
> 
> ❤️ Donate: https://www.buymeacoffee.com/szczyglis

## Overview

**PyGPT** is **all-in-one** Desktop AI Assistant that provides direct interaction with OpenAI language models, including `o1`, `gpt-4o`, `gpt-4`, `gpt-4 Vision`, and `gpt-3.5`, through the `OpenAI API`. By utilizing `Langchain` and `Llama-index`, the application also supports alternative LLMs, like those available on `HuggingFace`, locally available models (like `Llama 3`,`Mistral` or `Bielik`), `Google Gemini` and `Anthropic Claude`.

This assistant offers multiple modes of operation such as chat, assistants, completions, and image-related tasks using `DALL-E 3` for generation and `gpt-4 Vision` for image analysis. **PyGPT** has filesystem capabilities for file I/O, can generate and run Python code, execute system commands, execute custom commands and manage file transfers. It also allows models to perform web searches with the `Google` and `Microsoft Bing`.

For audio interactions, **PyGPT** includes speech synthesis using the `Microsoft Azure`, `Google`, `Eleven Labs` and `OpenAI` Text-To-Speech services. Additionally, it features speech recognition capabilities provided by `OpenAI Whisper`, `Google` and `Bing` enabling the application to understand spoken commands and transcribe audio inputs into text. It features context memory with save and load functionality, enabling users to resume interactions from predefined points in the conversation. Prompt creation and management are streamlined through an intuitive preset system.

**PyGPT**'s functionality extends through plugin support, allowing for custom enhancements. Its multi-modal capabilities make it an adaptable tool for a range of AI-assisted operations, such as text-based interactions, system automation, daily assisting, vision applications, natural language processing, code generation and image creation.

Multiple operation modes are included, such as chat, text completion, assistant, vision, Langchain, Chat with files (via `Llama-index`), commands execution, external API calls and image generation, making **PyGPT** a multi-tool for many AI-driven tasks.

**Video** (mp4, version `2.2.0`, build `2024-04-28`):

https://github.com/szczyglis-dev/py-gpt/assets/61396542/7140ded4-1639-4c12-ac33-201b68b99a16

**Screenshot** (version `2.2.0`, build `2024-04-28`):

![v2_main](https://github.com/szczyglis-dev/py-gpt/assets/61396542/d9f2e67f-919c-4faa-b059-6e2f5efd23e6)

You can download compiled 64-bit versions for Windows and Linux here: https://pygpt.net/#download

## Features

- Desktop AI Assistant for `Linux`, `Windows` and `Mac`, written in Python.
- Works similarly to `ChatGPT`, but locally (on a desktop computer).
- 10 modes of operation: Chat, Vision, Completion, Assistant, Image generation, Langchain, Chat with files, Experts, Agent (Llama-index), and Agent (legacy, autonomous).
- Supports multiple models: `o1`, `gpt-4`, `gpt-3.5`, and any model accessible through `Langchain` and `Llama-index` such as `Llama 3`, `Mistral`, `Google Gemini`, `Anthropic Claude`, `Bielik`, etc.
- Included support features for individuals with disabilities: customizable keyboard shortcuts, voice control, and translation of on-screen actions into audio via speech synthesis.
- Handles and stores the full context of conversations (short and long-term memory).
- Real-time video camera capture in Vision mode.
- Internet access via `Google` and `Microsoft Bing`.
- Speech synthesis via `Microsoft Azure`, `Google`, `Eleven Labs` and `OpenAI` Text-To-Speech services.
- Speech recognition via `OpenAI Whisper`, `Google`, `Google Cloud` and `Microsoft Bing`.
- Image analysis via `gpt4-o` and `gpt-4 vision`.
- Crontab / Task scheduler included.
- Integrated `Langchain` support (you can connect to any LLM, e.g., on `HuggingFace`).
- Integrated `Llama-index` support: chat with `txt`, `pdf`, `csv`, `html`, `md`, `docx`, `json`, `epub`, `xlsx`, `xml`, webpages, `Google`, `GitHub`, video/audio, images and other data types, or use conversation history as additional context provided to the model.
- Integrated calendar, day notes and search in contexts by selected date.
- Commands execution (via plugins: access to the local filesystem, Python code interpreter, system commands execution).
- Custom commands creation and execution.
- Manages files and attachments with options to upload, download, and organize.
- Context history with the capability to revert to previous contexts (long-term memory).
- Allows you to easily manage prompts with handy editable presets.
- Provides an intuitive operation and interface.
- Includes a notepad.
- Includes simple painter / drawing tool.
- Includes optional Autonomous Mode (Agents).
- Supports multiple languages.
- Enables the use of all the powerful features of `o1`, `gpt-4`, `gpt-4-vision`, and `gpt-3.5`.
- Requires no previous knowledge of using AI models.
- Simplifies image generation using `DALL-E 3` and `DALL-E 2`.
- Possesses the potential to support future OpenAI models.
- Fully configurable.
- Themes support.
- Real-time code syntax highlighting.
- Plugins support.
- Built-in token usage calculation.
- It's open source; source code is available on `GitHub`.
- Utilizes the user's own API key.

The application is free, open-source, and runs on PCs with `Linux`, `Windows 10`, `Windows 11` and `Mac`. 
Full Python source code is available on `GitHub`.

**PyGPT uses the user's API key  -  to use the application, 
you must have a registered OpenAI account and your own API key.**

You can also use built-it Langchain support to connect to other Large Language Models (LLMs), 
such as those on HuggingFace. Additional API keys may be required.

# Installation

## Compiled versions (Linux, Windows 10 and 11)

You can download compiled versions for `Linux` and `Windows` (10/11). 

Download the `.msi` or `zip`/`tar.gz` for the appropriate OS from the download page at https://pygpt.net and then extract files from the archive and run the application. 64-bit only.

Linux version requires `GLIBC` >= `2.35`.

## Snap Store

You can install **PyGPT** directly from Snap Store:

```commandline
sudo snap install pygpt
```

To manage future updates just use:

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
```

**Connecting IPython in Docker in Snap version**:

To use IPython in the Snap version, you must connect PyGPT to the Docker daemon (built into the Snap package):

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

## Source Code

An alternative method is to download the source code from `GitHub` and execute the application using the Python interpreter (>=3.10, <3.12). 

### Running from GitHub source code

1. Clone git repository or download .zip file:

```commandline
git clone https://github.com/szczyglis-dev/py-gpt.git
cd py-gpt
```

2. Create virtual environment:

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

**Install with Poetry**

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

4. Install requirements:

```commandline
poetry install
```

5. Run the application:

```commandline
poetry run python3 run.py
```

**Tip**: you can use `PyInstaller` to create a compiled version of
the application for your system (required version >= `6.0.0`).

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
and an active API key that must be input into the program.

## Debugging and logging

**Tip:** Go to `Debugging and Logging` section for instructions on how to log and diagnose issues in a more detailed manner.


# Quick Start

## Setting-up OpenAI API KEY

**Tip:** The API key is required to work with the OpenAI API. If you wish to use custom API endpoints or local API that do not require API keys, simply enter anything into the API key field to avoid a prompt about the API key being empty.

During the initial launch, you must configure your API key within the application.

To do so, navigate to the menu:

``` ini
Config -> Settings...
```

and then paste the API key into the `OpenAI API KEY` field.

![v2_settings](https://github.com/szczyglis-dev/py-gpt/assets/61396542/43622c58-6cdb-4ed8-b47d-47729763db04)

The API key can be obtained by registering on the OpenAI website:

<https://platform.openai.com>

Your API keys will be available here:

<https://platform.openai.com/account/api-keys>

**Note:** The ability to use models within the application depends on the API user's access to a given model!

# Working modes

## Chat

**+ inline Vision and Image generation**

This mode in **PyGPT** mirrors `ChatGPT`, allowing you to chat with models such as `GPT-4`, `GPT-4 Turbo` and `GPT-3.5`. It's easy to switch models whenever you want. It works by using the `ChatCompletion API`.

The main part of the interface is a chat window where conversations appear. Right below that is where you type your messages. On the right side of the screen, there's a section to set up or change your system prompts. You can also save these setups as presets to quickly switch between different models or tasks.

Above where you type your messages, the interface shows you the number of tokens your message will use up as you type it – this helps to keep track of usage. There's also a feature to upload files in this area. Go to the `Files` tab to manage your uploads or add attachments to send to the OpenAI API (but this makes effect only in `Assisant` and `Vision` modes).

![v2_mode_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f573ee22-8539-4259-b180-f97e54bc0d94)

**Vision:** If you want to send photos or image from camera to analysis you must enable plugin **GPT-4 Vision Inline** in the Plugins menu.
Plugin allows you to send photos or image from camera to analysis in any Chat mode:

![v3_vision_plugins](https://github.com/szczyglis-dev/py-gpt/assets/61396542/104b0a80-7cf8-4a02-aa74-27e89ad2e409)

With this plugin, you can capture an image with your camera or attach an image and send it for analysis to discuss the photograph:

![v3_vision_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/3fbd99e2-5bbf-4bd4-81d8-fd4d7db9d8eb)

**Image generation:** If you want to generate images (using DALL-E) directly in chat you must enable plugin **DALL-E 3 Inline** in the Plugins menu.
Plugin allows you to generate images in Chat mode:

![v3_img_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/c288a4b3-c932-4201-b5a3-8452aea49817)

## Completion

This mode provides in-depth access to a broader range of capabilities offered by Large Language Models (LLMs). While it maintains a chat-like interface for user interaction, it introduces additional settings and functional richness beyond typical chat exchanges. Users can leverage this mode to prompt models for complex text completions, role-play dialogues between different characters, perform text analysis, and execute a variety of other sophisticated tasks. It supports any model provided by the OpenAI API as well as other models through `Langchain`.

Similar to chat mode, on the right-hand side of the interface, there are convenient presets. These allow you to fine-tune instructions and swiftly transition between varied configurations and pre-made prompt templates.

Additionally, this mode offers options for labeling the AI and the user, making it possible to simulate dialogues between specific characters - for example, you could create a conversation between Batman and the Joker, as predefined in the prompt. This feature presents a range of creative possibilities for setting up different conversational scenarios in an engaging and exploratory manner.

![v2_mode_completion](https://github.com/szczyglis-dev/py-gpt/assets/61396542/045ecb99-edcb-4eb1-9ff0-0b493dee0e27)

From version `2.0.107` the `davinci` models are deprecated and has been replaced with `gpt-3.5-turbo-instruct` model in Completion mode.

## Assistants

This mode uses the new OpenAI's **Assistants API**.

This mode expands on the basic chat functionality by including additional external tools like a `Code Interpreter` for executing code, `Retrieval Files` for accessing files, and custom `Functions` for enhanced interaction and integration with other APIs or services. In this mode, you can easily upload and download files. **PyGPT** streamlines file management, enabling you to quickly upload documents and manage files created by the model.

Setting up new assistants is simple - a single click is all it takes, and they instantly sync with the `OpenAI API`. Importing assistants you've previously created with OpenAI into **PyGPT** is also a seamless process.

![v2_mode_assistant](https://github.com/szczyglis-dev/py-gpt/assets/61396542/5c3b5604-928d-4f29-940a-21cc83c8dc34)

In Assistant mode you are allowed to storage your files (per Assistant) and manage them easily from app:

![v2_mode_assistant_upload](https://github.com/szczyglis-dev/py-gpt/assets/61396542/b2c835ea-2816-4b85-bb6f-e08874e758f7)

Please note that token usage calculation is unavailable in this mode. Nonetheless, file (attachment) 
uploads are supported. Simply navigate to the `Files` tab to effortlessly manage files and attachments which 
can be sent to the OpenAI API.

### Vector stores (via Assistants API)

Assistant mode supports the use of external vector databases offered by the OpenAI API. This feature allows you to store your files in a database and then search them using the Assistant's API. Each assistant can be linked to one vector database—if a database is linked, all files uploaded in this mode will be stored in the linked vector database. If an assistant does not have a linked vector database, a temporary database is automatically created during the file upload, which is accessible only in the current thread. Files from temporary databases are automatically deleted after 7 days.

To enable the use of vector stores, enable the `Chat with files` checkbox in the Assistant settings. This enables the `File search` tool in Assistants API.

To manage external vector databases, click the DB icon next to the vector database selection list in the Assistant creation and editing window. In this management window, you can create a new database, edit an existing one, or import a list of all existing databases from the OpenAI server:

![v2_assistant_stores](https://github.com/szczyglis-dev/py-gpt/assets/61396542/2f605326-5bf5-4c82-8dfd-cb1c0edf6724)

You can define, using `Expire days`, how long files should be automatically kept in the database before deletion (as storing files on OpenAI incurs costs). If the value is set to 0, files will not be automatically deleted.

The vector database in use will be displayed in the list of uploaded files, on the field to the right—if a file is stored in a database, the name of the database will be displayed there; if not, information will be shown indicating that the file is only accessible within the thread:

![v2_assistant_stores_upload](https://github.com/szczyglis-dev/py-gpt/assets/61396542/8f13c2eb-f961-4eae-b08b-0b4937f06ca9)

## Vision (GPT-4 Vision)

**INFO:** From version `2.2.6` (2024-04-30) Vision is available directly in Chat mode, without any plugins - if the model supports Vision (currently: `gpt-4-turbo` and `gpt-4-turbo-2024-04-09`).

This mode enables image analysis using the `GPT-4 Vision` model. Functioning much like the chat mode, 
it also allows you to upload images or provide URLs to images. The vision feature can analyze both local 
images and those found online. 

Vision is integrated into any chat mode via plugin `GPT-4 Vision (inline)`. Just enable the plugin and use Vision in standard modes.

Vision mode also includes real-time video capture from camera. To enable capture check the option `Camera` on the right-bottom corner. It will enable real-time capturing from your camera. To capture image from camera and append it to chat just click on video at left side. You can also enable `Auto capture` - image will be captured and appended to chat message every time you send message.

![v2_capture_enable](https://github.com/szczyglis-dev/py-gpt/assets/61396542/c40ce0b4-57c8-4643-9982-25d15e68377e)

**1) Video camera real-time image capture**

![v2_capture1](https://github.com/szczyglis-dev/py-gpt/assets/61396542/477bb7fa-4639-42bb-8466-937e88e4a835)

![v3_vision_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/3fbd99e2-5bbf-4bd4-81d8-fd4d7db9d8eb)

**2) you can also provide an image URL**

![v2_mode_vision](https://github.com/szczyglis-dev/py-gpt/assets/61396542/d1b68225-bf7f-4aa5-9562-b973211b57d7)

**3) or you can just upload your local images or use the inline Vision in the standard chat mode:**

![v2_mode_vision_upload](https://github.com/szczyglis-dev/py-gpt/assets/61396542/7885d7d0-072e-4053-a81b-6374711fd348)

**Tip:** When using `Vision (inline)` by utilizing a plugin in standard mode, such as `Chat` (not `Vision` mode), the `+ Vision` special checkbox will appear at the bottom of the Chat window. It will be automatically enabled any time you provide content for analysis (like an uploaded photo). When the checkbox is enabled, the vision model is used. If you wish to exit the vision model after image analysis, simply uncheck the checkbox. It will activate again automatically when the next image content for analysis is provided.

## Langchain

This mode enables you to work with models that are supported by `Langchain`. The Langchain support is integrated 
into the application, allowing you to interact with any LLM by simply supplying a configuration 
file for the specific model. You can add as many models as you like; just list them in the configuration 
file named `models.json`.

Available LLMs providers supported by **PyGPT**, in `Langchain` and `Chat with files (llama-index)` modes:

```
- OpenAI
- Azure OpenAI
- Google (Gemini, etc.)
- HuggingFace
- Anthropic
- Ollama (Llama3, Mistral, etc.)
```

![v2_mode_langchain](https://github.com/szczyglis-dev/py-gpt/assets/61396542/0471b6f9-7953-42cc-92bd-007f2c2e59d0)

You have the ability to add custom model wrappers for models that are not available by default in **PyGPT**. 
To integrate a new model, you can create your own wrapper and register it with the application. 
Detailed instructions for this process are provided in the section titled `Managing models / Adding models via Langchain`.

##  Chat with files (Llama-index)

This mode enables chat interaction with your documents and entire context history through conversation. 
It seamlessly incorporates `Llama-index` into the chat interface, allowing for immediate querying of your indexed documents.

**Querying single files**

You can also query individual files "on the fly" using the `query_file` command from the `Files I/O` plugin. This allows you to query any file by simply asking a question about that file. A temporary index will be created in memory for the file being queried, and an answer will be returned from it. From version `2.1.9` similar command is available for querying web and external content: `Directly query web content with Llama-index`.

For example:

If you have a file: `data/my_cars.txt` with content `My car is red.`

You can ask for: `Query the file my_cars.txt about what color my car is.`

And you will receive the response: `Red`.

Note: this command indexes the file only for the current query and does not persist it in the database. To store queried files also in the standard index you must enable the option "Auto-index readed files" in plugin settings. Remember to enable "Execute commands" checkbox to allow usage of query commands. 

**Using Chat with files mode**

In this mode, you are querying the whole index, stored in a vector store database.
To start, you need to index (embed) the files you want to use as additional context.
Embedding transforms your text data into vectors. If you're unfamiliar with embeddings and how they work, check out this article:

https://stackoverflow.blog/2023/11/09/an-intuitive-introduction-to-text-embeddings/

For a visualization from OpenAI's page, see this picture:

![vectors](https://github.com/szczyglis-dev/py-gpt/assets/61396542/4bbb3860-58a0-410d-b5cb-3fbfadf1a367)

Source: https://cdn.openai.com/new-and-improved-embedding-model/draft-20221214a/vectors-3.svg

To index your files, simply copy or upload them  into the `data` directory and initiate indexing (embedding) by clicking the `Index all` button, or right-click on a file and select `Index...`. Additionally, you have the option to utilize data from indexed files in any Chat mode by activating the `Chat with files (Llama-index, inline)` plugin.

![v2_idx1](https://github.com/szczyglis-dev/py-gpt/assets/61396542/c3dfbc89-cbfe-4ae3-b7e7-821401d755cd)

After the file(s) are indexed (embedded in vector store), you can use context from them in chat mode:

![v2_idx2](https://github.com/szczyglis-dev/py-gpt/assets/61396542/70c9ab66-82d9-4f61-81ed-268743bfa6b4)

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
- Txt/raw files (txt)
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

You can configure data loaders in `Settings / Llama-index / Data Loaders` by providing list of keyword arguments for specified loaders.
You can also develop and provide your own custom loader and register it within the application.

Llama-index is also integrated with context database - you can use data from database (your context history) as additional context in discussion. 
Options for indexing existing context history or enabling real-time indexing new ones (from database) are available in `Settings / Llama-index` section.

**WARNING:** remember that when indexing content, API calls to the embedding model are used. Each indexing consumes additional tokens. Always control the number of tokens used on the OpenAI page.

**Tip:** when using `Chat with files` you are using additional context from db data and files indexed from `data` directory, not the files sending via `Attachments` tab. 
Attachments tab in `Chat with files` mode can be used to provide images to `Vision (inline)` plugin only.

**Token limit:** When you use `Chat with files` in non-query mode, Llama-index adds extra context to the system prompt. If you use a plugins (which also adds more instructions to system prompt), you might go over the maximum number of tokens allowed. If you get a warning that says you've used too many tokens, turn off plugins you're not using or turn off the "Execute commands" option to reduce the number of tokens used by the system prompt.

**Available vector stores** (provided by `Llama-index`):

```
- ChromaVectorStore
- ElasticsearchStore
- PinecodeVectorStore
- RedisVectorStore
- SimpleVectorStore
```

You can configure selected vector store by providing config options like `api_key`, etc. in `Settings -> Llama-index` window. 
Arguments provided here (on list: `Vector Store (**kwargs)` in `Advanced settings` will be passed to selected vector store provider. 
You can check keyword arguments needed by selected provider on Llama-index API reference page: 

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

**RedisVectorStore**

Keyword arguments for RedisVectorStore(`**kwargs`):

- `index_name` (default: current index ID, already set, not required)
- any other keyword arguments provided on list

You can extend list of available providers by creating custom provider and registering it on app launch.

By default, you are using chat-based mode when using `Chat with files`.
If you want to only query index (without chat) you can enable `Query index only (without chat)` option.

### Adding custom vector stores and data loaders

You can create a custom vector store provider or data loader for your data and develop a custom launcher for the application. To register your custom vector store provider or data loader, simply register it by passing the vector store provider instance to `vector_stores` keyword argument and loader instance in the `loaders` keyword argument:

```python

# custom_launcher.py

from pygpt_net.app import run
from plugins import CustomPlugin, OtherCustomPlugin
from llms import CustomLLM
from vector_stores import CustomVectorStore
from loaders import CustomLoader

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

run(
    plugins=plugins,
    llms=llms,
    vector_stores=vector_stores,  # <--- list with custom vector store providers
    loaders=loaders  # <--- list with custom data loaders
)
```
The vector store provider must be an instance of `pygpt_net.provider.vector_stores.base.BaseStore`. 
You can review the code of the built-in providers in `pygpt_net.provider.vector_stores` and use them as examples when creating a custom provider.

The data loader must be an instance of `pygpt_net.provider.loaders.base.BaseLoader`. 
You can review the code of the built-in loaders in `pygpt_net.provider.loaders` and use them as examples when creating a custom loader.

**Configuring data loaders**

In the `Settings -> Llama-index -> Data loaders` section you can define the additional keyword arguments to pass into data loader instance.

In most cases, an internal Llama-index loaders are used internally. 
You can check these base loaders e.g. here:

File: https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-file/llama_index/readers/file

Web: https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-web

**Tip:** to index an external data or data from the Web just ask for it, by using `Command: Web Search` plugin, e.g. you can ask the model with `Please index the youtube video: URL to video`, etc. Data loader for a specified content will be choosen automatically.

Allowed additional keyword arguments for built-in data loaders (files):

**CSV Files**  (file_csv)

- `concat_rows` - bool, default: `True`
- `encoding` - str, default: `utf-8`

**HTML Files**  (file_html)

- `tag` - str, default: `section`
- `ignore_no_id` - bool, default: `False`

**Image (vision)**  (file_image_vision)

This loader can operate in two modes: local model and API.
If the local mode is enabled, then the local model will be used. The local mode requires a Python/PyPi version of the application and is not available in the compiled or Snap versions.
If the API mode (default) is selected, then the OpenAI API and the standard vision model will be used. 

**Note:** Usage of API mode consumes additional tokens in OpenAI API (for `GPT-4 Vision` model)!

Local mode requires `torch`, `transformers`, `sentencepiece` and `Pillow` to be installed and uses the `Salesforce/blip2-opt-2.7b` model to describing images.

- `keep_image` - bool, default: `False`
- `local_prompt` - str, default: `Question: describe what you see in this image. Answer:`
- `api_prompt` - str, default: `Describe what you see in this image` - Prompt to use in API
- `api_model` - str, default: `gpt-4-vision-preview` - Model to use in API
- `api_tokens` - int, default: `1000` - Max output tokens in API

**IPYNB Notebook files**  (file_ipynb)

- `parser_config` - dict, default: `None`
- `concatenate` - bool, default: `False`

**Markdown files**  (file_md)

- `remove_hyperlinks` - bool, default: `True`
- `remove_images` - bool, default: `True`

**PDF documents**  (file_pdf)

- `return_full_document` - bool, default: `False`

**Video/Audio**  (file_video_audio)

This loader can operate in two modes: local model and API.
If the local mode is enabled, then the local `Whisper` model will be used. The local mode requires a Python/PyPi version of the application and is not available in the compiled or Snap versions.
If the API mode (default) is selected, then the currently selected provider in `Audio Input` plugin will be used. If the `OpenAI Whisper` is chosen then the OpenAI API and the API Whisper model will be used. 

**Note:** Usage of Whisper via API consumes additional tokens in OpenAI API (for `Whisper` model)!

Local mode requires `torch` and `openai-whisper` to be installed and uses the `Whisper` model locally to transcribing video and audio.

- `model_version` - str, default: `base` - Whisper model to use, available models: https://github.com/openai/whisper

**XML files**  (file_xml)

- `tree_level_split` - int, default: `0`

Allowed additional keyword arguments for built-in data loaders (Web and external content):

**Bitbucket**  (web_bitbucket)

- `username` - str, default: `None`
- `api_key` - str, default: `None`
- `extensions_to_skip` - list, default: `[]`

**ChatGPT Retrieval**  (web_chatgpt_retrieval)

- `endpoint_url` - str, default: `None`
- `bearer_token` - str, default: `None`
- `retries` - int, default: `None`
- `batch_size` - int, default: `100`

**Google Calendar** (web_google_calendar)

- `credentials_path` - str, default: `credentials.json`
- `token_path` - str, default: `token.json`

**Google Docs** (web_google_docs)

- `credentials_path` - str, default: `credentials.json`
- `token_path` - str, default: `token.json`

**Google Drive** (web_google_drive)

- `credentials_path` - str, default: `credentials.json`
- `token_path` - str, default: `token.json`
- `pydrive_creds_path` - str, default: `creds.txt`
- `client_config` - dict, default: `{}`

**Google Gmail** (web_google_gmail)

- `credentials_path` - str, default: `credentials.json`
- `token_path` - str, default: `token.json`
- `use_iterative_parser` - bool, default: `False`
- `max_results` - int, default: `10`
- `results_per_page` - int, default: `None`

**Google Keep** (web_google_keep)

- `credentials_path` - str, default: `keep_credentials.json`

**Google Sheets** (web_google_sheets)

- `credentials_path` - str, default: `credentials.json`
- `token_path` - str, default: `token.json`

**GitHub Issues**  (web_github_issues)

- `token` - str, default: `None`
- `verbose` - bool, default: `False`

**GitHub Repository**  (web_github_repository)

- `token` - str, default: `None`
- `verbose` - bool, default: `False`
- `concurrent_requests` - int, default: `5`
- `timeout` - int, default: `5`
- `retries` - int, default: `0`
- `filter_dirs_include` - list, default: `None`
- `filter_dirs_exclude` - list, default: `None`
- `filter_file_ext_include` - list, default: `None`
- `filter_file_ext_exclude` - list, default: `None`

**Microsoft OneDrive**  (web_microsoft_onedrive)

- `client_id` - str, default: `None`
- `client_secret` - str, default: `None`
- `tenant_id` - str, default: `consumers`

**Sitemap (XML)**  (web_sitemap)

- `html_to_text` - bool, default: `False`
- `limit` - int, default: `10`

**SQL Database**  (web_database)

- `engine` - str, default: `None`
- `uri` - str, default: `None`
- `scheme` - str, default: `None`
- `host` - str, default: `None`
- `port` - str, default: `None`
- `user` - str, default: `None`
- `password` - str, default: `None`
- `dbname` - str, default: `None`

**Twitter/X posts**  (web_twitter)

- `bearer_token` - str, default: `None`
- `num_tweets` - int, default: `100`

##  Agent (Llama-index) 

**Currently in beta version** -- introduced in `2.4.10` (2024-11-14)

Mode that allows the use of agents offered by `Llama-index`.

Includes built-in agents:

- OpenAI
- ReAct
- Structured Planner (sub-tasks)

In the future, the list of built-in agents will be expanded.

You can also create your own agent by creating a new provider that inherits from `pygpt_net.provider.agents.base`.

**Tools / Plugins**  
In this mode, all commands from active plugins are available (commands from plugins are automatically converted into tools for the agent on-the-fly).

**RAG / Using indexes**  
If an index is selected in the agent preset, a tool for reading data from the index is automatically added to the agent, creating a RAG automatically.

Multimodality is currently unavailable, only text is supported. Vision support will be added in the future.

**Loop / Evaluate Mode**

You can run the agent in autonomous mode, in a loop, and with evaluation of the current output. When you enable the `Loop / Evaluate` checkbox, after the final response is given, the quality of the answer will be rated on a percentage scale of `0% to 100%` by another agent. If the response receives a score lower than the one expected (set using a slider at the bottom right corner of the screen, with a default value `75%`), a prompt will be sent to the agent requesting improvements and enhancements to the response.

Setting the expected (required) score to `0%` means that the response will be evaluated every time the agent produces a result, and it will always be prompted to self-improve its answer. This way, you can put the agent in an autonomous loop, where it will continue to operate until it succeeds.

You can set the limit of steps in such a loop by going to `Settings -> Agents and experts -> Llama-index agents -> Max evaluation steps `. The default value is `3`, meaning the agent will only make three attempts to improve or correct its answer. If you set the limit to zero, there will be no limit, and the agent can operate in this mode indefinitely (watch out for tokens!).

You can change the prompt used for evaluating the response in `Settings -> Prompts -> Agent: evaluation prompt in loop`. Here, you can adjust it to suit your needs, for example, by defining more or less critical feedback for the responses received.

##  Agent (legacy, autonomous) 

This is an older version of the Agent mode, still available as legacy. However, it is recommended to use the newer mode: `Agent (Llama-index)`.

**WARNING: Please use this mode with caution** - autonomous mode, when connected with other plugins, may produce unexpected results!

The mode activates autonomous mode, where AI begins a conversation with itself. 
You can set this loop to run for any number of iterations. Throughout this sequence, the model will engage
in self-dialogue, answering his own questions and comments, in order to find the best possible solution, subjecting previously generated steps to criticism.

![v2_agent_toolbox](https://github.com/szczyglis-dev/py-gpt/assets/61396542/a0ae5d13-942e-4a18-9c53-33e7ad1886ff)

**WARNING:** Setting the number of run steps (iterations) to `0` activates an infinite loop which can generate a large number of requests and cause very high token consumption, so use this option with caution! Confirmation will be displayed every time you run the infinite loop.

This mode is similar to `Auto-GPT` - it can be used to create more advanced inferences and to solve problems by breaking them down into subtasks that the model will autonomously perform one after another until the goal is achieved.

You can create presets with custom instructions for multiple agents, incorporating various workflows, instructions, and goals to achieve.

All plugins are available for agents, so you can enable features such as file access, command execution, web searching, image generation, vision analysis, etc., for your agents. Connecting agents with plugins can create a fully autonomous, self-sufficient system. All currently enabled plugins are automatically available to the Agent.

When the `Auto-stop` option is enabled, the agent will attempt to stop once the goal has been reached.

In opposition to `Auto-stop`, when the `Always continue...` option is enabled, the agent will use the "always continue" prompt to generate additional reasoning and automatically proceed to the next step, even if it appears that the task has been completed.

**Options**

The agent is essentially a **virtual** mode that internally sequences the execution of a selected underlying mode. 
You can choose which internal mode the agent should use in the settings:

```Settings / Agent (autonomous) / Sub-mode to use```

Available choices include: `chat`, `completion`, `langchain`, `vision`, `llama_index` (Chat with files).

Default is: `chat`.

If you want to use the Llama-index mode when running the agent, you can also specify which index `Llama-index` should use with the option:

```Settings / Agent (autonomous) / Index to use```

![v2_agent_settings](https://github.com/szczyglis-dev/py-gpt/assets/61396542/c577d219-eb25-4f0e-9ea5-adf20a6b6b81)


##  Experts (co-op, co-operation mode)

Added in version 2.2.7 (2024-05-01).

**This mode is experimental.**

Expert mode allows for the creation of experts (using presets) and then consulting them during a conversation. In this mode, a primary base context is created for conducting the conversation. From within this context, the model can make requests to an expert to perform a task and return the results to the main thread. When an expert is called in the background, a separate context is created for them with their own memory. This means that each expert, during the life of one main context, also has access to their own memory via their separate, isolated context.

**In simple terms - you can imagine an expert as a separate, additional instance of the model running in the background, which can be called at any moment for assistance, with its own context and memory, as well as its own specialized instructions in a given subject.**

Experts do not share contexts with one another, and the only point of contact between them is the main conversation thread. In this main thread, the model acts as a manager of experts, who can exchange data between them as needed.

An expert is selected based on the name in the presets; for example, naming your expert as: ID = python_expert, name = "Python programmer" will create an expert whom the model will attempt to invoke for matters related to Python programming. You can also manually request to refer to a given expert:

```bash
Call the Python expert to generate some code.
```

Experts can be activated or deactivated - to enable or disable use RMB context menu to select the `Enable/Disable` options from the presets list. Only enabled experts are available to use in the thread.

Experts can also be used in `Agent (autonomous)` mode - by creating a new agent using a preset. Simply move the appropriate experts to the active list to automatically make them available for use by the agent.

You can also use experts in "inline" mode - by activating the `Experts (inline)` plugin. This allows for the use of experts in any mode, such as normal chat.

Expert mode, like agent mode, is a "virtual" mode - you need to select a target mode of operation for it, which can be done in the settings at `Settings / Agent (autonomous) / Sub-mode for experts`.

You can also ask for a list of active experts at any time:

```bash
Give me a list of active experts.
```

# Accessibility

Since version `2.2.8`, PyGPT has added beta support for disabled people and voice control. This may be very useful for blind people.


In the `Config / Accessibility` menu, you can turn on accessibility features such as:


- activating voice control

- translating actions and events on the screen with audio speech

- setting up keyboard shortcuts for actions.


**Using voice control**

Voice control can be turned on in two ways: globally, through settings in `Config -> Accessibility`, and by using the `Voice control (inline)` plugin. Both options let you use the same voice commands, but they work a bit differently - the global option allows you to run commands outside of a conversation, anywhere, while the plugin option lets you execute commands directly during a conversation – allowing you to interact with the model and execute commands at the same time, within the conversation.

In the plugin (inline) option, you can also turn on a special trigger word that will be needed for content to be recognized as a voice command. You can set this up by going to `Plugins -> Settings -> Voice Control (inline)`:

```bash
Magic prefix for voice commands
```

**Tip:** When the voice control is enabled via a plugin, simply provide commands while providing the content of the conversation by using the standard `Microphone` button.


**Enabling voice control globally**


Turn on the voice control option in `Config / Accessibility`:


```bash
Enable voice control (using microphone)
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
Audio notify microphone listening start/stop
```

To enable a sound notification when a voice command is recognized and command execution begins, turn on the option:


```bash
Audio notify voice command execution
```

For voice translation of on-screen events and information about completed commands via speech synthesis, you can turn on the option:

```bash
Use voice synthesis to describe events on the screen.
```

![v2_access](https://github.com/szczyglis-dev/py-gpt/assets/61396542/02dd161b-6fb1-48f9-9217-40c658888833)


# Files and attachments

## Input attachments (upload)

**PyGPT** makes it simple for users to upload files to the server and send them to the model for tasks like analysis, similar to attaching files in `ChatGPT`. There's a separate `Files` tab next to the text input area specifically for managing file uploads. Users can opt to have files automatically deleted after each upload or keep them on the list for repeated use.

![v2_file_input](https://github.com/szczyglis-dev/py-gpt/assets/61396542/bd3d9840-2bc4-4ba8-a603-69724f9eb620)

The attachment feature is available in both the `Assistant` and `Vision` modes at default.
In `Assistant` mode, you can send documents and files to analyze, while in `Vision` mode, you can send images.
In other modes, you can enable attachments by activating the `Vision (inline)` plugin (for providing images only).

## Files (download, code generation)

**PyGPT** enables the automatic download and saving of files created by the model. This is carried out in the background, with the files being saved to an `data` folder located within the user's working directory. To view or manage these files, users can navigate to the `Files` tab which features a file browser for this specific directory. Here, users have the interface to handle all files sent by the AI.

This `data` directory is also where the application stores files that are generated locally by the AI, such as code files or any other data requested from the model. Users have the option to execute code directly from the stored files and read their contents, with the results fed back to the AI. This hands-off process is managed by the built-in plugin system and model-triggered commands. You can also indexing files from this directory (using integrated `Llama-index`) and use it's contents as additional context provided to discussion.

The `Command: Files I/O` plugin takes care of file operations in the `data` directory, while the `Command: Code Interpreter` plugin allows for the execution of code from these files.

![v2_file_output](https://github.com/szczyglis-dev/py-gpt/assets/61396542/2ada219d-68c9-45e3-96af-86ac5bc73593)

To allow the model to manage files or python code execution, the `Execute commands` option must be active, along with the above-mentioned plugins:

![v2_code_execute](https://github.com/szczyglis-dev/py-gpt/assets/61396542/d5181eeb-6ab4-426f-93f0-037d256cb078)

# Draw (paint)

Using the `Draw` tool, you can create quick sketches and submit them to the model for analysis. You can also edit opened from disk or captured from camera images, for example, by adding elements like arrows or outlines to objects. Additionally, you can capture screenshots from the system - the captured image is placed in the drawing tool and attached to the query being sent.

![v2_draw](https://github.com/szczyglis-dev/py-gpt/assets/61396542/09c1de36-1241-4330-9fd7-67c6e09888fa)

To capture the screenshot just click on the `Ask with screenshot` option in a tray-icon dropdown:

![v2_screenshot](https://github.com/szczyglis-dev/py-gpt/assets/61396542/7305a814-ca76-4f8f-8908-47f6a9496fa5)

# Calendar

Using the calendar, you can go back to selected conversations from a specific day and add daily notes. After adding a note, it will be marked on the list, and you can change the color of its label by right-clicking and selecting `Set label color`. By clicking on a particular day of the week, conversations from that day will be displayed.

![v2_calendar](https://github.com/szczyglis-dev/py-gpt/assets/61396542/c7d17375-b61f-452c-81bc-62a7d466fc18)

# Context and memory

## Short and long-term memory

**PyGPT** features a continuous chat mode that maintains a long context of the ongoing dialogue. It preserves the entire conversation history and automatically appends it to each new message (prompt) you send to the AI. Additionally, you have the flexibility to revisit past conversations whenever you choose. The application keeps a record of your chat history, allowing you to resume discussions from the exact point you stopped.

## Handling multiple contexts

On the left side of the application interface, there is a panel that displays a list of saved conversations. You can save numerous contexts and switch between them with ease. This feature allows you to revisit and continue from any point in a previous conversation. **PyGPT** automatically generates a summary for each context, akin to the way `ChatGPT` operates and gives you the option to modify these titles itself.

![v2_context_list](https://github.com/szczyglis-dev/py-gpt/assets/61396542/9228ea4c-f30c-4b02-ba85-da10b4e2eb7b)

You can disable context support in the settings by using the following option:

``` ini
Config -> Settings -> Use context 
```

## Clearing history

You can clear the entire memory (all contexts) by selecting the menu option:

``` ini
File -> Clear history...
```

## Context storage

On the application side, the context is stored in the `SQLite` database located in the working directory (`db.sqlite`).
In addition, all history is also saved to `.txt` files for easy reading.

Once a conversation begins, a title for the chat is generated and displayed on the list to the left. This process is similar to `ChatGPT`, where the subject of the conversation is summarized, and a title for the thread is created based on that summary. You can change the name of the thread at any time.

# Presets

## What is preset?

Presets in **PyGPT** are essentially templates used to store and quickly apply different configurations. Each preset includes settings for the mode you want to use (such as chat, completion, or image generation), an initial system message, an assigned name for the AI, a username for the session, and the desired "temperature" for the conversation. A warmer "temperature" setting allows the AI to provide more creative responses, while a cooler setting encourages more predictable replies. These presets can be used across various modes and with models accessed via the `OpenAI API` or `Langchain`.

The system lets you create as many presets as needed and easily switch among them. Additionally, you can clone an existing preset, which is useful for creating variations based on previously set configurations and experimentation.

![v2_preset](https://github.com/szczyglis-dev/py-gpt/assets/61396542/88167631-feb6-45ca-a006-25a21ec2339e)

## Example usage

The application includes several sample presets that help you become acquainted with the mechanism of their use.


# Image generation (DALL-E 3 and DALL-E 2)

## DALL-E 3

**PyGPT** enables quick and easy image creation with `DALL-E 3`. 
The older model version, `DALL-E 2`, is also accessible. Generating images is akin to a chat conversation  -  a user's prompt triggers the generation, followed by downloading, saving to the computer, 
and displaying the image onscreen. You can send raw prompt to `DALL-E` in `Image generation` mode or ask the model for the best prompt.

Image generation using DALL-E is available in every mode via plugin `DALL-E 3 Image Generation (inline)`. Just ask any model, in any mode, like e.g. GPT-4 to generate an image and it will do it inline, without need to mode change.

If you want to generate images (using DALL-E) directly in chat you must enable plugin **DALL-E 3 Inline** in the Plugins menu.
Plugin allows you to generate images in Chat mode:

![v3_img_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/c288a4b3-c932-4201-b5a3-8452aea49817)

## Multiple variants

You can generate up to **4 different variants** (DALL-E 2) for a given prompt in one session. DALL-E 3 allows one image.
To select the desired number of variants to create, use the slider located in the right-hand corner at 
the bottom of the screen. This replaces the conversation temperature slider when you switch to image generation mode.

## Raw mode

There is an option for switching prompt generation mode.

If **Raw Mode** is enabled, DALL-E will receive the prompt exactly as you have provided it.
If **Raw Mode** is disabled, GPT will generate the best prompt for you based on your instructions.

![v2_dalle2](https://github.com/szczyglis-dev/py-gpt/assets/61396542/e1c30292-8ed0-4346-8b85-6d7a02d65fb6)

## Image storage

Once you've generated an image, you can easily save it anywhere on your disk by right-clicking on it. 
You also have the options to delete it or view it in full size in your web browser.

**Tip:** Use presets to save your prepared prompts. 
This lets you quickly use them again for generating new images later on.

The app keeps a history of all your prompts, allowing you to revisit any session and reuse previous 
prompts for creating new images.

Images are stored in ``img`` directory in **PyGPT** user data folder.

# Managing models

All models are specified in the configuration file `models.json`, which you can customize. 
This file is located in your working directory. You can add new models provided directly by `OpenAI API`
and those supported by `Langchain` and `Llama-index` to this file. Configuration for Langchain wrapper is placed in `langchain` key.

## Adding custom LLMs via Langchain and Llama-index

To add a new model using the Langchain or Llama-index wrapper in **PyGPT**, insert the model's configuration details into the `models.json` file. This should include the model's name, its supported modes (either `chat`, `completion`, or both), the LLM provider (which can be either e.g. `OpenAI` or `HuggingFace`), and, if you are using a `HuggingFace` model, an optional `API KEY`.

Example of models configuration - `models.json`:

```
"gpt-3.5-turbo": {
    "id": "gpt-3.5-turbo",
    "name": "gpt-3.5-turbo",
    "mode": [
        "chat",
        "assistant",
        "langchain",
        "llama_index"
    ],
    "langchain": {
        "provider": "openai",
        "mode": [
            "chat"
        ],
        "args": [
            {
                "name": "model_name",
                "value": "gpt-3.5-turbo",
                "type": "str"
            }
        ],
        "env": [
            {
                "name": "OPENAI_API_KEY",
                "value": "{api_key}"
            }
        ]
    },
    "llama_index": {
        "provider": "openai",
        "mode": [
            "chat"
        ],
        "args": [
            {
                "name": "model",
                "value": "gpt-3.5-turbo",
                "type": "str"
            }
        ],
        "env": [
            {
                "name": "OPENAI_API_KEY",
                "value": "{api_key}"
            }
        ]
    },
    "ctx": 4096,
    "tokens": 4096,
    "default": false
},
```

There is built-in support for those LLMs providers:

```
- OpenAI (openai)
- Azure OpenAI (azure_openai)
- Google (google)
- HuggingFace (huggingface)
- Anthropic (anthropic)
- Ollama (ollama)
```

## Using other models (non-GPT)


### Llama 3, Mistral, and other local models

How to use locally installed Llama 3 or Mistral models:

1) Choose a working mode: `Chat with files` or `Langchain`.

2) On the models list - select, edit, or add a new model (with `ollama` provider). You can edit the model settings through the right mouse button click -> `Edit`, then configure the model parameters in the `advanced` section.

3) Download and install Ollama from here: https://github.com/ollama/ollama

For example, on Linux:

```curl -fsSL https://ollama.com/install.sh | sh```

4) Run the model (e.g. Llama 3) locally on your machine. For example, on Linux:

```ollama run llama3.1```

5) Return to PyGPT and select the correct model from models list to chat with selected model using Ollama running locally.

**Example available models**

- llama3.1
- codellama
- mistral
- llama2-uncensored

You can add more models by editing the models list.

**List of all models supported by Ollama**

https://ollama.com/library

https://github.com/ollama/ollama

**IMPORTANT:** Remember to define the correct model name in the **kwargs list in the model settings.

**Using local embedding models**

Refer to: https://docs.llamaindex.ai/en/stable/examples/embeddings/ollama_embedding/

You can use an Ollama instance for embeddings. Simply select the `ollama` provider in:

```Config -> Settings -> Indexes (llama-index) -> Embeddings -> Embeddings provider```

Define parameters like model name and Ollama base URL in the Embeddings provider **kwargs list, e.g.:

- name: `model_name`, value: `llama3.1`, type: `str`

- name: `base_url`, value: `http://localhost:11434`, type: `str`

### Google Gemini and Anthropic Claude

To use `Gemini` or `Claude` models, select the `Chat with files` mode in PyGPT and select a predefined model.
Remember to configure the required parameters like API keys in the model ENV config fields (RMB click on the model name and select `Edit`).

**Google Gemini**

Required ENV:

- GOOGLE_API_KEY

Required **kwargs:

- model

**Anthropic Claude**

Required ENV:

- ANTHROPIC_API_KEY

Required **kwargs:

- model

## Adding custom LLM providers

Handling LLMs with Langchain and Llama-index is implemented through separated wrappers. This allows for the addition of support for any provider and model available via Langchain or Llama-index. All built-in wrappers for the models and its providers are placed in the `pygpt_net.provider.llms`.

These wrappers are loaded into the application during startup using `launcher.add_llm()` method:

```python
# app.py

from pygpt_net.provider.llms.openai import OpenAILLM
from pygpt_net.provider.llms.azure_openai import AzureOpenAILLM
from pygpt_net.provider.llms.anthropic import AnthropicLLM
from pygpt_net.provider.llms.hugging_face import HuggingFaceLLM
from pygpt_net.provider.llms.ollama import OllamaLLM
from pygpt_net.provider.llms.google import GoogleLLM


def run(**kwargs):
    """Runs the app."""
    # Initialize the app
    launcher = Launcher()
    launcher.init()

    # Register plugins
    ...

    # Register langchain and llama-index LLMs wrappers
    launcher.add_llm(OpenAILLM())
    launcher.add_llm(AzureOpenAILLM())
    launcher.add_llm(AnthropicLLM())
    launcher.add_llm(HuggingFaceLLM())
    launcher.add_llm(OllamaLLM())
    launcher.add_llm(GoogleLLM())

    # Launch the app
    launcher.run()
```

To add support for providers not included by default, you can create your own wrapper that returns a custom model to the application and then pass this custom wrapper to the launcher.

Extending **PyGPT** with custom plugins and LLM wrappers is straightforward:

- Pass instances of custom plugins and LLM wrappers directly to the launcher.

To register custom LLM wrappers:

- Provide a list of LLM wrapper instances as `llms` keyword argument.

**Example:**


```python
# launcher.py

from pygpt_net.app import run
from plugins import CustomPlugin, OtherCustomPlugin
from llms import CustomLLM

plugins = [
    CustomPlugin(),
    OtherCustomPlugin(),
]
llms = [
    CustomLLM(),  # <--- custom LLM provider (wrapper)
]
vector_stores = []

run(
    plugins=plugins, 
    llms=llms, 
    vector_stores=vector_stores,
)
```

**Examples (tutorial files)** 

See the `examples` directory in this repository with examples of custom launcher, plugin, vector store, LLM (Langchain and Llama-index) provider and data loader:

- `examples/custom_launcher.py`

- `examples/example_audio_input.py`

- `examples/example_audio_output.py`

- `examples/example_data_loader.py`

- `examples/example_llm.py`  <-- use it as an example

- `examples/example_plugin.py`

- `examples/example_vector_store.py`

- `examples/example_web_search.py`

These example files can be used as a starting point for creating your own extensions for **PyGPT**.

To integrate your own model or provider into **PyGPT**, you can also reference the classes located in the `pygpt_net.provider.llms`. These samples can act as an more complex example for your custom class. Ensure that your custom wrapper class includes two essential methods: `chat` and `completion`. These methods should return the respective objects required for the model to operate in `chat` and `completion` modes.

Every single LLM provider (wrapper) inherits from `BaseLLM` class and can provide 3 components: provider for Langchain, provider for Llama-index, and provider for Embeddings.


## Adding custom Vector Store providers

**From version 2.0.114 you can also register your own Vector Store provider**:

```python
# app.py

# vector stores
from pygpt_net.provider.vector_stores.chroma import ChromaProvider
from pygpt_net.provider.vector_stores.elasticsearch import ElasticsearchProvider
from pygpt_net.provider.vector_stores.pinecode import PinecodeProvider
from pygpt_net.provider.vector_stores.redis import RedisProvider
from pygpt_net.provider.vector_stores.simple import SimpleProvider

def run(**kwargs):
    # ...
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

    # ...
```

To register your custom vector store provider just register it by passing provider instance in `vector_stores` keyword argument:

```python

# custom_launcher.py

from pygpt_net.app import run
from plugins import CustomPlugin, OtherCustomPlugin
from llms import CustomLLM
from vector_stores import CustomVectorStore

plugins = [
    CustomPlugin(),
    OtherCustomPlugin(),
]
llms = [
    CustomLLM(),
]
vector_stores = [
    CustomVectorStore(),  # <--- custom vector store provider
]

run(
    plugins=plugins,
    llms=llms,
    vector_stores=vector_stores,
)
```

# Plugins

**PyGPT** can be enhanced with plugins to add new features.

**Tip:** Plugins works best with GPT-4 models.

The following plugins are currently available, and model can use them instantly:

- `Audio Input` - provides speech recognition.

- `Audio Output` - provides voice synthesis.

- `Autonomous Agent (inline)` - enables autonomous conversation (AI to AI), manages loop, and connects output back to input. This is the inline Agent mode.

- `Chat with files (Llama-index, inline)` - plugin integrates `Llama-index` storage in any chat and provides additional knowledge into context (from indexed files and previous context from database).

- `Command: API calls` - plugin lets you connect the model to the external services using custom defined API calls.

- `Command: Code Interpreter` - responsible for generating and executing Python code, functioning much like 
the Code Interpreter on ChatGPT, but locally. This means GPT can interface with any script, application, or code. 
The plugin can also execute system commands, allowing GPT to integrate with your operating system. 
Plugins can work in conjunction to perform sequential tasks; for example, the `Files` plugin can write generated 
Python code to a file, which the `Code Interpreter` can execute it and return its result to GPT.

- `Command: Custom Commands` - allows you to create and execute custom commands on your system.

- `Command: Files I/O` - provides access to the local filesystem, enabling GPT to read and write files, 
as well as list and create directories.

- `Command: Mouse and Keyboard` - provides the ability to control the mouse and keyboard by the model.

- `Command: Web Search` - provides the ability to connect to the Web, search web pages for current data, and index external content using Llama-index data loaders.

- `Command: Serial port / USB` - plugin provides commands for reading and sending data to USB ports.

- `Context history (calendar, inline)` - provides access to context history database.

- `Crontab / Task scheduler` - plugin provides cron-based job scheduling - you can schedule tasks/prompts to be sent at any time using cron-based syntax for task setup.

- `DALL-E 3: Image Generation (inline)` - integrates DALL-E 3 image generation with any chat and mode. Just enable and ask for image in Chat mode, using standard model like GPT-4. The plugin does not require the `Execute commands` option to be enabled.

- `Experts (inline)` - allows calling experts in any chat mode. This is the inline Experts (co-op) mode.

- `GPT-4 Vision (inline)` - integrates Vision capabilities with any chat mode, not just Vision mode. When the plugin is enabled, the model temporarily switches to vision in the background when an image attachment or vision capture is provided.

- `Real Time` - automatically appends the current date and time to the system prompt, informing the model about current time.

- `System Prompt Extra (append)` - appends additional system prompts (extra data) from a list to every current system prompt. You can enhance every system prompt with extra instructions that will be automatically appended to the system prompt.

- `Voice Control (inline)` - provides voice control command execution within a conversation.


## Audio Input

The plugin facilitates speech recognition (by default using the `Whisper` model from OpenAI, `Google` and `Bing` are also available). It allows for voice commands to be relayed to the AI using your own voice. Whisper doesn't require any extra API keys or additional configurations; it uses the main OpenAI key. In the plugin's configuration options, you should adjust the volume level (min energy) at which the plugin will respond to your microphone. Once the plugin is activated, a new `Speak` option will appear at the bottom near the `Send` button  -  when this is enabled, the application will respond to the voice received from the microphone.

The plugin can be extended with other speech recognition providers.

Options:

- `Provider` *provider*

Choose the provider. *Default:* `Whisper`

Available providers:

- Whisper (via `OpenAI API`)
- Whisper (local model) - not available in compiled and Snap versions, only Python/PyPi version
- Google (via `SpeechRecognition` library)
- Google Cloud (via `SpeechRecognition` library)
- Microsoft Bing (via `SpeechRecognition` library)

**Whisper (API)**

- `Model` *whisper_model*

Choose the model. *Default:* `whisper-1`

**Whisper (local)**

- `Model` *whisper_local_model*

Choose the local model. *Default:* `base`

Available models: https://github.com/openai/whisper

**Google**

- `Additional keywords arguments` *google_args*

Additional keywords arguments for r.recognize_google(audio, **kwargs)

**Google Cloud**

- `Additional keywords arguments` *google_cloud_args*

Additional keywords arguments for r.recognize_google_cloud(audio, **kwargs)

**Bing**

- `Additional keywords arguments` *bing_args*

Additional keywords arguments for r.recognize_bing(audio, **kwargs)


**General options**

- `Auto send` *auto_send*

Automatically send recognized speech as input text after recognition. *Default:* `True`

- `Advanced mode` *advanced*

Enable only if you want to use advanced mode and the settings below. Do not enable this option if you just want to use the simplified mode (default). *Default:* `False`


**Advanced mode options**

- `Timeout` *timeout*

The duration in seconds that the application waits for voice input from the microphone. *Default:* `5`

- `Phrase max length` *phrase_length*

Maximum duration for a voice sample (in seconds). *Default:* `10`

- `Min energy` *min_energy*

Minimum threshold multiplier above the noise level to begin recording. *Default:* `1.3`

- `Adjust for ambient noise` *adjust_noise*

Enables adjustment to ambient noise levels. *Default:* `True`

- `Continuous listen` *continuous_listen*

Experimental: continuous listening - do not stop listening after a single input. 
Warning: This feature may lead to unexpected results and requires fine-tuning with 
the rest of the options! If disabled, listening must be started manually 
by enabling the `Speak` option. *Default:* `False`


- `Wait for response` *wait_response*

Wait for a response before initiating listening for the next input. *Default:* `True`

- `Magic word` *magic_word*

Activate listening only after the magic word is provided. *Default:* `False`

- `Reset Magic word` *magic_word_reset*

Reset the magic word status after it is received (the magic word will need to be provided again). *Default:* `True`

- `Magic words` *magic_words*

List of magic words to initiate listening (Magic word mode must be enabled). *Default:* `OK, Okay, Hey GPT, OK GPT`

- `Magic word timeout` *magic_word_timeout*

The number of seconds the application waits for magic word. *Default:* `1`

- `Magic word phrase max length` *magic_word_phrase_length*

The minimum phrase duration for magic word. *Default:* `2`

- `Prefix words` *prefix_words*

List of words that must initiate each phrase to be processed. For example, you can define words like "OK" or "GPT"—if set, any phrases not starting with those words will be ignored. Insert multiple words or phrases separated by commas. Leave empty to deactivate.  *Default:* `empty`

- `Stop words` *stop_words*

List of words that will stop the listening process. *Default:* `stop, exit, quit, end, finish, close, terminate, kill, halt, abort`

Options related to Speech Recognition internals:

- `energy_threshold` *recognition_energy_threshold*

Represents the energy level threshold for sounds. *Default:* `300`

- `dynamic_energy_threshold` *recognition_dynamic_energy_threshold*

Represents whether the energy level threshold (see recognizer_instance.energy_threshold) for sounds 
should be automatically adjusted based on the currently ambient noise level while listening. *Default:* `True`

- `dynamic_energy_adjustment_damping` *recognition_dynamic_energy_adjustment_damping*

Represents approximately the fraction of the current energy threshold that is retained after one second 
of dynamic threshold adjustment. *Default:* `0.15`

- `pause_threshold` *recognition_pause_threshold*

Represents the minimum length of silence (in seconds) that will register as the end of a phrase. *Default:* `0.8`

- `adjust_for_ambient_noise: duration` *recognition_adjust_for_ambient_noise_duration*

The duration parameter is the maximum number of seconds that it will dynamically adjust the threshold 
for before returning. *Default:* `1`

Options reference: https://pypi.org/project/SpeechRecognition/1.3.1/

## Audio Output

The plugin lets you turn text into speech using the TTS model from OpenAI or other services like ``Microsoft Azure``, ``Google``, and ``Eleven Labs``. You can add more text-to-speech providers to it too. `OpenAI TTS` does not require any additional API keys or extra configuration; it utilizes the main OpenAI key. 
Microsoft Azure requires to have an Azure API Key. Before using speech synthesis via `Microsoft Azure`, `Google` or `Eleven Labs`, you must configure the audio plugin with your API keys, regions and voices if required.

![v2_azure](https://github.com/szczyglis-dev/py-gpt/assets/61396542/8035e9a5-5a01-44a1-85da-6e44c52459e4)

Through the available options, you can select the voice that you want the model to use. More voice synthesis providers coming soon.

To enable voice synthesis, activate the `Audio Output` plugin in the `Plugins` menu or turn on the `Audio Output` option in the `Audio / Voice` menu (both options in the menu achieve the same outcome).

**Options**

- `Provider` *provider*

Choose the provider. *Default:* `OpenAI TTS`

Available providers:

- OpenAI TTS
- Microsoft Azure TTS
- Google TTS
- Eleven Labs TTS

**OpenAI Text-To-Speech**

- `Model` *openai_model*

Choose the model. Available options:

```
  - tts-1
  - tts-1-hd
```
*Default:* `tts-1`

- `Voice` *openai_voice*

Choose the voice. Available voices to choose from:

```
  - alloy
  - echo
  - fable
  - onyx
  - nova
  - shimmer
```

*Default:* `alloy`

**Microsoft Azure Text-To-Speech**

- `Azure API Key` *azure_api_key*

Here, you should enter the API key, which can be obtained by registering for free on the following website: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech

- `Azure Region` *azure_region*

You must also provide the appropriate region for Azure here. *Default:* `eastus`

- `Voice (EN)` *azure_voice_en*

Here you can specify the name of the voice used for speech synthesis for English. *Default:* `en-US-AriaNeural`

- `Voice (non-English)` *azure_voice_pl*

Here you can specify the name of the voice used for speech synthesis for other non-english languages. *Default:* `pl-PL-AgnieszkaNeural`

**Google Text-To-Speech**

- `Google Cloud Text-to-speech API Key` *google_api_key*

You can obtain your own API key at: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com

- `Voice` *google_voice*

Specify voice. Voices: https://cloud.google.com/text-to-speech/docs/voices

- `Language code` *google_api_key*

Language code. Language codes: https://cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages

**Eleven Labs Text-To-Speech**

- `Eleven Labs API Key` *eleven_labs_api_key*

You can obtain your own API key at: https://elevenlabs.io/speech-synthesis

- `Voice ID` *eleven_labs_voice*

Voice ID. Voices: https://elevenlabs.io/voice-library

- `Model` *eleven_labs_model*

Specify model. Models: https://elevenlabs.io/docs/speech-synthesis/models


If speech synthesis is enabled, a voice will be additionally generated in the background while generating a response via GPT.

Both `OpenAI TTS` and `OpenAI Whisper` use the same single API key provided for the OpenAI API, with no additional keys required.

## Autonomous Agent (inline)

**WARNING: Please use autonomous mode with caution!** - this mode, when connected with other plugins, may produce unexpected results!

The plugin activates autonomous mode in standard chat modes, where AI begins a conversation with itself. 
You can set this loop to run for any number of iterations. Throughout this sequence, the model will engage
in self-dialogue, answering his own questions and comments, in order to find the best possible solution, subjecting previously generated steps to criticism.

This mode is similar to `Auto-GPT` - it can be used to create more advanced inferences and to solve problems by breaking them down into subtasks that the model will autonomously perform one after another until the goal is achieved. The plugin is capable of working in cooperation with other plugins, thus it can utilize tools such as web search, access to the file system, or image generation using `DALL-E`.

You can adjust the number of iterations for the self-conversation in the `Plugins / Settings...` menu under the following option:

- `Iterations` *iterations*

*Default:* `3`

**WARNING**: Setting this option to `0` activates an **infinity loop** which can generate a large number of requests and cause very high token consumption, so use this option with caution!

- `Prompts` *prompts*

Editable list of prompts used to instruct how to handle autonomous mode, you can create as many prompts as you want. 
First active prompt on list will be used to handle autonomous mode. **INFO:** At least one active prompt is required!

- `Auto-stop after goal is reached` *auto_stop*

If enabled, plugin will stop after goal is reached." *Default:* `True`

- `Reverse roles between iterations` *reverse_roles*

Only for Completion/Langchain modes. 
If enabled, this option reverses the roles (AI <> user) with each iteration. For example, 
if in the previous iteration the response was generated for "Batman," the next iteration will use that 
response to generate an input for "Joker." *Default:* `True`

## Chat with files (Llama-index, inline)

Plugin integrates `Llama-index` storage in any chat and provides additional knowledge into context.

- `Ask Llama-index first` *ask_llama_first*

When enabled, then `Llama-index` will be asked first, and response will be used as additional knowledge in prompt. When disabled, then `Llama-index` will be asked only when needed. **INFO: Disabled in autonomous mode (via plugin)!** *Default:* `False`

- `Auto-prepare question before asking Llama-index first` *prepare_question*

When enabled, then question will be prepared before asking Llama-index first to create best query. *Default:* `False`

- `Model for question preparation` *model_prepare_question*

Model used to prepare question before asking Llama-index. *Default:* `gpt-3.5-turbo`

- `Max output tokens for question preparation` *prepare_question_max_tokens*

Max tokens in output when preparing question before asking Llama-index. *Default:* `500`

- `Prompt for question preparation` *syntax_prepare_question*

System prompt for question preparation.

- `Max characters in question` *max_question_chars*

Max characters in question when querying Llama-index, 0 = no limit. *Default:* `1000`

- `Append metadata to context` *append_meta*

If enabled, then metadata from Llama-index will be appended to additional context. *Default:* `False`

- `Model` *model_query*

Model used for querying `Llama-index`. *Default:* `gpt-3.5-turbo`

- `Indexes IDs` *idx*

Indexes to use. If you want to use multiple indexes at once then separate them by comma. *Default:* `base`


## Command: API calls

**PyGPT** lets you connect the model to the external services using custom defined API calls.

To activate this feature, turn on the `Command: API calls` plugin found in the `Plugins` menu.

In this plugin you can provide list of allowed API calls, their parameters and request types. The model will replace provided placeholders with required params and make API call to external service.

- `Your custom API calls` *cmds*

You can provide custom API calls on the list here.

Params to specify for API call:

- **Enabled** (True / False)
- **Name:** unique API call name (ID)
- **Instruction:** description for model when and how to use this API call
- **GET params:** list, separated by comma, GET params to append to endpoint URL
- **POST params:** list, separated by comma, POST params to send in POST request
- **POST JSON:** provide the JSON object, template to send in POST JSON request, use `%param%` as POST param placeholders
- **Headers:** provide the JSON object with dictionary of extra request headers, like Authorization, API keys, etc.
- **Request type:** use GET for basic GET request, POST to send encoded POST params or POST_JSON to send JSON-encoded object as body
- **Endpoint:** API endpoint URL, use `{param}` as GET param placeholders

An example API call is provided with plugin by default, it calls the Wikipedia API:

- Name: `search_wiki`
- Instructiom: `send API call to Wikipedia to search pages by query`
- GET params: `query, limit`
- Type: `GET`
- API endpoint: https://en.wikipedia.org/w/api.php?action=opensearch&limit={limit}&format=json&search={query}

In the above example, every time you ask the model for query Wiki for provided query (e.g. `Call the Wikipedia API for query: Nikola Tesla`) it will replace placeholders in provided API endpoint URL with a generated query and it will call prepared API endpoint URL, like below:

https://en.wikipedia.org/w/api.php?action=opensearch&limit=5&format=json&search=Nikola%20Tesla

You can specify type of request: `GET`, `POST` and `POST JSON`.

In the `POST` request you can provide POST params, they will be encoded and send as POST data.

In the `POST JSON` request you must provide JSON object template to be send, using `%param%` placeholders in the JSON object to be replaced with the model.

You can also provide any required credentials, like Authorization headers, API keys, tokens, etc. using the `headers` field - you can provide a JSON object here with a dictionary `key => value` - provided JSON object will be converted to headers dictonary and send with the request.

- `Disable SSL verify` *disable_ssl*

Disables SSL verification when making requests. *Default:* `False`

- `Timeout` *timeout*

Connection timeout (seconds). *Default:* `5`

- `User agent` *user_agent*

User agent to use when making requests. *Default:* `Mozilla/5.0`


## Command: Code Interpreter

### Executing Code

From version `2.4.13` with built-in `IPython`.

The plugin operates similarly to the `Code Interpreter` in `ChatGPT`, with the key difference that it works locally on the user's system. It allows for the execution of any Python code on the computer that the model may generate. When combined with the `Command: Files I/O` plugin, it facilitates running code from files saved in the `data` directory. You can also prepare your own code files and enable the model to use them or add your own plugin for this purpose. You can execute commands and code on the host machine or in Docker container.

**IPython:** Starting from version `2.4.13`, it is highly recommended to adopt the new option: `IPython`, which offers significant improvements over previous workflows. IPython provides a robust environment for executing code within a kernel, allowing you to maintain the state of your session by preserving the results of previous commands. This feature is particularly useful for iterative development and data analysis, as it enables you to build upon prior computations without starting from scratch. Moreover, IPython supports the use of magic commands, such as `!pip install <package_name>`, which facilitate the installation of new packages directly within the session. This capability streamlines the process of managing dependencies and enhances the flexibility of your development environment. Overall, IPython offers a more efficient and user-friendly experience for executing and managing code.

To use IPython, Docker must be installed on your system. 

You can find the installation instructions here: https://docs.docker.com/engine/install/

**Tip: connecting IPython in Docker in Snap version**:

To use IPython in the Snap version, you must connect PyGPT to the Docker daemon (built into the Snap package):

```commandline
sudo snap connect pygpt:docker-executables docker:docker-executables
```

````commandline
sudo snap connect pygpt:docker docker:docker-daemon
````


**Code interpreter:** a real-time Python code interpreter is built-in. Click the `<>` icon to open the interpreter window. Both the input and output of the interpreter are connected to the plugin. Any output generated by the executed code will be displayed in the interpreter. Additionally, you can request the model to retrieve contents from the interpreter window output.

![v2_python](https://github.com/szczyglis-dev/py-gpt/assets/61396542/793e554c-7619-402a-8370-ab89c7464fec)

### Executing system commands

Another feature is the ability to execute system commands and return their results. With this functionality, the plugin can run any system command, retrieve the output, and then feed the result back to the model. When used with other features, this provides extensive integration capabilities with the system.


**Tip:** always remember to enable the `Execute commands` option to allow execute commands from the plugins.


**Options:**

**General**

- `Auto-append CWD to sys_exec` *auto_cwd*

Automatically append current working directory to `sys_exec` command. *Default:* `True`

- `Connect to the Python code interpreter window` *attach_output*

Automatically attach code input/output to the Python code interpreter window. *Default:* `True`

- `Enable: sys_exec` *cmd.sys_exec*

Allows `sys_exec` command execution. If enabled, provides system commands execution. *Default:* `True`

- `Enable: get_python_output` *cmd.get_python_output*

Allows `get_python_output` command execution. If enabled, it allows retrieval of the output from the Python code interpreter window. *Default:* `True`

- `Enable: get_python_input` *cmd.get_python_input*

Allows `get_python_input` command execution. If enabled, it allows retrieval all input code (from edit section) from the Python code interpreter window. *Default:* `True`

- `Enable: clear_python_output` *cmd.clear_python_output*

Allows `clear_python_output` command execution. If enabled, it allows clear the output of the Python code interpreter window. *Default:* `True`


**IPython**

- `Dockerfile` *ipython_dockerfile*

You can customize the Dockerfile for the image used by IPython by editing the configuration above and rebuilding the image via Tools -> Rebuild IPython Docker Image.

- `Session Key` *ipython_session_key*

It must match the key provided in the Dockerfile.

- `Docker image name` *ipython_image_name*

Custom image name

- `Docker container name` *ipython_container_name*

Custom container name

- `Connection address` *ipython_conn_addr*

Default: 127.0.0.1

- `Port: shell` *ipython_port_shell*

Default: 5555

- `Port: iopub` *ipython_port_iopub*

Default: 5556

- `Port: stdin` *ipython_port_stdin*

Default: 5557

- `Port: control` *ipython_port_control*

Default: 5558

- `Port: hb` *ipython_port_hb*

Default: 5559


- `Enable: ipython_execute` *cmd.ipython_execute*

Allows Python code execution in IPython interpreter (in current kernel). *Default:* `True`

- `Enable: ipython_execute_new` *cmd.ipython_execute_new*

Allows Python code execution in IPython interpreter (in new kernel). *Default:* `True`

- `Enable: python_kernel_restart` *cmd.ipython_kernel_restart*

Allows to restart IPython kernel. *Default:* `True`



**Python (legacy)**

- `Python command template` *python_cmd_tpl*

Python command template (use {filename} as path to file placeholder). *Default:* `python3 {filename}`

- `Enable: code_execute` *cmd.code_execute*

Allows `code_execute` command execution. If enabled, provides Python code execution (generate and execute from file). *Default:* `True`

- `Enable: code_execute_all` *cmd.code_execute_all*

Allows `code_execute_all` command execution. If enabled, provides execution of all the Python code in interpreter window. *Default:* `True`

- `Enable: code_execute_file` *cmd.code_execute_file*

Allows `code_execute_file` command execution. If enabled, provides Python code execution from existing .py file. *Default:* `True`


**HTML Canvas**

- `Enable: render_html_output` *cmd.render_html_output*

Allows `render_html_output` command execution. If enabled, it allows to render HTML/JS code in built-it HTML/JS browser (HTML Canvas). *Default:* `True`

- `Enable: get_html_output` *cmd.get_html_output*

Allows `get_html_output` command execution. If enabled, it allows retrieval current output from HTML Canvas. *Default:* `True`

- `Sandbox (docker container)` *sandbox_docker*

Execute commands in sandbox (docker container). Docker must be installed and running. *Default:* `False`

- `Docker image` *sandbox_docker_image*

Docker image to use for sandbox *Default:* `python:3.8-alpine`



## Command: Custom Commands

With the `Custom Commands` plugin, you can integrate **PyGPT** with your operating system and scripts or applications. You can define an unlimited number of custom commands and instruct GPT on when and how to execute them. Configuration is straightforward, and **PyGPT** includes a simple tutorial command for testing and learning how it works:

![v2_custom_cmd](https://github.com/szczyglis-dev/py-gpt/assets/61396542/b30b8724-9ca1-44b1-abc7-78241588e1f6)

To add a new custom command, click the **ADD** button and then:

1. Provide a name for your command: this is a unique identifier for GPT.
2. Provide an `instruction` explaining what this command does; GPT will know when to use the command based on this instruction.
3. Define `params`, separated by commas - GPT will send data to your commands using these params. These params will be placed into placeholders you have defined in the `cmd` field. For example:

If you want instruct GPT to execute your Python script named `smart_home_lights.py` with an argument, such as `1` to turn the light ON, and `0` to turn it OFF, define it as follows:

- **name**: lights_cmd
- **instruction**: turn lights on/off; use 1 as 'arg' to turn ON, or 0 as 'arg' to turn OFF
- **params**: arg
- **cmd**: `python /path/to/smart_home_lights.py {arg}`

The setup defined above will work as follows:

When you ask GPT to turn your lights ON, GPT will locate this command and prepare the command `python /path/to/smart_home_lights.py {arg}` with `{arg}` replaced with `1`. On your system, it will execute the command:

```python /path/to/smart_home_lights.py 1```

And that's all. GPT will take care of the rest when you ask to turn ON the lights.

You can define as many placeholders and parameters as you desire.

Here are some predefined system placeholders for use:

- `{_time}` - current time in `H:M:S` format
- `{_date}` - current date in `Y-m-d` format
- `{_datetime}` - current date and time in `Y-m-d H:M:S` format
- `{_file}` - path to the file from which the command is invoked
- `{_home}` - path to **PyGPT**'s home/working directory

You can connect predefined placeholders with your own params.

*Example:*

- **name**: song_cmd
- **instruction**: store the generated song on hard disk
- **params**: song_text, title
- **cmd**: `echo "{song_text}" > {_home}/{title}.txt`


With the setup above, every time you ask GPT to generate a song for you and save it to the disk, it will:

1. Generate a song.
2. Locate your command.
3. Execute the command by sending the song's title and text.
4. The command will save the song text into a file named with the song's title in the PyGPT working directory.

**Example tutorial command**

**PyGPT** provides simple tutorial command to show how it works, to run it just ask GPT for execute `tutorial test command` and it will show you how it works:

```> please execute tutorial test command```

![v2_custom_cmd_example](https://github.com/szczyglis-dev/py-gpt/assets/61396542/97cbc5b9-0dd9-487e-9182-d9873dea42ab)

## Command: Files I/O

The plugin allows for file management within the local filesystem. It enables the model to create, read, write and query files located in the `data` directory, which can be found in the user's work directory. With this plugin, the AI can also generate Python code files and thereafter execute that code within the user's system.

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
- Indexing files and directories using Llama-index
- Querying files using Llama-index
- Searching for files and directories

If a file being created (with the same name) already exists, a prefix including the date and time is added to the file name.

**Options:**

**General**

- `Enable: send (upload) file as attachment` *cmd.send_file*

Allows `cmd.send_file` command execution. *Default:* `True`

- `Enable: read file` *cmd.read_file*

Allows `read_file` command execution. *Default:* `True`

- `Enable: append to file` *cmd.append_file*

Allows `append_file` command execution. Text-based files only (plain text, JSON, CSV, etc.) *Default:* `True`

- `Enable: save file` *cmd.save_file*

Allows `save_file` command execution. Text-based files only (plain text, JSON, CSV, etc.) *Default:* `True`

- `Enable: delete file` *cmd.delete_file*

Allows `delete_file` command execution. *Default:* `True`

- `Enable: list files (ls)` *cmd.list_files*

Allows `list_dir` command execution. *Default:* `True`

- `Enable: list files in dirs in directory (ls)` *cmd.list_dir*

Allows `mkdir` command execution. *Default:* `True`

- `Enable: downloading files` *cmd.download_file*

Allows `download_file` command execution. *Default:* `True`

- `Enable: removing directories` *cmd.rmdir*

Allows `rmdir` command execution. *Default:* `True`

- `Enable: copying files` *cmd.copy_file*

Allows `copy_file` command execution. *Default:* `True`

- `Enable: copying directories (recursive)` *cmd.copy_dir*

Allows `copy_dir` command execution. *Default:* `True`

- `Enable: move files and directories (rename)` *cmd.move*

Allows `move` command execution. *Default:* `True`

- `Enable: check if path is directory` *cmd.is_dir*

Allows `is_dir` command execution. *Default:* `True`

- `Enable: check if path is file` *cmd.is_file*

Allows `is_file` command execution. *Default:* `True`

- `Enable: check if file or directory exists` *cmd.file_exists*

Allows `file_exists` command execution. *Default:* `True`

- `Enable: get file size` *cmd.file_size*

Allows `file_size` command execution. *Default:* `True`

- `Enable: get file info` *cmd.file_info*

Allows `file_info` command execution. *Default:* `True`

- `Enable: find file or directory` *cmd.find*

Allows `find` command execution. *Default:* `True`

- `Enable: get current working directory` *cmd.cwd*

Allows `cwd` command execution. *Default:* `True`

- `Use data loaders` *use_loaders*

Use data loaders from Llama-index for file reading (`read_file` command). *Default:* `True`

**Indexing**

- `Enable: quick query the file with Llama-index` *cmd.query_file*

Allows `query_file` command execution (in-memory index). If enabled, model will be able to quick index file into memory and query it for data (in-memory index) *Default:* `True`

- `Model for query in-memory index` *model_tmp_query*

Model used for query temporary index for `query_file` command (in-memory index). *Default:* `gpt-3.5-turbo`

- `Enable: indexing files to persistent index` *cmd.file_index*

Allows `file_index` command execution. If enabled, model will be able to index file or directory using Llama-index (persistent index). *Default:* `True`

- `Index to use when indexing files` *idx*

ID of index to use for indexing files (persistent index). *Default:* `base`

- `Auto index reading files` *auto_index*

If enabled, every time file is read, it will be automatically indexed (persistent index). *Default:* `False`

- `Only index reading files` *only_index*

If enabled, file will be indexed without return its content on file read (persistent index). *Default:* `False`


## Command: Mouse And Keyboard

Introduced in version: `2.4.4` (2024-11-09)

**WARNING: Use this plugin with caution - allowing all options gives the model full control over the mouse and keyboard**

The plugin allows for controlling the mouse and keyboard by the model. With this plugin, you can send a task to the model, e.g., "open notepad, type something in it" or "open web browser, do search, find something."

Plugin capabilities include:

- Get mouse cursor position
- Control mouse cursor position
- Control mouse clicks
- Control mouse scroll
- Control the keyboard (pressing keys, typing text)
- Making screenshots

The `Execute commands` option must be enabled to use this plugin.

**Options:**

**General**

- `Prompt` *prompt*

Prompt used to instruct how to control the mouse and keyboard.

- `Enable: Allow mouse movement` *allow_mouse_move*

Allows mouse movement. *Default:* `True`

- `Enable: Allow mouse click` *allow_mouse_click*

Allows mouse click. *Default:* `True`

- `Enable: Allow mouse scroll` *allow_mouse_scroll*

Allows mouse scroll. *Default:* `True`

- `Enable: Allow keyboard key press` *allow_keyboard*

Allows keyboard typing. *Default:* `True`

- `Enable: Allow making screenshots` *allow_screenshot*

Allows making screenshots. *Default:* `True`

- `Enable: mouse_get_pos` *cmd.mouse_get_pos*

Allows `mouse_get_pos` command execution. *Default:* `True`

- `Enable: mouse_set_pos` *cmd.mouse_set_pos*

Allows `mouse_set_pos` command execution. *Default:* `True`

- `Enable: make_screenshot` *cmd.make_screenshot*

Allows `make_screenshot` command execution. *Default:* `True`

- `Enable: mouse_click` *cmd.mouse_click*

Allows `mouse_click` command execution. *Default:* `True`

- `Enable: mouse_move` *cmd.mouse_move*

Allows `mouse_move` command execution. *Default:* `True`

- `Enable: mouse_scroll` *cmd.mouse_scroll*

Allows `mouse_scroll` command execution. *Default:* `True`

- `Enable: keyboard_key` *cmd.keyboard_key*

Allows `keyboard_key` command execution. *Default:* `True`

- `Enable: keyboard_type` *cmd.keyboard_type*

Allows `keyboard_type` command execution. *Default:* `True`


## Command: Web Search

**PyGPT** lets you connect GPT to the internet and carry out web searches in real time as you make queries.

To activate this feature, turn on the `Command: Web Search` plugin found in the `Plugins` menu.

Web searches are provided by `Google Custom Search Engine` and `Microsoft Bing` APIs and can be extended with other search engine providers. 

**Options**

- `Provider` *provider*

Choose the provider. *Default:* `Google`

Available providers:

- Google
- Microsoft Bing

**Google**

To use this provider, you need an API key, which you can obtain by registering an account at:

https://developers.google.com/custom-search/v1/overview

After registering an account, create a new project and select it from the list of available projects:

https://programmablesearchengine.google.com/controlpanel/all

After selecting your project, you need to enable the `Whole Internet Search` option in its settings. 
Then, copy the following two items into **PyGPT**:

- `Api Key`
- `CX ID`

These data must be configured in the appropriate fields in the `Plugins / Settings...` menu:

![v2_plugin_google](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f2e0df62-caaa-40ef-9b1e-239b2f912ec8)

- `Google Custom Search API KEY` *google_api_key*

You can obtain your own API key at https://developers.google.com/custom-search/v1/overview

- `Google Custom Search CX ID` *google_api_cx*

You will find your CX ID at https://programmablesearchengine.google.com/controlpanel/all - remember to enable "Search on ALL internet pages" option in project settings.

**Microsoft Bing**

- `Bing Search API KEY` *bing_api_key*

You can obtain your own API key at https://www.microsoft.com/en-us/bing/apis/bing-web-search-api

- `Bing Search API endpoint` *bing_endpoint*

API endpoint for Bing Search API, default: https://api.bing.microsoft.com/v7.0/search

**General options**

- `Number of pages to search` *num_pages*

Number of max pages to search per query. *Default:* `10`

- `Max content characters` *max_page_content_length*

Max characters of page content to get (0 = unlimited). *Default:* `0`

- `Per-page content chunk size` *chunk_size*

Per-page content chunk size (max characters per chunk). *Default:* `20000`

- `Disable SSL verify` *disable_ssl*

Disables SSL verification when crawling web pages. *Default:* `False`

- `Timeout` *timeout*

Connection timeout (seconds). *Default:* `5`

- `User agent` *user_agent*

User agent to use when making requests. *Default:* `Mozilla/5.0`.

- `Max result length` *max_result_length*

Max length of summarized result (characters). *Default:* `1500`

- `Max summary tokens` *summary_max_tokens*

Max tokens in output when generating summary. *Default:* `1500`

- `Enable: search the Web` *cmd.web_search*

Allows `web_search` command execution. If enabled, model will be able to search the Web. *Default:* `True`

- `Enable: opening URLs` *cmd.web_url_open*

Allows `web_url_open` command execution. If enabled, model will be able to open specified URL and summarize content. *Default:* `True`

- `Enable: reading the raw content from URLs` *cmd.web_url_raw*

Allows `web_url_raw` command execution. If enabled, model will be able to open specified URL and get the raw content. *Default:* `True`

- `Enable: getting a list of URLs from search results` *cmd.web_urls*

Allows `web_urls` command execution. If enabled, model will be able to search the Web and get founded URLs list. *Default:* `True`

- `Enable: indexing web and external content` *cmd.web_index*

Allows `web_index` command execution. If enabled, model will be able to index pages and external content using Llama-index (persistent index). *Default:* `True`

- `Enable: quick query the web and external content` *cmd.web_index_query*

Allows `web_index_query` command execution. If enabled, model will be able to quick index and query web content using Llama-index (in-memory index). *Default:* `True`

- `Auto-index all used URLs using Llama-index` *auto_index*

If enabled, every URL used by the model will be automatically indexed using Llama-index (persistent index). *Default:* `False`

- `Index to use` *idx*

ID of index to use for web page indexing (persistent index). *Default:* `base`

- `Model used for web page summarize` *summary_model*

Model used for web page summarize. *Default:* `gpt-3.5-turbo-1106`

- `Summarize prompt` *prompt_summarize*

Prompt used for web search results summarize, use {query} as a placeholder for search query.

- `Summarize prompt (URL open)` *prompt_summarize_url*

Prompt used for specified URL page summarize.

## Command: Serial port / USB

Provides commands for reading and sending data to USB ports.

**Tip:** in Snap version you must connect the interface first: https://snapcraft.io/docs/serial-port-interface

You can send commands to, for example, an Arduino or any other controllers using the serial port for communication.

![v2_serial](https://github.com/szczyglis-dev/py-gpt/assets/61396542/386d46fa-2e7c-43a6-918c-17eeef9344e0)

Above is an example of co-operation with the following code uploaded to `Arduino Uno` and connected via USB:

```cpp
// example.ino

void setup() {
  Serial.begin(9600);
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    if (input.length() > 0) {
      Serial.println("OK, response for: " + input);
    }
  }
}
```

**Options**

- `USB port` *serial_port*

USB port name, e.g. `/dev/ttyUSB0`, `/dev/ttyACM0`, `COM3`. *Default:* `/dev/ttyUSB0`

- `Connection speed (baudrate, bps)` *serial_bps*

Port connection speed, in bps. *Default:* `9600`

- `Timeout` *timeout*

Timeout in seconds. *Default:* `1`

- `Sleep` *sleep*

Sleep in seconds after connection *Default:* `2`

- `Enable: Send text commands to USB port` *cmd.serial_send*

Allows `serial_send` command execution. *Default:* `True`

- `Enable: Send raw bytes to USB port` *cmd.serial_send_bytes*

Allows `serial_send_bytes` command execution. *Default:* `True`

- `Enable: Read data from USB port` *cmd.serial_read*

Allows `serial_read` command execution. *Default:* `True`

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

You can also use `@` ID tags to automatically use summary of previous contexts in current discussion.
To use context from previous discussion with specified ID use following syntax in your query:

```@123```

Where `123` is the ID of previous context (conversation) in database, example of use:

```Let's talk about discussion @123```


**Options**

- `Enable: using context @ ID tags` *use_tags*

When enabled, it allows to automatically retrieve context history using @ tags, e.g. use @123 in question to use summary of context with ID 123 as additional context. *Default:* `False`

- `Enable: get date range context list` *cmd.get_ctx_list_in_date_range*

Allows `get_ctx_list_in_date_range` command execution. If enabled, it allows getting the list of context history (previous conversations). *Default:* `True

- `Enable: get context content by ID` *cmd.get_ctx_content_by_id*

Allows `get_ctx_content_by_id` command execution. If enabled, it allows getting summarized content of context with defined ID. *Default:* `True`

- `Enable: count contexts in date range` *cmd.count_ctx_in_date*

Allows `count_ctx_in_date` command execution. If enabled, it allows counting contexts in date range. *Default:* `True`

- `Enable: get day note` *cmd.get_day_note*

Allows `get_day_note` command execution. If enabled, it allows retrieving day note for specific date. *Default:* `True`

- `Enable: add day note` *cmd.add_day_note*

Allows `add_day_note` command execution. If enabled, it allows adding day note for specific date. *Default:* `True`

- `Enable: update day note` *cmd.update_day_note*

Allows `update_day_note` command execution. If enabled, it allows updating day note for specific date. *Default:* `True`

- `Enable: remove day note` *cmd.remove_day_note*

Allows `remove_day_note` command execution. If enabled, it allows removing day note for specific date. *Default:* `True`

- `Model` *model_summarize*

Model used for summarize. *Default:* `gpt-3.5-turbo`

- `Max summary tokens` *summary_max_tokens*

Max tokens in output when generating summary. *Default:* `1500`

- `Max contexts to retrieve` *ctx_items_limit*

Max items in context history list to retrieve in one query. 0 = no limit. *Default:* `30`

- `Per-context items content chunk size` *chunk_size*

Per-context content chunk size (max characters per chunk). *Default:* `100000 chars`

**Options (advanced)**

- `Prompt: @ tags (system)` *prompt_tag_system*

Prompt for use @ tag (system).

- `Prompt: @ tags (summary)` *prompt_tag_summary*

Prompt for use @ tag (summary).


## Crontab / Task scheduler

Plugin provides cron-based job scheduling - you can schedule tasks/prompts to be sent at any time using cron-based syntax for task setup.

![v2_crontab](https://github.com/szczyglis-dev/py-gpt/assets/61396542/9fe8b25e-bbd2-4f03-9e5b-438e6f04d784)

- `Your tasks` *crontab*

Add your cron-style tasks here. 
They will be executed automatically at the times you specify in the cron-based job format. 
If you are unfamiliar with Cron, consider visiting the Cron Guru page for assistance: https://crontab.guru

Number of active tasks is always displayed in a tray dropdown menu:

![v2_crontab_tray](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f9d1825f-4511-4b7f-bdce-45ee18408021)

- `Create a new context on job run` *new_ctx*

If enabled, then a new context will be created on every run of the job. *Default:* `True`

- `Show notification on job run` *show_notify*

If enabled, then a tray notification will be shown on every run of the job. *Default:* `True`


## DALL-E 3: Image Generation (inline)

The plugin integrates `DALL-E 3` image generation with any chat mode. Simply enable it and request an image in Chat mode, using a standard model such as `GPT-4`. The plugin does not require the `Execute commands` option to be enabled.

**Options**

- `Prompt` *prompt*

The prompt is used to generate a query for the `DALL-E` image generation model, which runs in the background.

##  Experts (inline)

The plugin allows calling experts in any chat mode. This is the inline Experts (co-op) mode.

See the `Mode -> Experts` section for more details.

## GPT-4 Vision (inline)

The plugin integrates vision capabilities across all chat modes, not just Vision mode. Once enabled, it allows the model to seamlessly switch to vision processing in the background whenever an image attachment or vision capture is detected.

**Tip:** When using `Vision (inline)` by utilizing a plugin in standard mode, such as `Chat` (not `Vision` mode), the `+ Vision` special checkbox will appear at the bottom of the Chat window. It will be automatically enabled any time you provide content for analysis (like an uploaded photo). When the checkbox is enabled, the vision model is used. If you wish to exit the vision model after image analysis, simply uncheck the checkbox. It will activate again automatically when the next image content for analysis is provided.

**Options**

- `Model` *model*

The model used to temporarily provide vision capabilities. *Default:* `gpt-4-vision-preview`.

- `Prompt` *prompt*

The prompt used for vision mode. It will append or replace current system prompt when using vision model.

- `Replace prompt` *replace_prompt*

Replace whole system prompt with vision prompt against appending it to the current prompt. *Default:* `False`

- `Enable: capturing images from camera` *cmd.camera_capture*

Allows `capture` command execution. If enabled, model will be able to capture images from camera itself. The `Execute commands` option must be enabled. *Default:* `False`

- `Enable: making screenshots` *cmd.make_screenshot*

Allows `screenshot` command execution. If enabled, model will be able to making screenshots itself. The `Execute commands` option must be enabled. *Default:* `False`

## Real Time

This plugin automatically adds the current date and time to each system prompt you send. 
You have the option to include just the date, just the time, or both.

When enabled, it quietly enhances each system prompt with current time information before sending it to GPT.

**Options**

- `Append time` *hour*

If enabled, it appends the current time to the system prompt. *Default:* `True`

- `Append date` *date*

If enabled, it appends the current date to the system prompt.  *Default:* `True`

- `Template` *tpl*

Template to append to the system prompt. The placeholder `{time}` will be replaced with the 
current date and time in real-time. *Default:* `Current time is {time}.`

## System Prompt Extra (append)

The plugin appends additional system prompts (extra data) from a list to every current system prompt. 
You can enhance every system prompt with extra instructions that will be automatically appended to the system prompt.

**Options**

- `Prompts` *prompts*

List of extra prompts - prompts that will be appended to system prompt. 
All active extra prompts defined on list will be appended to the system prompt in the order they are listed here.


## Voice Control (inline)

The plugin provides voice control command execution within a conversation.

See the ``Accessibility`` section for more details.


# Creating Your Own Plugins

You can create your own plugin for **PyGPT** at any time. The plugin can be written in Python and then registered with the application just before launching it. All plugins included with the app are stored in the `plugin` directory - you can use them as coding examples for your own plugins.

PyGPT can be extended with:

- Custom plugins

- Custom LLMs wrappers

- Custom vector store providers

- Custom data loaders

- Custom audio input providers

- Custom audio output providers

- Custom web search engine providers


**Examples (tutorial files)** 

See the `examples` directory in this repository with examples of custom launcher, plugin, vector store, LLM (Langchain and Llama-index) provider and data loader:

- `examples/custom_launcher.py`

- `examples/example_audio_input.py`

- `examples/example_audio_output.py`

- `examples/example_data_loader.py`

- `examples/example_llm.py`

- `examples/example_plugin.py`

- `examples/example_vector_store.py`

- `examples/example_web_search.py`

These example files can be used as a starting point for creating your own extensions for **PyGPT**.

Extending PyGPT with custom plugins, LLMs wrappers and vector stores:

- You can pass custom plugin instances, LLMs wrappers and vector store providers to the launcher.

- This is useful if you want to extend PyGPT with your own plugins, vectors storage and LLMs.

To register custom plugins:

- Pass a list with the plugin instances as `plugins` keyword argument.

To register custom LLMs wrappers:

- Pass a list with the LLMs wrappers instances as `llms` keyword argument.

To register custom vector store providers:

- Pass a list with the vector store provider instances as `vector_stores` keyword argument.

To register custom data loaders:

- Pass a list with the data loader instances as `loaders` keyword argument.

To register custom audio input providers:

- Pass a list with the audio input provider instances as `audio_input` keyword argument.

To register custom audio output providers:

- Pass a list with the audio output provider instances as `audio_output` keyword argument.

To register custom web providers:

- Pass a list with the web provider instances as `web` keyword argument.

**Example:**


```python
# custom_launcher.py

from pygpt_net.app import run
from plugins import CustomPlugin, OtherCustomPlugin
from llms import CustomLLM
from vector_stores import CustomVectorStore

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

run(
    plugins=plugins,
    llms=llms,
    vector_stores=vector_stores,
)
```

## Handling events

In the plugin, you can receive and modify dispatched events.
To do this, create a method named `handle(self, event, *args, **kwargs)` and handle the received events like here:

```python
# custom_plugin.py

from pygpt_net.core.dispatcher import Event


def handle(self, event: Event, *args, **kwargs):
    """
    Handle dispatched events

    :param event: event object
    """
    name = event.name
    data = event.data
    ctx = event.ctx

    if name == Event.INPUT_BEFORE:
        self.some_method(data['value'])
    elif name == Event.CTX_BEGIN:
        self.some_other_method(ctx)
    else:
    	# ...
```

**List of Events**

Event names are defined in `Event` class in `pygpt_net.core.dispatcher.Event`.

Syntax: `event name` - triggered on, `event data` *(data type)*:

- `AI_NAME` - when preparing an AI name, `data['value']` *(string, name of the AI assistant)*

- `AUDIO_INPUT_RECORD_START` - start audio input recording

- `AUDIO_INPUT_RECORD_STOP` -  stop audio input recording

- `AUDIO_INPUT_RECORD_TOGGLE` - toggle audio input recording

- `AUDIO_INPUT_TRANSCRIBE` - on audio file transcribe, `data['path']` *(string, path to audio file)*

- `AUDIO_INPUT_STOP` - force stop audio input

- `AUDIO_INPUT_TOGGLE` - when speech input is enabled or disabled, `data['value']` *(bool, True/False)*

- `AUDIO_OUTPUT_STOP` - force stop audio output

- `AUDIO_OUTPUT_TOGGLE` - when speech output is enabled or disabled, `data['value']` *(bool, True/False)*

- `AUDIO_READ_TEXT` - on text read using speech synthesis, `data['text']` *(str, text to read)*

- `CMD_EXECUTE` - when a command is executed, `data['commands']` *(list, commands and arguments)*

- `CMD_INLINE` - when an inline command is executed, `data['commands']` *(list, commands and arguments)*

- `CMD_SYNTAX` - when appending syntax for commands, `data['prompt'], data['syntax']` *(string, list, prompt and list with commands usage syntax)*

- `CMD_SYNTAX_INLINE` - when appending syntax for commands (inline mode), `data['prompt'], data['syntax']` *(string, list, prompt and list with commands usage syntax)*

- `CTX_AFTER` - after the context item is sent, `ctx`

- `CTX_BEFORE` - before the context item is sent, `ctx`

- `CTX_BEGIN` - when context item create, `ctx`

- `CTX_END` - when context item handling is finished, `ctx`

- `CTX_SELECT` - when context is selected on list, `data['value']` *(int, ctx meta ID)*

- `DISABLE` - when the plugin is disabled, `data['value']` *(string, plugin ID)*

- `ENABLE` - when the plugin is enabled, `data['value']` *(string, plugin ID)*

- `FORCE_STOP` - on force stop plugins

- `INPUT_BEFORE` - upon receiving input from the textarea, `data['value']` *(string, text to be sent)*

- `MODE_BEFORE` - before the mode is selected `data['value'], data['prompt']` *(string, string, mode ID)*

- `MODE_SELECT` - on mode select `data['value']` *(string, mode ID)*

- `MODEL_BEFORE` - before the model is selected `data['value']` *(string, model ID)*

- `MODEL_SELECT` - on model select `data['value']` *(string, model ID)*

- `PLUGIN_SETTINGS_CHANGED` - on plugin settings update (saving settings)

- `PLUGIN_OPTION_GET` - on request for plugin option value `data['name'], data['value']` *(string, any, name of requested option, value)*

- `POST_PROMPT` - after preparing a system prompt, `data['value']` *(string, system prompt)*

- `PRE_PROMPT` - before preparing a system prompt, `data['value']` *(string, system prompt)*

- `SYSTEM_PROMPT` - when preparing a system prompt, `data['value']` *(string, system prompt)*

- `UI_ATTACHMENTS` - when the attachment upload elements are rendered, `data['value']` *(bool, show True/False)*

- `UI_VISION` - when the vision elements are rendered, `data['value']` *(bool, show True/False)*

- `USER_NAME` - when preparing a user's name, `data['value']` *(string, name of the user)*

- `USER_SEND` - just before the input text is sent, `data['value']` *(string, input text)*


You can stop the propagation of a received event at any time by setting `stop` to `True`:

```
event.stop = True
```

Events flow can be debugged by enabling the option `Config -> Settings -> Developer -> Log and debug events`.

# Functions and commands execution

**INFO:** From version `2.2.20` PyGPT uses native API function calls by default. You can go back to internal syntax (described below) by switching off option `Config -> Settings -> Prompts -> Use native API function calls`. Native API function calls are available in Chat, Completion and Assistant modes only (using OpenAI API).

In background, **PyGPT** uses an internal syntax to define commands and their parameters, which can then be used by the model and executed on the application side or even directly in the system. This syntax looks as follows (example command below):

```~###~{"cmd": "send_email", "params": {"quote": "Why don't skeletons fight each other? They don't have the guts!"}}~###~```

It is a JSON object wrapped between `~###~`. The application extracts the JSON object from such formatted text and executes the appropriate function based on the provided parameters and command name. Many of these types of commands are defined in plugins (e.g., those used for file operations or internet searches). You can also define your own commands using the `Custom Commands` plugin, or simply by creating your own plugin and adding it to the application.

**Tip:** The `Execute commands` option checkbox must be enabled to allow the execution of commands from plugins. Disable the option if you do not want to use commands, to prevent additional token usage (as the command execution system prompt consumes additional tokens).

![v2_code_execute](https://github.com/szczyglis-dev/py-gpt/assets/61396542/d5181eeb-6ab4-426f-93f0-037d256cb078)

When native API function calls are disabled, a special system prompt responsible for invoking commands is added to the main system prompt if the `Execute commands` option is active.

However, there is an additional possibility to define your own commands and execute them with the help of GPT.
These are functions - defined on the OpenAI API side and described using JSON objects. You can find a complete guide on how to define functions here:

https://platform.openai.com/docs/guides/function-calling

https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models

PyGPT offers compatibility of these functions with commands used in the application. All you need to do is define the appropriate functions using the syntax required by OpenAI, and PyGPT will do the rest, translating such syntax on the fly into its own internal format.

You can define functions for modes: `Chat` and `Assistants`.
Note that - in Chat mode, they should be defined in `Presets`, and for Assistants, in the `Assistant` settings.

**Example of usage:**

1) Chat

Create a new Preset, open the Preset edit dialog and add a new function using `+ Function` button with the following content:

**Name:** `send_email`

**Description:** `Sends a quote using email`

**Params (JSON):**

```json
{
        "type": "object",
        "properties": {
            "quote": {
                "type": "string",
                "description": "A generated funny quote"
            }
        },
        "required": [
            "quote"
        ]
}
```

Then, in the `Custom Commands` plugin, create a new command with the same name and the same parameters:

**Command name:** `send_email`

**Instruction/prompt:** `send mail` *(don't needed, because it will be called on OpenAI side)*

**Params list:** `quote`

**Command to execute:** `echo "OK. Email sent: {quote}"`

At next, enable the `Execute commands` option and enable the plugin.

Ask GPT in Chat mode:

```Create a funny quote and email it```

In response you will receive prepared command, like this:

```~###~{"cmd": "send_email", "params": {"quote": "Why do we tell actors to 'break a leg?' Because every play has a cast!"}}~###~```

After receiving this, PyGPT will execute the system `echo` command with params given from `params` field and replacing `{quote}` placeholder with `quote` param value.

As a result, response like this will be sent to the model:

```[{"request": {"cmd": "send_email"}, "result": "OK. Email sent: Why do we tell actors to 'break a leg?' Because every play has a cast!"}]```


2) Assistant

In this mode (via Assistants API), it should be done similarly, with the difference that here the functions should be defined in the assistant's settings.

With this flow you can use both forms - OpenAI and PyGPT - to define and execute commands and functions in the application. They will cooperate with each other and you can use them interchangeably.

# Tools

PyGPT features several useful tools, including:

- Indexer
- Media Player
- Image viewer
- Text editor
- Transcribe audio/video files
- Python code interpreter
- HTML/JS Canvas (built-in HTML renderer)

![v2_tool_menu](https://github.com/szczyglis-dev/py-gpt/assets/61396542/fb3f44af-f0de-4e18-bcac-e20389a651c9)


### Indexer


This tool allows indexing of local files or directories and external web content to a vector database, which can then be used with the `Chat with Files` mode. Using this tool, you can manage local indexes and add new data with built-in `Llama-index` integration.

![v2_tool_indexer](https://github.com/szczyglis-dev/py-gpt/assets/61396542/1caeab6e-6119-44e2-a7cb-ed34f8fe9e30)

### Media Player


A simple video/audio player that allows you to play video files directly from within the app.


### Image Viewer


A simple image browser that lets you preview images directly within the app.


### Text Editor


A simple text editor that enables you to edit text files directly within the app.


### Transcribe Audio/Video Files


An audio transcription tool with which you can prepare a transcript from a video or audio file. It will use a speech recognition plugin to generate the text from the file.


### Python Code Interpreter


This tool allows you to run Python code directly from within the app. It is integrated with the `Code Interpreter` plugin, ensuring that code generated by the model is automatically available from the interpreter. In the plugin settings, you can enable the execution of code in a Docker environment.

### HTML/JS Canvas

Allows to render HTML/JS code in HTML Canvas (built-in renderer based on Chromium). To use it, just ask the model to render the HTML/JS code in built-in browser (HTML Canvas). Tool is integrated with the `Code Interpreter` plugin.


# Token usage calculation

## Input tokens

The application features a token calculator. It attempts to forecast the number of tokens that 
a particular query will consume and displays this estimate in real time. This gives you improved 
control over your token usage. The app provides detailed information about the tokens used for the user's prompt, 
the system prompt, any additional data, and those used within the context (the memory of previous entries).

**Remember that these are only approximate calculations and do not include, for example, the number of tokens consumed by some plugins. You can find the exact number of tokens used on the OpenAI website.**

![v2_tokens1](https://github.com/szczyglis-dev/py-gpt/assets/61396542/29b610be-9e96-41cc-84f0-1b946886f801)

## Total tokens

After receiving a response from the model, the application displays the actual total number of tokens used for the query (received from the API).

![v2_tokens2](https://github.com/szczyglis-dev/py-gpt/assets/61396542/c81e95b5-7c33-41a6-8910-21d674db37e5)

# Configuration

## Settings

The following basic options can be modified directly within the application:

``` ini
Config -> Settings...
```

![v2_settings](https://github.com/szczyglis-dev/py-gpt/assets/61396542/43622c58-6cdb-4ed8-b47d-47729763db04)

**General**

- `OpenAI API KEY`: The personal API key you'll need to enter into the application for it to function.

- `OpenAI ORGANIZATION KEY`: The organization's API key, which is optional for use within the application.

- `API Endpoint`: OpenAI API endpoint URL, default: https://api.openai.com/v1.

- `Proxy address`: Proxy address to be used for connection; supports HTTP/SOCKS.

- `Minimize to tray on exit`: Minimize to tray icon on exit. Tray icon enabled is required for this option to work. Default: False.

- `Render engine`: chat output render engine: `WebEngine / Chromium` - for full HTML/CSS and `Legacy (markdown)` for legacy, simple markdown CSS output. Default: WebEngine / Chromium.

- `OpenGL hardware acceleration`: enables hardware acceleration in `WebEngine / Chromium` renderer.  Default: False.

- `Application environment (os.environ)`: Additional environment vars to set on application start.

**Layout**

- `Zoom`: Adjusts the zoom in chat window (web render view). `WebEngine / Chromium` render mode only.

- `Code syntax highlight`: Syntax highlight theme in code blocks. `WebEngine / Chromium` render mode only.

- `Font Size (chat window)`: Adjusts the font size in the chat window (plain-text) and notepads.

- `Font Size (input)`: Adjusts the font size in the input window.

- `Font Size (ctx list)`: Adjusts the font size in contexts list.

- `Font Size (toolbox)`: Adjusts the font size in toolbox on right.

- `Layout density`: Adjusts layout elements density. Default: -1. 

- `DPI scaling`: Enable/disable DPI scaling. Restart of the application is required for this option to take effect. Default: True. 

- `DPI factor`: DPI factor. Restart of the application is required for this option to take effect. Default: 1.0. 

- `Display tips (help descriptions)`: Display help tips, Default: True.

- `Store dialog window positions`: Enable or disable dialogs positions store/restore, Default: True.

- `Use theme colors in chat window`: Use color theme in chat window, Default: True.

- `Disable markdown formatting in output`: Enables plain-text display in output window, Default: False.

**Files and attachments**

- `Store attachments in the workdir upload directory`: Enable to store a local copy of uploaded attachments for future use. Default: True

- `Store images, capture and upload in data directory`: Enable to store everything in single data directory. Default: False

- `Directory for file downloads`: Subdirectory for downloaded files, e.g. in Assistants mode, inside "data". Default: "download"

**Context**

- `Context Threshold`: Sets the number of tokens reserved for the model to respond to the next prompt.

- `Limit of last contexts on list to show  (0 = unlimited)`: Limit of the last contexts on list, default: 0 (unlimited)

- `Show context groups on top of the context list`: Display groups on top, default: False

- `Show date separators on the context list`: Show date periods, default: True

- `Show date separators in groups on the context list`: Show date periods in groups, default: True

- `Show date separators in pinned on the context list`: Show date periods in pinned items, default: False

- `Use Context`: Toggles the use of conversation context (memory of previous inputs).

- `Store History`: Toggles conversation history store.

- `Store Time in History`: Chooses whether timestamps are added to the .txt files.

- `Context Auto-summary`: Enables automatic generation of titles for contexts, Default: True.

- `Lock incompatible modes`: If enabled, the app will create a new context when switched to an incompatible mode within an existing context.

- `Search also in conversation content, not only in titles`: When enabled, context search will also consider the content of conversations, not just the titles of conversations.

- `Show Llama-index sources`: If enabled, sources utilized will be displayed in the response (if available, it will not work in streamed chat).

- `Show code interpreter output`: If enabled, output from the code interpreter in the Assistant API will be displayed in real-time (in stream mode), Default: True.

- `Use extra context output`: If enabled, plain text output (if available) from command results will be displayed alongside the JSON output, Default: True.

- `Convert lists to paragraphs`: If enabled, lists (ul, ol) will be converted to paragraphs (p), Default: True.

- `Model used for auto-summary`: Model used for context auto-summary (default: *gpt-3.5-turbo-1106*).

**Models**

- `Max Output Tokens`: Sets the maximum number of tokens the model can generate for a single response.

- `Max Total Tokens`: Sets the maximum token count that the application can send to the model, including the conversation context.

- `RPM limit`: Sets the limit of maximum requests per minute (RPM), 0 = no limit.

- `Temperature`: Sets the randomness of the conversation. A lower value makes the model's responses more deterministic, while a higher value increases creativity and abstraction.

- `Top-p`: A parameter that influences the model's response diversity, similar to temperature. For more information, please check the OpenAI documentation.

- `Frequency Penalty`: Decreases the likelihood of repetition in the model's responses.

- `Presence Penalty`: Discourages the model from mentioning topics that have already been brought up in the conversation.

**Prompts**

- `Use native API function calls`: Use API function calls to run commands from plugins instead of using command prompts - Chat and Assistants modes ONLY, default: True

- `Command execute: instruction`: Prompt for appending command execution instructions. Placeholders: {schema}, {extra}

- `Command execute: extra footer (non-Assistant modes)`: Extra footer to append after commands JSON schema.

- `Command execute: extra footer (Assistant mode only)`: PAdditional instructions to separate local commands from the remote environment that is already configured in the Assistants.

- `Context: auto-summary (system prompt)`: System prompt for context auto-summary.

- `Context: auto-summary (user message)`: User message for context auto-summary. Placeholders: {input}, {output}

- `Agent: evaluation prompt in loop (Llama-index)`: Prompt used for evaluating the response in Agents (Llama-index) mode.

- `Agent: system instruction (Legacy)`: Prompt to instruct how to handle autonomous mode.

- `Agent: continue (Legacy)`: Prompt sent to automatically continue the conversation.

- `Agent: continue (always, more steps) (Legacy)`: Prompt sent to always automatically continue the conversation (more reasoning - "Always continue..." option).

- `Agent: goal update (Legacy)`: Prompt to instruct how to update current goal status.

- `Experts: Master prompt`: Prompt to instruct how to handle experts.

- `DALL-E: image generate`: Prompt for generating prompts for DALL-E (if raw-mode is disabled).

**Images**

- `DALL-E Image size`: The resolution of the generated images (DALL-E). Default: 1792x1024.

- `DALL-E Image quality`: The image quality of the generated images (DALL-E). Default: standard.

- `Open image dialog after generate`: Enable the image dialog to open after an image is generated in Image mode.

- `DALL-E: prompt generation model`: Model used for generating prompts for DALL-E (if raw-mode is disabled).

**Vision**

- `Vision: Camera capture width (px)`: Video capture resolution (width).

- `Vision: Camera capture height (px)`: Video capture resolution (height).

- `Vision: Camera IDX (number)`: Video capture camera index (number of camera).

- `Vision: Image capture quality`: Video capture image JPEG quality (%).

**Indexes (Llama-index)**

- `Indexes`: List of created indexes.

- `Vector Store`: Vector store to use (vector database provided by Llama-index).

- `Vector Store (**kwargs)`: Keyword arguments for vector store provider (api_key, index_name, etc.).

- `Embeddings provider`: Embeddings provider.

- `Embeddings provider (ENV)`: ENV vars to embeddings provider (API keys, etc.).

- `Embeddings provider (**kwargs)`: Keyword arguments for embeddings provider (model name, etc.).

- `RPM limit for embeddings API calls`: Specify the limit of maximum requests per minute (RPM), 0 = no limit.

- `Recursive directory indexing`: Enables recursive directory indexing, default is False.

- `Replace old document versions in the index during re-indexing`: If enabled, previous versions of documents will be deleted from the index when the newest versions are indexed, default is True.

- `Excluded file extensions`: File extensions to exclude if no data loader for this extension, separated by comma.

- `Force exclude files`: If enabled, the exclusion list will be applied even when the data loader for the extension is active. Default: False.

- `Stop indexing on error`: If enabled, indexing will stop whenever an error occurs Default: True.

- `Custom metadata to append/replace to indexed documents (file)`: Define custom metadata key => value fields for specified file extensions, separate extensions by comma.\nAllowed placeholders: {path}, {relative_path} {filename}, {dirname}, {relative_dir} {ext}, {size}, {mtime}, {date}, {date_time}, {time}, {timestamp}. Use * (asterisk) as extension if you want to apply field to all files. Set empty value to remove field with specified key from metadata.

- `Custom metadata to append/replace to indexed documents (web)`: Define custom metadata key => value fields for specified external data loaders.\nAllowed placeholders: {date}, {date_time}, {time}, {timestamp} + {data loader args}

- `Additional keyword arguments (**kwargs) for data loaders`: Additional keyword arguments, such as settings, API keys, for the data loader. These arguments will be passed to the loader; please refer to the Llama-index or LlamaHub loaders reference for a list of allowed arguments for the specified data loader.

- `Use local models in Video/Audio and Image (vision) loaders`: Enables usage of local models in Video/Audio and Image (vision) loaders. If disabled then API models will be used (GPT-4 Vision and Whisper). Note: local models will work only in Python version (not compiled/Snap). Default: False.

- `Auto-index DB in real time`: Enables conversation context auto-indexing in defined modes.

- `ID of index for auto-indexing`: Index to use if auto-indexing of conversation context is enabled.

- `Enable auto-index in modes`: List of modes with enabled context auto-index, separated by comma.

- `DB (ALL), DB (UPDATE), FILES (ALL)`: Index the data – batch indexing is available here.

- `Chat mode`: chat mode for use in query engine, default: context

**Agent and experts**

**General**

- `Display a tray notification when the goal is achieved.`: If enabled, a notification will be displayed after goal achieved / finished run.

**Llama-index Agents**

- `Max steps (per iteration)` - Max steps is one iteration before goal achieved

- `Max evaluation steps in loop` - Maximum evaluation steps to achieve the final result, set 0 to infinity

- `Append and compare previous evaluation prompt in next evaluation` - If enabled, previous improvement prompt will be checked in next eval in loop, default: False

- `Verbose` - enables verbose mode.

**Legacy**

- `Sub-mode for agents`: Sub-mode to use in Agent mode (chat, completion, langchain, llama_index, etc.). Default: chat.

- `Sub-mode for experts`: Sub-mode to use in Experts mode (chat, completion, langchain, llama_index, etc.). Default: chat.

- `Index to use`: Only if sub-mode is llama_index (Chat with files), choose the index to use in both Agent and Expert modes.

**Accessibility**

- `Enable voice control (using microphone)`: enables voice control (using microphone and defined commands).

- `Model`: model used for voice command recognition.

- `Use voice synthesis to describe events on the screen.`: enables audio description of on-screen events.

- `Use audio output cache`: If enabled, all static audio outputs will be cached on the disk instead of being generated every time. Default: True.

- `Audio notify microphone listening start/stop`: enables audio "tick" notify when microphone listening started/ended.

- `Audio notify voice command execution`: enables audio "tick" notify when voice command is executed.

- `Control shortcut keys`: configuration for keyboard shortcuts for a specified actions.

- `Blacklist for voice synthesis events describe (ignored events)`: list of muted events for 'Use voice synthesis to describe event' option.

- `Voice control actions blacklist`: Disable actions in voice control; add actions to the blacklist to prevent execution through voice commands.

**Updates**

- `Check for updates on start`: Enables checking for updates on start. Default: True.

- `Check for updates in background`: Enables checking for updates in background (checking every 5 minutes). Default: True.

**Developer**

- `Show debug menu`: Enables debug (developer) menu.

- `Log and debug context`: Enables logging of context input/output.

- `Log and debug events`: Enables logging of event dispatch.

- `Log plugin usage to console`: Enables logging of plugin usage to console.

- `Log DALL-E usage to console`: Enables logging of DALL-E usage to console.

- `Log Llama-index usage to console`: Enables logging of Llama-index usage to console.

- `Log Assistants usage to console`: Enables logging of Assistants API usage to console.

- `Log level`: toggle log level (ERROR|WARNING|INFO|DEBUG)


## JSON files

The configuration is stored in JSON files for easy manual modification outside of the application. 
These configuration files are located in the user's work directory within the following subdirectory:

``` ini
{HOME_DIR}/.config/pygpt-net/
```

# Notepad

The application has a built-in notepad, divided into several tabs. This can be useful for storing information in a convenient way, without the need to open an external text editor. The content of the notepad is automatically saved whenever the content changes.

![v2_notepad](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f6aa0126-bad1-4e6c-ace6-72e979186433)

# Profiles

You can create multiple profiles for an app and switch between them. Each profile uses its own configuration, settings, context history, and a separate folder for user files. This allows you to set up different environments and quickly switch between them, changing the entire setup with just one click.

The app lets you create new profiles, edit existing ones, and duplicate current ones.

To create a new profile, select the option from the menu: `Config -> Profile -> New Profile...`

To edit saved profiles, choose the option from the menu: `Config -> Profile -> Edit Profiles...`

To switch to a created profile, pick the profile from the menu: `Config -> Profile -> [Profile Name]`

Each profile uses its own user directory (workdir). You can link a newly created or edited profile to an existing workdir with its configuration.

The name of the currently active profile is shown as (Profile Name) in the window title.

# Advanced configuration

## Manual configuration

You can manually edit the configuration files in this directory (this is your work directory):

``` ini
{HOME_DIR}/.config/pygpt-net/
```

- `assistants.json` - stores the list of assistants.
- `attachments.json` - stores the list of current attachments.
- `config.json` - stores the main configuration settings.
- `models.json` - stores models configurations.
- `cache` - a directory for audio cache.
- `capture` - a directory for captured images from camera and screenshots
- `css` - a directory for CSS stylesheets (user override)
- `history` - a directory for context history in `.txt` format.
- `idx` - `Llama-index` indexes
- `img` - a directory for images generated with `DALL-E 3` and `DALL-E 2`, saved as `.png` files.
- `locale` - a directory for locales (user override)
- `data` - a directory for data files and files downloaded/generated by GPT.
- `presets` - a directory for presets stored as `.json` files.
- `upload` - a directory for local copies of attachments coming from outside the workdir
- `db.sqlite` - a database with contexts, notepads and indexes data records
- `app.log` - a file with error and debug log

---

## Translations / Locale

Locale `.ini` files are located in the app directory:

``` ini
./data/locale
```

This directory is automatically scanned when the application launches. To add a new translation, 
create and save the file with the appropriate name, for example:

``` ini
locale.es.ini   
```

This will add Spanish as a selectable language in the application's language menu.

**Overwriting CSS and locales with Your Own Files:**

You can also overwrite files in the `locale` and `css` app directories with your own files in the user directory. 
This allows you to overwrite language files or CSS styles in a very simple way - by just creating files in your working directory.


``` ini
{HOME_DIR}/.config/pygpt-net/
```

- `locale` - a directory for locales in `.ini` format.
- `css` - a directory for CSS styles in `.css` format.

**Adding Your Own Fonts**

You can add your own fonts and use them in CSS files. To load your own fonts, you should place them in the `%workdir%/fonts` directory. Supported font types include: `otf`, `ttf`.
You can see the list of loaded fonts in `Debug / Config`.

**Example:**

```
%workdir%
|_css
|_data
|_fonts
   |_MyFont
     |_MyFont-Regular.ttf
     |_MyFont-Bold.ttf
     |...
```

```css
pre {{
    font-family: 'MyFont';
}}
```

## Debugging and Logging

In `Settings -> Developer` dialog, you can enable the `Show debug menu` option to turn on the debugging menu. The menu allows you to inspect the status of application elements. In the debugging menu, there is a `Logger` option that opens a log window. In the window, the program's operation is displayed in real-time.

**Logging levels**:

By default, all errors and exceptions are logged to the file:

```ini
{HOME_DIR}/.config/pygpt-net/app.log
```

To increase the logging level (`ERROR` level is default), run the application with `--debug` argument:

``` ini
python3 run.py --debug=1
```

or

```ini
python3 run.py --debug=2
```

The value `1` enables the `INFO`logging level.

The value `2` enables the `DEBUG` logging level (most information).

## Compatibility (legacy) mode

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

## Updates

### Updating PyGPT

**PyGPT** comes with an integrated update notification system. When a new version with additional features is released, you'll receive an alert within the app. 

To get the new version, simply download it and start using it in place of the old one. All your custom settings like configuration, presets, indexes, and past conversations will be kept and ready to use right away in the new version.


## Coming soon

- Enhanced integration with Langchain
- More vector databases support
- Development of autonomous agents

## DISCLAIMER

This application is not officially associated with OpenAI. The author shall not be held liable for any damages 
resulting from the use of this application. It is provided "as is," without any form of warranty. 
Users are reminded to be mindful of token usage - always verify the number of tokens utilized by the model on 
the OpenAI website and engage with the application responsibly. Activating plugins, such as Web Search,
may consume additional tokens that are not displayed in the main window. 

**Always monitor your actual token usage on the OpenAI website.**

---

# CHANGELOG

## Recent changes:

**2.4.15 (2024-11-18)**

- Vision analysis added to all modes.
- Added commands for the Vision plugin: image analysis from an attachment, screenshot analysis, camera image analysis - performed in the background in every mode, without switching to vision mode.
- Improved execution of multiple commands at once..
- Improved integration with IPython and extended instructions for the model.
- Other fixes and improvements.

**2.4.14 (2024-11-17)**

- Added a `Loop / evaluate` mode for Llama-index agents, allowing them to work autonomously in a loop and evaluates the correctness of received results using a percentage scale from 0% to 100%, and automatically continue and correct responses below expected value.
- Updated layout: mode and model lists replaced with comboboxes.

**2.4.13 (2024-11-16)**

- Introduced `Code Interpreter (v2)` with `IPython`: Enables session state retention on a kernel and building on previous computations, allowing for a Jupyter-like workflow, which is useful for iterative development and data analysis. Supports magic commands like `!pip install <package_name>` for package installation within the session. (currently in beta)

**2.4.12 (2024-11-15)**

- Added httpx-socks to the dependencies, enabling the use of SOCKS proxies.

**2.4.11 (2024-11-15)**

- Added a new Llama-index agent: OpenAI Assistant.
- Added proxy settings to the configuration dialog.
- Added more models to the Agent (Llama-index) mode.
- Improved the agents/presets dialog window.
- Disabled the "OpenAI API KEY is not set" Llama-index error when using a local model in Chat with Files mode. You can now use local embeddings, such as Llama3 via Ollama, and use local models without any warnings.

**2.4.10 (2024-11-14)**

- Added support for Llama Index agents. (beta)
- Introduced a new working mode: Agent (Llama Index).
- Added 3 Llama Index agents: OpenAI Agent, ReAct Agent, and Structured Planner Agent.
- Fixed: passing an embed model to vector stores on indexing.
- Fixed: python3-tk error in snap version.

**2.4.9 (2024-11-12)**

- Mouse movement has been moved to the PyAutoGUI library for seamless operation.
- Bridge calls have been moved to an asynchronous thread.
- Fixed the DALL-E call in Image mode.
- Speed improvements and optimizations.

**2.4.8 (2024-11-12)**

- Fix: restoring order of notepads.
- Fix: mouse move offset in Mouse and Keyboard plugin.

**2.4.7 (2024-11-11)**

- Added a new tool: `HTML/JS Canvas`, connected to the `Code Interpreter` plugin. This feature enables real-time rendering of HTML/JS code in a Chromium-based output by using two new `Code Interpreter` commands: `render_html_output` and `get_html_output`.
- Added an SVG icon to the New Tab button.
- Improved the system prompt and execution flow in the `Command: Mouse And Keyboard` plugin and introduced a new option Auto-focus to the plugin settings (default: False).

**2.4.6 (2024-11-10)**

- Fixed notepad tab titles in Copy To menu.

**2.4.5 (2024-11-09)**

- Added a new [+] tab button to the right of the tabs.
- Fixed the issue where the tab name disappeared when creating a new tab.
- Fixed the broken find option (CTRL+F) in the chat window.

**2.4.4 (2024-11-09)**

- Added a new plugin: Command: Mouse And Keyboard. The plugin allows the model to control the mouse and keyboard, control the cursor position, click mouse buttons, use scroll, type text, and press keys on the keyboard.

**2.4.3 (2024-11-08)**

- Added button to hide output from tools/plugins.
- Added tooltips on the preset list showing the system prompt of the preset.
- Added restoration of tooltips for chat tabs.
- Removed disruptive tooltips from the plugin settings window.
- Improved reading of current tab information in event reading with speech synthesis.
- Minor improvements.

**2.4.2 (2024-11-08)**

- Improved commands and tools handling.
- Improved autonomous mode.

**2.4.1 (2024-11-08)**

- Added titles for conversations in tabs.
- Tab tools added to the tools menu.
- Fix: Reload tabs after changing profile.
- Other fixes.

**2.4.0 (2024-11-06)**

- Added the ability to have conversations in multiple tabs (right-click on the tab bar to add new tabs via "Add a new chat", similar to a web browser).
- Added the option to add notepad tabs using the right-click context menu and selecting "Add a new notepad".
- Added tab reorganization via drag and drop (you can now arrange tabs freely using the mouse).
- Added the ability to name tabs.

**2.3.4 (2024-11-03)**

- Support for LaTeX: Mathematical formulas can now be displayed in the chat window using `KaTeX`library (https://katex.org/). This enhancement allows for real-time rendering of complex mathematical expressions.

**2.3.3 (2024-11-03)**

- Added support for models: OpenAI `o1` and `o1-mini` and `SpeakLeash/bielik-11b-v2.2` (Polish LLM: https://bielik.ai).


# Credits and links

**Official website:** <https://pygpt.net>

**Documentation:** <https://pygpt.readthedocs.io>

**Support and donate:** <https://pygpt.net/#donate>

**GitHub:** <https://github.com/szczyglis-dev/py-gpt>

**Discord:** <https://pygpt.net/discord>

**Snap Store:** <https://snapcraft.io/pygpt>

**PyPI:** <https://pypi.org/project/pygpt-net>

**Author:** Marcin Szczygliński (Poland, EU)

**Contact:** <info@pygpt.net>

**License:** MIT License

# Special thanks

GitHub's community:

- [@BillionShields](https://github.com/BillionShields)

- [@gfsysa](https://github.com/gfsysa)

- [@glinkot](https://github.com/glinkot)

- [@kaneda2004](https://github.com/kaneda2004)

- [@linnflux](https://github.com/linnflux)

- [@moritz-t-w](https://github.com/moritz-t-w)

- [@oleksii-honchar](https://github.com/oleksii-honchar)

- [@yf007](https://github.com/yf007)

## Third-party libraries

Full list of external libraries used in this project is located in the [requirements.txt](https://github.com/szczyglis-dev/py-gpt/blob/master/requirements.txt) file in the main folder of the repository.

All used SVG icons are from `Material Design Icons` provided by Google:

https://github.com/google/material-design-icons

https://fonts.google.com/icons

Monaspace fonts provided by GitHub: https://github.com/githubnext/monaspace

Code of the Llama-index offline loaders integrated into app is taken from LlamaHub: https://llamahub.ai

Awesome ChatGPT Prompts (used in templates): https://github.com/f/awesome-chatgpt-prompts/

Code syntax highlight powered by: https://highlightjs.org

LaTeX support by: https://katex.org and https://github.com/mitya57/python-markdown-math
