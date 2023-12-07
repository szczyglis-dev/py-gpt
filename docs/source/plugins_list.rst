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


Command: Code Interpreter
-------------------------

**Executing Code**

The plugin operates similarly to the ``Code Interpreter`` in ``ChatGPT``, with the key difference that it works locally on the user's system. It allows for the execution of any Python code on the computer that the model may generate. When combined with the ``Command: Files I/O`` plugin, it facilitates running code from files saved in the ``output`` directory. You can also prepare your own code files and enable the model to use them or add your own plugin for this purpose.

**Executing system commands**

Another feature is the ability to execute system commands and return their results. With this functionality, the plugin can run any system command, retrieve the output, and then feed the result back to the model. When used with other features, this provides extensive integration capabilities with the system.

**Options:**

``Python command template`` *python_cmd_tpl*

*Default:* `python3 {filename}`

Python command template.

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

*Default:* `eastus`

You must also provide the appropriate region for Azure here.


``Voice (EN)`` *voice_en*

*Default:* `en-US-AriaNeural`

Here you can specify the name of the voice used for speech synthesis for English.


``Voice (PL)`` *voice_pl*

*Default:* `pl-PL-AgnieszkaNeural`

Here you can specify the name of the voice used for speech synthesis for the Polish language.

If speech synthesis is enabled, a voice will be additionally generated in the background while generating a response via GPT.

Both ``OpenAI TTS`` and ``OpenAI Whisper`` use the same single API key provided for the OpenAI API, with no additional keys required.


Audio Output (OpenAI TTS)
--------------------------

The plugin enables voice synthesis using the TTS model developed by OpenAI. Using this plugin does not require any additional API keys or extra configuration; it utilizes the main OpenAI key. Through the available options, you can select the voice that you want the model to use.

``Model`` *model*

*Default:* `tts-1`

Choose the model. Available options:

* tts-1
* tts-1-hd

``Voice`` *voice*

*Default:* `alloy`

Choose the voice. Available voices to choose from:

* alloy
* echo
* fable
* onyx
* nova
* shimmer

Audio Input (OpenAI Whisper)
----------------------------

The plugin facilitates speech recognition using the ``Whisper`` model by OpenAI. It allows for voice commands to be relayed to the AI using your own voice. The plugin doesn't require any extra API keys or additional configurations; it uses the main OpenAI key. In the plugin's configuration options, you should adjust the volume level (min energy) at which the plugin will respond to your microphone. Once the plugin is activated, a new ``Speak`` option will appear at the bottom near the ``Send`` button  -  when this is enabled, the application will respond to the voice received from the microphone.

Configuration options:

``Model`` *model*

*Default:* `whisper-1`

Choose the model.

``Timeout`` *timeout*

*Default:* `2`

The number of seconds the application waits for voice input from the microphone.

``Phrase max length`` *phrase_length*

*Default:* `2`

Maximum duration for a voice sample (in seconds).

``Min energy`` *min_energy*

*Default:* `4000`

The minimum volume level for the microphone to trigger voice detection. If the microphone is too sensitive, increase this value.

``Adjust for ambient noise`` *adjust_noise*

*Default:* `True`

Enables adjustment to ambient noise levels.

``Continuous listen`` *continuous_listen*

*Default:* `True`

Enables continuous microphone listening. If the option is enabled, the microphone will be listening at all times. If disabled, listening must be started manually by enabling the ``Speak`` option.


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

*Default:* `True`

The option clears the previous answer in the context, which is then used as input for the next iteration.


``Reverse roles between iterations`` *reverse_roles*

*Default:* `True`

If enabled, this option reverses the roles (AI <> user) with each iteration. For example, 
if in the previous iteration the response was generated for "Batman," the next iteration will use that 
response to generate an input for "Joker."


Real Time
----------

This plugin automatically adds the current date and time to each system prompt you send. 
You have the option to include just the date, just the time, or both.

When enabled, it quietly enhances each system prompt with current time information before sending it to GPT.

**Options**

``Append time`` *hour*

*Default:* `True`

If enabled, it appends the current time to the system prompt.


``Append date`` *date*

*Default:* `True`

If enabled, it appends the current date to the system prompt.


``Template`` *tpl*

*Default:* `Current time is {time}.`

Template to append to the system prompt. The placeholder ``{time}`` will be replaced with the 
current date and time in real-time.

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