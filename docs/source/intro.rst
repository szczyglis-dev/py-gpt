Introduction
=============

What is PYGPT?
----------------

**PYGPT** is a desktop application that allows you to talk to OpenAI's LLM
models such as **GPT4** and **GPT3** using your own computer and ``OpenAI API``.
It allows you to talk in chat mode and in completion mode, as well as generate images
using **DALL-E 2**. PYGPT also adds access to the Internet for GPT via Google Custom Search API
and Wikipedia API and includes voice synthesis using Microsoft Azure Text-to-Speech API.
Moreover, the application has implemented context memory support, context storage,
history of contexts, which can be restored at any time and e.g. continue the conversation
from point in history, and also has a convenient and intuitive system of presets that allows
you to quickly and pleasantly create and manage your prompts.

.. image:: images/app1.jpg
   :width: 800

Features
---------
| - desktop application for ``Windows`` and ``Linux``, written in Python
| - works similar to ``ChatGPT``, but locally (on desktop)
| - 3 modes of operation: chatbot, text completion and image generation
| - supports multiple models: ``GPT4`` and ``GPT3``
| - handles and stores full context of the conversation (short-term memory)
| - stores the history of contexts with the ability to return to previous context (long-term memory)
| - adds access to the Internet for GPT via Google Custom Search API and Wikipedia API
| - includes voice synthesis using Microsoft Azure Text-to-Speech API
| - allows you to easily manage prompts with handy editable presets
| - intuitive operation and interface
| - allows you to use all the powerful features of ``GPT4`` and ``GPT3``
| - no knowledge of using AI models required
| - enables easy and convenient generation of images using ``DALL-E 2``
| - has the ability to support future OpenAI models
| - fully configurable
| - plugins support
| - built-in tokens usage calculation
| - it's open source, source code is available on ``GitHub``
| - **uses the user's API key**


The application is free, open source and runs on PC with ``Windows 10``, ``Windows 11`` and ``Linux``. 
The full **Python** source code is available on ``GitHub``.


**PYGPT uses the user's API key - to use the application, you must have a registered OpenAI
account and your own API key.**

**DISCLAIMER**

This application is not affiliated with OpenAI in any way.
Author is not responsible for any damage caused by the use of this application.
Application is provided as is, without any warranty.
Please also remember about tokens usage - always check the number of tokens used by
the model on OpenAI website and use the application responsibly.
Enabled plugins (like e.g. Web Search) may use additional tokens,
not listed in main window. Always control your real token usage on OpenAI website.
