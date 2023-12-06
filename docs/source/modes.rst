Chat, completion, assistants and vision
=======================================

Chat
----
This default mode operates very similarly to ``ChatGPT``, allowing you to engage in conversation 
with models like ``GPT-4``, ``GPT-4 Turbo``, ``GPT-3.5``, and ``GPT-3``. You have the flexibility 
to switch between the currently active model at any time. This mode employs the `ChatCompletion API`.

The central area of the application interface features a chat window, with a user text input field (prompt) 
just below it. On the right side of the application window, you can effortlessly define or modify 
your system prompt for the model or craft a prompt preset and save it for future use. 
This feature enables you to swiftly move between various model configurations, facilitating convenient 
experimentation.

Displayed between the chat window and the input field is a real-time calculation of the number of 
tokens that a particular query will consume. Additionally, a file (attachment) upload functionality 
is accessible here. Simply navigate to the `Files` tab to manage files and attachments, 
which can be uploaded to the OpenAI API.

.. image:: images/v2_mode_chat.png
   :width: 800



Text Completion
---------------
This advanced mode is more comprehensive and offers greater utilization of Large Language Models (LLMs). 
While operating similarly to a chat interface, it provides more configuration options and features than 
standard chat interactions. In this mode, you can engage the model in a wider array of tasks, 
such as text completion, simulating conversations as various characters, text analysis, and much more. 
It grants access to any model supported by the OpenAI API as well as models available through Langchain integration.

As with chat mode, on the right side, you'll find handy presets that enable you to freely configure 
the model and rapidly switch between different configurations and prompt templates.

This mode also introduces fields for naming the AI and the user, allowing you to, for instance, 
simulate conversations between fictional characters  -  like Batman and the Joker  -  if defined in 
the starting prompt. These options open up creative opportunities to explore various dialogue 
scenarios in a fun and imaginative way.

.. image:: images/v2_mode_completion.png
   :width: 800

In this mode, models from the ``davinci`` family within ``GPT-3`` are available. 
**Note:** The `davinci` models are slated for deprecation in the near future.


Assistants
----------
This mode uses the new OpenAI's **Assistants API**.

It looks similar to the standard chat mode but further provides access to tools such as a ``Code Interpreter``, 
``Retrieval Files``, and ``Functions``. File uploads and downloads are also featured in this mode. 
**PYGPT** offers pragmatic support for file management; you can rapidly upload your documents and efficiently 
receive and handle files sent to you by the model.

Creating multiple assistants is a one-click process, and they automatically synchronize with the OpenAI API. 
Importing your existing assistants from OpenAI is smooth and straightforward.

Please note that token usage calculation is unavailable in this mode. Nonetheless, file (attachment) 
uploads are supported. Simply navigate to the ``Files`` tab to effortlessly manage files and attachments which 
can be sent to the OpenAI API.

.. image:: images/v2_mode_assistant.png
   :width: 800


Vision (GPT-4 Vision)
---------------------

This mode enables image analysis using the ``GPT-4 Vision`` model. Functioning much like the chat mode, 
it also allows you to upload images or provide URLs to images. The vision feature can analyze both local 
images and those found online.

**1) you can provide an image URL**

.. image:: images/v2_mode_vision.png
   :width: 800

**2) you can also upload your local images**

.. image:: images/v2_mode_vision_upload.png
   :width: 800


Langchain
----------

This mode enables you to work with models that are supported by ``Langchain``. The Langchain wrapper is integrated 
into the application, allowing you to connect to any Large Language Model by simply supplying a configuration 
file for the specific model. You can add as many models as you like; just list them in the configuration 
file named ``models.json``.

Available LLMs providers supported by **PYGPT**:

* OpenAI
* Azure OpenAI
* HuggingFace
* Anthropic
* Llama 2
* Ollama

.. image:: images/v2_mode_langchain.png
   :width: 800

You can create and add your own model wrapper for any specified model not included by default and then register it to application.
How to do this is described in section ``Managing models / Adding models to Langchain``.