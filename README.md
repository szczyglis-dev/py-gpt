# PYGPT v2

Release: **2.0.1** build: **2023.12.07** | Official website: https://pygpt.net | Docs: https://pygpt.readthedocs.io

PyPi: https://pypi.org/project/pygpt-net

### **Compiled versions for Linux and Windows**: https://pygpt.net/#download

## Overview

**PYGPT** is **all-in-one** desktop AI assistant that provides direct interaction with OpenAI language models, including `GPT-4`, `GPT-4 Vision`, and `GPT-3.5`, through the `OpenAI API`. The application also integrates with alternative LLMs, like those available on `HuggingFace`, by utilizing `Langchain`.

This assistant offers multiple modes of operation such as chat, assistants, completions, and image-related tasks using `DALL-E 3` for generation and `GPT-4 Vision` for analysis. **PYGPT** has filesystem capabilities for file I/O, can generate and run Python code, execute system commands, and manage file transfers. It also allows models to perform web searches with the `Google Custom Search API`.

For audio interactions, **PYGPT** includes speech synthesis using the `Microsoft Azure Text-to-Speech API` and `OpenAI's TTS API`. Additionally, it features speech recognition capabilities provided by `OpenAI Whisper`, enabling the application to understand spoken commands and transcribe audio inputs into text. It features context memory with save and load functionality, enabling users to resume interactions from predefined points in the conversation. Prompt creation and management are streamlined through an intuitive preset system.

**PYGPT**'s functionality extends through plugin support, allowing for custom enhancements. Its multi-modal capabilities make it an adaptable tool for a range of AI-assisted operations, such as text-based interactions, system automation, vision applications, natural language processing via Langchain, and creative image synthesis.

Multiple operation modes are included, such as chatbot, text completion, assistant, vision, Langchain, and image generation, making **PYGPT** a comprehensive tool for many AI-driven tasks.

![v2_main](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/0c55c04c-130f-412d-8104-f5b4f7f19e7a)

You can download compiled version for Windows and Linux here: https://pygpt.net/#download

## Features

- Desktop AI Assistant for `Windows` and `Linux`, written in Python.
- Works similarly to `ChatGPT`, but locally (on a desktop computer).
- 6 modes of operation: Assistant, Chat, Vision, Completion, Image generation, Langchain.
- Supports multiple models: `GPT-4`, `GPT-3.5`, and `GPT-3`, including any model accessible through `Langchain`.
- Handles and stores the full context of conversations (short-term memory).
- Internet access via `Google Custom Search API`.
- Speech synthesis via `Microsoft Azure TTS` and `OpenAI TTS`.
- Speech recognition via `OpenAI Whisper`.
- Image analysis via `GPT-4 Vision`.
- Integrated `Langchain` support (you can connect to any LLM, e.g., on `HuggingFace`).
- Commands execution (via plugins: access to the local filesystem, Python code interpreter, system commands execution).
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

**PYGPT uses the user's API key  -  to use the application, 
you must have a registered OpenAI account and your own API key.**

You can also use buil-it Langchain support to connect to other Large Language Models (LLMs), 
such as those on HuggingFace. Additional API keys may be required.


# Requirements

## Supported Systems (Compiled Version)

PYGPT is compatible with PCs running `Windows 10`, `Windows 11`, or `Linux`. 
Simply download the installer or the archive for the appropriate version from the download page, 
extract it, install it, and run the application.

## Python Version (Source Code)

An alternative method is to download the source code from GitHub and execute the application using 
the Python interpreter (version 3.9 or higher). The application can also be installed from PyPI 
using the command `pip install` and we recommend this type of installation.

### PyPi (pip)

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

**Troubleshooting**: 

If you have problems with xcb plugin with newer versions of PySide on Linux, e.g. like this:

```commandline
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. 
Reinstalling the application may fix this problem.
```

...then install libxcb on linux:

