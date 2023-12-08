Plugins list
============

Command: Files I/O
-----------------

The plugin allows for file management within the local filesystem. It enables the model to create, read, and write files and directories located in the `output` directory, which can be found in the user's work directory. With this plugin, the AI can also generate Python code files and thereafter execute that code within the user's system.

Plugin capabilities include:

* Reading files
* Writing files
* Executing code from files
* Creating directories
* Listing files and directories

If a file being created (with the same name) already exists, a prefix including the date and time is added to the file name.

**Options:**

- ``Enable: Read file`` *cmd_read_file*

Allow `read_file` command. *Default:* `True`

- ``Enable: Append to file`` *cmd_append_file*

Allow `append_file` command. *Default:* `True`

- ``Enable: Save file`` *cmd_save_file*

Allow `save_file` command. *Default:* `True`

- ``Enable: Delete file`` *cmd_delete_file*

Allow `delete_file` command. *Default:* `True`

- ``Enable: List files (ls)`` *cmd_list_files*

Allow `list_files` command. *Default:* `True`

- ``Enable: List directories (ls)`` *cmd_list_dirs*

Allow `list_dirs` command. *Default:* `True`

- ``Enable: Directory creation (mkdir)`` *cmd_mkdir*

Allow `mkdir` command. *Default:* `True`


Command: Code Interpreter
-------------------------

**Executing Code**

The plugin operates similarly to the ``Code Interpreter`` in ``ChatGPT``, with the key difference that it works locally on the user's system. It allows for the execution of any Python code on the computer that the model may generate. When combined with the ``Command: Files I/O`` plugin, it facilitates running code from files saved in the ``output`` directory. You can also prepare your own code files and enable the model to use them or add your own plugin for this purpose.

**Executing system commands**

Another feature is the ability to execute system commands and return their results. With this functionality, the plugin can run any system command, retrieve the output, and then feed the result back to the model. When used with other features, this provides extensive integration capabilities with the system.

**Options:**

- ``Python command template`` *python_cmd_tpl*

Python command template (use {filename} as path to file placeholder). *Default:* `python3 {filename}`

- ``Enable: Python Code Generate and Execute`` *cmd_code_execute*

Allow Python code execution (generate and execute from file). *Default:* `True`

- ``Enable: Python Code Execute (File)`` *cmd_code_execute_file*

Allow Python code execution from existing file. *Default:* `True`
 
- ``Enable: System Command Execute`` *cmd_sys_exec*

Allow system commands execution. *Default:* `True`


Command: Google Web Search
--------------------------

**PYGPT** lets you connect GPT to the internet and carry out web searches in real time as you make queries.

To activate this feature, turn on the ``Command: Google Web Search`` plugin found in the ``Plugins`` menu.

Web searches are automated through the ``Google Custom Search Engine`` API. 
To use this feature, you need an API key, which you can obtain by registering an account at:

https://developers.google.com/custom-search/v1/overview

After registering an account, create a new project and select it from the list of available projects:

https://programmablesearchengine.google.com/controlpanel/all

After selecting your project, you need to enable the ``Whole Internet Search`` option in its settings. 
Then, copy the following two items into PYGPT:

* Api Key
* CX ID

These data must be configured in the appropriate fields in the ``Plugins / Settings...`` menu:

.. image:: images/v2_plugin_google.png
   :width: 600


Audio Output (Microsoft Azure)
--------------------------

**PYGPT** implements voice synthesis using the ``Microsoft Azure Text-To-Speech`` API.
This feature requires to have an ``Microsoft Azure`` API Key. 
You can get API KEY for free from here: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech


To enable voice synthesis, activate the ``Audio Output (Microsoft Azure)`` plugin in the ``Plugins`` menu or 
turn on the ``Voice`` option in the ``Audio / Voice`` menu (both options in the menu achieve the same outcome).

Before using speech synthesis, you must configure the audio plugin with your Azure API key and the correct 
Region in the settings.

This is done through the ``Plugins / Settings...`` menu by selecting the `Audio (Azure)` tab:

.. image:: images/v2_azure.png
   :width: 600

**Options:**

``Azure API Key`` *azure_api_key*

Here, you should enter the API key, which can be obtained by registering for free on the following website: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech

``Azure Region`` *azure_region*

You must also provide the appropriate region for Azure here. *Default:* `eastus`

``Voice (EN)`` *voice_en*

Here you can specify the name of the voice used for speech synthesis for English. *Default:* `en-US-AriaNeural`


``Voice (PL)`` *voice_pl*

