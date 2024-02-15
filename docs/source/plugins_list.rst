Plugins reference
=================

Audio Input (OpenAI Whisper)
----------------------------

The plugin facilitates speech recognition using the ``Whisper`` model by OpenAI. It allows for voice commands to be relayed to the AI using your own voice. The plugin doesn't require any extra API keys or additional configurations; it uses the main OpenAI key. In the plugin's configuration options, you should adjust the volume level (min energy) at which the plugin will respond to your microphone. Once the plugin is activated, a new ``Speak`` option will appear at the bottom near the ``Send`` button  -  when this is enabled, the application will respond to the voice received from the microphone.

**Options**

- ``Model`` *model*

Choose the model. *Default:* `whisper-1`

- ``Timeout`` *timeout*

The duration in seconds that the application waits for voice input from the microphone. *Default:* `5`

- ``Phrase max length`` *phrase_length*

Maximum duration for a voice sample (in seconds).  *Default:* `10`

- ``Min energy`` *min_energy*

Minimum threshold multiplier above the noise level to begin recording. *Default:* `1.3`

- ``Adjust for ambient noise`` *adjust_noise*

Enables adjustment to ambient noise levels. *Default:* `True`

- ``Continuous listen`` *continuous_listen*

Experimental: continuous listening - do not stop listening after a single input. Warning: This feature may lead to unexpected results and requires fine-tuning with the rest of the options! If disabled, listening must be started manually by enabling the ``Speak`` option. *Default:* `False`

- ``Auto send`` *auto_send*

Automatically send recognized speech as input text after recognition.. *Default:* `True`

- ``Wait for response`` *wait_response*

Wait for a response before initiating listening for the next input. *Default:* `True`

- ``Magic word`` *magic_word*

Activate listening only after the magic word is provided. *Default:* `False`

- ``Reset Magic word`` *magic_word_reset*

Reset the magic word status after it is received (the magic word will need to be provided again). *Default:* `True`

- ``Magic words`` *magic_words*

List of magic words to initiate listening (Magic word mode must be enabled). *Default:* `OK, Okay, Hey GPT, OK GPT`

- ``Magic word timeout`` *magic_word_timeout*

he number of seconds the application waits for magic word. *Default:* `1`

- ``Magic word phrase max length`` *magic_word_phrase_length*

The minimum phrase duration for magic word. *Default:* `2`

- ``Prefix words`` *prefix_words*

List of words that must initiate each phrase to be processed. For example, you can define words like "OK" or "GPT"—if set, any phrases not starting with those words will be ignored. Insert multiple words or phrases separated by commas. Leave empty to deactivate.  *Default:* `empty`

- ``Stop words`` *stop_words*

List of words that will stop the listening process. *Default:* `stop, exit, quit, end, finish, close, terminate, kill, halt, abort`

**Advanced options**

Options related to Speech Recognition internals:

- ``energy_threshold`` *recognition_energy_threshold*

Represents the energy level threshold for sounds. *Default:* `300`

- ``dynamic_energy_threshold`` *recognition_dynamic_energy_threshold*

Represents whether the energy level threshold (see recognizer_instance.energy_threshold) for sounds should be automatically adjusted based on the currently ambient noise level while listening. *Default:* `True`

- ``dynamic_energy_adjustment_damping`` *recognition_dynamic_energy_adjustment_damping*

Represents approximately the fraction of the current energy threshold that is retained after one second of dynamic threshold adjustment. *Default:* `0.15`

- ``pause_threshold`` *recognition_pause_threshold*

Represents the minimum length of silence (in seconds) that will register as the end of a phrase. *Default:* `0.8`

- ``adjust_for_ambient_noise: duration`` *recognition_adjust_for_ambient_noise_duration*

The duration parameter is the maximum number of seconds that it will dynamically adjust the threshold for before returning. *Default:* `1`

Options reference: https://pypi.org/project/SpeechRecognition/1.3.1/


Audio Output (Microsoft Azure)
------------------------------

**PyGPT** implements voice synthesis using the ``Microsoft Azure Text-To-Speech`` API.
This feature requires to have an ``Microsoft Azure`` API Key. 
You can get API KEY for free from here: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech

