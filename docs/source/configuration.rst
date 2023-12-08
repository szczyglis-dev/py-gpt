Configuration
=============

Settings
--------
The following basic options can be modified directly within the application:

.. code-block:: ini

   Config -> Settings...


.. image:: images/v2_settings.png
   :width: 400

* ``Temperature`` Sets the randomness of the conversation. A lower value makes the model's responses more deterministic, while a higher value increases creativity and abstraction.
* ``Top-p`` A parameter that influences the model's response diversity, similar to temperature. For more information, please check the OpenAI documentation.
* ``Frequency Penalty`` Decreases the likelihood of repetition in the model's responses.
* ``Presence Penalty`` Discourages the model from mentioning topics that have already been brought up in the conversation.
* ``Use Context`` Toggles the use of conversation context (memory of previous inputs). When turned off, the context won't be saved or factored into conversation responses.
* ``Context Auto-summary`` Toggles context auto-summarization on contexts list. (GPT-3.5 is used for this)
* ``Store History`` Dictates whether the conversation history and context are saved. When turned off, history won't be written to the disk upon closing the application.
* ``Store Time in History`` Chooses whether timestamps are added to the .txt files. These files are stored in the *history* directory within the user's work directory.
* ``Context Threshold`` Sets the number of tokens reserved for the model to respond to the next prompt. This helps accommodate responses without exceeding the model's limit, such as 4096 tokens.
* ``Max Output Tokens`` Determines the maximum number of tokens the model can generate for a single response.
* ``Max Total Tokens`` Defines the maximum token count that the application can send to the model, including the conversation context. To prevent reaching the model capacity, this setting helps manage the size of the context included in messages.
* ``Font Size (chat window)`` Adjusts the font size in the chat window for better readability.
* ``Font Size (input)`` Adjusts the font size in the input window for better readability.
* ``Font Size (ctx list)`` Adjusts the font size in contexts list.
* ``OpenAI API KEY`` The personal API key you'll need to enter into the application for it to function.
* ``OpenAI ORGANIZATION KEY`` The organization's API key, which is optional for use within the application.
* ``Auto-summary system prompt`` System prompt for context auto-summary (GPT-3.5 is used for this)
* ``Auto-summary instruction`` Summary prompt for context auto-summary (GPT-3.5 is used for this)


JSON files
-----------
The configuration is stored in JSON files for easy manual modification outside of the application. 
These configuration files are located in the user's work directory within the following subdirectory:

.. code-block:: ini

   {HOME_DIR}/.config/pygpt-net/