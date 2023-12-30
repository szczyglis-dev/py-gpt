# PyGPT - Desktop AI Assistant

[![pygpt](https://snapcraft.io/pygpt/badge.svg)](https://snapcraft.io/pygpt)

Release: **2.0.67** | build: **2023.12.30** | Python: **3.10+**

Official website: https://pygpt.net | Documentation: https://pygpt.readthedocs.io

Snap Store: https://snapcraft.io/pygpt | PyPi: https://pypi.org/project/pygpt-net

Compiled version for Linux (tar.gz) and Windows 10/11 (msi) 64-bit: https://pygpt.net/#download

## Overview

**PyGPT** is **all-in-one** Desktop AI Assistant that provides direct interaction with OpenAI language models, including `GPT-4`, `GPT-4 Vision`, and `GPT-3.5`, through the `OpenAI API`. The application also integrates with alternative LLMs, like those available on `HuggingFace`, by utilizing `Langchain`.

This assistant offers multiple modes of operation such as chat, assistants, completions, and image-related tasks using `DALL-E 3` for generation and `GPT-4 Vision` for analysis. **PyGPT** has filesystem capabilities for file I/O, can generate and run Python code, execute system commands, execute custom commands and manage file transfers. It also allows models to perform web searches with the `Google Custom Search API`.

For audio interactions, **PyGPT** includes speech synthesis using the `Microsoft Azure Text-to-Speech API` and `OpenAI's TTS API`. Additionally, it features speech recognition capabilities provided by `OpenAI Whisper`, enabling the application to understand spoken commands and transcribe audio inputs into text. It features context memory with save and load functionality, enabling users to resume interactions from predefined points in the conversation. Prompt creation and management are streamlined through an intuitive preset system.

**PyGPT**'s functionality extends through plugin support, allowing for custom enhancements. Its multi-modal capabilities make it an adaptable tool for a range of AI-assisted operations, such as text-based interactions, system automation, daily assisting, vision applications, natural language processing, code generation and image creation.

Multiple operation modes are included, such as chat, text completion, assistant, vision, Langchain, commands execution and image generation, making **PyGPT** a comprehensive tool for many AI-driven tasks.

Video (mp4):

https://github.com/szczyglis-dev/py-gpt/assets/61396542/bbf5076d-6c91-4a45-bbdd-9564d18a6612

Screenshot:

![v2_main](https://github.com/szczyglis-dev/py-gpt/assets/61396542/7216bc26-b580-41bc-b2d9-c7fe5f271450)

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
- Integrated `Langchain` support (you can connect to any LLM, e.g., on `HuggingFace`).
- Commands execution (via plugins: access to the local filesystem, Python code interpreter, system commands execution).
- Custom commands creation and execution
- Manages files and attachments with options to upload, download, and organize.
- Context history with the capability to revert to previous contexts (long-term memory).
- Allows you to easily manage prompts with handy editable presets.
- Provides an intuitive operation and interface.
- Includes a notebook.
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

**Info:** to use camera in Snap version you must connect the camera with interface:

```commandline
sudo snap connect pygpt:camera
```

[![Get it from the Snap Store](https://snapcraft.io/static/images/badges/en/snap-store-black.svg)](https://snapcraft.io/pygpt)

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

## Chatbot

This mode in **PyGPT** mirrors `ChatGPT`, allowing you to chat with models such as `GPT-4`, `GPT-4 Turbo`, `GPT-3.5`, and `GPT-3`. It's easy to switch models whenever you want. It works by using the `ChatCompletion API`.

The main part of the interface is a chat window where conversations appear. Right below that is where you type your messages. On the right side of the screen, there's a section to set up or change your system prompts. You can also save these setups as presets to quickly switch between different models or tasks.

Above where you type your messages, the interface shows you the number of tokens your message will use up as you type it – this helps to keep track of usage. There's also a feature to upload files in this area. Go to the `Files` tab to manage your uploads or add attachments to send to the OpenAI API (but this makes effect only in `Assisant` and `Vision` modes).

![v2_mode_chat](https://github.com/szczyglis-dev/py-gpt/assets/61396542/1579417c-8e8d-4b98-b255-6593103a1c4f)

## Completion

This advanced mode provides in-depth access to a broader range of capabilities offered by Large Language Models (LLMs). While it maintains a chat-like interface for user interaction, it introduces additional settings and functional richness beyond typical chat exchanges. Users can leverage this mode to prompt models for complex text completions, role-play dialogues between different characters, perform text analysis, and execute a variety of other sophisticated tasks. It supports any model provided by the OpenAI API as well as other models through `Langchain`.

Similar to chat mode, on the right-hand side of the interface, there are convenient presets. These allow you to fine-tune instructions and swiftly transition between varied configurations and pre-made prompt templates.

Additionally, this mode offers options for labeling the AI and the user, making it possible to simulate dialogues between specific characters - for example, you could create a conversation between Batman and the Joker, as predefined in the prompt. This feature presents a range of creative possibilities for setting up different conversational scenarios in an engaging and exploratory manner.

![v2_mode_completion](https://github.com/szczyglis-dev/py-gpt/assets/61396542/1c5f80aa-4864-451f-be4d-ee72efd5b0c4)

In this mode, models from the `davinci` family within `GPT-3` are available. 
**Note:** The `davinci` models are tagged for deprecation in the near future.

## Assistants

This mode uses the new OpenAI's **Assistants API**.

This mode expands on the basic chat functionality by including additional external tools like a `Code Interpreter` for executing code, `Retrieval Files` for accessing files, and custom `Functions` for enhanced interaction and integration with other APIs or services. In this mode, you can easily upload and download files. **PyGPT** streamlines file management, enabling you to quickly upload documents and manage files created by the model.

Setting up new assistants is simple - a single click is all it takes, and they instantly sync with the `OpenAI API`. Importing assistants you've previously created with OpenAI into **PyGPT** is also a seamless process.

![v2_mode_assistant](https://github.com/szczyglis-dev/py-gpt/assets/61396542/8752bb86-234b-4769-821d-ac7826f8641f)

In Assistant mode you are allowed to storage your files (per Assistant) and manage them easily from app:

![v2_mode_assistant_upload](https://github.com/szczyglis-dev/py-gpt/assets/61396542/ac599b23-e675-4db1-b7b7-d134fa9b15b1)

Please note that token usage calculation is unavailable in this mode. Nonetheless, file (attachment) 
uploads are supported. Simply navigate to the `Files` tab to effortlessly manage files and attachments which 
can be sent to the OpenAI API.

## Vision (GPT-4 Vision)

This mode enables image analysis using the `GPT-4 Vision` model. Functioning much like the chat mode, 
it also allows you to upload images or provide URLs to images. The vision feature can analyze both local 
images and those found online. 

**From version 2.0.14** - Vision mode also includes real-time video capture from camera. To enable capture check the option "Camera" on the right-bottom corner. It will enable real-time capturing from your camera. To capture image from camera and append it to chat just click on video at left side. You can also enable "Auto capture" mode - image will be captured and appended to chat message every time you send message.

![v2_capture_enable](https://github.com/szczyglis-dev/py-gpt/assets/61396542/dd8ee149-afd2-4d7b-b2be-5c4e9725c584)


**1) Video camera real-time image capture:**

![v2_capture1](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f69a5510-fc34-4073-80ef-fcc5ce5c50a7)


![v2_capture_result](https://github.com/szczyglis-dev/py-gpt/assets/61396542/ac9a8223-75f0-418b-81c7-9855d04ffde3)

**2) ...you can also provide an image URL:**

![v2_mode_vision](https://github.com/szczyglis-dev/py-gpt/assets/61396542/051bfaf7-467c-4e44-bd79-3c28548ea41e)

**3) ...or you can just upload your local images:**

![v2_mode_vision_upload](https://github.com/szczyglis-dev/py-gpt/assets/61396542/1508ccc2-f0a0-4f42-a9e6-106462890dae)

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

You have the ability to add custom model wrappers for models that are not available by default in **PyGPT**. To integrate a new model, you can create your own wrapper and register it with the application. Detailed instructions for this process are provided in the section titled `Managing models / Adding models via Langchain`.

# Files and attachments

## Input (upload)

**PyGPT** makes it simple for users to upload files to the server and send them to the model for tasks like analysis, similar to attaching files in `ChatGPT`. There's a separate `Files` tab next to the text input area specifically for managing file uploads. Users can opt to have files automatically deleted after each upload or keep them on the list for repeated use.

![v2_file_input](https://github.com/szczyglis-dev/py-gpt/assets/61396542/f61b677a-6c5e-41fb-8029-edc7f0eded0a)

The attachment feature is available in both the `Assistant` and `Vision` modes.

## Output (download, generation)

**PyGPT** enables the automatic download and saving of files created by the model. This is carried out in the background, with the files being saved to an `output` folder located within the user's working directory. To view or manage these files, users can navigate to the `Output` tab which features a file browser for this specific directory. Here, users have the interface to handle all files sent by the AI.

This `output` directory is also where the application stores files that are generated locally by the AI, such as code files or any other outputs requested from the model. Users have the option to execute code directly from the stored files and read their contents, with the results fed back to the AI. This hands-off process is managed by the built-in plugin system and model-triggered commands.

The `Command: Files I/O` plugin takes care of file operations in the `output` directory, while the `Command: Code Interpreter` plugin allows for the execution of code from these files.

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
The older model version, `DALL-E 2`, is also accessible. Generating images is akin to a chat conversation  -  
a user's prompt triggers the generation, followed by downloading, saving to the computer, 
and displaying the image onscreen.

## Multiple variants

You can generate up to **4 different variants** (DALL-E 2) for a given prompt in one session. DALL-E 3 allows one image.
To select the desired number of variants to create, use the slider located in the right-hand corner at 
the bottom of the screen. This replaces the conversation temperature slider when you switch to image generation mode.

![v2_dalle](https://github.com/szczyglis-dev/py-gpt/assets/61396542/46b42488-b0fb-4da0-a937-7b04fe7606bd)


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

run(plugins, llms)  # <-- LLMs as the second argument
```

To integrate your own model or provider into **PyGPT**, you can reference the sample classes located in the `llm` directory of the application. These samples can act as an example for your custom class. Ensure that your custom wrapper class includes two essential methods: `chat` and `completion`. These methods should return the respective objects required for the model to operate in `chat` and `completion` modes.

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

- `Self Loop` - creates a self-loop mode, where GPT can generate a continuous conversation between 
two AI instances, effectively talking to itself.

- `Real Time` - automatically adds the current date and time to prompts, informing the model of the real-time moment.

## Command: Files I/O

The plugin allows for file management within the local filesystem. It enables the model to create, read, and write files and directories located in the `output` directory, which can be found in the user's work directory. With this plugin, the AI can also generate Python code files and thereafter execute that code within the user's system.

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

The plugin operates similarly to the `Code Interpreter` in `ChatGPT`, with the key difference that it works locally on the user's system. It allows for the execution of any Python code on the computer that the model may generate. When combined with the `Command: Files I/O` plugin, it facilitates running code from files saved in the `output` directory. You can also prepare your own code files and enable the model to use them or add your own plugin for this purpose. You can execute commands and code on the host machine or in Docker container.

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


## Self Loop

The plugin introduces a "talk with yourself" mode, where GPT begins a conversation with itself. 
You can set this loop to run for any number of iterations. Throughout such a sequence, the model will engage 
in self-dialogue, responding to its own questions and comments. This feature is available in both `Chat` and `Completion` modes. 
To enhance the experience in Completion mode, you can assign specific names (roles) to each participant in the dialogue.

To effectively start this mode, it's important to craft the system prompt carefully, ensuring it indicates to GPT that 
it is conversing with itself. The outcomes can be intriguing, so it's worth exploring what happens when you try this.

You can adjust the number of iterations for the self-conversation in the `Plugins / Settings...` menu under the following option:

- `Iterations` *iterations*

*Default:* `3`

**Additional options:**

- `Clear context output` *clear_output*

The option clears the previous answer in the context, which is then used as input for the next iteration. *Default:* `True`

- `Reverse roles between iterations` *reverse_roles*

If enabled, this option reverses the roles (AI <> user) with each iteration. For example, 
if in the previous iteration the response was generated for "Batman," the next iteration will use that 
response to generate an input for "Joker." *Default:* `True`


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

def handle(self, event, *args, **kwargs):
    """
    Handle dispatched events

    :param event: event object
    """
    name = event.name
    data = event.data
    ctx = event.ctx

    if name == 'input.before':
        self.some_method(data['value'])
    elif name == 'ctx.begin':
        self.some_other_method(ctx)
    else:
    	# ...
```

**List of Events**

Syntax: **event name** - triggered on, `event data` *(data type)*:

- **ai.name** - when preparing an AI name, `data['value']` *(string, name of the AI assistant)*

- **audio.input.toggle** - when speech input is enabled or disabled, `data['value']` *(bool, True/False)*

- **cmd.execute** - when a command is executed, `data['commands']` *(list, commands and arguments)*

- **cmd.syntax** - when appending syntax for commands, `data['prompt'], data['syntax']` *(string, list, prompt and list with commands usage syntax)*

- **ctx.after** - after the context item is sent, `ctx`

- **ctx.before** - before the context item is sent, `ctx`

- **ctx.begin** - when context item create, `ctx`

- **ctx.end** - when context item handling is finished, `ctx`

- **disable** - when the plugin is disabled, `data['value']` *(string, plugin ID)*

- **enable** - when the plugin is enabled, `data['value']` *(string, plugin ID)*

- **input.before** - upon receiving input from the textarea, `data['value']` *(string, text to be sent)*

- **system.prompt** - when preparing a system prompt, `data['value']` *(string, system prompt)*

- **user.name** - when preparing a user's name, `data['value']` *(string, name of the user)*

- **user.send** - just before the input text is sent, `data['value']` *(string, input text)*


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
- `models.json` - stores models configurations.
- `context.json` - maintains an index of contexts.
- `context` - a directory for context files in `.json` format.
- `capture` - a directory for captured images from camera
- `history` - a directory for history logs in `.txt` format.
- `img` - a directory for images generated with `DALL-E 3` and `DALL-E 2`, saved as `.png` files.
- `output` - a directory for output files and files downloaded/generated by GPT.
- `presets` - a directory for presets stored as `.json` files.

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

**Overwriting with your own files:**

You can also overwrite files in the `locale` and `css` app directories with your own files in the user directory. 
This allows you to overwrite language files or CSS styles in a very simple way - by just creating files in your working directory.


``` ini
{HOME_DIR}/.config/pygpt-net/
```

- `locale` - a directory for locales in `.ini` format.
- `css` - a directory for css styles

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

## 2.0.67 (2023-12-30)

- Notepad restore fix

## 2.0.66 (2023-12-30)

- Added "Rename" option to Notepad Tabs (via RMB)
- Improved language switching

## 2.0.65 (2023-12-30)

- Image generation, vision capture and assistants run listeners moved to async threadpool
- Added saving state of scroll value in chat window
- Added search string save and restore
- Added input text save and restore
- Updated tests and code cleanup
- Added translations (only main app): DE, ES, FR, IT, UA 
- Small fixes and optimizations

## 2.0.64 (2023-12-29)

- Commands and plugins execution moved to asynchronous native QT threadpool
- Improved theme switching
- Improved debugger window
- Small fixes and optimizations

# 2.0.63 (2023-12-28)

- Fixed context append bug
- Improved layout resize

## 2.0.62 (2023-12-28)

- Fixed date display on context list
- Added mode display in context tooltips
- Added "Contexts list records limit" config option in settings
- Added tokens calculator tooltips

## 2.0.61 (2023-12-28)

- DALL-E multiple messages in one context fix

## 2.0.60 (2023-12-28)

- Message append fix

## 2.0.59 (2023-12-28)

- Storage of context has been changed from JSON files to SQLite database, automatic migration is included - you will not lose your existing data after update :)
- Added "Search" functionality for contexts and a search input at the bottom.
- Updated contexts now automatically land at the top of the list.
- Added the ability to store more information about each context.
- Integration of searching, utilizing SQLite, and vector database search coming soon.
- Improved DALL-E image generation.

## 2.0.58 (2023-12-27)

- Code refactor
- Added stream response mode to Vision mode
- Added token calculation to Langchain mode
- Optimizations and small fixes

## 2.0.57 (2023-12-26)

- Added threadpool for async workers handling
- Fixed segmentation fault error on app exit
- Refactored class names

## 2.0.56 (2023-12-25)

- Reorganized project structure
- Relative imports changed to absolute imports
- Updated core paths
- Fixed plugin response hanging
- Fixed recursion problem in error logger
- Fixed platform module name

## 2.0.55 (2023-12-25)

- Fixed max model ctx tokens 

## 2.0.54 (2023-12-25)

- Updater new version check moved to post-setup
- Fixed default assistant preset
- Added link to Snap Store to updater window

## 2.0.52 (2023-12-25)

- Added DPI option in settings: enable/disable and scale factor
- Fixed font-size change with mouse scroll on notepad window

## 2.0.51 (2023-12-25)

- Added auto-content truncate before tokens limit exceeded
- Added dynamic max tokens switching
- Fixed real-time tokens calculation

## 2.0.50 (2023-12-25)

- Fixed async logging
- Updated tests

## 2.0.49 (2023-12-24)

- Fixed crash on async command call
- Fixed UI issues
- Added data providers
- Refactored classes

## 2.0.48 (2023-12-23)

- Added custom errors handler with logging.

## 2.0.47 (2023-12-23)

- Added "Copy to Notepad/Input" to the context menu for selected text.
- Added an option to read selected text using speech synthesis in the Notepad window.
- Added a configurable number of notepads.
- Refactored UI classes.
- Added a thread-safe plugin debugger/logger.
- Fixed UI issues.

## 2.0.46 (2023-12-22)

- Improved tokens calculation (added extra tokens from plugins to real-time calculation)
- Added new context menu option to selected text in output/input: "Read with speech synthesis"

## 2.0.45 (2023-12-22)

- Added "light" themes
- Fixed tokens calculation
- Updated tests

## 2.0.44 (2023-12-21)

- Fixed language switch in plugins settings

## 2.0.43 (2023-12-21)

- PyGPT publicated at Snap Store: https://snapcraft.io/pygpt
- Added link to Snap Store in app menu

## 2.0.42 (2023-12-20)

- Audio output library changed to `PyGame` mixer (instead of `PyDub`)
- Added `PyGame` as a dependency and removed `PyDub` and `simpleaudio` dependencies
- Added audio input/output stop immediately on plugin disable

## 2.0.41 (2023-12-20)

- Added "sandbox" feature to the Code Interpreter – it allows the use of any Docker image as an environment for code and commands execution.
- Context auto-summary moved to an async thread.
- Command execution moved to an async thread.

## 2.0.40 (2023-12-19)

- Totally improved material themes support
- Added QSS-configurable themes to chat output window and code highlighter
- Added ability to overriding styles per any theme in user directory
- Fixed UI layout elements
- Fixed DPI issues in Windows systems

## 2.0.39 (2023-12-18)

- Fixed dialogs closing with the Esc key
- Added an indicator for "can append to context in this mode"
- Added functionality to fetch filenames from the API when importing files uploaded to Assistants
- Enabled switching to newly created Assistants after creation
- Optimized class structure

## 2.0.38 (2023-12-18)

- Multi-language support added to plugins
- Implemented feature to override locale and CSS files by overwriting them in the home directory
- Bug fixes

## 2.0.37 (2023-12-18)

- Fixed prompt typing in real-time on the right toolbox
- Added toolbox font change option
- Simplified custom plugins and wrappers for LLMs application (see Docs for more details)
- Bug fixes
- UI fixes

## 2.0.36 (2023-12-18)

- Improved plugins handling
- Added Event Dispatcher and event-based system

## 2.0.35 (2023-12-18)

- Fixed lists focus lost and selection disappearing
- Added clickable links to API keys pages
- Added scroll position store in notepads
- Auto auto-switch to preset after create
- Assistants files and thread moved to external classes
- UI fixes
- Code fixes

## 2.0.34 (2023-12-17)

- Added option "Lock incompatible modes" to prevent mixing of incompatible contexts.
- Added PyPI link to the About menu. 

## 2.0.33 (2023-12-17)

- Fixed dialog's save/update button handlers
- Fixed uploaded files reload in assistants
- Fixed focus loss on assistants list
- Fixed Output Files header
- Fixed UI
- Added delete confirmation to dictionary options
- Added context change lock before response generation
- Added allowed types for contexts
- Added a link to the documentation in the menu
- Added saving state of opened advanced options in plugins
- Disabled mouse scroll on sliders

## 2.0.32 (2023-12-16)

- Added real-time font-size change with CTRL + mouse scroll in input, output and notepad windows
- Increased allowed font-size to 42
- Fixed line display in plugin settings

## 2.0.31 (2023-12-16)

- Speech recognition (Whisper) small fixes, optimization and improvements
- Added advanced internal options to speech recognition config

## 2.0.30 (2023-12-15)

- Speech recognition and synthesis fixes and improvements
- Fixed and improved speech recognition via Whisper
- Fixed and improved voice synthesis via OpenAI TTS and MS Azure
- Added new options to speech recognition: magic words, stop words, auto-send and wait for response
- Added new more intuitive voice input/output control panel in UI

## 2.0.29 (2023-12-14)

- Added config and plugin options getters/setters
- Changed logo
- Small UI fixes

## 2.0.28 (2023-12-14)

- Added new hidden Credentials/API Key field type (asterisks against plain-text)
- Simplified presets editing
- Fixed Assistants function management
- Improved UI
- Improved settings editing

## 2.0.27 (2023-12-14)

- Added specified "url open" command to Web Search plugin
- Added additional advanced options to above plugins
- Improved Web Search and Commands Execution
- Improved updater and config patcher
- Improved command execution logging

## 2.0.26 (2023-12-13)

- Added advanced config options for plugins
- Added additional file operations to Files I/O plugin

## 2.0.25 (2023-12-13)

- Added advanced settings
- Added clear on capture config option
- Added capture quality config option
- Added launcher shortcuts
- Improved plugins
- Improved WebSearch
- Optimized commands response
- Fixed UI issues

## 2.0.24 (2023-12-12)

- Fixed empty string in tokens calculator
- Added attachments reset before auto-capture from camera

## 2.0.23 (2023-12-12)

- Improved python code execution

## 2.0.22 (2023-12-12)

- Fix: env API KEY name for Langchain mode

## 2.0.21 (2023-12-12)

- Simplified assistant configuration
- Added assistant configuration validation
- Improved UI
- Improved language switcher

## 2.0.20 (2023-12-11)

- Improved Assistants API
- Added assistant uploaded files storage
- Added assistant uploaded files management
- Added assistant remote functions management
- Fixed "open in directory" option on Windows in DALL-E image generation
- Improved attachments and file upload management
- Improved UI and more

## 2.0.19 (2023-12-10)

- Optimized DALL-E prompt generator helper

## 2.0.18 (2023-12-10)

- Config fix

## 2.0.17 (2023-12-10)

- Small fixes

## 2.0.16 (2023-12-10)

- Added multiple cameras config
- Added DALL-E prompt generation RAW MODE ON/OFF switch
- Improved camera handling

## 2.0.15 (2023-12-10)

- Added camera release / disable on camera off

## 2.0.14 (2023-12-10)

- Added real-time video capture from camera in "Vision" mode

## 2.0.13 (2023-12-10)

- Fixed path resolving in "open in directory" option on Windows OS
- Added real-time apply of "layout density" (after "save changes" in Settings)
- Default "layout density" changed to 0
- Updated locale

## 2.0.12 (2023-12-09)

- Improved system commands execution

## 2.0.11 (2023-12-09)

- Small fixes

## 2.0.10 (2023-12-09)

- Updated locale

## 2.0.9 (2023-12-09)

- Added `Command: Custom Commands` feature; plugin allows to easily create and execute custom commands
- Added new features to `Command: Files I/O`: downloading files, copying files and dirs, moving files and dirs

## 2.0.8 (2023-12-08)

- Improved Web Search plugin

## 2.0.7 (2023-12-08)

- Improved code execution with Code Interpreter / Files I/O plugins

## 2.0.6 (2023-12-08)

- Added layout density configuration

## 2.0.5 (2023-12-08)

- Added support for external CSS
- Added custom fonts support
- Improved material theme support

## 2.0.4 (2023-12-08)

- Added configuration options for plugins: Files I/O, Code Interpreter
- UI fixes

## 2.0.3 (2023-12-07)

- Python code execution fix

## 2.0.2 (2023-12-07)

- Added python command template settings
- Added layout state restore
- Refactored settings
- Improved settings window
- Bugfixes

## 2.0.1 (2023-12-07)

- Fixed settings dialog initialization
- Fixed models.json migration
- Added enter key behaviour settings
- Added font size settings for input and context list
- Added ctx auto-summary settings
- Added python command plugin settings

## 2.0.0 (2023-12-05)

New features in version 2.0.0:

- Added support for new models: GPT-4 Turbo, GPT-4 Vision, and DALL-E 3
- Integrated Langchain with support for any model it provides
- Assistants API and simple assistant configuration setup
- Vision and image analysis capabilities through GPT-4 Vision
- Image generation with DALL-E 3
- File and attachment support including upload, download, and management
- New built-in notepad feature
- Multiple assistants support
- Command execution support
- Filesystem access allows GPT to read and write files
- Asynchronous (stream) mode added
- Local Python code interpreter that enables code execution by GPT
- System command executions directly from GPT
- Voice synthesis provided via Microsoft Azure TTS and OpenAI TTS (Text-To-Speech)
- Voice recognition provided by OpenAI Whisper
- Automatic summarization of context titles
- Upgraded Web Browser plugin
- More precise token calculation functionality
- Added output markup highlight
- Improved UX
- Bug fixes
- Plus additional enhancements and expanded capabilities

## 0.9.6 (2023.04.16)

- Added real-time logger
- Improved debug mode

## 0.9.5 (2023.04.16)

- Added web plugin (adds access to the Internet using Google Custom Search Engine and Wikipedia API)
- Added voice output plugin (adds voice synthesis using Microsoft Azure)

## 0.9.4 (2023.04.15)

- Added plugins support

## 0.9.3 (2023.04.14)

- Packed into PyPI package

## 0.9.2 (2023.04.12)

- Added theme color settings
- Small UI fixes

## 0.9.1 (2023.04.11)

- Added organization key configuration (by @kaneda2004, PR#1)
- Added config versions patching

## 0.9.0 (2023.04.09)

- Initial release

# Credits and links

**Official website:** <https://pygpt.net>

**Documentation:** <https://pygpt.readthedocs.io>

**GitHub:** <https://github.com/szczyglis-dev/py-gpt>

**Snap Store:** <https://snapcraft.io/pygpt>

**PyPI:** <https://pypi.org/project/pygpt-net>

**Author:** Marcin Szczygliński (Poland, EU)

**Contact:** <info@pygpt.net>

**License:** MIT License

