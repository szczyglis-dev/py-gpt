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
   :width: 400

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

**Info:** From version ``2.0.107`` the davinci models are deprecated and has been replaced with ``gpt-3.5-turbo-instruct`` model.


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


Chat with files (Llama-index)
-----------------------------

This mode enables chat interaction with your documents and entire context history through conversation. 
It seamlessly incorporates ``Llama-index`` into the chat interface, allowing for immediate querying of your indexed documents. 
To begin, you must first index the files you wish to include. 
Simply copy or upload them into the ``data`` directory and initiate indexing by clicking the ``Index all`` button, or right-click on a file and select ``Index...``. 
Additionally, you have the option to utilize data from indexed files in any Chat mode by activating the ``Chat with files (Llama-index, inline)`` plugin.

Built-in file loaders (offline): ``text files``, ``pdf``, ``csv``, ``md``, ``docx``, ``json``, ``epub``, ``xlsx``. 
You can extend this list in ``Settings / Llama-index`` by providing list of online loaders (from ``LlamaHub``).
All loaders included for offline use are also from ``LlamaHub``, but they are attached locally with all necessary library dependencies included.

**From version ``2.0.100`` Llama-index is also integrated with database - you can use data from database (your history contexts) as additional context in discussion. 
Options for indexing existing context history or enabling real-time indexing new ones (from database) are available in ``Settings / Llama-index`` section.**

**WARNING:** remember that when indexing content, API calls to the embedding model (``text-embedding-ada-002``) are used. Each indexing consumes additional tokens. 
Always control the number of tokens used on the OpenAI page.

**Tip:** when using ``Chat with files`` you are using additional context from db data and files indexed from ``data`` directory, not the files sending via ``Attachments`` tab. 
Attachments tab in ``Chat with files`` mode can be used to provide images to ``Vision (inline)`` plugin only.

**Available vector stores** (provided by ``Llama-index``):

* ChromaVectorStore
* ElasticsearchStore
* PinecodeVectorStore
* RedisVectorStore
* SimpleVectorStore

You can configure selected vector store by providing config options like ``api_key``, etc. in ``Settings -> Llama-index`` window. 
Arguments provided here (on list: ``Vector Store (**kwargs)`` in ``Advanced settings`` will be passed to selected vector store provider. 
You can check keyword arguments needed by selected provider on Llama-index API reference page: 

https://docs.llamaindex.ai/en/stable/api_reference/storage/vector_store.html

Which keyword arguments are passed to providers?

For ``ChromaVectorStore`` and ``SimpleVectorStore`` all arguments are set by PyGPT and passed internally (you do not need to configure anything). For other providers you can provide these arguments:

**ElasticsearchStore**

Arguments for ElasticsearchStore(``**kwargs``):

* index_name (default: current index ID, already set, not required)
* any other keyword arguments provided on list


**PinecodeVectorStore**

Arguments for Pinecone(``**kwargs``):

* api_key
* index_name (default: current index ID, already set, not required)

**RedisVectorStore**

Arguments for RedisVectorStore(``**kwargs``):

* index_name (default: current index ID, already set, not required)
* any other keyword arguments provided on list


You can extend list of available providers by creating custom provider and registering it on app launch.

**Multiple vector databases support is already in beta.**
Will work better in next releases.

By default, you are using chat-based mode when using ``Chat with files``.
If you want to only query index (without chat) you can enable ``Query index only (without chat)`` option.