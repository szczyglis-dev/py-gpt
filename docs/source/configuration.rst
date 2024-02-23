Configuration
=============

Settings
--------
The following basic options can be modified directly within the application:

.. code-block:: ini

   Config -> Settings...


.. image:: images/v2_settings.png
   :width: 400

**General**

* ``OpenAI API KEY`` The personal API key you'll need to enter into the application for it to function.

* ``OpenAI ORGANIZATION KEY`` The organization's API key, which is optional for use within the application.

* ``Number of notepads`` Number of notepad tabs. Restart of the application is required for this option to take effect.

* ``Show tray icon`` Show/hide tray icon. Tray icon provides additional features like "Ask with screenshot" or "Open notepad". Restart of the application is required for this option to take effect. Default: True.

- ``Minimize to tray on exit``: Minimize to tray icon on exit. Tray icon enabled is required for this option to work. Default: False.

**Layout**

* ``Font Size (chat window)`` Adjusts the font size in the chat window.

* ``Font Size (input)`` Adjusts the font size in the input window.

* ``Font Size (ctx list)`` Adjusts the font size in contexts list.

* ``Font Size (toolbox)`` Adjusts the font size in toolbox on right.

* ``Layout density`` Adjusts layout elements density. Default: -1. 

* ``DPI scaling`` Enable/disable DPI scaling. Restart of the application is required for this option to take effect. Default: True. 

* ``DPI factor`` DPI factor. Restart of the application is required for this option to take effect. Default: 1.0. 

* ``Display tips (help descriptions)`` Display help tips, Default: True.

* ``Store dialog window positions``: Enable or disable dialogs positions store/restore, Default: True.

* ``Use theme colors in chat window`` Use color theme in chat window, Default: True.

* ``Disable markdown formatting in output`` Enable plain-text display in output window, Default: False.

**Files and attachments**

* ``Store attachments in the workdir upload directory``: Enable to store a local copy of uploaded attachments for future use. Default: True

* ``Store images, capture and uploads in data directory``: Enable to store everything in single data directory. Default: False

* ``Directory for file downloads``: Subdirectory for downloaded files, e.g. in Assistants mode, inside "data". Default: "download"

**Context**

* ``Context Threshold`` Sets the number of tokens reserved for the model to respond to the next prompt.

* ``Limit of last contexts on list to show  (0 = unlimited)`` Limit of the last contexts on list, default: 0 (unlimited).

* ``Use Context`` Toggles the use of conversation context (memory of previous inputs).

* ``Store History`` Toggles conversation history store.

* ``Store Time in History`` Chooses whether timestamps are added to the .txt files.

* ``Context Auto-summary`` Enables automatic generation of titles for contexts, Default: True.

* ``Lock incompatible modes`` If enabled, the app will create a new context when switched to an incompatible mode within an existing context.

* ``Search also in conversation content, not only in titles``: When enabled, context search will also consider the content of conversations, not just the titles of conversations.

* ``Model used for auto-summary`` Model used for context auto-summary (default: *gpt-3.5-turbo-1106*).

* ``Prompt (sys): auto summary`` System prompt for context auto-summary.

* ``Prompt (user): auto summary`` User prompt for context auto-summary.

**Models**

* ``Max Output Tokens`` Determines the maximum number of tokens the model can generate for a single response.

* ``Max Total Tokens`` Defines the maximum token count that the application can send to the model, including the conversation context.

* ``Temperature`` Sets the randomness of the conversation. A lower value makes the model's responses more deterministic, while a higher value increases creativity and abstraction.

* ``Top-p`` A parameter that influences the model's response diversity, similar to temperature. For more information, please check the OpenAI documentation.

* ``Frequency Penalty`` Decreases the likelihood of repetition in the model's responses.

* ``Presence Penalty`` Discourages the model from mentioning topics that have already been brought up in the conversation.

* ``Prompt (append): command execute instruction`` Prompt for appending command execution instructions.

**Images**

* ``DALL-E Image size`` The resolution of the generated images (DALL-E). Default: 1792x1024

* ``DALL-E Image quality`` The image quality of the generated images (DALL-E). Default: standard

* ``Open image dialog after generate`` Enable the image dialog to open after an image is generated in Image mode.

* ``DALL-E: Prompt (sys): prompt generation`` Prompt for generating prompts for DALL-E (if RAW mode is disabled).

* ``DALL-E: prompt generation model`` Model used for generating prompts for DALL-E (if RAW mode is disabled).

**Vision**

* ``Vision: Camera capture width (px)`` Video capture resolution (width).

* ``Vision: Camera capture height (px)`` Video capture resolution (height).

* ``Vision: Camera IDX (number)`` Video capture camera index (number of camera).

* ``Vision: Image capture quality`` Video capture image JPEG quality (%).

**Indexes (Llama-index)**

* ``Indexes`` List of created indexes

* ``Auto-index DB in real time`` Enables conversation context auto-indexing.

* ``Recursive directory indexing``: Enables recursive directory indexing, default is False.

* ``Replace old document versions in the index during re-indexing``: If enabled, previous versions of documents will be deleted from the index when the newest versions are indexed, default is True.

* ``Vector Store`` Vector store in use (vector database provided by Llama-index).

* ``Vector Store (**kwargs)`` Arguments for vector store (api_key, index_name, etc.).

* ``Log (console)`` Enables logging to console.

* ``Additional online data loaders`` List of the online data loaders from Llama Hub to use. Only for Python version, will not work in compiled version.

* ``DB (ALL), DB (UPDATE), FILES (ALL)`` Index the data – batch indexing is available here

**Agent (autonomous)**

* ``Sub-mode to use``: Sub-mode to use in Agent mode (chat, completion, langchain, llama_index, etc.). Default: chat.

* ``Index to use``: Only if sub-mode is llama_index (Chat with files), choose the index to use in Agent mode.

* ``Display a tray notification when the goal is achieved.``: If enabled, a notification will be displayed after goal achieved / finished run.

**Updates**

- ``Check for updates on start``: Enables checking for updates on start. Default: True.

- ``Check for updates in background``: Enables checking for updates in background (checking every 5 minutes). Default: True.

**Developer**

* ``Show debug menu`` enables debug (developer) menu

* ``Log llama-index usages to console`` Enables logging llama-index usages to console.


JSON files
-----------
The configuration is stored in JSON files for easy manual modification outside of the application. 
These configuration files are located in the user's work directory within the following subdirectory:

.. code-block:: ini

   {HOME_DIR}/.config/pygpt-net/