To enable voice synthesis, activate the ``Audio Output (Microsoft Azure)`` plugin in the ``Plugins`` menu or turn on the ``Voice`` option in the ``Audio / Voice`` menu (both options in the menu achieve the same outcome).

Before using speech synthesis, you must configure the audio plugin with your Azure API key and the correct 
Region in the settings.

This is done through the ``Plugins / Settings...`` menu by selecting the `Audio (Azure)` tab:

.. image:: images/v2_azure.png
   :width: 600

**Options**

- ``Azure API Key`` *azure_api_key*

Here, you should enter the API key, which can be obtained by registering for free on the following website: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech

- ``Azure Region`` *azure_region*

You must also provide the appropriate region for Azure here. *Default:* `eastus`

- ``Voice (EN)`` *voice_en*

Here you can specify the name of the voice used for speech synthesis for English. *Default:* `en-US-AriaNeural`

- ``Voice (non-English)`` *voice_pl*

Here you can specify the name of the voice used for speech synthesis for other non-english language. *Default:* `pl-PL-AgnieszkaNeural`

If speech synthesis is enabled, a voice will be additionally generated in the background while generating a response via GPT.

Both ``OpenAI TTS`` and ``OpenAI Whisper`` use the same single API key provided for the OpenAI API, with no additional keys required.


Audio Output (OpenAI TTS)
-------------------------

The plugin enables voice synthesis using the TTS model developed by OpenAI. Using this plugin does not require any additional API keys or extra configuration; it utilizes the main OpenAI key. Through the available options, you can select the voice that you want the model to use.

**Options**

- ``Model`` *model*

Choose the model. Available options:

* tts-1
* tts-1-hd

*Default:* `tts-1`

- ``Voice`` *voice*

Choose the voice. Available voices to choose from:

* alloy
* echo
* fable
* onyx
* nova
* shimmer

*Default:* `alloy`


Autonomous Mode (inline)
------------------------

**WARNING: Please use autonomous mode with caution!** - this mode, when connected with other plugins, may produce unexpected results!

The plugin activates autonomous mode in standard chat modes, where AI begins a conversation with itself. 
You can set this loop to run for any number of iterations. Throughout this sequence, the model will engage
in self-dialogue, answering his own questions and comments, in order to find the best possible solution, subjecting previously generated steps to criticism.

This mode is similar to ``Auto-GPT`` - it can be used to create more advanced inferences and to solve problems by breaking them down into subtasks that the model will autonomously perform one after another until the goal is achieved. The plugin is capable of working in cooperation with other plugins, thus it can utilize tools such as web search, access to the file system, or image generation using ``DALL-E``.

**Options**

You can adjust the number of iterations for the self-conversation in the ``Plugins / Settings...`` menu under the following option:

- ``Iterations`` *iterations*

*Default:* `3`

**WARNING**: Setting this option to ``0`` activates an **infinity loop** which can generate a large number of requests and cause very high token consumption, so use this option with caution!

- ``Prompts`` *prompts*

Editable list of prompts used to instruct how to handle autonomous mode, you can create as many prompts as you want. 
First active prompt on list will be used to handle autonomous mode.

- ``Auto-stop after goal is reached`` *auto_stop*

If enabled, plugin will stop after goal is reached. *Default:* ``True``

- ``Reverse roles between iterations`` *reverse_roles*

Only for Completion/Langchain modes. 
If enabled, this option reverses the roles (AI <> user) with each iteration. For example, 
if in the previous iteration the response was generated for "Batman," the next iteration will use that 
response to generate an input for "Joker." *Default:* `True`


Chat with files (Llama-index, inline)
-------------------------------------

Plugin integrates ``Llama-index`` storage in any chat and provides additional knowledge into context.

**Options**

- ``Ask Llama-index first`` *ask_llama_first*

When enabled, then ``Llama-index`` will be asked first, and response will be used as additional knowledge in prompt. 
When disabled, then ``Llama-index`` will be asked only when needed. *Default:* `False`

- ``Model`` *model_query*

Model used for querying ``Llama-index``. *Default:* ``gpt-3.5-turbo``

- ``Index name`` *idx*