```commandline
sudo apt install libxcb-cursor0
```

If this not help then try to downgrade PySide to `PySide6-Essentials==6.4.2`:

```commandline
pip install PySide6-Essentials==6.4.2
```

### Running from GitHub source code

1. Clone git repository or download .zip file:

```commandline
git clone https://github.com/szczyglis-dev/py-gpt.git
cd py-gpt
```

2. Create virtual environment:

```commandline
python -m venv venv
source venv/bin/activate
```

3. Install requirements:

```commandline
pip install -r requirements.txt
```

4. Run the application:

```commandline
cd src/pygpt_net
python app.py
```

**Tip**: you can use `PyInstaller` to create a compiled version of
the application for your system (version < 6.x, e.g. 5.13.2).

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

![v2_settings](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/43e24223-2541-4a5a-8caa-aad9279e8b07)


The API key can be obtained by registering on the OpenAI website:

<https://platform.openai.com>

Your API keys will be available here:

<https://platform.openai.com/account/api-keys>

**Note:** The ability to use models within the application depends on the API user's access to a given model!

# Chat, completion, assistants and vision (GPT-4, GPT-3.5, Langchain)

## Chatbot

This mode in **PYGPT** mirrors `ChatGPT`, allowing you to chat with models such as `GPT-4`, `GPT-4 Turbo`, `GPT-3.5`, and `GPT-3`. It's easy to switch models whenever you want. It works by using the `ChatCompletion API`.

The main part of the interface is a chat window where conversations appear. Right below that is where you type your messages. On the right side of the screen, there's a section to set up or change your system prompts. You can also save these setups as presets to quickly switch between different models or tasks.

Above where you type your messages, the interface shows you the number of tokens your message will use up as you type it – this helps to keep track of usage. There's also a feature to upload files in this area. Go to the `Files` tab to manage your uploads or add attachments to send to the OpenAI API (but this makes effect only in `Assisant` and `Vision` modes).

![v2_mode_chat](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/39ae90c4-085c-4777-82f3-f926a3278e5e)

## Completion

This advanced mode provides in-depth access to a broader range of capabilities offered by Large Language Models (LLMs). While it maintains a chat-like interface for user interaction, it introduces additional settings and functional richness beyond typical chat exchanges. Users can leverage this mode to prompt models for complex text completions, role-play dialogues between different characters, perform text analysis, and execute a variety of other sophisticated tasks. It supports any model provided by the OpenAI API as well as other models through `Langchain`.

Similar to chat mode, on the right-hand side of the interface, there are convenient presets. These allow you to fine-tune instructions and swiftly transition between varied configurations and pre-made prompt templates.

Additionally, this mode offers options for labeling the AI and the user, making it possible to simulate dialogues between specific characters - for example, you could create a conversation between Batman and the Joker, as predefined in the prompt. This feature presents a range of creative possibilities for setting up different conversational scenarios in an engaging and exploratory manner.

![v2_mode_completion](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/745eda5f-32cd-4e44-b730-92946592f4f7)

In this mode, models from the `davinci` family within `GPT-3` are available. 
**Note:** The `davinci` models are tagged for deprecation in the near future.

## Assistants

This mode uses the new OpenAI's **Assistants API**.

This mode expands on the basic chat functionality by including additional external tools like a `Code Interpreter` for executing code, `Retrieval Files` for accessing files, and custom `Functions` for enhanced interaction and integration with other APIs or services. In this mode, you can easily upload and download files. **PYGPT** streamlines file management, enabling you to quickly upload documents and manage files created by the model.

Setting up new assistants is simple - a single click is all it takes, and they instantly sync with the `OpenAI API`. Importing assistants you've previously created with OpenAI into **PYGPT** is also a seamless process.

![v2_mode_assistant](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/05a92913-1762-440f-9d5c-36ae9aa23775)

