Introduction
=============

Overview
----------------

**PYGPT** is an **"all-in-one"** desktop AI assistant that enables you to converse with ``OpenAI`` LLMs such as ``GPT-4``, 
``GPT-4 Vision``, and ``GPT-3.5`` directly from your computer using the ``OpenAI API``. Additionally, the application supports alternative models, 
for instance, those from ``HuggingFace``, facilitated through integrated ``Langchain`` support is built in.

The assistant operates in various modes, including chat, assistant, and completion, as well as generating images 
with ``DALL-E 3`` and analyzing images via ``GPT-4 Vision``. **PYGPT** also offers access to the filesystem for reading 
and writing files, generates and executes Python code, runs system commands, and facilitates files 
uploads and downloads. Moreover, it enables the model to access the internet using the ``Google Custom Search API``.

Assistant supports speech synthesis via ``Microsoft Azure Text-to-Speech API`` and ``OpenAI's TTS API``, 
along with speech recognition through ``OpenAI Whisper``. Additionally, **PYGPT** provides features such as context 
memory support, context storage, and a history of contexts that can be restored at any moment - allowing users to, 
for example, continue a conversation from a specific point in history. The app also offers a user-friendly 
and intuitive presets system that simplifies prompt creation and management. 
Plugin support is available for even more extended functionality.

Multiple operation modes are included, such as chatbot, text completion, assistant, vision, Langchain, 
and image generation, making **PYGPT** a versatile and comprehensive tool for various AI-driven tasks.

.. image:: images/v2_main.png
   :width: 800

Features
---------
* Desktop AI Assistant for ``Windows`` and ``Linux``, written in Python.
* Works similarly to ``ChatGPT``, but locally (on a desktop computer).
* 6 modes of operation: Assistant, Chat, Vision, Completion, Image generation, Langchain.
* Supports multiple models: ``GPT-4``, ``GPT-3.5``, and ``GPT-3``, including any model accessible through ``Langchain``.
* Handles and stores the full context of conversations (short-term memory).
* Internet access via ``Google Custom Search API``.
* Voice synthesis via ``Microsoft Azure TTS`` and ``OpenAI TTS``.
* Voice recognition through ``OpenAI Whisper``.
* Image analysis via ``GPT-4 Vision``.
* Integrated ``Langchain`` support (you can connect to any LLM, e.g., on ``HuggingFace``).
* Commands execution (via plugins: access to the local filesystem, Python code interpreter, system commands execution).
* Manages files and attachments with options to upload, download, and organize.
* Context history with the capability to revert to previous contexts (long-term memory).
* Allows you to easily manage prompts with handy editable presets.
* Provides an intuitive operation and interface.
* Includes a notebook.
* Supports multiple languages.
* Enables the use of all the powerful features of ``GPT-4``, ``GPT-4V``, and ``GPT-3.5``.
* Requires no previous knowledge of using AI models.
* Simplifies image generation using ``DALL-E 3`` and ``DALL-E 2``.
* Possesses the potential to support future OpenAI models.
* Fully configurable.
* Themes support.
* Plugins support.
* Built-in token usage calculation.
* It's open source; source code is available on ``GitHub``.
* Utilizes the user's own API key.


The application is free, open-source, and runs on PCs with ``Windows 10``, ``Windows 11``, and ``Linux``. 
The full Python source code is available on ``GitHub``.


**PYGPT uses the user's API key  -  to utilize the application, 
you must possess a registered OpenAI account and your own API key.**

.. note::
   This application is not officially associated with OpenAI. The author shall not be held liable for any damages 
   resulting from the use of this application. It is provided "as is," without any form of warranty. 
   Users are reminded to be mindful of token usage - always verify the number of tokens utilized by the model on 
   the OpenAI website and engage with the application responsibly. Activating plugins, such as Web Search, 
   may consume additional tokens that are not displayed in the main window. 
   **Always monitor your actual token usage on the OpenAI website.**