Index to use. *Default:* ``base``.


Command: Code Interpreter
-------------------------

**Executing Code**

The plugin operates similarly to the ``Code Interpreter`` in ``ChatGPT``, with the key difference that it works locally on the user's system. It allows for the execution of any Python code on the computer that the model may generate. When combined with the ``Command: Files I/O`` plugin, it facilitates running code from files saved in the ``data`` directory. You can also prepare your own code files and enable the model to use them or add your own plugin for this purpose. You can execute commands and code on the host machine or in Docker container.

**Executing system commands**

Another feature is the ability to execute system commands and return their results. With this functionality, the plugin can run any system command, retrieve the output, and then feed the result back to the model. When used with other features, this provides extensive integration capabilities with the system.

**Options**

- ``Python command template`` *python_cmd_tpl*

Python command template (use {filename} as path to file placeholder). *Default:* ``python3 {filename}``

- ``Enable: Python Code Generate and Execute`` *cmd_code_execute*

Allows Python code execution (generate and execute from file). *Default:* `True`

- ``Enable: Python Code Execute (File)`` *cmd_code_execute_file*

Allows Python code execution from existing file. *Default:* `True`
 
- ``Enable: System Command Execute`` *cmd_sys_exec*

Allows system commands execution. *Default:* `True`

- ``Sandbox (docker container)`` *sandbox_docker*

Execute commands in sandbox (docker container). Docker must be installed and running. *Default:* `False`

- ``Docker image`` *sandbox_docker_image*

Docker image to use for sandbox *Default:* ``python:3.8-alpine``

Command: Custom Commands
------------------------

With the ``Custom Commands`` plugin, you can integrate **PyGPT** with your operating system and scripts or applications. You can define an unlimited number of custom commands and instruct GPT on when and how to execute them. Configuration is straightforward, and **PyGPT** includes a simple tutorial command for testing and learning how it works:

.. image:: images/v2_custom_cmd.png
   :width: 800

To add a new custom command, click the **ADD** button and then:

1. Provide a name for your command: this is a unique identifier for GPT.
2. Provide an ``instruction`` explaining what this command does; GPT will know when to use the command based on this instruction.
3. Define ``params``, separated by commas - GPT will send data to your commands using these params. These params will be placed into placeholders you have defined in the ``cmd`` field. For example:

If you want instruct GPT to execute your Python script named ``smart_home_lights.py`` with an argument, such as ``1`` to turn the light ON, and ``0`` to turn it OFF, define it as follows:

- **name**: lights_cmd
- **instruction**: turn lights on/off; use 1 as 'arg' to turn ON, or 0 as 'arg' to turn OFF
- **params**: arg
- **cmd**: ``python /path/to/smart_home_lights.py {arg}``

The setup defined above will work as follows:

When you ask GPT to turn your lights ON, GPT will locate this command and prepare the command ``python /path/to/smart_home_lights.py {arg}`` with ``{arg}`` replaced with ``1``. On your system, it will execute the command:

.. code-block:: console

  python /path/to/smart_home_lights.py 1

And that's all. GPT will take care of the rest when you ask to turn ON the lights.

You can define as many placeholders and parameters as you desire.

Here are some predefined system placeholders for use:

- ``{_time}`` - current time in ``H:M:S`` format
- ``{_date}`` - current date in ``Y-m-d`` format
- ``{_datetime}`` - current date and time in ``Y-m-d H:M:S`` format
- ``{_file}`` - path to the file from which the command is invoked
- ``{_home}`` - path to PyGPT's home/working directory

You can connect predefined placeholders with your own params.

*Example:*

- **name**: song_cmd
- **instruction**: store the generated song on hard disk
- **params**: song_text, title
- **cmd**: ``echo "{song_text}" > {_home}/{title}.txt``

With the setup above, every time you ask GPT to generate a song for you and save it to the disk, it will:

1. Generate a song.
2. Locate your command.
3. Execute the command by sending the song's title and text.
4. The command will save the song text into a file named with the song's title in the **PyGPT** working directory.

**Example tutorial command**

**PyGPT** provides simple tutorial command to show how it work, to run it just ask GPT for execute ``tutorial test command`` and it will show you how it works:

