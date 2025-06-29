Introduction
=============

Overview
----------------

**PyGPT** is **all-in-one** Desktop AI Assistant that provides direct interaction with OpenAI language models, including ``o1``, ``o3``, ``gpt-4``, ``gpt-4 Vision``, and ``gpt-3.5``, through the ``OpenAI API``. By utilizing ``LlamaIndex``, the application also supports alternative LLMs, like those available on ``HuggingFace``, locally available models via ``Ollama`` (like ``Llama 3``, ``Mistral``, ``DeepSeek V3/R1`` or ``Bielik``), ``Google Gemini``, ``Anthropic Claude``, and ``xAI Grok``.

This assistant offers multiple modes of operation such as chat, assistants, completions, and image-related tasks using ``DALL-E 3`` for generation and ``gpt-4o`` and ``gpt-4-vision`` for image analysis. **PyGPT** has filesystem capabilities for file I/O, can generate and run Python code, execute system commands, and manage file transfers. It also allows models to perform web searches with the ``Google`` and ``Microsoft Bing``.

For audio interactions, **PyGPT** includes speech synthesis using the ``Microsoft Azure``, ``Google``, ``Eleven Labs`` and ``OpenAI`` Text-To-Speech services. Additionally, it features speech recognition capabilities provided by ``OpenAI Whisper``, ``Google`` and ``Bing``, enabling the application to understand spoken commands and transcribe audio inputs into text. It features context memory with save and load functionality, enabling users to resume interactions from predefined points in the conversation. Prompt creation and management are streamlined through an intuitive preset system.

**PyGPT**'s functionality extends through plugin support, allowing for custom enhancements. Its multi-modal capabilities make it an adaptable tool for a range of AI-assisted operations, such as text-based interactions, system automation, daily assisting, vision applications, natural language processing, code generation and image creation.

Multiple operation modes are included, such as chatbot, text completion, assistant, vision, Chat with Files (via ``LlamaIndex``), commands execution, external API calls and image generation, making **PyGPT** a multi-tool for many AI-driven tasks.

.. image:: images/v2_main.png
   :width: 800

Features
---------
* Desktop AI Assistant for ``Linux``, ``Windows`` and ``Mac``, written in Python.
* Works similarly to ``ChatGPT``, but locally (on a desktop computer).
* 11 modes of operation: Chat, Chat with Files, Chat with Audio, Research (Perplexity), Completion, Image generation, Vision, Assistants, Experts, Agents and Autonomous Mode.
* Supports multiple models: ``o1``, ``GPT-4o``, ``GPT-4``, ``GPT-3.5``, and any model accessible through ``LlamaIndex`` and ``Ollama`` such as ``Llama 3``, ``Mistral``, ``Google Gemini``, ``xAI Grok``, ``Anthropic Claude``, ``DeepSeek V3/R1``, ``Bielik``, etc.
* Chat with your own Files: integrated ``LlamaIndex`` support: chat with data such as: ``txt``, ``pdf``, ``csv``, ``html``, ``md``, ``docx``, ``json``, ``epub``, ``xlsx``, ``xml``, webpages, ``Google``, ``GitHub``, video/audio, images and other data types, or use conversation history as additional context provided to the model.
* Built-in vector databases support and automated files and data embedding.
* Included support features for individuals with disabilities: customizable keyboard shortcuts, voice control, and translation of on-screen actions into audio via speech synthesis.
* Handles and stores the full context of conversations (short and long-term memory).
* Internet access via ``Google`` and ``Microsoft Bing``.
* Speech synthesis via ``Microsoft Azure``, ``Google``, ``Eleven Labs`` and ``OpenAI`` Text-To-Speech services.
* Speech recognition via ``OpenAI Whisper``, ``Google`` and ``Microsoft Speech Recognition``.
* Real-time video camera capture in Vision mode.
* Image analysis via ``GPT-4 Vision`` and ``GPT-4o``.
* Integrated calendar, day notes and search in contexts by selected date.
* Tools and commands execution (via plugins: access to the local filesystem, Python Code Interpreter, system commands execution, and more).
* Custom commands creation and execution.
* Crontab / Task scheduler included.
* Manages files and attachments with options to upload, download, and organize.
* Context history with the capability to revert to previous contexts (long-term memory).
* Allows you to easily manage prompts with handy editable presets.
* Provides an intuitive operation and interface.
* Includes a notepad.
* Includes simple painter / drawing tool.
* Supports multiple languages.
* Requires no previous knowledge of using AI models.
* Simplifies image generation using ``DALL-E``.
* Fully configurable.
* Themes support.
* Real-time code syntax highlighting.
* Plugins support.
* Built-in token usage calculation.
* Possesses the potential to support future OpenAI models.
* **Open source**; source code is available on ``GitHub``.
* Utilizes the user's own API key.
* and many more.


The application is free, open-source, and runs on PCs with ``Linux``, ``Windows 10``, ``Windows 11`` and ``Mac``. 
Full Python source code is available on ``GitHub``.


**PyGPT uses the user's API key  -  to use the GPT models, 
you must have a registered OpenAI account and your own API key. Local models do not require any API keys.**

.. note::
   This application is not officially associated with OpenAI. The author shall not be held liable for any damages 
   resulting from the use of this application. It is provided "as is," without any form of warranty. 
   Users are reminded to be mindful of token usage - always verify the number of tokens utilized by the model on 
   the OpenAI website and engage with the application responsibly. Activating plugins, such as Web Search, 
   may consume additional tokens that are not displayed in the main window. 
   **Always monitor your actual token usage on the OpenAI website.**
