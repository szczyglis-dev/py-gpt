# PyGPT - Desktop AI Assistant

[![pygpt](https://snapcraft.io/pygpt/badge.svg)](https://snapcraft.io/pygpt)

Release: **2.0.114** | build: **2024.01.21** | Python: **3.10+**

Official website: https://pygpt.net | Documentation: https://pygpt.readthedocs.io

Snap Store: https://snapcraft.io/pygpt | PyPi: https://pypi.org/project/pygpt-net

Compiled version for Linux (tar.gz) and Windows 10/11 (msi) 64-bit: https://pygpt.net/#download

## Overview

**PyGPT** is **all-in-one** Desktop AI Assistant that provides direct interaction with OpenAI language models, including `GPT-4`, `GPT-4 Vision`, and `GPT-3.5`, through the `OpenAI API`. The application also integrates with alternative LLMs, like those available on `HuggingFace`, by utilizing `Langchain`.

This assistant offers multiple modes of operation such as chat, assistants, completions, and image-related tasks using `DALL-E 3` for generation and `GPT-4 Vision` for analysis. **PyGPT** has filesystem capabilities for file I/O, can generate and run Python code, execute system commands, execute custom commands and manage file transfers. It also allows models to perform web searches with the `Google Custom Search API`.

For audio interactions, **PyGPT** includes speech synthesis using the `Microsoft Azure Text-to-Speech API` and `OpenAI's TTS API`. Additionally, it features speech recognition capabilities provided by `OpenAI Whisper`, enabling the application to understand spoken commands and transcribe audio inputs into text. It features context memory with save and load functionality, enabling users to resume interactions from predefined points in the conversation. Prompt creation and management are streamlined through an intuitive preset system.

**PyGPT**'s functionality extends through plugin support, allowing for custom enhancements. Its multi-modal capabilities make it an adaptable tool for a range of AI-assisted operations, such as text-based interactions, system automation, daily assisting, vision applications, natural language processing, code generation and image creation.

Multiple operation modes are included, such as chat, text completion, assistant, vision, Langchain, commands execution and image generation, making **PyGPT** a comprehensive tool for many AI-driven tasks.

**Video** (mp4, version 2.0.77, build 2024-01-05):

https://github.com/szczyglis-dev/py-gpt/assets/61396542/5898136b-e06d-400b-83cf-99d801db61a8

**Screenshot** (version 2.0.77 build 2024-01-05):

![v2_main](https://github.com/szczyglis-dev/py-gpt/assets/61396542/08e0c68f-685a-4dd7-9369-ee8915cd84ab)

You can download compiled version for Windows and Linux here: https://pygpt.net/#download

## Features

- Desktop AI Assistant for `Windows` and `Linux`, written in Python.
- Works similarly to `ChatGPT`, but locally (on a desktop computer).
- 6 modes of operation: Assistant, Chat, Vision, Completion, Image generation, Langchain.
- Supports multiple models: `GPT-4`, `GPT-3.5`, and `GPT-3`, including any model accessible through `Langchain`.
- Handles and stores the full context of conversations (short-term memory).
- Real-time video camera capture in Vision mode
- Internet access via `Google Custom Search API`.
- Speech synthesis via `Microsoft Azure TTS` and `OpenAI TTS`.
- Speech recognition via `OpenAI Whisper`.
- Image analysis via `GPT-4 Vision`.
- Crontab / Task scheduler included
- Integrated `Langchain` support (you can connect to any LLM, e.g., on `HuggingFace`).
- Integrated `Llama-index` support: chat with `txt`, `pdf`, `csv`, `md`, `docx`, `json`, `epub`, `xlsx` or use previous conversations as additional context provided to model.
- Integrated calendar, day notes and search in contexts by selected date
- Commands execution (via plugins: access to the local filesystem, Python code interpreter, system commands execution).
- Custom commands creation and execution
- Manages files and attachments with options to upload, download, and organize.
- Context history with the capability to revert to previous contexts (long-term memory).
- Allows you to easily manage prompts with handy editable presets.
- Provides an intuitive operation and interface.
- Includes a notebook.
- Includes simple drawing feature
- Includes optional Autonomous Mode
- Supports multiple languages.
- Enables the use of all the powerful features of `GPT-4`, `GPT-4V`, and `GPT-3.5`.
- Requires no previous knowledge of using AI models.
- Simplifies image generation using `DALL-E 3` and `DALL-E 2`.
- Possesses the potential to support future OpenAI models.
- Fully configurable.
- Themes support.
- Plugins support.
- Built-in token usage calculation.
- It's open source; source code is available on `GitHub`.
- Utilizes the user's own API key.

The application is free, open-source, and runs on PCs with `Windows 10`, `Windows 11`, and `Linux`. 
The full Python source code is available on `GitHub`.

**PyGPT uses the user's API key  -  to use the application, 
you must have a registered OpenAI account and your own API key.**

You can also use built-it Langchain support to connect to other Large Language Models (LLMs), 
such as those on HuggingFace. Additional API keys may be required.

# Installation

## Compiled versions (Windows, Linux)

You can download compiled versions for `Windows 10`, `Windows 11` and `Linux`. 

Download the `.msi` or `tar.gz` for the appropriate OS from the download page at https://pygpt.net and then extract files from the archive and run the application.

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

**File explorer:** `Open file` and `Open in folder` options may not work in Snap version.

## PyPi (pip)

The application can also be installed from `PyPI` using `pip install`:

1. Create virtual environment:

```commandline
python -m venv venv
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

An alternative method is to download the source code from `GitHub` and execute the application using 
the Python interpreter (version `3.10` or higher). 

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

**Tip**: you can use `PyInstaller` to create a compiled version of
the application for your system (version < `6.x`, e.g. `5.13.2`).

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

If this not help then try to downgrade PySide to `PySide6-Essentials==6.4.2`:


```commandline
pip install PySide6-Essentials==6.4.2
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

**Camera access in Snap version:**

To use camera in Vision mode in Snap version you must connect the camera with:

```commandline
sudo snap connect pygpt:camera
```

## Other requirements

For operation, an internet connection is needed (for API connectivity), a registered OpenAI account, 
and an active API key that must be input into the program.


# Quick Start

## Setting-up OpenAI API KEY

During the initial launch, you must configure your API key within the application.

To do so, navigate to the menu:

``` ini
Config -> Settings...
```

and then paste the API key into the `OpenAI API KEY` field.

![v2_settings](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f4be3d53-23ee-4b0e-9e46-296253f688b8)

The API key can be obtained by registering on the OpenAI website:

<https://platform.openai.com>

Your API keys will be available here:

<https://platform.openai.com/account/api-keys>

**Note:** The ability to use models within the application depends on the API user's access to a given model!

# Chat, completion, assistants and vision (GPT-4, GPT-3.5, Langchain)

## Chat (+ inline Vision and Image generation)

This mode in **PyGPT** mirrors `ChatGPT`, allowing you to chat with models such as `GPT-4`, `GPT-4 Turbo`, `GPT-3.5`, and `GPT-3`. It's easy to switch models whenever you want. It works by using the `ChatCompletion API`.

The main part of the interface is a chat window where conversations appear. Right below that is where you type your messages. On the right side of the screen, there's a section to set up or change your system prompts. You can also save these setups as presets to quickly switch between different models or tasks.

Above where you type your messages, the interface shows you the number of tokens your message will use up as you type it – this helps to keep track of usage. There's also a feature to upload files in this area. Go to the `Files` tab to manage your uploads or add attachments to send to the OpenAI API (but this makes effect only in `Assisant` and `Vision` modes).

![v2_mode_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/1579417c-8e8d-4b98-b255-6593103a1c4f)

**Vision:** If you want to send photos or image from camera to analysis you must enable plugin **GPT-4 Vision Inline** in the Plugins menu.
Plugin allows you to send photos or image from camera to analysis in any Chat mode:

![v3_vision_plugins](https://github.com/szczyglis-dev/py-gpt/assets/61396542/4366d955-cb01-4cfb-b15a-f98eed8a142b)

With this plugin, you can capture an image with your camera or attach an image and send it for analysis to discuss the photograph:

![v3_vision_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/6be4b1db-2f39-40ce-a42a-2c549181b6dd)

**Image generation:** If you want to generate images (using DALL-E) directly in chat you must enable plugin **DALL-E 3 Inline** in the Plugins menu.
Plugin allows you to generate images in Chat mode:

![v3_img_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/0cf29093-373e-4c71-ab02-9a630f88c68e)

## Completion

This advanced mode provides in-depth access to a broader range of capabilities offered by Large Language Models (LLMs). While it maintains a chat-like interface for user interaction, it introduces additional settings and functional richness beyond typical chat exchanges. Users can leverage this mode to prompt models for complex text completions, role-play dialogues between different characters, perform text analysis, and execute a variety of other sophisticated tasks. It supports any model provided by the OpenAI API as well as other models through `Langchain`.

Similar to chat mode, on the right-hand side of the interface, there are convenient presets. These allow you to fine-tune instructions and swiftly transition between varied configurations and pre-made prompt templates.

Additionally, this mode offers options for labeling the AI and the user, making it possible to simulate dialogues between specific characters - for example, you could create a conversation between Batman and the Joker, as predefined in the prompt. This feature presents a range of creative possibilities for setting up different conversational scenarios in an engaging and exploratory manner.

![v2_mode_completion](https://github.com/szczyglis-dev/py-gpt/assets/61396542/1c5f80aa-4864-451f-be4d-ee72efd5b0c4)

In this mode, models from the `davinci` family within `GPT-3` are available. 

**Info:** From version `2.0.107` the davinci models are deprecated and has been replaced with `gpt-3.5-turbo-instruct` model.

## Assistants

This mode uses the new OpenAI's **Assistants API**.

This mode expands on the basic chat functionality by including additional external tools like a `Code Interpreter` for executing code, `Retrieval Files` for accessing files, and custom `Functions` for enhanced interaction and integration with other APIs or services. In this mode, you can easily upload and download files. **PyGPT** streamlines file management, enabling you to quickly upload documents and manage files created by the model.

Setting up new assistants is simple - a single click is all it takes, and they instantly sync with the `OpenAI API`. Importing assistants you've previously created with OpenAI into **PyGPT** is also a seamless process.

![v2_mode_assistant](https://github.com/szczyglis-dev/py-gpt/assets/61396542/d199fefc-d795-4fc7-8570-acbc219f9ba4)

In Assistant mode you are allowed to storage your files (per Assistant) and manage them easily from app:

![v2_mode_assistant_upload](https://github.com/szczyglis-dev/py-gpt/assets/61396542/ac599b23-e675-4db1-b7b7-d134fa9b15b1)

Please note that token usage calculation is unavailable in this mode. Nonetheless, file (attachment) 
uploads are supported. Simply navigate to the `Files` tab to effortlessly manage files and attachments which 
can be sent to the OpenAI API.

## Vision (GPT-4 Vision)

This mode enables image analysis using the `GPT-4 Vision` model. Functioning much like the chat mode, 
it also allows you to upload images or provide URLs to images. The vision feature can analyze both local 
images and those found online. 

**From version 2.0.68** - Vision is integrated into any chat mode via plugin `GPT-4 Vision (inline)`. Just enable plugin and use Vision in standard modes.

**From version 2.0.14** - Vision mode also includes real-time video capture from camera. To enable capture check the option `Camera` on the right-bottom corner. It will enable real-time capturing from your camera. To capture image from camera and append it to chat just click on video at left side. You can also enable `Auto capture` - image will be captured and appended to chat message every time you send message.

![v2_capture_enable](https://github.com/szczyglis-dev/py-gpt/assets/61396542/dd8ee149-afd2-4d7b-b2be-5c4e9725c584)


**1) Video camera real-time image capture**

![v2_capture1](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f69a5510-fc34-4073-80ef-fcc5ce5c50a7)


![v3_vision_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/6be4b1db-2f39-40ce-a42a-2c549181b6dd)

**2) you can also provide an image URL**

![v2_mode_vision](https://github.com/szczyglis-dev/py-gpt/assets/61396542/051bfaf7-467c-4e44-bd79-3c28548ea41e)

**3) or you can just upload your local images**

![v2_mode_vision_upload](https://github.com/szczyglis-dev/py-gpt/assets/61396542/54656c2c-330c-4f6a-b7cf-002042594e73)

**4) or just use the inline Vision in the standard chat mode.**

## Langchain

This mode enables you to work with models that are supported by `Langchain`. The Langchain support is integrated 
into the application, allowing you to interact with any LLM by simply supplying a configuration 
file for the specific model. You can add as many models as you like; just list them in the configuration 
file named `models.json`.

Available LLMs providers supported by **PyGPT**:

```
- OpenAI
- Azure OpenAI
- HuggingFace
- Anthropic
- Llama 2
- Ollama
```

![v2_mode_langchain](https://github.com/szczyglis-dev/py-gpt/assets/61396542/d0a30457-468e-42ec-b470-77888bce3b81)

You have the ability to add custom model wrappers for models that are not available by default in **PyGPT**. 
To integrate a new model, you can create your own wrapper and register it with the application. 
Detailed instructions for this process are provided in the section titled `Managing models / Adding models via Langchain`.

##  Chat with files (Llama-index)

This mode enables chat interaction with your documents and entire context history through conversation. 
It seamlessly incorporates `Llama-index` into the chat interface, allowing for immediate querying of your indexed documents. 
To begin, you must first index the files you wish to include. 
Simply copy or upload them into the `data` directory and initiate indexing by clicking the `Index all` button, or right-click on a file and select `Index...`. 
Additionally, you have the option to utilize data from indexed files in any Chat mode by activating the `Chat with files (Llama-index, inline)` plugin.

Built-in file loaders (offline): `text files`, `pdf`, `csv`, `md`, `docx`, `json`, `epub`, `xlsx`. 
You can extend this list in `Settings / Llama-index` by providing list of online loaders (from `LlamaHub`).
All loaders included for offline use are also from `LlamaHub`, but they are attached locally with all necessary library dependencies included.

**From version `2.0.100` Llama-index is also integrated with database - you can use data from database (your history contexts) as additional context in discussion. 
Options for indexing existing context history or enabling real-time indexing new ones (from database) are available in `Settings / Llama-index` section.**

**WARNING:** remember that when indexing content, API calls to the embedding model (`text-embedding-ada-002`) are used. Each indexing consumes additional tokens. 
Always control the number of tokens used on the OpenAI page.

**Tip:** when using `Chat with files` you are using additional context from db data and files indexed from `data` directory, not the files sending via `Attachments` tab. 
Attachments tab in `Chat with files` mode can be used to provide images to `Vision (inline)` plugin only.

**Available vector stores** (provided by `Llama-index`):

```
- ChromaVectorStore
- ElasticsearchStore
- PinecodeVectorStore
- RedisVectorStore
- SimpleVectorStore
```

You can configure selected vector store by providing config options like `api_key`, etc. in `Settings -> Llama-index` window. 
Arguments provided here (on list: `Vector Store (**kwargs)` will be passed to selected vector store provider. 
You can check keyword arguments needed by selected provider on Llama-index API reference page: 

https://docs.llamaindex.ai/en/stable/api_reference/storage/vector_store.html


Witch keywords arguments are passed to providers?

For `ChromaVectorStore` and `SimpleVectorStore` all arguments are set by PyGPT and passed internally (you do not need to configure anything).
For other providers you can provide these arguments:

**ElasticsearchStore**

Arguments for ElasticsearchStore(`**kwargs`):

- index_name (default: index name, already set, not required)
- all keyword arguments provided on list


**PinecodeVectorStore**

Arguments for Pinecone(`**kwargs`):

- api_key

Index name is already set and not required.

**RedisVectorStore**

Arguments for RedisVectorStore(`**kwargs`):

- index_name (default: index name, already set, not required)
- all keyword arguments provided on list


You can extend list of available providers by creating custom provider and registering it on app launch.

**Multiple vector databases support is already in beta.**
Will work better in next releases.

By default, you are using chat-based mode when using `Chat with files`.
If you want to only query index (without chat) you can enable `Query index only (without chat)` option.

# Files and attachments

## Input (upload)

**PyGPT** makes it simple for users to upload files to the server and send them to the model for tasks like analysis, similar to attaching files in `ChatGPT`. There's a separate `Files` tab next to the text input area specifically for managing file uploads. Users can opt to have files automatically deleted after each upload or keep them on the list for repeated use.

![v2_file_input](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f61b677a-6c5e-41fb-8029-edc7f0eded0a)

The attachment feature is available in both the `Assistant` and `Vision` modes.

## Files (download, generation)

**PyGPT** enables the automatic download and saving of files created by the model. This is carried out in the background, with the files being saved to an `data` folder located within the user's working directory. To view or manage these files, users can navigate to the `Files` tab which features a file browser for this specific directory. Here, users have the interface to handle all files sent by the AI.

This `data` directory is also where the application stores files that are generated locally by the AI, such as code files or any other data requested from the model. Users have the option to execute code directly from the stored files and read their contents, with the results fed back to the AI. This hands-off process is managed by the built-in plugin system and model-triggered commands. You can also indexing files from this directory (using integrated Llama-index) and use it's contents as additional context provided to discussion.

The `Command: Files I/O` plugin takes care of file operations in the `data` directory, while the `Command: Code Interpreter` plugin allows for the execution of code from these files.

![v2_file_output](https://github.com/szczyglis-dev/py-gpt/assets/61396542/c01ca3fc-c7dd-4532-ae4c-e9c75e2c005c)

To allow the model to manage files or python code execution, the `Execute commands` option must be active, along with the above-mentioned plugins:

![v2_code_execute](https://github.com/szczyglis-dev/py-gpt/assets/61396542/df7087c3-71c7-4387-8ced-4c51cd7d1116)

# Context and memory

## Short and long-term memory

**PyGPT** features a continuous chat mode that maintains a long context of the ongoing dialogue. It preserves the entire conversation history and automatically appends it to each new message (prompt) you send to the AI. Additionally, you have the flexibility to revisit past conversations whenever you choose. The application keeps a record of your chat history, allowing you to resume discussions from the exact point you stopped.

## Handling multiple contexts

On the left side of the application interface, there is a panel that displays a list of saved conversations. You can save numerous contexts and switch between them with ease. This feature allows you to revisit and continue from any point in a previous conversation. **PyGPT** automatically generates a summary for each context, akin to the way `ChatGPT` operates and gives you the option to modify these titles itself.

![v2_context_list](https://github.com/szczyglis-dev/py-gpt/assets/61396542/501f272b-8d91-415a-b0ef-22355c7fdc5f)

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

On the application side, the context is stored in the user's directory as `JSON` files. 
In addition, all history is also saved to `.txt` files for easy reading.

Once a conversation begins, a title for the chat is generated and displayed on the list to the left. This process is similar to `ChatGPT`, where the subject of the conversation is summarized, and a title for the thread is created based on that summary. You can change the name of the thread at any time.

# Presets

## What is preset?

Presets in **PyGPT** are essentially templates used to store and quickly apply different configurations. Each preset includes settings for the mode you want to use (such as chat, completion, or image generation), an initial system message, an assigned name for the AI, a username for the session, and the desired "temperature" for the conversation. A warmer "temperature" setting allows the AI to provide more creative responses, while a cooler setting encourages more predictable replies. These presets can be used across various modes and with models accessed via the `OpenAI API` or `Langchain`.

The system lets you create as many presets as needed and easily switch among them. Additionally, you can clone an existing preset, which is useful for creating variations based on previously set configurations and experimentation.

![v2_preset](https://github.com/szczyglis-dev/py-gpt/assets/61396542/5e1874e2-a5f3-4b91-9412-6fb5b52943b2)

## Example usage

The application includes several sample presets that help you become acquainted with the mechanism of their use.


# Images generation (DALL-E 3 and DALL-E 2)

## DALL-E 3

**PyGPT** enables quick and straightforward image creation with `DALL-E 3`. 
The older model version, `DALL-E 2`, is also accessible. Generating images is akin to a chat conversation  -  a user's prompt triggers the generation, followed by downloading, saving to the computer, 
and displaying the image onscreen. You can send raw prompt to `DALL-E` in `Image generation` mode or ask the model for the best prompt.

**From version 2.0.68 (released 2023-12-31) image generation using DALL-E is available in every mode via plugin `DALL-E 3 Image Generation (inline)`. Just ask any model, in any mode, like e.g. GPT-4 to generate an image and it will do it inline, without need to mode change.**

If you want to generate images (using DALL-E) directly in chat you must enable plugin **DALL-E 3 Inline** in the Plugins menu.
Plugin allows you to generate images in Chat mode:

![v3_img_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/0cf29093-373e-4c71-ab02-9a630f88c68e)

## Multiple variants

You can generate up to **4 different variants** (DALL-E 2) for a given prompt in one session. DALL-E 3 allows one image.
To select the desired number of variants to create, use the slider located in the right-hand corner at 
the bottom of the screen. This replaces the conversation temperature slider when you switch to image generation mode.

## Raw mode

There is an option for switching prompt generation mode.

If **Raw Mode** is enabled, DALL-E will receive the prompt exactly as you have provided it.
If **Raw Mode** is disabled, GPT will generate the best prompt for you based on your instructions.

![v2_dalle2](https://github.com/szczyglis-dev/py-gpt/assets/61396542/d32e753f-7a3f-4e32-86d9-9a479ea24f77)

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
and those supported by `Langchain` to this file. Configuration for Langchain wrapper is placed in `langchain` key.

## Adding custom LLMs via Langchain

To add a new model using the Langchain wrapper in **PyGPT**, insert the model's configuration details into the `models.json` file. This should include the model's name, its supported modes (either `chat`, `completion`, or both), the LLM provider (which can be either e.g. `OpenAI` or `HuggingFace`), and, if you are using a `HuggingFace` model, an optional `API KEY`.

Example of models configuration - `models.json`:

```
"gpt-4-1106-preview": {
    "id": "gpt-4-1106-preview",
    "name": "gpt-4-turbo-1106",
    "mode": [
        "chat",
        "assistant",
        "langchain"
    ],
    "langchain": {
            "provider": "openai",
            "mode": [
                "chat"
            ],
            "args": {
                "model_name": "gpt-4-1106-preview"
            }
        },
        "ctx"
    "ctx": 128000,
    "tokens": 4096
},
"google/flan-t5-xxl": {
    "id": "google/flan-t5-xxl",
    "name": "Google - flan-t5-xxl",
    "mode": [
        "langchain"
    ],
    "langchain": {
        "provider": "huggingface",
        "mode": [
            "chat"
        ],
        "args": {
            "repo_id": "google/flan-t5-xxl"
        },
        "api_key": "XXXXXXXXXXXXXXXXXXXXXX"
    },
    "ctx": 4096,
    "tokens": 4096
},
```

There is bult-in support for those LLMs providers:

```
- OpenAI (openai)
- Azure OpenAI (azure_openai)
- HuggingFace (huggingface)
- Anthropic (anthropic)
- Llama 2 (llama2)
- Ollama (ollama)
```

## Adding custom LLM providers

Handling LLMs with Langchain is implemented through separated wrappers. This allows for the addition of support for any provider and model available via Langchain. All built-in wrappers for the models and its providers are placed in the `llm` directory.

These wrappers are loaded into the application during startup using `launcher.add_llm()` method:

```python
# app.py

from pygpt_net.llm.OpenAI import OpenAILLM
from pygpt_net.llm.AzureOpenAI import AzureOpenAILLM
from pygpt_net.llm.Anthropic import AnthropicLLM
from pygpt_net.llm.HuggingFace import HuggingFaceLLM
from pygpt_net.llm.Llama2 import Llama2LLM
from pygpt_net.llm.Ollama import OllamaLLM

def run(plugins=None, llms=None):
    """Runs the app."""
    # Initialize the app
    launcher = Launcher()
    launcher.init()

    # Register plugins
    ...

    # Register langchain LLMs wrappers
    launcher.add_llm(OpenAILLM())
    launcher.add_llm(AzureOpenAILLM())
    launcher.add_llm(AnthropicLLM())
    launcher.add_llm(HuggingFaceLLM())
    launcher.add_llm(Llama2LLM())
    launcher.add_llm(OllamaLLM())

    # Launch the app
    launcher.run()
```

To add support for providers not included by default, you can create your own wrapper that returns a custom model to the application and then pass this custom wrapper to the launcher.

Extending PyGPT with custom plugins and LLM wrappers is straightforward:

- Pass instances of custom plugins and LLM wrappers directly to the launcher.

To register custom LLM wrappers:

- Provide a list of LLM wrapper instances as the second argument when initializing the custom app launcher.

**Example:**


```python
# my_launcher.py

from pygpt_net.app import run
from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
from my_llms import MyCustomLLM

plugins = [
    MyCustomPlugin(),
    MyOtherCustomPlugin(),
]
llms = [
    MyCustomLLM(),
]

run(plugins=plugins, llms=llms)
```

To integrate your own model or provider into **PyGPT**, you can reference the sample classes located in the `llm` directory of the application. These samples can act as an example for your custom class. Ensure that your custom wrapper class includes two essential methods: `chat` and `completion`. These methods should return the respective objects required for the model to operate in `chat` and `completion` modes.


## Adding custom Vector Store providers

**From version 2.0.114 you can also register your own Vector Store provider**:

```python
# app.y

# vector stores
from pygpt_net.core.idx.storage.chroma import ChromaProvider as ChromaVectorStore
from pygpt_net.core.idx.storage.elasticsearch import ElasticsearchProvider as ElasticsearchVectorStore
from pygpt_net.core.idx.storage.pinecode import PinecodeProvider as PinecodeVectorStore
from pygpt_net.core.idx.storage.redis import RedisProvider as RedisVectorStore
from pygpt_net.core.idx.storage.simple import SimpleProvider as SimpleVectorStore

def run(plugins: list = None,
        llms: list = None,
        vector_stores: list = None):
```

To register your custom vector store provider just register it by passing provier instance to `vector_stores` list:

```python

# my_launcher.py

from pygpt_net.app import run
from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
from my_llms import MyCustomLLM
from my_vector_stores import MyCustomVectorStore

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

run(
    plugins=plugins,
    llms=llms,
    vector_stores=vector_stores
)
```

# Plugins

The application can be enhanced with plugins to add new features.

The following plugins are currently available, and GPT can use them instantly:

- `Command: Google Web Search` - allows searching the internet via the Google Custom Search Engine.

- `Command: Files I/O` - grants access to the local filesystem, enabling GPT to read and write files, 
as well as list and create directories.

- `Command: Code Interpreter` - responsible for generating and executing Python code, functioning much like 
the Code Interpreter on ChatGPT, but locally. This means GPT can interface with any script, application, or code. 
The plugin can also execute system commands, allowing GPT to integrate with your operating system. 
Plugins can work in conjunction to perform sequential tasks; for example, the `Files` plugin can write generated 
Python code to a file, which the `Code Interpreter` can execute it and return its result to GPT.

- `Command: Custom Commands` - allows you to create and execute custom commands on your system.

- `Audio Output (Microsoft Azure)` - provides voice synthesis using the Microsoft Azure Text To Speech API.

- `Audio Output (OpenAI TTS)` - provides voice synthesis using the OpenAI Text To Speech API.

- `Audio Input (OpenAI Whisper)` - offers speech recognition through the OpenAI Whisper API.

- `Autonomous Mode: AI to AI conversation` - Enables autonomous conversation (AI to AI), manages loop, and connects output back to input.

- `Real Time` - automatically adds the current date and time to prompts, informing the model of the real-time moment.

- `DALL-E 3: Image Generation (inline)` - integrates DALL-E 3 image generation with any chat and mode. Just enable and ask for image in Chat mode, using standard model like GPT-4. The plugin does not require the "Execute commands" option to be enabled.

- `GPT-4 Vision (inline)` - integrates Vision capabilities with any chat mode, not just Vision mode. When the plugin is enabled, the model temporarily switches to vision in the background when an image attachment or vision capture is provided.

- `Chat with files (Llama-index, inline)` - plugin integrates `Llama-index` storage in any chat and provides additional knowledge into context (from indexed files and previous context from database). `Experimental`.

- `Crontab / Task scheduler` - plugin provides cron-based job scheduling - you can schedule tasks/prompts to be sent at any time using cron-based syntax for task setup.

## Command: Files I/O

The plugin allows for file management within the local filesystem. It enables the model to create, read, and write files and directories located in the `data` directory, which can be found in the user's work directory. With this plugin, the AI can also generate Python code files and thereafter execute that code within the user's system.

Plugin capabilities include:

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

If a file being created (with the same name) already exists, a prefix including the date and time is added to the file name.

**Options:**

- `Enable: Read file` *cmd_read_file*

Allows `read_file` command. *Default:* `True`

- `Enable: Append to file` *cmd_append_file*

Allows `append_file` command. *Default:* `True`

- `Enable: Save file` *cmd_save_file*

Allows `save_file` command. *Default:* `True`

- `Enable: Delete file` *cmd_delete_file*

Allows `delete_file` command. *Default:* `True`

- `Enable: List files (ls)` *cmd_list_files*

Allows `list_dir` command. *Default:* `True`

- `Enable: List files in dirs in directory (ls)` *cmd_list_dir*

Allows `mkdir` command. *Default:* `True`

- `Enable: Downloading files` *cmd_download_file*

Allows `download_file` command. *Default:* `True`

- `Enable: Removing directories` *cmd_rmdir*

Allows `rmdir` command. *Default:* `True`

- `Enable: Copying files` *cmd_copy_file*

Allows `copy_file` command. *Default:* `True`

- `Enable: Copying directories (recursive)` *cmd_copy_dir*

Allows `copy_dir` command. *Default:* `True`

- `Enable: Move files and directories (rename)` *cmd_move*

Allows `move` command. *Default:* `True`

- `Enable: Check if path is directory` *cmd_is_dir*

Allows `is_dir` command. *Default:* `True`

- `Enable: Check if path is file` *cmd_is_file*

Allows `is_file` command. *Default:* `True`

- `Enable: Check if file or directory exists` *cmd_file_exists*

Allows `file_exists` command. *Default:* `True`

- `Enable: Get file size` *cmd_file_size*

Allows `file_size` command. *Default:* `True`

- `Enable: Get file info` *cmd_file_info*

Allows `file_info` command. *Default:* `True`


## Command: Code Interpreter

### Executing Code

The plugin operates similarly to the `Code Interpreter` in `ChatGPT`, with the key difference that it works locally on the user's system. It allows for the execution of any Python code on the computer that the model may generate. When combined with the `Command: Files I/O` plugin, it facilitates running code from files saved in the `data` directory. You can also prepare your own code files and enable the model to use them or add your own plugin for this purpose. You can execute commands and code on the host machine or in Docker container.

### Executing system commands

Another feature is the ability to execute system commands and return their results. With this functionality, the plugin can run any system command, retrieve the output, and then feed the result back to the model. When used with other features, this provides extensive integration capabilities with the system.

**Options:**

- `Python command template` *python_cmd_tpl*

Python command template (use {filename} as path to file placeholder). *Default:* `python3 {filename}`

- `Enable: Python Code Generate and Execute` *cmd_code_execute*

Allows Python code execution (generate and execute from file). *Default:* `True`

- `Enable: Python Code Execute (File)` *cmd_code_execute_file*

Allows Python code execution from existing file. *Default:* `True`
 
- `Enable: System Command Execute` *cmd_sys_exec*

Allows system commands execution. *Default:* `True`

- `Sandbox (docker container)` *sandbox_docker*

Executes commands in sandbox (docker container). Docker must be installed and running. *Default:* `False`

- `Docker image` *sandbox_docker_image*

Docker image to use for sandbox *Default:* `python:3.8-alpine`


## Command: Custom Commands

With the `Custom Commands` plugin, you can integrate **PyGPT** with your operating system and scripts or applications. You can define an unlimited number of custom commands and instruct GPT on when and how to execute them. Configuration is straightforward, and **PyGPT** includes a simple tutorial command for testing and learning how it works:

![v2_custom_cmd](https://github.com/szczyglis-dev/py-gpt/assets/61396542/2d102ef9-2002-4ab4-8018-52431d5823bb)

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

**PyGPT** provides simple tutorial command to show how it work, to run it just ask GPT for execute `tutorial test command` and it will show you how it works:

```> please execute tutorial test command```

![v2_custom_cmd_example](https://github.com/szczyglis-dev/py-gpt/assets/61396542/b55c25cb-7432-4290-9edb-952edcf3c030)


## Command: Google Web Search

**PyGPT** lets you connect GPT to the internet and carry out web searches in real time as you make queries.

To activate this feature, turn on the `Command: Google Web Search` plugin found in the `Plugins` menu.

Web searches are automated through the `Google Custom Search Engine` API. 
To use this feature, you need an API key, which you can obtain by registering an account at:

https://developers.google.com/custom-search/v1/overview

After registering an account, create a new project and select it from the list of available projects:

https://programmablesearchengine.google.com/controlpanel/all

After selecting your project, you need to enable the `Whole Internet Search` option in its settings. 
Then, copy the following two items into **PyGPT**:

- `Api Key`
- `CX ID`

These data must be configured in the appropriate fields in the `Plugins / Settings...` menu:

![v2_plugin_google](https://github.com/szczyglis-dev/py-gpt/assets/61396542/6f80df94-4bd7-4bc6-bf59-7e1dab188b63)


## Audio Output (Microsoft Azure)

**PyGPT** implements voice synthesis using the `Microsoft Azure Text-To-Speech` API.
This feature requires to have an `Microsoft Azure` API Key. 
You can get API KEY for free from here: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech


To enable voice synthesis, activate the `Audio Output (Microsoft Azure)` plugin in the `Plugins` menu or 
turn on the `Voice` option in the `Audio / Voice` menu (both options in the menu achieve the same outcome).

Before using speech synthesis, you must configure the audio plugin with your Azure API key and the correct 
Region in the settings.

This is done through the `Plugins / Settings...` menu by selecting the `Audio (Azure)` tab:

![v2_azure](https://github.com/szczyglis-dev/py-gpt/assets/61396542/cfd2181c-eb70-42eb-8f73-cdc783defb1c)

**Options:**

- `Azure API Key` *azure_api_key*

Here, you should enter the API key, which can be obtained by registering for free on the following website: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech

- `Azure Region` *azure_region*

You must also provide the appropriate region for Azure here. *Default:* `eastus`

- `Voice (EN)` *voice_en*

Here you can specify the name of the voice used for speech synthesis for English. *Default:* `en-US-AriaNeural`

- `Voice (non-English)` *voice_pl*

Here you can specify the name of the voice used for speech synthesis for other non-english languages. *Default:* `pl-PL-AgnieszkaNeural`

If speech synthesis is enabled, a voice will be additionally generated in the background while generating a response via GPT.

Both `OpenAI TTS` and `OpenAI Whisper` use the same single API key provided for the OpenAI API, with no additional keys required.

## Audio Output (OpenAI TTS)

The plugin enables voice synthesis using the TTS model developed by OpenAI. Using this plugin does not require any additional API keys or extra configuration; it utilizes the main OpenAI key. Through the available options, you can select the voice that you want the model to use.

- `Model` *model*

Choose the model. Available options:

```
  - tts-1
  - tts-1-hd
```
*Default:* `tts-1`

- `Voice` *voice*

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

## Audio Input (OpenAI Whisper)

The plugin facilitates speech recognition using the `Whisper` model by OpenAI. It allows for voice commands to be relayed to the AI using your own voice. The plugin doesn't require any extra API keys or additional configurations; it uses the main OpenAI key. In the plugin's configuration options, you should adjust the volume level (min energy) at which the plugin will respond to your microphone. Once the plugin is activated, a new `Speak` option will appear at the bottom near the `Send` button  -  when this is enabled, the application will respond to the voice received from the microphone.

Configuration options:

- `Model` *model*

Choose the model. *Default:* `whisper-1`

- `Timeout` *timeout*

The duration in seconds that the application waits for voice input from the microphone. *Default:* `2`

- `Phrase max length` *phrase_length*

Maximum duration for a voice sample (in seconds). *Default:* `2`

- `Min energy` *min_energy*

Minimum threshold multiplier above the noise level to begin recording. *Default:* `1.3`

- `Adjust for ambient noise` *adjust_noise*

Enables adjustment to ambient noise levels. *Default:* `True`

- `Continuous listen` *continuous_listen*

EXPERIMENTAL: continuous listening - do not stop listening after a single input. 
Warning: This feature may lead to unexpected results and requires fine-tuning with 
the rest of the options! If disabled, listening must be started manually 
by enabling the `Speak` option. *Default:* `False`

- `Auto send` *auto_send*

Automatically send recognized speech as input text after recognition. *Default:* `True`

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

**Advanced options**

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


## Autonomous Mode: AI to AI conversation

**WARNING: Please use autonomous mode with caution!** - this mode, when connected with other plugins, may produce unexpected results!

The plugin activates autonomous mode, where AI begins a conversation with itself. 
You can set this loop to run for any number of iterations. Throughout this sequence, the model will engage
in self-dialogue, answering his own questions and comments, in order to find the best possible solution, subjecting previously generated steps to criticism.

This mode is similar to `Auto-GPT` - it can be used to create more advanced inferences and to solve problems by breaking them down into subtasks that the model will autonomously perform one after another until the goal is achieved. The plugin is capable of working in cooperation with other plugins, thus it can utilize tools such as web search, access to the file system, or image generation using `DALL-E`.

You can adjust the number of iterations for the self-conversation in the `Plugins / Settings...` menu under the following option:

- `Iterations` *iterations*

*Default:* `3`

**WARNING**: Setting this option to `0` activates an **infinity loop** which can generate a large number of requests and cause very high token consumption, so use this option with caution!

- `Auto-stop after goal is reached` *auto_stop*

If enabled, plugin will stop after goal is reached." *Default:* `True`

- `Prompt` *prompt*

Prompt used to instruct how to handle autonomous mode. You can extend it with your own rules.

*Default:* 

```console
AUTONOMOUS MODE:
1. You will now enter self-dialogue mode, where you will be conversing with yourself, not with a human.
2. When you enter self-dialogue mode, remember that you are engaging in a conversation with yourself. Any user input will be considered a reply featuring your previous response.
3. The objective of this self-conversation is well-defined—focus on achieving it.
4. Your new message should be a continuation of the last response you generated, essentially replying to yourself and extending it.
5. After each response, critically evaluate its effectiveness and alignment with the goal. If necessary, refine your approach.
6. Incorporate self-critique after every response to capitalize on your strengths and address areas needing improvement.
7. To advance towards the goal, utilize all the strategic thinking and resources at your disposal.
8. Ensure that the dialogue remains coherent and logical, with each response serving as a stepping stone towards the ultimate objective.
9. Treat the entire dialogue as a monologue aimed at devising the best possible solution to the problem.
10. Conclude the self-dialogue upon realizing the goal or reaching a pivotal conclusion that meets the initial criteria.
11. You are allowed to use any commands and tools without asking for it.
12. While using commands, always use the correct syntax and never interrupt the command before generating the full instruction.
13. ALWAYS break down the main task into manageable logical subtasks, systematically addressing and analyzing each one in sequence.
14. With each subsequent response, make an effort to enhance your previous reply by enriching it with new ideas and do it automatically without asking for it.
15. Any input that begins with 'user: ' will come from me, and I will be able to provide you with ANY additional commands or goal updates in this manner. The other inputs, not prefixed with 'user: ' will represent your previous responses.
16. Start by breaking down the task into as many smaller sub-tasks as possible, then proceed to complete each one in sequence.  Next, break down each sub-task into even smaller tasks, carefully and step by step go through all of them until the required goal is fully and correctly achieved.
```

**Tip:** do not append `user:` prefix to your input - this prefix is appended to user input automatically behind the scenes.

- `Extended Prompt` *extended_prompt*

Extended Prompt used to instruct how to handle autonomous mode. You can extend it with your own rules. You can choose extended prompt to more extended step-by-step reasoning.

*Default:* 

```console
AUTONOMOUS MODE:
1. You will now enter self-dialogue mode, where you will be conversing with yourself, not with a human.
2. When you enter self-dialogue mode, remember that you are engaging in a conversation with yourself. Any user input will be considered a reply featuring your previous response.
3. The objective of this self-conversation is well-defined—focus on achieving it.
4. Your new message should be a continuation of the last response you generated, essentially replying to yourself and extending it.
5. After each response, critically evaluate its effectiveness and alignment with the goal. If necessary, refine your approach.
6. Incorporate self-critique after every response to capitalize on your strengths and address areas needing improvement.
7. To advance towards the goal, utilize all the strategic thinking and resources at your disposal.
8. Ensure that the dialogue remains coherent and logical, with each response serving as a stepping stone towards the ultimate objective.
9. Treat the entire dialogue as a monologue aimed at devising the best possible solution to the problem.10. Conclude the self-dialogue upon realizing the goal or reaching a pivotal conclusion that meets the initial criteria.
11. You are allowed to use any commands and tools without asking for it.
12. While using commands, always use the correct syntax and never interrupt the command before generating the full instruction.
13. Break down the main task into manageable logical subtasks, systematically addressing and analyzing each one in sequence.
14. With each subsequent response, make an effort to enhance your previous reply by enriching it with new ideas and do it automatically without asking for it.
15. Any input that begins with 'user: ' will come from me, and I will be able to provide you with ANY additional commands or goal updates in this manner. The other inputs, not prefixed with 'user: ' will represent your previous responses.
16. Start by breaking down the task into as many smaller sub-tasks as possible, then proceed to complete each one in sequence.  Next, break down each sub-task into even smaller tasks, carefully and step by step go through all of them until the required goal is fully and correctly achieved.
17. Always split every step into parts: main goal, current sub-task, potential problems, pros and cons, criticism of the previous step, very detailed (about 10-15 paragraphs) response to current subtask, possible improvements, next sub-task to achieve and summary.
18. Do not start the next subtask until you have completed the previous one.
19. Ensure to address and correct any criticisms or mistakes from the previous step before starting the next subtask.
20. Do not finish until all sub-tasks and the main goal are fully achieved in the best possible way. If possible, improve the path to the goal until the full objective is achieved.
21. Conduct the entire discussion in my native language.
22. Upon reaching the final goal, provide a comprehensive summary including all solutions found, along with a complete, expanded response.
```

- `Use extended` *use_extended*

If enabled, extended prompt will be used." *Default:* `False`

- `Reverse roles between iterations` *reverse_roles*

Only for Completion/Langchain modes. 
If enabled, this option reverses the roles (AI <> user) with each iteration. For example, 
if in the previous iteration the response was generated for "Batman," the next iteration will use that 
response to generate an input for "Joker." *Default:* `True`

## Crontab / Task scheduler

Plugin provides cron-based job scheduling - you can schedule tasks/prompts to be sent at any time using cron-based syntax for task setup.

- `Your tasks` *crontab*


Add your cron-style tasks here. 
They will be executed automatically at the times you specify in the cron-based job format. 
If you are unfamiliar with Cron, consider visiting the Cron Guru page for assistance: https://crontab.guru

- `Create a new context on job run` *new_ctx*

If enabled, then a new context will be created on every run of the job." *Default:* `True`


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

## DALL-E 3: Image Generation (inline)

Integrates DALL-E 3 image generation with any chat and mode. Just enable and ask for image in Chat mode, using standard model like GPT-4. The plugin does not require the "Execute commands" option to be enabled.

**Options**

- `Prompt` *prompt*

Prompt used for generating a query for DALL-E in background.

## GPT-4 Vision (inline)

Plugin integrates vision capabilities with any chat mode, not just Vision mode. When the plugin is enabled, the model temporarily switches to vision in the background when an image attachment or vision capture is provided.

**Options**

- `Model` *model*

The model used to temporarily provide vision capabilities; default is `gpt-4-vision-preview`.


- `Prompt` *prompt*

Prompt used for vision mode. It will append or replace current system prompt when using vision model.


- `Replace prompt` *replace_prompt*

replace_prompt.description = Replace whole system prompt with vision prompt against appending it to the current prompt.


- `Allow command: camera capture` *cmd_capture*

Allow to use command: camera capture (`Execute commands` option enabled is required).
If enabled, model will be able to capture images from camera itself.


- `Allow command: make screenshot` *screenshot*

Allow to use command: make screenshot (`Execute commands` option enabled is required).
If enabled, model will be able to making screenshots itself.


## Chat with files (Llama-index, inline)

Plugin integrates Llama-index storage in any chat and provides additional knowledge into context.

- `Ask Llama-index first` *ask_llama_first*


When enabled, then Llama-index will be asked first, and response will be used as additional knowledge in prompt. When disabled, then Llama-index will be asked only when needed.

- `Model` *model_query*


Model used for querying Llama-index, default: gpt-3.5-turbo

- `Indexes IDs` *idx*


Indexes to use, default: base, if you want to use multiple indexes at once then separate them by comma.

# Creating Your Own Plugins

You can create your own plugin for **PyGPT** at any time. The plugin can be written in Python and then registered with the application just before launching it. All plugins included with the app are stored in the `plugin` directory - you can use them as coding examples for your own plugins.

Extending PyGPT with custom plugins and LLMs wrappers:

- You can pass custom plugin instances and LLMs wrappers to the launcher.

- This is useful if you want to extend PyGPT with your own plugins and LLMs.

To register custom plugins:

- Pass a list with the plugin instances as the first argument.

To register custom LLMs wrappers:

- Pass a list with the LLMs wrappers instances as the second argument.

**Example:**


```python
# my_launcher.py

from pygpt_net.app import run
from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
from my_llms import MyCustomLLM

plugins = [
    MyCustomPlugin(),
    MyOtherCustomPlugin(),
]
llms = [
    MyCustomLLM(),
]

run(plugins, llms)  # <-- plugins as the first argument
```

## Handling events

In the plugin, you can receive and modify dispatched events.
To do this, create a method named `handle(self, event, *args, **kwargs)` and handle the received events like here:

```python
# my_plugin.py

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

Syntax: **event name** - triggered on, `event data` *(data type)*:

- **AI_NAME** - when preparing an AI name, `data['value']` *(string, name of the AI assistant)*

- **AUDIO_INPUT_STOP** - force stop audio input

- **AUDIO_INPUT_TOGGLE** - when speech input is enabled or disabled, `data['value']` *(bool, True/False)*

- **AUDIO_OUTPUT_STOP** - force stop audio output

- **AUDIO_OUTPUT_TOGGLE** - when speech output is enabled or disabled, `data['value']` *(bool, True/False)*

- **AUDIO_READ_TEXT** - on text read with speech synthesis, `data['value']` *(str)*

- **CMD_EXECUTE** - when a command is executed, `data['commands']` *(list, commands and arguments)*

- **CMD_INLINE** - when an inline command is executed, `data['commands']` *(list, commands and arguments)*

- **CMD_SYNTAX** - when appending syntax for commands, `data['prompt'], data['syntax']` *(string, list, prompt and list with commands usage syntax)*

- **CTX_AFTER** - after the context item is sent, `ctx`

- **CTX_BEFORE** - before the context item is sent, `ctx`

- **CTX_BEGIN** - when context item create, `ctx`

- **CTX_END** - when context item handling is finished, `ctx`

- **CTX_SELECT** - when context is selected on list, `data['value']` *(int, ctx meta ID)*

- **DISABLE** - when the plugin is disabled, `data['value']` *(string, plugin ID)*

- **ENABLE** - when the plugin is enabled, `data['value']` *(string, plugin ID)*

- **FORCE_STOP** - on force stop plugins

- **INPUT_BEFORE** - upon receiving input from the textarea, `data['value']` *(string, text to be sent)*

- **MODE_BEFORE** - before the mode is selected `data['value'], data['prompt']` *(string, string, mode ID)*

- **MODE_SELECT** - on mode select `data['value']` *(string, mode ID)*

- **MODEL_BEFORE** - before the model is selected `data['value']` *(string, model ID)*

- **MODEL_SELECT** - on model select `data['value']` *(string, model ID)*

- **PLUGIN_SETTINGS_CHANGED** - on plugin settings update

- **PLUGIN_OPTION_GET** - on request for plugin option value `data['name'], data['value']` *(string, any, name of requested option, value)*

- **POST_PROMPT** - after preparing a system prompt, `data['value']` *(string, system prompt)*

- **PRE_PROMPT** - before preparing a system prompt, `data['value']` *(string, system prompt)*

- **SYSTEM_PROMPT** - when preparing a system prompt, `data['value']` *(string, system prompt)*

- **UI_ATTACHMENTS** - when the attachment upload elements are rendered, `data['value']` *(bool, show True/False)*

- **UI_VISION** - when the vision elements are rendered, `data['value']` *(bool, show True/False)*

- **USER_NAME** - when preparing a user's name, `data['value']` *(string, name of the user)*

- **USER_SEND** - just before the input text is sent, `data['value']` *(string, input text)*


You can stop the propagation of a received event at any time by setting `stop` to `True`:

```
event.stop = True
```


# Token usage calculation

## Input tokens

The application features a token calculator. It attempts to forecast the number of tokens that 
a particular query will consume and displays this estimate in real time. This gives you improved 
control over your token usage. The app provides detailed information about the tokens used for the user's prompt, 
the system prompt, any additional data, and those used within the context (the memory of previous entries).

**Remember that these are only approximate calculations and do not include, for example, the number of tokens consumed by some plugins. You can find the exact number of tokens used on the OpenAI website.**

![v2_tokens1](https://github.com/szczyglis-dev/py-gpt/assets/61396542/8f1d9217-6610-41ee-a72d-60b3ae45b61d)

## Total tokens

After receiving a response from the model, the application displays the actual total number of tokens used for the query.

![v2_tokens2](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f8f09e58-50bd-4703-aa1c-041a10d14cdd)

# Configuration

## Settings

The following basic options can be modified directly within the application:

``` ini
Config -> Settings...
```

![v2_settings](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f4be3d53-23ee-4b0e-9e46-296253f688b8)

- `OpenAI API KEY`: The personal API key you'll need to enter into the application for it to function.

- `OpenAI ORGANIZATION KEY`: The organization's API key, which is optional for use within the application.

- `Font Size (chat window)`: Adjusts the font size in the chat window for better readability.

- `Font Size (input)`: Adjusts the font size in the input window for better readability.

- `Font Size (ctx list)`: Adjusts the font size in contexts list.

- `Font Size (toolbox)`: Adjusts the font size in toolbox on right.

- `Layout density`: Adjusts layout elements density. "Apply changes" required to take effect. Default: 0. 

- `DPI scaling`: Enable/disable DPI scaling. Restart of app required. Default: true. 

- `DPI factor`: DPI factor. Restart of app required. Default: 1.0. 

- `Use theme colors in chat window`: use color theme in chat window, Default: True

- `Max Output Tokens`: Determines the maximum number of tokens the model can generate for a single response.

- `Max Total Tokens`: Defines the maximum token count that the application can send to the model, 
including the conversation context. To prevent reaching the model capacity, this setting helps 
manage the size of the context included in messages.

- `Context Threshold`: Sets the number of tokens reserved for the model to respond to the next prompt. 
This helps accommodate responses without exceeding the model's limit, such as 4096 tokens.

- `Limit of last contexts on list to show  (0 = unlimited)`: Limit of last contexts on list, default: 0 (unlimited)

- `Use Context`: Toggles the use of conversation context (memory of previous inputs). 
When turned off, the context won't be saved or factored into conversation responses.

- `Store History`: Dictates whether the conversation history and context are saved. 
When turned off, history won't be written to the disk upon closing the application.

- `Store Time in History`: Chooses whether timestamps are added to the .txt files. 
These files are stored in the *history* directory within the user's work directory.

- `Lock incompatible modes`: If enabled, the app will create a new context when switched to an incompatible mode within an existing context.

- `Temperature`: Sets the randomness of the conversation. A lower value makes the model's 
responses more deterministic, while a higher value increases creativity and abstraction.

- `Top-p`: A parameter that influences the model's response diversity, similar to temperature. 
For more information, please check the OpenAI documentation.

- `Frequency Penalty`: Decreases the likelihood of repetition in the model's responses.

- `Presence Penalty`: Discourages the model from mentioning topics that have already been 
brought up in the conversation.

- `DALL-E Image size`: Generated image size (DALL-E 2 only)

- `Number of notepads`: Number of notepad windows (restart is required after every change)

- `Vision: Camera`: Enables camera in Vision mode

- `Vision: Auto capture`: Enables auto-capture on message send in Vision mode

- `Vision: Camera capture width (px)`: Video capture resolution (width)

- `Vision: Camera capture height (px)`: Video capture resolution (heigth)

- `Vision: Camera IDX (number)`: Video capture camera index (number of camera)

- `Vision: Image capture quality`: Video capture image JPEG quality (%)

**Advanced options**:

- `Model used for auto-summary`: Model used for context auto-summary (default: *gpt-3.5-turbo-1106*)

- `Prompt (sys): auto summary`: System prompt for context auto-summary

- `Prompt (user): auto summary`: User prompt for context auto-summary

- `Prompt (append): command execute instruction`: Prompt for appending command execution instructions

- `DALL-E: Prompt (sys): prompt generation`: Prompt for generating prompts for DALL-E (if disabled RAW mode)

- `DALL-E: prompt generation model`: Model used for generating prompts for DALL-E (if disabled RAW mode)


## JSON files

The configuration is stored in JSON files for easy manual modification outside of the application. 
These configuration files are located in the user's work directory within the following subdirectory:

``` ini
{HOME_DIR}/.config/pygpt-net/
```

# Notebook

The application has a built-in notebook, divided into several tabs. This can be useful for storing informations in a convenient way, without the need to open an external text editor. The content of the notebook is automatically saved whenever the content changes.

![v2_notepad](https://github.com/szczyglis-dev/py-gpt/assets/61396542/d055f50d-8823-42de-8c9e-0ebafcc89d71)

# Advanced configuration

## Manual configuration


You can manually edit the configuration files in this directory:

``` ini
{HOME_DIR}/.config/pygpt-net/
```

- `assistants.json` - contains the list of assistants.
- `attachments.json` - keeps track of the current attachments.
- `config.json` - holds the main configuration settings.
- `indexes.json` - holds information about `Llama-index` indexes
- `models.json` - stores models configurations.
- `capture` - a directory for captured images from camera
- `css` - a directory for CSS stylesheets (user override)
- `history` - a directory for history logs in `.txt` format.
- `idx` - `Llama-index` indexes
- `img` - a directory for images generated with `DALL-E 3` and `DALL-E 2`, saved as `.png` files.
- `locale` - a directory for locales (user override)
- `data` - a directory for data files and files downloaded/generated by GPT.
- `presets` - a directory for presets stored as `.json` files.
- `db.sqlite` - database with contexts and notepads data

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

**Overwriting CSS and locales with your own files:**

You can also overwrite files in the `locale` and `css` app directories with your own files in the user directory. 
This allows you to overwrite language files or CSS styles in a very simple way - by just creating files in your working directory.


``` ini
{HOME_DIR}/.config/pygpt-net/
```

- `locale` - a directory for locales in `.ini` format.
- `css` - a directory for css styles in `.css` format.

---

## Updates

### Updating PyGPT

**PyGPT** comes with an integrated update notification system. When a new version with additional features is released, you'll receive an alert within the app. 

To update, just download the latest release and begin using it instead of the old version. Rest assured, all your personalized settings such as saved contexts and conversation history will be retained and instantly available in the new version.


## Coming soon

- Enhanced integration with Langchain
- Vector databases support
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

# 2.0.114 (2024-01-21)

- Added support for Vector Store databases: `Chroma`, `Elasticsearch`, `Pinecone` and `Redis` (beta)
- Added config options for selecting and configuring Vector Store providers
- Added ability to extend PyGPT with custom Vector Store providers
- Added commands to the `Vision (inline)` plugin: get camera capture and make screenshot. Options must be enabled in the plugin settings. When enabled, they allow the model to capture images from the camera and make screenshots itself.
- Added `Query index only (without chat)` option to `Chat with files` mode.

# 2.0.113 (2024-01-20)

- Added %workdir% placeholder to attachments and images files paths storage for more flexibility in moving data between environments
- Refactored base plugin options handling

# 2.0.112 (2024-01-19)

- Fixed image variants slider in image mode
- Fixed vision checkbox visibility
- Fixed user directory path when handling different directories/symlinks
- Added config option for disable opening image dialog after image generate
- Added Scheduled tasks entry in taskbar dropdown
- Added * (asterisk) indicator after date modified if newer than last indexed time
- Date of modified in file explorer changed to format YYYY-MM-DD HH:MM:SS

# 2.0.111 (2024-01-19)

- Fixed: opening files and directories in Snap and Windows versions
- Fixed: camera capture handling between mode switch
- Added: info about snap connect camera in Snap version (if not connected)
- Added: missing app/tray icon in compiled versions

# 2.0.110 (2024-01-19)

- Fixed bug: history file clear on ctx remove - bug [#9](https://github.com/szczyglis-dev/py-gpt/issues/9)
- Vision inline allowed in modes: Langchain and Chat with files (llama-index)
- Event names moved to Event class

## 2.0.109 (2024-01-18)

- Fixed bug: float inputs value update behaviour - bug [#8](https://github.com/szczyglis-dev/py-gpt/issues/8)
- Added: plugin description tooltips - feature [#7](https://github.com/szczyglis-dev/py-gpt/issues/7)
- Added: focus window on "New context..." in tray - feature [#13](https://github.com/szczyglis-dev/py-gpt/issues/13)
- Added: Ask with screenshot option to tray menu - feature [#11](https://github.com/szczyglis-dev/py-gpt/issues/11)
- Added: Open Notepad option to tray menu - feature [#14](https://github.com/szczyglis-dev/py-gpt/issues/14)


The full changelog is located in the **[CHANGELOG.md](CHANGELOG.md)** file in the main folder of this repository.


# Credits and links

**Official website:** <https://pygpt.net>

**Documentation:** <https://pygpt.readthedocs.io>

**GitHub:** <https://github.com/szczyglis-dev/py-gpt>

**Snap Store:** <https://snapcraft.io/pygpt>

**PyPI:** <https://pypi.org/project/pygpt-net>

**Author:** Marcin Szczygliński (Poland, EU)

**Contact:** <info@pygpt.net>

**License:** MIT License