.. code-block:: console

  > please execute tutorial test command

.. image:: images/v2_custom_cmd_example.png
   :width: 800


Command: Files I/O
------------------

The plugin allows for file management within the local filesystem. It enables the model to create, read, and write files and directories located in the ``data`` directory, which can be found in the user's work directory. With this plugin, the AI can also generate Python code files and thereafter execute that code within the user's system.

Plugin capabilities include:

* Sending files as attachments
* Reading files
* Appending to files
* Writing files
* Deleting files and directories
* Listing files and directories
* Creating directories
* Downloading files
* Copying files and directories
* Moving (renaming) files and directories

If a file being created (with the same name) already exists, a prefix including the date and time is added to the file name.

**Options**

- ``Enable: Get and upload file as attachment`` *cmd_get_file*

Allows `cmd_get_file` command execution. *Default:* `False`

- ``Enable: Read file`` *cmd_read_file*

Allows `read_file` command execution. *Default:* `True`

- ``Enable: Append to file`` *cmd_append_file*

Allows `append_file` command execution. *Default:* `True`

- ``Enable: Save file`` *cmd_save_file*

Allows `save_file` command execution. *Default:* `True`

- ``Enable: Delete file`` *cmd_delete_file*

Allows `delete_file` command execution. *Default:* `True`

- ``Enable: List files in directory (ls)`` *cmd_list_dir*

Allows `list_dirs` command execution. *Default:* `True`

- ``Enable: Directory creation (mkdir)`` *cmd_mkdir*

Allows `mkdir` command execution. *Default:* `True`

- ``Enable: Downloading files`` *cmd_download_file*

Allows `download_file` command execution. *Default:* `True`

- ``Enable: Removing directories`` *cmd_rmdir*

Allows `rmdir` command execution. *Default:* `True`

- ``Enable: Copying files`` *cmd_copy_file*

Allows `copy_file` command execution. *Default:* `True`

- ``Enable: Copying directories (recursive)`` *cmd_copy_dir*

Allows `copy_dir` command execution. *Default:* `True`

- ``Enable: Move files and directories (rename)`` *cmd_move*

Allows `move` command execution. *Default:* `True`

- ``Enable: Check if path is directory`` *cmd_is_dir*

Allows `is_dir` command execution. *Default:* `True`

- ``Enable: Check if path is file`` *cmd_is_file*

Allows `is_file` command execution. *Default:* `True`

- ``Enable: Check if file or directory exists`` *cmd_file_exists*

Allows `file_exists` command execution. *Default:* `True`

- ``Enable: Get file size`` *cmd_file_size*

Allows `file_size` command execution. *Default:* `True`

- ``Enable: Get file info`` *cmd_file_info*

Allows `file_info` command execution. *Default:* `True`


Command: Google Web Search
--------------------------

**PyGPT** lets you connect GPT to the internet and carry out web searches in real time as you make queries.

To activate this feature, turn on the ``Command: Google Web Search`` plugin found in the ``Plugins`` menu.

Web searches are automated through the ``Google Custom Search Engine`` API. 
To use this feature, you need an API key, which you can obtain by registering an account at:

https://developers.google.com/custom-search/v1/overview

After registering an account, create a new project and select it from the list of available projects:

https://programmablesearchengine.google.com/controlpanel/all

After selecting your project, you need to enable the ``Whole Internet Search`` option in its settings. 
Then, copy the following two items into **PyGPT**:

* Api Key
* CX ID

These data must be configured in the appropriate fields in the ``Plugins / Settings...`` menu:

.. image:: images/v2_plugin_google.png
   :width: 600


Command: Serial port / USB
---------------------------

Provides commands for reading and sending data to USB ports.

**Tip:** in Snap version you must connect the interface first: https://snapcraft.io/docs/serial-port-interface

You can send commands to, for example, an Arduino or any other controllers using the serial port for communication.

.. image:: images/v2_serial.png
   :width: 600

Above is an example of co-operation with the following code uploaded to ``Arduino Uno`` and connected via USB:

