Chat, completion, assistants and vision
=======================================

Chat (+ inline Vision and Image generation)
----
This mode in **PyGPT** mirrors ``ChatGPT``, allowing you to chat with models such as ``GPT-4``, ``GPT-4 Turbo``, ``GPT-3.5``, and ``GPT-3``. It's easy to switch models whenever you want. It works by using the ``ChatCompletion API``.

The main part of the interface is a chat window where conversations appear. Right below that is where you type your messages. On the right side of the screen, there's a section to set up or change your system prompts. You can also save these setups as presets to quickly switch between different models or tasks.

Above where you type your messages, the interface shows you the number of tokens your message will use up as you type it – this helps to keep track of usage. There's also a feature to upload files in this area. Go to the ``Files`` tab to manage your uploads or add attachments to send to the OpenAI API (but this takes effect only in `Assisant` and `Vision` modes)..

.. image:: images/v2_mode_chat.png
   :width: 800


**Vision:** If you want to send photos or image from camera to analysis you must enable plugin "GPT-4 Vision Inline" in the Plugins menu.
Plugin allows you to send photos or image from camera to analysis in any Chat mode:


.. image:: images/v3_vision_plugins.png
   :width: 600

With this plugin, you can capture an image with your camera or attach an image and send it for analysis to discuss the photograph:

.. image:: images/v3_vision_chat.png
:width: 800


**Image generation:** If you want to generate images (using DALL-E) directly in chat you must enable plugin "DALL-E 3 Inline" in the Plugins menu.
Plugin allows you to generate images in Chat mode:

.. image:: images/v3_img_chat.png
:width: 800


Text Completion
---------------
This advanced mode provides in-depth access to a broader range of capabilities offered by Large Language Models (LLMs). While it maintains a chat-like interface for user interaction, it introduces additional settings and functional richness beyond typical chat exchanges. Users can leverage this mode to prompt models for complex text completions, role-play dialogues between different characters, perform text analysis, and execute a variety of other sophisticated tasks. It supports any model provided by the OpenAI API as well as other models through ``Langchain``.

Similar to chat mode, on the right-hand side of the interface, there are convenient presets. These allow you to fine-tune instructions and swiftly transition between varied configurations and pre-made prompt templates.

Additionally, this mode offers options for labeling the AI and the user, making it possible to simulate dialogues between specific characters - for example, you could create a conversation between Batman and the Joker, as predefined in the prompt. This feature presents a range of creative possibilities for setting up different conversational scenarios in an engaging and exploratory manner.

.. image:: images/v2_mode_completion.png
   :width: 800

In this mode, models from the ``davinci`` family within ``GPT-3`` are available. 
**Note:** The `davinci` models are tagged for deprecation in the near future.


Assistants
----------
This mode uses the new OpenAI's **Assistants API**.

This mode expands on the basic chat functionality by including additional external tools like a ``Code Interpreter`` for executing code, ``Retrieval Files`` for accessing files, and custom ``Functions`` for enhanced interaction and integration with other APIs or services. In this mode, you can easily upload and download files. **PyGPT** streamlines file management, enabling you to quickly upload documents and manage files created by the model.

Setting up new assistants is simple - a single click is all it takes, and they instantly sync with the ``OpenAI API``. Importing assistants you've previously created with OpenAI into **PyGPT** is also a seamless process.

.. image:: images/v2_mode_assistant.png
   :width: 800

In Assistant mode you are allowed to storage your files (per Assistant) and manage them easily from app:

.. image:: images/v2_mode_assistant_upload.png
   :width: 800

Vision (GPT-4 Vision)
---------------------

This mode enables image analysis using the ``GPT-4 Vision`` model. Functioning much like the chat mode, 
it also allows you to upload images or provide URLs to images. The vision feature can analyze both local 
images and those found online.

**From version 2.0.68** - Vision is integrated into any chat mode via plugin ``GPT-4 Vision (inline)``. Just enable plugin and use Vision in standard modes.

**From version 2.0.14** - Vision mode also includes real-time video capture from camera. To enable capture check the option ``Camera`` on the right-bottom corner. It will enable real-time capturing from your camera. To capture image from camera and append it to chat just click on video at left side. You can also enable ``Auto capture`` - image will be captured and appended to chat message every time you send message.

.. image:: images/v2_capture_enable.png
   :width: 400

**1) Video camera real-time image capture:**

.. image:: images/v2_capture1.png
   :width: 800

.. image:: images/v3_vision_chat.png
   :width: 800

**2) you can also provide an image URL**

.. image:: images/v2_mode_vision.png
   :width: 800

**3) or you can just upload your local images**

.. image:: images/v2_mode_vision_upload.png
   :width: 800


**4) or just use the inline Vision in the standard chat mode.**


Langchain
----------

This mode enables you to work with models that are supported by ``Langchain``. The Langchain support is integrated 
into the application, allowing you to interact with any LLM by simply supplying a configuration 
file for the specific model. You can add as many models as you like; just list them in the configuration 
file named ``models.json``.

Available LLMs providers supported by **PyGPT**:

* OpenAI
* Azure OpenAI
* HuggingFace
* Anthropic
* Llama 2
* Ollama

.. image:: images/v2_mode_langchain.png
   :width: 800

You have the ability to add custom model wrappers for models that are not available by default in **PyGPT**. To integrate a new model, you can create your own wrapper and register it with the application. Detailed instructions for this process are provided in the section titled ``Managing models / Adding models via Langchain``.