Configuration
=============

Settings
--------
The following basic options can be modified directly within the application:

.. code-block:: ini

   Config -> Settings...


.. image:: images/v2_settings.png
   :width: 400

* ``OpenAI API KEY`` The personal API key you'll need to enter into the application for it to function.
* ``OpenAI ORGANIZATION KEY`` The organization's API key, which is optional for use within the application.
* ``Font Size (chat window)`` Adjusts the font size in the chat window for better readability.
* ``Font Size (input)`` Adjusts the font size in the input window for better readability.
* ``Font Size (ctx list)`` Adjusts the font size in contexts list.
* ``Font Size (toolbox)`` Adjusts the font size in toolbox on right.
* ``Layout density`` Adjusts layout elements density. "Apply changes" required to take effect. Default: 0.
* ``DPI scaling`` Enable/disable DPI scaling. Restart of app required. Default: true.
* ``DPI factor`` DPI factor. Restart of app required. Default: 1.0. 
* ``Max Output Tokens`` Determines the maximum number of tokens the model can generate for a single response.
* ``Max Total Tokens`` Defines the maximum token count that the application can send to the model, including the conversation context. To prevent reaching the model capacity, this setting helps manage the size of the context included in messages.
* ``Context Threshold`` Sets the number of tokens reserved for the model to respond to the next prompt. This helps accommodate responses without exceeding the model's limit, such as 4096 tokens.
* ``Limit of last contexts on list to show  (0 = unlimited)`` Limit of last contexts on list, default: 0 (unlimited)
* ``Use Context`` Toggles the use of conversation context (memory of previous inputs). When turned off, the context won't be saved or factored into conversation responses.
* ``Store History`` Dictates whether the conversation history and context are saved. When turned off, history won't be written to the disk upon closing the application.
* ``Store Time in History`` Chooses whether timestamps are added to the .txt files. These files are stored in the *history* directory within the user's work directory.
* ``Context Auto-summary`` Toggles context auto-summarization on contexts list. (GPT-3.5 is used for this)
* ``Lock incompatible modes`` If enabled, the app will create a new context when switched to an incompatible mode within an existing context.
* ``Temperature`` Sets the randomness of the conversation. A lower value makes the model's responses more deterministic, while a higher value increases creativity and abstraction.
* ``Top-p`` A parameter that influences the model's response diversity, similar to temperature. For more information, please check the OpenAI documentation.
* ``Frequency Penalty`` Decreases the likelihood of repetition in the model's responses.
* ``Presence Penalty`` Discourages the model from mentioning topics that have already been brought up in the conversation.
* ``DALL-E Image size`` Generated image size (DALL-E 2 only)
* ``Number of notepads`` Number of notepad windows (restart is required after every change)
* ``Vision: Camera`` Enables camera in Vision mode
* ``Vision: Auto capture`` Enables auto-capture on message send in Vision mode
* ``Vision: Camera capture width (px)`` Video capture resolution (width)
* ``Vision: Camera capture height (px)`` Video capture resolution (heigth)
* ``Vision: Camera IDX (number)`` Video capture camera index (number of camera)
* ``Vision: Image capture quality`` Video capture image JPEG quality (%)

**Advanced options**:

* ``Model used for auto-summary`` Model used for context auto-summary (default: *gpt-3.5-turbo-1106*)
* ``Prompt (sys): auto summary`` System prompt for context auto-summary
* ``Prompt (user): auto summary`` User prompt for context auto-summary
* ``Prompt (append): command execute instruction`` Prompt for appending command execution instructions
* ``DALL-E: Prompt (sys): prompt generation`` Prompt for generating prompts for DALL-E (if disabled RAW mode)
* ``DALL-E: prompt generation model`` Model used for generating prompts for DALL-E (if disabled RAW mode)


JSON files
-----------
The configuration is stored in JSON files for easy manual modification outside of the application. 
These configuration files are located in the user's work directory within the following subdirectory:

.. code-block:: ini

   {HOME_DIR}/.config/pygpt-net/