.. code-block:: cpp

   // example.ino

   void setup() {
     Serial.begin(9600);
   }

   void loop() {
     if (Serial.available() > 0) {
       String input = Serial.readStringUntil('\n');
       if (input.length() > 0) {
         Serial.println("OK, response for: " + input);
       }
     }
   }

**Options**

``USB port`` *serial_port*

USB port name, e.g. /dev/ttyUSB0, /dev/ttyACM0, COM3, *Default:* ``/dev/ttyUSB0``

- ``Connection speed (baudrate, bps)`` *serial_bps*

Port connection speed, in bps *Default:* ``9600``

- ``Timeout`` *timeout*

Timeout in seconds *Default:* ``1``

- ``Sleep`` *sleep*

Sleep in seconds after connection. *Default:* ``2``

- ``Enable: Send text commands to USB port`` *cmd_serial_send*

Allows ``serial_send`` command execution". *Default:* ``True``

- ``Enable: Send raw bytes to USB port`` *cmd_serial_send_bytes*

Allows ``serial_send_bytes`` command execution. *Default:* ``True``

- ``Enable: Read data from USB port`` *cmd_serial_read*

Allows ``serial_read`` command execution. *Default:* ``True``

- ``Syntax: serial_send`` *syntax_serial_send*

Syntax for sending text command to USB port, *Default:* '"serial_send": send text command to USB port, params: "command"'

- ``Syntax: serial_send_bytes`` *syntax_serial_send_bytes*

Syntax for sending raw bytes to USB port. *Default:* '"serial_send_bytes": send raw bytes to USB port, params: "bytes"''

- ``Syntax: serial_read`` *syntax_serial_read*

Syntax for reading data from USB port. *Default:* '"serial_read": read data from serial port in seconds duration, params: "duration"`


Context history (calendar, inline)
----------------------------------

Provides access to context history database.
Plugin also provides access to reading and creating day notes.

Examples of use, you can ask e.g. for the following:

* Give me today day note
* Save a new note for today
* Update my today note with...
* Get the list of yesterday conversations
* Get contents of conversation ID 123

etc.

From version ``2.0.147`` it is possible to use ``@`` ID tags to automatically use summary of previous contexts in current discussion.
To use context from previous discussion with specified ID use following syntax in your query:

.. code-block:: ini

   @123

Where ``123`` is the ID of previous context (conversation) in database, example of use:

.. code-block:: ini

   Let's talk about discussion @123

**Options**

- ``Enable: using context @ ID tags`` *use_tags*

When enabled, it allows to automatically retrieve context history using @ tags, e.g. use @123 in question to use summary of context with ID 123 as additional context. *Default:* ``False``

- ``Enable: get date range context list`` *cmd_get_ctx_list_in_date_range*

When enabled, it allows getting the list of context history (previous conversations). *Default:* ``True``

- ``Enable: get context content by ID`` *cmd_get_ctx_content_by_id*

When enabled, it allows getting summarized content of context with defined ID. *Default:* ``True``

- ``Enable: count contexts in date range`` *cmd_count_ctx_in_date*

When enabled, it allows counting contexts in date range. *Default:* ``True``

- ``Enable: get day note`` *cmd_get_day_note*

When enabled, it allows retrieving day note for specific date. *Default:* ``True``

- ``Enable: add day note`` *cmd_add_day_note*

When enabled, it allows adding day note for specific date. *Default:* ``True``

- ``Enable: update day note`` *cmd_update_day_note*

When enabled, it allows updating day note for specific date. *Default:* ``True``

- ``Enable: remove day note`` *cmd_remove_day_note*

When enabled, it allows removing day note for specific date. *Default:* ``True``

- ``Model`` *model_summarize*

Model used for summarize. *Default:* ``gpt-3.5-turbo``

- ``Max summary tokens`` *summary_max_tokens*

Max tokens in output when generating summary. *Default:* ``1500``

- ``Max contexts to retrieve`` *ctx_items_limit*

Max items in context history list to retrieve in one query. 0 = no limit. *Default:* ``30``

- ``Per-context items content chunk size`` *chunk_size*

Per-context content chunk size (max characters per chunk). *Default:* ``100000 chars``

**Options (advanced)**

- ``Syntax: get_ctx_list_in_date_range`` *syntax_get_ctx_list_in_date_range*