Please note that token usage calculation is unavailable in this mode. Nonetheless, file (attachment) 
uploads are supported. Simply navigate to the `Files` tab to effortlessly manage files and attachments which 
can be sent to the OpenAI API.

## Vision (GPT-4 Vision)

This mode enables image analysis using the `GPT-4 Vision` model. Functioning much like the chat mode, 
it also allows you to upload images or provide URLs to images. The vision feature can analyze both local 
images and those found online.

**1) you can provide an image URL**

![v2_mode_vision](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/6a78042c-0c83-4dd2-865f-48e028b16689)

**2) you can also upload your local images**

![v2_mode_vision_upload](https://github.com/szczyglis-dev/py-gpt/assets/61396542/e9a3ecc2-a083-4d79-96c0-f7b6c522525a)

## Langchain

This mode enables you to work with models that are supported by `Langchain`. The Langchain support is integrated 
into the application, allowing you to interact with any LLM by simply supplying a configuration 
file for the specific model. You can add as many models as you like; just list them in the configuration 
file named `models.json`.

Available LLMs providers supported by **PYGPT**:

```
- OpenAI
- Azure OpenAI
- HuggingFace
- Anthropic
- Llama 2
- Ollama
```

![v2_mode_langchain](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/2c288bc9-41d7-4d92-ac54-68fc10974a0b)

You have the ability to add custom model wrappers for models that are not available by default in **PYGPT**. To integrate a new model, you can create your own wrapper and register it with the application. Detailed instructions for this process are provided in the section titled `Managing models / Adding models via Langchain`.

# Files and attachments

## Input (upload)

**PYGPT** makes it simple for users to upload files to the server and send them to the model for tasks like analysis, similar to attaching files in `ChatGPT`. There's a separate `Files` tab next to the text input area specifically for managing file uploads. Users can opt to have files automatically deleted after each upload or keep them on the list for repeated use.

![v2_file_input](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/af675e8a-6664-48ba-8241-84fe9cb378ec)

The attachment feature is available in both the `Assistant` and `Vision` modes.

## Output (download, generation)

**PYGPT** enables the automatic download and saving of files created by the model. This is carried out in the background, with the files being saved to an `output` folder located within the user's working directory. To view or manage these files, users can navigate to the `Output` tab which features a file browser for this specific directory. Here, users have the interface to handle all files sent by the AI.

This `output` directory is also where the application stores files that are generated locally by the AI, such as code files or any other outputs requested from the model. Users have the option to execute code directly from the stored files and read their contents, with the results fed back to the AI. This hands-off process is managed by the built-in plugin system and model-triggered commands.

The `Command: Files I/O` plugin takes care of file operations in the `output` directory, while the `Command: Code Interpreter` plugin allows for the execution of code from these files.

![v2_file_output](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/363ffa9f-f43e-4f87-89b9-289a3ecd7993)

To allow the model to manage files or python code execution, the `Execute commands` option must be active, along with the above-mentioned plugins:

![v2_code_execute](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/997d98fd-8d19-47f8-9992-38f328ff3421)

# Context and memory

## Short and long-term memory

**PYGPT** features a continuous chat mode that maintains a long context of the ongoing dialogue. It preserves the entire conversation history and automatically appends it to each new message (prompt) you send to the AI. Additionally, you have the flexibility to revisit past conversations whenever you choose. The application keeps a record of your chat history, allowing you to resume discussions from the exact point you stopped.

## Handling multiple contexts

On the left side of the application interface, there is a panel that displays a list of saved conversations. You can save numerous contexts and switch between them with ease. This feature allows you to revisit and continue from any point in a previous conversation. **PYGPT** automatically generates a summary for each context, akin to the way `ChatGPT` operates and gives you the option to modify these titles itself.

![v2_context_list](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/9f0ab805-b887-401e-8c22-59447893d735)

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

Presets in **PYGPT** are essentially templates used to store and quickly apply different configurations. Each preset includes settings for the mode you want to use (such as chat, completion, or image generation), an initial system message, an assigned name for the AI, a username for the session, and the desired "temperature" for the conversation. A warmer "temperature" setting allows the AI to provide more creative responses, while a cooler setting encourages more predictable replies. These presets can be used across various modes and with models accessed via the `OpenAI API` or `Langchain`.

The system lets you create as many presets as needed and easily switch among them. Additionally, you can clone an existing preset, which is useful for creating variations based on previously set configurations and experimentation.

![v2_preset](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/1319ab14-9be2-481c-8294-c03900062883)


## Example usage

The application includes several sample presets that help you become acquainted with the mechanism of their use.


# Images generation (DALL-E 3 and DALL-E 2)

## DALL-E 3

PYGPT enables quick and straightforward image creation with `DALL-E 3`. 
The older model version, `DALL-E 2`, is also accessible. Generating images is akin to a chat conversation  -  
a user's prompt triggers the generation, followed by downloading, saving to the computer, 
and displaying the image onscreen.

## Multiple variants

You can generate up to **4 different variants** for a given prompt in one session. 
To select the desired number of variants to create, use the slider located in the right-hand corner at 
the bottom of the screen. This replaces the conversation temperature slider when you switch to image generation mode.

![v2_dalle](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/d2d901f7-b997-4327-95b3-28cf3222129e)

## Image storage

Once you've generated an image, you can easily save it anywhere on your disk by right-clicking on it. 
You also have the options to delete it or view it in full size in your web browser.

**Tip:** Use presets to save your prepared prompts. 
This lets you quickly use them again for generating new images later on.

The app keeps a history of all your prompts, allowing you to revisit any session and reuse previous 
prompts for creating new images.

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

- `Audio Output (Microsoft Azure)` - provides voice synthesis using the Microsoft Azure Text To Speech API.

- `Audio Output (OpenAI TTS)` - provides voice synthesis using the OpenAI Text To Speech API.

- `Audio Input (OpenAI Whisper)` - offers speech recognition through the OpenAI Whisper API.

- `Self Loop` - creates a self-loop mode, where GPT can generate a continuous conversation between 
two AI instances, effectively talking to itself.

- `Real Time` - automatically adds the current date and time to prompts, informing the model of the real-time moment.


# Managing models

All models are specified in the configuration file `models.json`, which you can customize. 
This file is located in your working directory. You can add new models provided directly by `OpenAI API`
and those supported by `Langchain` to this file. Configuration for Langchain wrapper is placed in `langchain` key.

## Adding custom LLMs via Langchain

To add a new model using the Langchain wrapper in **PYGPT**, insert the model's configuration details into the `models.json` file. This should include the model's name, its supported modes (either `chat`, `completion`, or both), the LLM provider (which can be either e.g. `OpenAI` or `HuggingFace`), and, if you are using a `HuggingFace` model, an optional `API KEY`.

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

from .llm.OpenAI import OpenAILLM
from .llm.AzureOpenAI import AzureOpenAILLM
from .llm.Anthropic import AnthropicLLM
from .llm.HuggingFace import HuggingFaceLLM
from .llm.Llama2 import Llama2LLM
from .llm.Ollama import OllamaLLM

def run():
    """Runs the app."""
    # Initialize the app
    launcher = Launcher()
    launcher.init()

    # Register plugins
    ...

    # Register Langchain LLMs
    launcher.add_llm(OpenAILLM())
    launcher.add_llm(AzureOpenAILLM())
    launcher.add_llm(AnthropicLLM())
    launcher.add_llm(HuggingFaceLLM())
    launcher.add_llm(Llama2LLM())
    launcher.add_llm(OllamaLLM())

    # Launch the app
    launcher.run()
```

To add support for any provider not included by default, simply create your own wrapper that returns a custom model to the application and register your class in a custom launcher, like so:

```python
# custom_launcher.py

from pygpt_net.app import Launcher
from my_llm import MyCustomLLM

def run():
    """Runs the app."""
    # Initialize the app
    launcher = Launcher()
    launcher.init()

    # Register plugins
    ...

    # Register Langchain LLMs
    ...
    launcher.add_llm(MyCustomLLM())

    # Launch the app
    launcher.run()
```

To integrate your own model or provider into **PYGPT**, you can reference the sample classes located in the `llm` directory of the application. These samples can act as an example for your custom class. Ensure that your custom wrapper class includes two essential methods: `chat` and `completion`. These methods should return the respective objects required for the model to operate in `chat` and `completion` modes.


# Plugins

## Command: Files I/O

The plugin allows for file management within the local filesystem. It enables the model to create, read, and write files and directories located in the `output` directory, which can be found in the user's work directory. With this plugin, the AI can also generate Python code files and thereafter execute that code within the user's system.

Plugin capabilities include:

- Reading files
- Writing files
- Executing code from files
- Creating directories
- Listing files and directories

If a file being created (with the same name) already exists, a prefix including the date and time is added to the file name.


## Command: Code Interpreter

### Executing Code

The plugin operates similarly to the `Code Interpreter` in `ChatGPT`, with the key difference that it works locally on the user's system. It allows for the execution of any Python code on the computer that the model may generate. When combined with the `Command: Files I/O` plugin, it facilitates running code from files saved in the `output` directory. You can also prepare your own code files and enable the model to use them or add your own plugin for this purpose.

### Executing system commands

Another feature is the ability to execute system commands and return their results. With this functionality, the plugin can run any system command, retrieve the output, and then feed the result back to the model. When used with other features, this provides extensive integration capabilities with the system.

**Options:**

- `Python command` *python_cmd*

*Default:* `python3`

Python command name.

## Command: Google Web Search

**PYGPT** lets you connect GPT to the internet and carry out web searches in real time as you make queries.

To activate this feature, turn on the `Command: Google Web Search` plugin found in the `Plugins` menu.

Web searches are automated through the `Google Custom Search Engine` API. 
To use this feature, you need an API key, which you can obtain by registering an account at:

https://developers.google.com/custom-search/v1/overview

After registering an account, create a new project and select it from the list of available projects:

https://programmablesearchengine.google.com/controlpanel/all

After selecting your project, you need to enable the `Whole Internet Search` option in its settings. 
Then, copy the following two items into PYGPT:

- `Api Key`
- `CX ID`

These data must be configured in the appropriate fields in the `Plugins / Settings...` menu:

![v2_plugin_google](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/0b6549e0-54f2-410f-a2c9-16c00d2b47c0)



## Audio Output (Microsoft Azure)

**PYGPT** implements voice synthesis using the `Microsoft Azure Text-To-Speech` API.
This feature requires to have an `Microsoft Azure` API Key. 
You can get API KEY for free from here: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech


To enable voice synthesis, activate the `Audio Output (Microsoft Azure)` plugin in the `Plugins` menu or 
turn on the `Voice` option in the `Audio / Voice` menu (both options in the menu achieve the same outcome).

Before using speech synthesis, you must configure the audio plugin with your Azure API key and the correct 
Region in the settings.

This is done through the `Plugins / Settings...` menu by selecting the `Audio (Azure)` tab:

![v2_azure](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/d8aeb457-e611-42aa-81f9-618be7e192dc)

**Options:**

- `Azure API Key` *azure_api_key*

Here, you should enter the API key, which can be obtained by registering for free on the following website: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech

- `Azure Region` *azure_region*

*Default:* `eastus`

You must also provide the appropriate region for Azure here.


- `Voice (EN)` *voice_en*

*Default:* `en-US-AriaNeural`

Here you can specify the name of the voice used for speech synthesis for English.


- `Voice (PL)` *voice_pl*

*Default:* `pl-PL-AgnieszkaNeural`

Here you can specify the name of the voice used for speech synthesis for the Polish language.

If speech synthesis is enabled, a voice will be additionally generated in the background while generating a response via GPT.

Both `OpenAI TTS` and `OpenAI Whisper` use the same single API key provided for the OpenAI API, with no additional keys required.

## Audio Output (OpenAI TTS)

The plugin enables voice synthesis using the TTS model developed by OpenAI. Using this plugin does not require any additional API keys or extra configuration; it utilizes the main OpenAI key. Through the available options, you can select the voice that you want the model to use.

- `Model` *model*

*Default:* `tts-1`

Choose the model. Available options:

```
  - tts-1
  - tts-1-hd
```

- `Voice` *voice*

*Default:* `alloy`

Choose the voice. Available voices to choose from:

```
  - alloy
  - echo
  - fable
  - onyx
  - nova
  - shimmer
```

## Audio Input (OpenAI Whisper)

The plugin facilitates speech recognition using the `Whisper` model by OpenAI. It allows for voice commands to be relayed to the AI using your own voice. The plugin doesn't require any extra API keys or additional configurations; it uses the main OpenAI key. In the plugin's configuration options, you should adjust the volume level (min energy) at which the plugin will respond to your microphone. Once the plugin is activated, a new `Speak` option will appear at the bottom near the `Send` button  -  when this is enabled, the application will respond to the voice received from the microphone.

Configuration options:

- `Model` *model*

*Default:* `whisper-1`

Choose the model.

- `Timeout` *timeout*

*Default:* `2`

The number of seconds the application waits for voice input from the microphone.

- `Phrase max length` *phrase_length*

*Default:* `2`

Maximum duration for a voice sample (in seconds).

- `Min energy` *min_energy*

*Default:* `4000`

The minimum volume level for the microphone to trigger voice detection. If the microphone is too sensitive, increase this value.

- `Adjust for ambient noise` *adjust_noise*

*Default:* `True`

Enables adjustment to ambient noise levels.

- `Continuous listen` *continuous_listen*

*Default:* `True`

Enables continuous microphone listening. If the option is enabled, the microphone will be listening at all times. If disabled, listening must be started manually by enabling the `Speak` option.


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

*Default:* `True`

The option clears the previous answer in the context, which is then used as input for the next iteration.


- `Reverse roles between iterations` *reverse_roles*

*Default:* `True`

If enabled, this option reverses the roles (AI <> user) with each iteration. For example, 
if in the previous iteration the response was generated for "Batman," the next iteration will use that 
response to generate an input for "Joker."


## Real Time

This plugin automatically adds the current date and time to each system prompt you send. 
You have the option to include just the date, just the time, or both.

When enabled, it quietly enhances each system prompt with current time information before sending it to GPT.

**Options**

- `Append time` *hour*

*Default:* `True`

If enabled, it appends the current time to the system prompt.


- `Append date` *date*

*Default:* `True`

If enabled, it appends the current date to the system prompt.


- `Template` *tpl*

*Default:* `Current time is {time}.`

Template to append to the system prompt. The placeholder `{time}` will be replaced with the 
current date and time in real-time.

# Creating Your Own Plugins

You can create your own plugin for **PYGPT** at any time. The plugin can be written in Python and then registered with the application just before launching it. All plugins included with the app are stored in the `plugin` directory - you can use them as coding examples for your own plugins. Then, you can create your own and register it in the system using:

```python
# custom_launcher.py

from pygpt_net.app import Launcher
from my_plugin import MyPlugin


def run():
    """Runs the app."""
    # Initialize the app
    launcher = Launcher()
    launcher.init()

    # Add your plugins
    ...
    launcher.add_plugin(MyPlugin())

    # Launch the app
    launcher.run()
```

# Token usage calculation

## Input tokens

The application features a token calculator. It attempts to forecast the number of tokens that 
a particular query will consume and displays this estimate in real time. This gives you improved 
control over your token usage. The app provides detailed information about the tokens used for the user's prompt, 
the system prompt, any additional data, and those used within the context (the memory of previous entries).

![v2_tokens1](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/6498a81b-8684-42fa-8c04-6553d4e60a12)

## Total tokens

After receiving a response from the model, the application displays the actual total number of tokens used for the query.

![v2_tokens2](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/bef4b5c3-e0a2-4af8-ba08-5e5a86029222)

# Configuration

## Settings

The following basic options can be modified directly within the application:

``` ini
Config -> Settings...
```

![v2_settings](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/43e24223-2541-4a5a-8caa-aad9279e8b07)

- `Temperature`: Sets the randomness of the conversation. A lower value makes the model's 
responses more deterministic, while a higher value increases creativity and abstraction.

- `Top-p`: A parameter that influences the model's response diversity, similar to temperature. 
For more information, please check the OpenAI documentation.

- `Frequency Penalty`: Decreases the likelihood of repetition in the model's responses.

- `Presence Penalty`: Discourages the model from mentioning topics that have already been 
brought up in the conversation.

- `Use Context`: Toggles the use of conversation context (memory of previous inputs). 
When turned off, the context won't be saved or factored into conversation responses.

- `Store History`: Dictates whether the conversation history and context are saved. 
When turned off, history won't be written to the disk upon closing the application.

- `Store Time in History`: Chooses whether timestamps are added to the .txt files. 
These files are stored in the *history* directory within the user's work directory.

- `Context Threshold`: Sets the number of tokens reserved for the model to respond to the next prompt. 
This helps accommodate responses without exceeding the model's limit, such as 4096 tokens.

- `Max Output Tokens`: Determines the maximum number of tokens the model can generate for a single response.

- `Max Total Tokens`: Defines the maximum token count that the application can send to the model, 
including the conversation context. To prevent reaching the model capacity, this setting helps 
manage the size of the context included in messages.

- `Font Size`: Adjusts the font size in the chat window for better readability.

- `OpenAI API KEY`: The personal API key you'll need to enter into the application for it to function.

- `OpenAI ORGANIZATION KEY`: The organization's API key, which is optional for use within the application.

## JSON files

The configuration is stored in JSON files for easy manual modification outside of the application. 
These configuration files are located in the user's work directory within the following subdirectory:

``` ini
{HOME_DIR}/.config/pygpt-net/
```

# Notebook

The application has a built-in notebook, divided into several tabs. This can be useful for storing informations in a convenient way, without the need to open an external text editor. The content of the notebook is automatically saved whenever the content changes.

![v2_notepad](https://github.com/szczyglis-dev/extended-dump-bundle/assets/61396542/515daacc-e079-444f-bff0-b135339feb51)


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
- `history` - a directory for history logs in `.txt` format.
- `img` - a directory for images generated with `DALL-E 3` and `DALL-E 2`, saved as `.png` files.
- `output` - a directory for output files and files downloaded/generated by GPT.
- `presets` - a directory for presets stored as `.json` files.

---

## Translations / Locale

Locale `.ini` files are located in the directory:

``` ini
./data/locale
```

This directory is automatically scanned when the application launches. To add a new translation, 
create and save the file with the appropriate name, for example:

``` ini
locale.es.ini   
```

This will add Spanish as a selectable language in the application's language menu.

---

## Updates

### Updating PYGPT

**PYGPT** comes with an integrated update notification system. When a new version with additional features is released, you'll receive an alert within the app. 

To update, just download the latest release and begin using it instead of the old version. Rest assured, all your personalized settings such as saved contexts and conversation history will be retained and instantly available in the new version.


## Coming soon

- Enhanced integration with Langchain and the Assistants API (functions management, etc.)
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

**PyPI:** <https://pypi.org/project/pygpt-net>

**Author:** Marcin Szczygliński (Poland, UE)

**Contact:** <info@pygpt.net>

**License:** MIT License