Here you can specify the name of the voice used for speech synthesis for the Polish language. *Default:* `pl-PL-AgnieszkaNeural`

If speech synthesis is enabled, a voice will be additionally generated in the background while generating a response via GPT.

Both ``OpenAI TTS`` and ``OpenAI Whisper`` use the same single API key provided for the OpenAI API, with no additional keys required.


Audio Output (OpenAI TTS)
--------------------------

The plugin enables voice synthesis using the TTS model developed by OpenAI. Using this plugin does not require any additional API keys or extra configuration; it utilizes the main OpenAI key. Through the available options, you can select the voice that you want the model to use.

``Model`` *model*

Choose the model. Available options:

* tts-1
* tts-1-hd

*Default:* `tts-1`

``Voice`` *voice*

Choose the voice. Available voices to choose from:

* alloy
* echo
* fable
* onyx
* nova
* shimmer

*Default:* `alloy`

Audio Input (OpenAI Whisper)
----------------------------

The plugin facilitates speech recognition using the ``Whisper`` model by OpenAI. It allows for voice commands to be relayed to the AI using your own voice. The plugin doesn't require any extra API keys or additional configurations; it uses the main OpenAI key. In the plugin's configuration options, you should adjust the volume level (min energy) at which the plugin will respond to your microphone. Once the plugin is activated, a new ``Speak`` option will appear at the bottom near the ``Send`` button  -  when this is enabled, the application will respond to the voice received from the microphone.

Configuration options:

``Model`` *model*

Choose the model. *Default:* `whisper-1`

``Timeout`` *timeout*

The number of seconds the application waits for voice input from the microphone. *Default:* `2`

``Phrase max length`` *phrase_length*

Maximum duration for a voice sample (in seconds).  *Default:* `2`

``Min energy`` *min_energy*

The minimum volume level for the microphone to trigger voice detection. If the microphone is too sensitive, increase this value. *Default:* `4000`

``Adjust for ambient noise`` *adjust_noise*

Enables adjustment to ambient noise levels. *Default:* `True`

``Continuous listen`` *continuous_listen*

Enables continuous microphone listening. If the option is enabled, the microphone will be listening at all times. If disabled, listening must be started manually by enabling the ``Speak`` option. *Default:* `True`


Self Loop
----------

The plugin introduces a "talk with yourself" mode, where GPT begins a conversation with itself. 
You can set this loop to run for any number of iterations. Throughout such a sequence, the model will engage 
in self-dialogue, responding to its own questions and comments. This feature is available in both ``Chat`` and ``Completion`` modes. 
To enhance the experience in Completion mode, you can assign specific names (roles) to each participant in the dialogue.

To effectively start this mode, it's important to craft the system prompt carefully, ensuring it indicates to GPT that 
it is conversing with itself. The outcomes can be intriguing, so it's worth exploring what happens when you try this.

You can adjust the number of iterations for the self-conversation in the ``Plugins / Settings...`` menu under the following option:

``Iterations`` *iterations*

*Default:* `3`


**Additional options:**

``Clear context output`` *clear_output*


The option clears the previous answer in the context, which is then used as input for the next iteration. *Default:* `True`


``Reverse roles between iterations`` *reverse_roles*

If enabled, this option reverses the roles (AI <> user) with each iteration. For example, 
if in the previous iteration the response was generated for "Batman," the next iteration will use that 
response to generate an input for "Joker." *Default:* `True`


Real Time
----------

This plugin automatically adds the current date and time to each system prompt you send. 
You have the option to include just the date, just the time, or both.

When enabled, it quietly enhances each system prompt with current time information before sending it to GPT.

**Options**

``Append time`` *hour*

If enabled, it appends the current time to the system prompt. *Default:* `True`

``Append date`` *date*

If enabled, it appends the current date to the system prompt. *Default:* `True` 

``Template`` *tpl*

Template to append to the system prompt. The placeholder ``{time}`` will be replaced with the 
current date and time in real-time. *Default:* `Current time is {time}.`

Creating Your Own Plugins
--------------------------

You can create your own plugin for **PYGPT** at any time. The plugin can be written in Python and then registered with the application just before launching it. All plugins included with the app are stored in the ``plugin`` directory - you can use them as coding examples for your own plugins. Then, you can create your own and register it in the system using:

.. code-block:: python

  # custom_launcher.py

  from pygpt_net.app import Launcher
  from my_plugin import MyPlugin


  def run():
      """Runs the app."""
      # Initialize the app
      launcher = Launcher()
      launcher.init()

      # Add your plugins
      ...
      launcher.add_plugin(MyPlugin())

      # Launch the app
      launcher.run()