Syntax for get_ctx_list_in_date_range command.

- ``Syntax: get_ctx_content_by_id`` *syntax_get_ctx_content_by_id*

Syntax for get_ctx_content_by_id command.

- ``Syntax: count_ctx_in_date`` *syntax_count_ctx_in_date*

Syntax for count_ctx_in_date command

- ``Syntax: get_day_note`` *syntax_get_day_note*

Syntax for get_day_note command

- ``Syntax: add_day_note`` *syntax_add_day_note*

Syntax for add_day_note command.

- ``Syntax: update_day_note`` *syntax_update_day_note*

Syntax for update_day_note command.

- ``Syntax: remove_day_note`` *syntax_remove_day_note*

Syntax for remove_day_note command.

- ``Prompt: @ tags (system)`` *prompt_tag_system*

Prompt for use @ tag (system).

- ``Prompt: @ tags (summary)`` *prompt_tag_summary*

Prompt for use @ tag (summary).


Crontab / Task scheduler
------------------------

Plugin provides cron-based job scheduling - you can schedule tasks/prompts to be sent at any time using cron-based syntax for task setup.

.. image:: images/v2_crontab.png
   :width: 800

**Options**

- ``Your tasks`` *crontab*

Add your cron-style tasks here. 
They will be executed automatically at the times you specify in the cron-based job format. 
If you are unfamiliar with Cron, consider visiting the Cron Guru page for assistance: https://crontab.guru

Number of active tasks is always displayed in tray-icon dropdown menu:

.. image:: images/v2_crontab_tray.png
   :width: 400

- ``Create a new context on job run`` *new_ctx*

If enabled, then a new context will be created on every run of the job." *Default:* ``True``

- ``Show notification on job run`` *show_notify*

If enabled, then a tray notification will be shown on every run of the job. *Default:* ``True``


DALL-E 3: Image Generation (inline)
-----------------------------------

Integrates DALL-E 3 image generation with any chat and mode. Just enable and ask for image in Chat mode, using standard model like GPT-4. 
The plugin does not require the ``Execute commands`` option to be enabled.

**Options**

- ``Prompt`` *prompt*

Prompt used for generating a query for DALL-E in background.


GPT-4 Vision (inline)
---------------------

Plugin integrates vision capabilities with any chat mode, not just Vision mode. 
When the plugin is enabled, the model temporarily switches to vision in the background when an image attachment or vision capture is provided.

**Options**

- ``Model`` *model*

The model used to temporarily provide vision capabilities; default is `gpt-4-vision-preview`.

- ``Prompt`` *prompt*

Prompt used for vision mode. It will append or replace current system prompt when using vision model.

- ``Replace prompt`` *replace_prompt*

Replace whole system prompt with vision prompt against appending it to the current prompt.

- ``Enable: "camera capture" command`` *cmd_capture*

Allows using command: camera capture (``Execute commands`` option enabled is required).
If enabled, model will be able to capture images from camera itself.

- ``Enable: "make screenshot" command`` *cmd_screenshot*

Allows adding command: make screenshot (``Execute commands`` option enabled is required).
If enabled, model will be able to making screenshots itself.


Real Time
----------

This plugin automatically adds the current date and time to each system prompt you send. 
You have the option to include just the date, just the time, or both.

When enabled, it quietly enhances each system prompt with current time information before sending it to GPT.

**Options**

- ``Append time`` *hour*

If enabled, it appends the current time to the system prompt. *Default:* `True`

- ``Append date`` *date*

If enabled, it appends the current date to the system prompt. *Default:* `True` 

- ``Template`` *tpl*

Template to append to the system prompt. The placeholder ``{time}`` will be replaced with the 
current date and time in real-time. *Default:* `Current time is {time}.`


System Prompt Extra (append)
-----------------------------

The plugin appends additional system prompts (extra data) from a list to every current system prompt. 
You can enhance every system prompt with extra instructions that will be automatically appended to the system prompt.

**Options**

- ``Prompts`` *prompts*

List of extra prompts - prompts that will be appended to system prompt. 
All active extra prompts defined on list will be appended to the system prompt in the order they are listed here.