Plugins
=======

Overview
-------------------------

**PyGPT** can be enhanced with plugins to add new features.

The following plugins are currently available, and model can use them instantly:

* ``API calls`` - plugin lets you connect the model to the external services using custom defined API calls.
* ``Audio Input`` - provides speech recognition.
* ``Audio Output`` - provides voice synthesis.
* ``Autonomous Agent (inline)`` - enables autonomous conversation (AI to AI), manages loop, and connects output back to input. This is the inline Agent mode.
* ``Bitbucket`` - Access Bitbucket API to manage repositories, issues, and pull requests.
* ``Chat with files (LlamaIndex, inline)`` - plugin integrates LlamaIndex storage in any chat and provides additional knowledge into context (from indexed files).
* ``Code Interpreter`` - responsible for generating and executing Python code, functioning much like the `Code Interpreter` on `ChatGPT`, but locally. This means model can interface with any script, application, or code. Plugins can work in conjunction to perform sequential tasks; for example, the `Files` plugin can write generated Python code to a file, which the `Code Interpreter` can execute it and return its result to model.
* ``Context history (calendar, inline)`` - provides access to context history database.
* ``Crontab / Task scheduler`` - plugin provides cron-based job scheduling - you can schedule tasks/prompts to be sent at any time using cron-based syntax for task setup.
* ``Custom Commands`` - allows you to create and execute custom commands on your system.
* ``Experts (inline)`` - allows calling experts in any chat mode. This is the inline Experts (co-op) mode.
* ``Facebook`` - Manage user info, pages, posts, and photos on Facebook pages.
* ``Files I/O`` - grants access to the local filesystem, enabling model to read and write files, as well as list and create directories.
* ``GitHub`` - Access GitHub API to manage repositories, issues, and pull requests.
* ``Google`` - Access Gmail, Drive, Docs, Maps, Calendar, Contacts, Colab, YouTube, Keep - for managing emails, files, events, notes, video info, and contacts.
* ``Image Generation (inline)`` - integrates DALL-E 3 image generation with any chat and mode. Just enable and ask for image in Chat mode, using standard model like GPT-4. The plugin does not require the ``+ Tools`` option to be enabled.
* ``Mailer`` - Provides the ability to send, receive and read emails.
* ``Mouse and Keyboard`` - provides the ability to control the mouse and keyboard by the model.
* ``Real Time`` - automatically appends the current date and time to the system prompt, informing the model about current time.
* ``Serial port / USB`` - plugin provides commands for reading and sending data to USB ports.
* ``Slack`` - Handle users, conversations, messages, and files on Slack.
* ``System (OS)`` - provides access to the operating system and executes system commands.
* ``System Prompt Extra`` - appends additional system prompts (extra data) from a list to every current system prompt. You can enhance every system prompt with extra instructions that will be automatically appended to the system prompt.
* ``Telegram`` - Send messages, photos, and documents; manage chats and contacts.
* ``Vision (inline)`` - integrates vision capabilities with any chat mode, not just Vision mode. When the plugin is enabled, the model temporarily switches to vision in the background when an image attachment or vision capture is provided.
* ``Voice Control (inline)`` - provides voice control command execution within a conversation.
* ``Web Search`` - provides the ability to connect to the Web, search web pages for current data, and index external content using LlamaIndex data loaders.
* ``X/Twitter`` - Interact with tweets and users, manage bookmarks and media, perform likes, retweets, and more.


Creating Your Own Plugins
-------------------------

You can create your own plugin for **PyGPT** at any time. The plugin can be written in Python and then registered with the application just before launching it. All plugins included with the app are stored in the ``plugin`` directory - you can use them as coding examples for your own plugins.

PyGPT can be extended with:

* custom plugins
* custom LLM wrappers
* custom vector store providers
* custom data loaders
* custom audio input providers
* custom audio output providers
* custom web search engine providers

See the section ``Extending PyGPT / Adding a custom plugin`` for more details.

API calls
----------

**PyGPT** lets you connect the model to the external services using custom defined API calls.

To activate this feature, turn on the ``API calls`` plugin found in the ``Plugins`` menu.

In this plugin you can provide list of allowed API calls, their parameters and request types. The model will replace provided placeholders with required params and make API call to external service.

- ``Your custom API calls`` *cmds*

You can provide custom API calls on the list here.

Params to specify for API call:

* **Enabled** (True / False)
* **Name:** unique API call name (ID)
* **Instruction:** description for model when and how to use this API call
* **GET params:** list, separated by comma, GET params to append to endpoint URL
* **POST params:** list, separated by comma, POST params to send in POST request
* **POST JSON:** provide the JSON object, template to send in POST JSON request, use ``%param%`` as POST param placeholders
* **Headers:** provide the JSON object with dictionary of extra request headers, like Authorization, API keys, etc.
* **Request type:** use GET for basic GET request, POST to send encoded POST params or POST_JSON to send JSON-encoded object as body
* **Endpoint:** API endpoint URL, use ``{param}`` as GET param placeholders

An example API call is provided with plugin by default, it calls the Wikipedia API:

* Name: ``search_wiki``
* Instructiom: ``send API call to Wikipedia to search pages by query``
* GET params: ``query, limit``
* Type: ``GET``
* API endpoint: https://en.wikipedia.org/w/api.php?action=opensearch&limit={limit}&format=json&search={query}

In the above example, every time you ask the model for query Wiki for provided query (e.g. ``Call the Wikipedia API for query: Nikola Tesla``) it will replace placeholders in provided API endpoint URL with a generated query and it will call prepared API endpoint URL, like below:

https://en.wikipedia.org/w/api.php?action=opensearch&limit=5&format=json&search=Nikola%20Tesla

You can specify type of request: ``GET``, ``POST`` and ``POST JSON``.

In the ``POST`` request you can provide POST params, they will be encoded and send as POST data.

In the ``POST JSON`` request you must provide JSON object template to be send, using ``%param%`` placeholders in the JSON object to be replaced with the model.

You can also provide any required credentials, like Authorization headers, API keys, tokens, etc. using the ``headers`` field - you can provide a JSON object here with a dictionary ``key => value`` - provided JSON object will be converted to headers dictonary and send with the request.

- ``Disable SSL verify`` *disable_ssl*

Disables SSL verification when making requests. *Default:* `False`

- ``Timeout`` *timeout*

Connection timeout (seconds). *Default:* `5`

- ``User agent`` *user_agent*

User agent to use when making requests, default: ``Mozilla/5.0``. *Default:* `Mozilla/5.0`


Audio Input
------------

The plugin facilitates speech recognition (by default using the ``Whisper`` model from OpenAI, ``Google`` and ``Bing`` are also available). It allows for voice commands to be relayed to the AI using your own voice. Whisper doesn't require any extra API keys or additional configurations; it uses the main OpenAI key. In the plugin's configuration options, you should adjust the volume level (min energy) at which the plugin will respond to your microphone. Once the plugin is activated, a new ``Speak`` option will appear at the bottom near the ``Send`` button  -  when this is enabled, the application will respond to the voice received from the microphone.

The plugin can be extended with other speech recognition providers.

**Options**

- ``Provider`` *provider*

Choose the provider. *Default:* `Whisper`

Available providers:

* Whisper (via ``OpenAI API``)
* Whisper (local model) - not available in compiled and Snap versions, only Python/PyPi version
* Google (via ``SpeechRecognition`` library)
* Google Cloud (via ``SpeechRecognition`` library)
* Microsoft Bing (via ``SpeechRecognition`` library)

**Whisper (API)**

- ``Model`` *whisper_model*

Choose the model. *Default:* `whisper-1`

**Whisper (local)**

- ``Model`` *whisper_local_model*

Choose the local model. *Default:* `base`

Available models: https://github.com/openai/whisper

**Google**

- ``Additional keywords arguments`` *google_args*

Additional keywords arguments for r.recognize_google(audio, **kwargs)

**Google Cloud**

- ``Additional keywords arguments`` *google_args*

Additional keywords arguments for r.recognize_google_cloud(audio, **kwargs)

**Bing**

- ``Additional keywords arguments`` *bing_args*

Additional keywords arguments for r.recognize_bing(audio, **kwargs)

**General options**

- ``Auto send`` *auto_send*

Automatically send recognized speech as input text after recognition. *Default:* `True`

- ``Advanced mode`` *advanced*

Enable only if you want to use advanced mode and the settings below. Do not enable this option if you just want to use the simplified mode (default). *Default:* `False`

**Advanced mode options**

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

Audio Output
-------------------------

The plugin lets you turn text into speech using the TTS model from OpenAI or other services like ``Microsoft Azure``, ``Google``, and ``Eleven Labs``. You can add more text-to-speech providers to it too. ``OpenAI TTS`` does not require any additional API keys or extra configuration; it utilizes the main OpenAI key. 
Microsoft Azure requires to have an Azure API Key. Before using speech synthesis via ``Microsoft Azure``, ``Google`` or ``Eleven Labs``, you must configure the audio plugin with your API keys, regions and voices if required.

.. image:: images/v2_azure.png
   :width: 600

Through the available options, you can select the voice that you want the model to use. More voice synthesis providers coming soon.

To enable voice synthesis, activate the ``Audio Output`` plugin in the ``Plugins`` menu or turn on the ``Audio Output`` option in the ``Audio / Voice`` menu (both options in the menu achieve the same outcome).

**Options**

- ``Provider`` *provider*

Choose the provider. *Default:* `OpenAI TTS`

Available providers:

* OpenAI TTS
* Microsoft Azure TTS
* Google TTS
* Eleven Labs TTS

**OpenAI Text-To-Speech**

- ``Model`` *openai_model*

Choose the model. Available options:

* tts-1
* tts-1-hd

*Default:* `tts-1`

- `Voice` *openai_voice*

Choose the voice. Available voices to choose from:

* alloy
* echo
* fable
* onyx
* nova
* shimmer

*Default:* `alloy`

**Microsoft Azure Text-To-Speech**

- ``Azure API Key`` *azure_api_key*

Here, you should enter the API key, which can be obtained by registering for free on the following website: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech

- ``Azure Region`` *azure_region*

You must also provide the appropriate region for Azure here. *Default:* `eastus`

- ``Voice (EN)`` *azure_voice_en*

Here you can specify the name of the voice used for speech synthesis for English. *Default:* `en-US-AriaNeural`

- ``Voice (non-English)`` *azure_voice_pl*

Here you can specify the name of the voice used for speech synthesis for other non-english languages. *Default:* `pl-PL-AgnieszkaNeural`

**Google Text-To-Speech**

- ``Google Cloud Text-to-speech API Key`` *google_api_key*

You can obtain your own API key at: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com

- ``Voice`` *google_voice*

Specify voice. Voices: https://cloud.google.com/text-to-speech/docs/voices

- ``Language code`` *google_api_key*

Language code. Language codes: https://cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages

**Eleven Labs Text-To-Speech**

- ``Eleven Labs API Key`` *eleven_labs_api_key*

You can obtain your own API key at: https://elevenlabs.io/speech-synthesis

- ``Voice ID`` *eleven_labs_voice*

Voice ID. Voices: https://elevenlabs.io/voice-library

- ``Model`` *eleven_labs_model*

Specify model. Models: https://elevenlabs.io/docs/speech-synthesis/models


If speech synthesis is enabled, a voice will be additionally generated in the background while generating a response via model.

Both ``OpenAI TTS`` and ``OpenAI Whisper`` use the same single API key provided for the OpenAI API, with no additional keys required.


Autonomous Agent (inline)
-------------------------

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

If enabled, plugin will stop after goal is reached. *Default:* `True`

- ``Reverse roles between iterations`` *reverse_roles*

Only for Completion mode. 
If enabled, this option reverses the roles (AI <> user) with each iteration. For example, 
if in the previous iteration the response was generated for "Batman," the next iteration will use that 
response to generate an input for "Joker." *Default:* `True`

Bitbucket
---------

The Bitbucket plugin allows for seamless integration with the Bitbucket Cloud API, offering functionalities to manage repositories, issues, and pull requests. This plugin provides highly configurable options for authentication, cached convenience, and manages HTTP requests efficiently.


* Retrieve details about the authenticated user.
* Get information about a specific user.
* List available workspaces.
* List repositories in a workspace.
* Get details about a specific repository.
* Create a new repository.
* Delete an existing repository.
* Retrieve contents of a file in a repository.
* Upload a file to a repository.
* Delete a file from a repository.
* List issues in a repository.
* Create a new issue.
* Comment on an existing issue.
* Update details of an issue.
* List pull requests in a repository.
* Create a new pull request.
* Merge an existing pull request.
* Search for repositories.

**Options**

- ``API base`` *api_base*

  Define the base URL for the Bitbucket Cloud API. *Default:* `https://api.bitbucket.org/2.0`

- ``HTTP timeout (s)`` *http_timeout*

  Set the timeout for HTTP requests in seconds. *Default:* `30`

**Auth options**

- ``Auth mode`` *auth_mode*

  Select the authentication mode. *Default:* `auto`

  Available modes:
  * auto
  * basic
  * bearer

- ``Username`` *bb_username*

  Provide your Bitbucket username (handle, not email).

- ``App Password`` *bb_app_password*

  Specify your Bitbucket App Password (Basic). This option is secret.

- ``Bearer token`` *bb_access_token*

  Enter the OAuth access token (Bearer). This option is secret.

**Cached convenience**

- ``(auto) User UUID`` *user_uuid*

  Cached after using the `bb_me` command.

- ``(auto) Username`` *username*

  Cached after using the `bb_me` command.

**Commands**

*Auth Options*

- ``bb_auth_set_mode``

  Set the authentication mode: auto|basic|bearer.

- ``bb_set_app_password``

  Set App Password credentials including username and app password.

- ``bb_set_bearer``

  Set the Bearer authentication token.

- ``bb_auth_check``

  Run diagnostics to show authentication results for `/user`.

*User Management*

- ``bb_me``

  Retrieve details for the authenticated user.

- ``bb_user_get``

  Fetch user information by username.

- ``bb_workspaces_list``

  List all accessible workspaces.

*Repositories Management*

- ``bb_repos_list``

  Display a list of repositories.

- ``bb_repo_get``

  Fetch details of a specific repository.

- ``bb_repo_create``

  Create a new repository in a specified workspace.

- ``bb_repo_delete``

  Delete a repository (requires confirmation).

*Contents Management*

- ``bb_contents_get``

  Retrieve file or directory contents from a repository.

- ``bb_file_put``

  Create or update a file in a repository.

- ``bb_file_delete``

  Delete specified files within a repository.

*Issues Management*

- ``bb_issues_list``

  List issues in a repository.

- ``bb_issue_create``

  Create a new issue within a repository.

- ``bb_issue_comment``

  Add a comment to an existing issue.

- ``bb_issue_update``

  Update details of an existing issue.

*Pull Requests Management*

- ``bb_prs_list``

  Display a list of pull requests.

- ``bb_pr_create``

  Create a new pull request.

- ``bb_pr_merge``

  Merge an existing pull request.

*Search Functionality*

- ``bb_search_repos``

  Search repositories using Bitbucket Query Language (BBQL).


Chat with files (LlamaIndex, inline)
-------------------------------------

Plugin integrates ``LlamaIndex`` storage in any chat and provides additional knowledge into context.

**Options**

- ``Ask LlamaIndex first`` *ask_llama_first*

When enabled, then `LlamaIndex` will be asked first, and response will be used as additional knowledge in prompt. When disabled, then `LlamaIndex` will be asked only when needed. **INFO: Disabled in autonomous mode (via plugin)!** *Default:* `False`

- ``Auto-prepare question before asking LlamaIndex first`` *prepare_question*

When enabled, then question will be prepared before asking LlamaIndex first to create best query.

- ``Model for question preparation`` *model_prepare_question*

Model used to prepare question before asking LlamaIndex. *Default:* `gpt-3.5-turbo`

- ``Max output tokens for question preparation`` *prepare_question_max_tokens*

Max tokens in output when preparing question before asking LlamaIndex. *Default:* `500`

- ``Prompt for question preparation`` *syntax_prepare_question*

System prompt for question preparation.

- ``Max characters in question`` *max_question_chars*

Max characters in question when querying LlamaIndex, 0 = no limit, default: `1000`

- ``Append metadata to context`` *append_meta*

If enabled, then metadata from LlamaIndex will be appended to additional context. *Default:* `False`

- ``Model`` *model_query*

Model used for querying ``LlamaIndex``. *Default:* ``gpt-3.5-turbo``

- ``Index name`` *idx*

Indexes to use. If you want to use multiple indexes at once then separate them by comma. *Default:* `base`


Code Interpreter
-------------------------

**Executing Code**

From version ``2.4.13`` with built-in ``IPython``.

The plugin operates similarly to the ``Code Interpreter`` in ``ChatGPT``, with the key difference that it works locally on the user's system. It allows for the execution of any Python code on the computer that the model may generate. When combined with the ``Files I/O`` plugin, it facilitates running code from files saved in the ``data`` directory. You can also prepare your own code files and enable the model to use them or add your own plugin for this purpose. You can execute commands and code on the host machine or in Docker container.

**IPython:** Starting from version ``2.4.13``, it is highly recommended to adopt the new option: ``IPython``, which offers significant improvements over previous workflows. IPython provides a robust environment for executing code within a kernel, allowing you to maintain the state of your session by preserving the results of previous commands. This feature is particularly useful for iterative development and data analysis, as it enables you to build upon prior computations without starting from scratch. Moreover, IPython supports the use of magic commands, such as ``!pip install <package_name>``, which facilitate the installation of new packages directly within the session. This capability streamlines the process of managing dependencies and enhances the flexibility of your development environment. Overall, IPython offers a more efficient and user-friendly experience for executing and managing code.

To use IPython in sandbox mode, Docker must be installed on your system. 

You can find the installation instructions here: https://docs.docker.com/engine/install/

**Tip: connecting IPython in Docker in Snap version**:

To use IPython in the Snap version, you must connect PyGPT to the Docker daemon:

.. code-block:: console

    $ sudo snap connect pygpt:docker-executables docker:docker-executables

.. code-block:: console

    $ sudo snap connect pygpt:docker docker:docker-daemon

**Code interpreter:** a real-time Python code interpreter is built-in. Click the ``<>`` icon to open the interpreter window. Both the input and output of the interpreter are connected to the plugin. Any output generated by the executed code will be displayed in the interpreter. Additionally, you can request the model to retrieve contents from the interpreter window output.

.. image:: images/v2_python.png
   :width: 600

**INFO:** Executing Python code using IPython in compiled versions requires an enabled sandbox (Docker container). You can connect the Docker container via ``Plugins -> Settings``.

**Tip:** always remember to enable the ``+ Tools`` option to allow execute commands from the plugins.

**Options:**

**General**

- ``Connect to the Python code interpreter window`` *attach_output*

Automatically attach code input/output to the Python code interpreter window. *Default:* ``True``

- ``Tool: get_python_output`` *cmd.get_python_output*

Allows ``get_python_output`` command execution. If enabled, it allows retrieval of the output from the Python code interpreter window. *Default:* ``True``

- ``Tool: get_python_input`` *cmd.get_python_input*

Allows ``get_python_input`` command execution. If enabled, it allows retrieval all input code (from edit section) from the Python code interpreter window. *Default:* ``True``

- ``Tool: clear_python_output`` *cmd.clear_python_output*

Allows ``clear_python_output`` command execution. If enabled, it allows clear the output of the Python code interpreter window. *Default:* ``True``


**IPython**

- ``Sandbox (docker container)`` *sandbox_ipython*

Executes IPython in sandbox (docker container). Docker must be installed and running.

- ``Dockerfile`` *ipython_dockerfile*

You can customize the Dockerfile for the image used by IPython by editing the configuration above and rebuilding the image via Tools -> Rebuild IPython Docker Image.

- ``Session Key`` *ipython_session_key*

It must match the key provided in the Dockerfile.

- ``Docker image name`` *ipython_image_name*

Custom Docker image name

- ``Docker container name`` *ipython_container_name*

Custom Docker container name

- ``Connection address`` *ipython_conn_addr*

Default: 127.0.0.1

- ``Port: shell`` *ipython_port_shell*

Default: 5555

- ``Port: iopub`` *ipython_port_iopub*

Default: 5556

- ``Port: stdin`` *ipython_port_stdin*

Default: 5557

- ``Port: control`` *ipython_port_control*

Default: 5558

- ``Port: hb`` *ipython_port_hb*

Default: 5559

- ``Tool: ipython_execute`` *cmd.ipython_execute*

Allows Python code execution in IPython interpreter (in current kernel). *Default:* ``True``

- ``Tool: python_kernel_restart`` *cmd.ipython_kernel_restart*

Allows to restart IPython kernel. *Default:* ``True``


**Python (legacy)**

- ``Sandbox (docker container)`` *sandbox_docker*

Executes commands in sandbox (docker container). Docker must be installed and running.

- ``Python command template`` *python_cmd_tpl*

Python command template (use {filename} as path to file placeholder). *Default:* ``python3 {filename}``

- ``Dockerfile`` *dockerfile*

You can customize the Dockerfile for the image used by legacy Python by editing the configuration above and rebuilding the image via Tools -> Rebuild Python (Legacy) Docker Image.

- ``Docker image name`` *image_name*

Custom Docker image name

- ``Docker container name`` *container_name*

Custom Docker container name

- ``Tool: code_execute`` *cmd.code_execute*

Allows ``code_execute`` command execution. If enabled, provides Python code execution (generate and execute from file). *Default:* ``True``

- ``Tool: code_execute_all`` *cmd.code_execute_all*

Allows ``code_execute_all`` command execution. If enabled, provides execution of all the Python code in interpreter window. *Default:* ``True``

- ``Tool: code_execute_file`` *cmd.code_execute_file*

Allows ``code_execute_file`` command execution. If enabled, provides Python code execution from existing .py file. *Default:* ``True``


**HTML Canvas**

- ``Tool: render_html_output`` *cmd.render_html_output*

Allows ``render_html_output`` command execution. If enabled, it allows to render HTML/JS code in built-it HTML/JS browser (HTML Canvas). *Default:* ``True``

- ``Tool: get_html_output`` *cmd.get_html_output*

Allows ``get_html_output`` command execution. If enabled, it allows retrieval current output from HTML Canvas. *Default:* ``True``

- ``Sandbox (docker container)`` *sandbox_docker*

Execute commands in sandbox (docker container). Docker must be installed and running. *Default:* ``False``

- ``Docker image`` *sandbox_docker_image*

Docker image to use for sandbox *Default:* ``python:3.8-alpine``

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

You can also use ``@`` ID tags to automatically use summary of previous contexts in current discussion.
To use context from previous discussion with specified ID use following syntax in your query:

.. code-block:: ini

   @123

Where ``123`` is the ID of previous context (conversation) in database, example of use:

.. code-block:: ini

   Let's talk about discussion @123

**Options**

- ``Enable: using context @ ID tags`` *use_tags*

When enabled, it allows to automatically retrieve context history using @ tags, e.g. use @123 in question to use summary of context with ID 123 as additional context. *Default:* `False`

- ``Tool: get date range context list`` *cmd.get_ctx_list_in_date_range*

Allows `get_ctx_list_in_date_range` command execution. If enabled, it allows getting the list of context history (previous conversations). *Default:* `True`

- ``Tool: get context content by ID`` *cmd.get_ctx_content_by_id*

Allows `get_ctx_content_by_id` command execution. If enabled, it allows getting summarized content of context with defined ID. *Default:* `True`

- ``Tool: count contexts in date range`` *cmd.count_ctx_in_date*

Allows `count_ctx_in_date` command execution. If enabled, it allows counting contexts in date range. *Default:* `True`

- ``Tool: get day note`` *cmd.get_day_note*

Allows `get_day_note` command execution. If enabled, it allows retrieving day note for specific date. *Default:* `True`

- ``Tool: add day note`` *cmd.add_day_note*

Allows `add_day_note` command execution. If enabled, it allows adding day note for specific date. *Default:* `True`

- ``Tool: update day note`` *cmd.update_day_note*

Allows `update_day_note` command execution. If enabled, it allows updating day note for specific date. *Default:* `True`

- ``Tool: remove day note`` *cmd.remove_day_note*

Allows `remove_day_note` command execution. If enabled, it allows removing day note for specific date. *Default:* `True`

- ``Model`` *model_summarize*

Model used for summarize. *Default:* `gpt-3.5-turbo`

- ``Max summary tokens`` *summary_max_tokens*

Max tokens in output when generating summary. *Default:* `1500`

- ``Max contexts to retrieve`` *ctx_items_limit*

Max items in context history list to retrieve in one query. 0 = no limit. *Default:* `30`

- ``Per-context items content chunk size`` *chunk_size*

Per-context content chunk size (max characters per chunk). *Default:* `100000 chars`

**Options (advanced)**

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

Number of active tasks is always displayed in a tray dropdown menu:

.. image:: images/v2_crontab_tray.png
   :width: 400

- ``Create a new context on job run`` *new_ctx*

If enabled, then a new context will be created on every run of the job." *Default:* `True`

- ``Show notification on job run`` *show_notify*

If enabled, then a tray notification will be shown on every run of the job. *Default:* `True`


Custom Commands
------------------------

With the ``Custom Commands`` plugin, you can integrate **PyGPT** with your operating system and scripts or applications. You can define an unlimited number of custom commands and instruct model on when and how to execute them. Configuration is straightforward, and **PyGPT** includes a simple tutorial command for testing and learning how it works:

.. image:: images/v2_custom_cmd.png
   :width: 800

To add a new custom command, click the **ADD** button and then:

1. Provide a name for your command: this is a unique identifier for model.
2. Provide an ``instruction`` explaining what this command does; model will know when to use the command based on this instruction.
3. Define ``params``, separated by commas - model will send data to your commands using these params. These params will be placed into placeholders you have defined in the ``cmd`` field. For example:

If you want instruct model to execute your Python script named ``smart_home_lights.py`` with an argument, such as ``1`` to turn the light ON, and ``0`` to turn it OFF, define it as follows:

- **name**: lights_cmd
- **instruction**: turn lights on/off; use 1 as 'arg' to turn ON, or 0 as 'arg' to turn OFF
- **params**: arg
- **cmd**: ``python /path/to/smart_home_lights.py {arg}``

The setup defined above will work as follows:

When you ask model to turn your lights ON, model will locate this command and prepare the command ``python /path/to/smart_home_lights.py {arg}`` with ``{arg}`` replaced with ``1``. On your system, it will execute the command:

.. code-block:: console

  python /path/to/smart_home_lights.py 1

And that's all. Model will take care of the rest when you ask to turn ON the lights.

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

With the setup above, every time you ask model to generate a song for you and save it to the disk, it will:

1. Generate a song.
2. Locate your command.
3. Execute the command by sending the song's title and text.
4. The command will save the song text into a file named with the song's title in the **PyGPT** working directory.

**Example tutorial command**

**PyGPT** provides simple tutorial command to show how it work, to run it just ask model for execute ``tutorial test command`` and it will show you how it works:

.. code-block:: console

  > please execute tutorial test command

.. image:: images/v2_custom_cmd_example.png
   :width: 800


Experts (inline)
-----------------

The plugin allows calling experts in any chat mode. This is the inline Experts (co-op) mode.

See the ``Work modes -> Experts`` section for more details.

Facebook
--------

The plugin integrates with Facebook's Graph API to enable various actions such as managing pages, posts, and media uploads. It uses OAuth2 for authentication and supports automatic token exchange processes. 

* Retrieving basic information about the authenticated user.
* Listing all Facebook pages the user has access to.
* Setting a specified Facebook page as the default.
* Retrieving a list of posts from a Facebook page.
* Creating a new post on a Facebook page.
* Deleting a post from a Facebook page.
* Uploading a photo to a Facebook page.

**Options**

- ``Graph API Version`` *graph_version*

Specify the API version. *Default:* `v21.0`

- ``API Base`` *api_base*

Base address for the Graph API. The version will be appended automatically.

- ``Authorize Base`` *authorize_base*

Base address for OAuth authorization. The version will be appended automatically.

- ``HTTP Timeout (s)`` *http_timeout*

Set the timeout for HTTP requests in seconds. *Default:* `30`

**OAuth2 (PKCE) Settings**

- ``App ID (client_id)`` *oauth2_client_id*

Provide your Facebook App ID.

- ``App Secret (optional)`` *oauth2_client_secret*

Required for long-lived token exchange unless using PKCE. *Secret*

- ``Confidential Client`` *oauth2_confidential*

Use `client_secret` on exchange instead of `code_verifier`.

- ``Redirect URI`` *oauth2_redirect_uri*

Matches one of the valid OAuth Redirect URIs in your Meta App. 

- ``Scopes`` *oauth2_scopes*

Space-separated authorized permissions. 

- ``User Access Token`` *oauth2_access_token*

Stores user access token. *Secret*

**Convenience Cache**

- ``User ID`` *user_id*

Cached after calling `fb_me` or OAuth exchange.

- ``User Name`` *user_name*

Cached after calling `fb_me` or OAuth exchange.

- ``Default Page ID`` *fb_page_id*

Selected via `fb_page_set_default`.

- ``Default Page Name`` *fb_page_name*

Selected via `fb_page_set_default`.

- ``Default Page Access Token`` *fb_page_access_token*

Cached with `fb_page_set_default` or on demand. *Secret*

**OAuth UX Options**

- ``Auto-start OAuth`` *oauth_auto_begin*

Automatically begin PKCE flow when commands need a user token.

- ``Open Browser Automatically`` *oauth_open_browser*

Open authorization URL in the default web browser.

- ``Use Local Server for OAuth`` *oauth_local_server*

Start a local HTTP server to capture redirect.

- ``OAuth Local Timeout (s)`` *oauth_local_timeout*

Duration to wait for a redirect with code. *Default:* `180`

- ``Success HTML`` *oauth_success_html*

HTML displayed on successful local callback.

- ``Fail HTML`` *oauth_fail_html*

HTML displayed on callback error.

- ``OAuth Local Port`` *oauth_local_port*

Set the local HTTP port; should be above 1024 and allowed in the app. *Default:* `8732`

- ``Allow Fallback Port`` *oauth_allow_port_fallback*

Choose a free local port if the preferred port is busy or forbidden.

**Supported Commands**

- ``Auth: Begin OAuth2`` *fb_oauth_begin*

Starts OAuth2 (PKCE) flow and returns the authorization URL.

- ``Auth: Exchange Code`` *fb_oauth_exchange*

Trades authorization code for a user access token.

- ``Auth: Extend User Token`` *fb_token_extend*

Exchanges a short-lived token for a long-lived token; requires app secret.

- ``Users: Me`` *fb_me*

Retrieves the authorized user's profile.

- ``Pages: List`` *fb_pages_list*

Lists pages the user manages with details like ID, name, and access token.

- ``Pages: Set Default`` *fb_page_set_default*

Caches name and access token for a default page.

- ``Posts: List`` *fb_page_posts*

Retrieves the page's feed (posts).

- ``Posts: Create`` *fb_page_post_create*

Publishes a post with optional text, links, and photos.

- ``Posts: Delete`` *fb_page_post_delete*

Removes a specified page post.

- ``Media: Upload Photo`` *fb_page_photo_upload*

Uploads a photo to a page from a local path or URL.


Files I/O
------------------

The plugin allows for file management within the local filesystem. It enables the model to create, read, write and query files located in the ``data`` directory, which can be found in the user's work directory. With this plugin, the AI can also generate Python code files and thereafter execute that code within the user's system.

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
* Reading file info
* Indexing files and directories using LlamaIndex
- Querying files using LlamaIndex
- Searching for files and directories

If a file being created (with the same name) already exists, a prefix including the date and time is added to the file name.

**Options:**

**General**

- ``Tool: send (upload) file as attachment`` *cmd.send_file*

Allows `send_file` command execution. *Default:* `True`

- ``Tool: read file`` *cmd.read_file*

Allows `read_file` command execution. *Default:* `True`

- ``Tool: append to file`` *cmd.append_file*

Allows `append_file` command execution. Text-based files only (plain text, JSON, CSV, etc.) *Default:* `True`

- ``Tool: save file`` *cmd.save_file*

Allows `save_file` command execution. Text-based files only (plain text, JSON, CSV, etc.) *Default:* `True`

- ``Tool: delete file`` *cmd.delete_file*

Allows `delete_file` command execution. *Default:* `True`

- ``Tool: list files (ls)`` *cmd.list_files*

Allows `list_dir` command execution. *Default:* `True`

- ``Tool: list files in dirs in directory (ls)`` *cmd.list_dir*

Allows `mkdir` command execution. *Default:* `True`

- ``Tool: downloading files`` *cmd.download_file*

Allows `download_file` command execution. *Default:* `True`

- ``Tool: removing directories`` *cmd.rmdir*

Allows `rmdir` command execution. *Default:* `True`

- ``Tool: copying files`` *cmd.copy_file*

Allows `copy_file` command execution. *Default:* `True`

- ``Tool: copying directories (recursive)`` *cmd.copy_dir*

Allows `copy_dir` command execution. *Default:* `True`

- ``Tool: move files and directories (rename)`` *cmd.move*

Allows `move` command execution. *Default:* `True`

- ``Tool: check if path is directory`` *cmd.is_dir*

Allows `is_dir` command execution. *Default:* `True`

- ``Tool: check if path is file`` *cmd.is_file*

Allows `is_file` command execution. *Default:* `True`

- ``Tool: check if file or directory exists`` *cmd.file_exists*

Allows `file_exists` command execution. *Default:* `True`

- ``Tool: get file size`` *cmd.file_size*

Allows `file_size` command execution. *Default:* `True`

- ``Tool: get file info`` *cmd.file_info*

Allows `file_info` command execution. *Default:* `True`

- ``Tool: find file or directory`` *cmd.find*

Allows `find` command execution. *Default:* `True`

- ``Tool: get current working directory`` *cmd.cwd*

Allows `cwd` command execution. *Default:* `True`

- ``Use data loaders`` *use_loaders*

Use data loaders from LlamaIndex for file reading (`read_file` command). *Default:* `True`

**Indexing**

- ``Tool: quick query the file with LlamaIndex`` *cmd.query_file*

Allows `query_file` command execution (in-memory index). If enabled, model will be able to quick index file into memory and query it for data (in-memory index) *Default:* `True`

- ``Model for query in-memory index`` *model_tmp_query*

Model used for query temporary index for `query_file` command (in-memory index). *Default:* `gpt-3.5-turbo`

- ``Tool: indexing files to persistent index`` *cmd.file_index*

Allows `file_index` command execution. If enabled, model will be able to index file or directory using LlamaIndex (persistent index). *Default:* `True`

- ``Index to use when indexing files`` *idx*

ID of index to use for indexing files (persistent index). *Default:* `base`

- ``Auto index reading files`` *auto_index*

If enabled, every time file is read, it will be automatically indexed (persistent index). *Default:* `False`

- ``Only index reading files`` *only_index*

If enabled, file will be indexed without return its content on file read (persistent index). *Default:* `False`

GitHub
------

The plugin provides seamless integration with GitHub, allowing various operations such as repository management, issue tracking, pull requests, and more through GitHub's API. This plugin requires authentication, which can be configured using a Personal Access Token (PAT) or OAuth Device Flow.

* Retrieve details about your GitHub profile.
* Get information about a specific GitHub user.
* List repositories for a user or organization.
* Retrieve details about a specific repository.
* Create a new repository.
* Delete an existing repository.
* Retrieve the contents of a file in a repository.
* Upload or update a file in a repository.
* Delete a file from a repository.
* List issues in a repository.
* Create a new issue in a repository.
* Add a comment to an existing issue.
* Close an existing issue.
* List pull requests in a repository.
* Create a new pull request.
* Merge an existing pull request.
* Search for repositories based on a query.
* Search for issues based on a query.
* Search for code based on a query.

**Options**

- ``API base`` *api_base*

  Configure the base URL for GitHub's API. *Default:* `https://api.github.com`

- ``Web base`` *web_base*

  Set the GitHub website base URL. *Default:* `https://github.com`

- ``API version header`` *api_version*

  Specify the API version for requests. *Default:* `2022-11-28`

- ``HTTP timeout (s)`` *http_timeout*

  Define timeout for API requests in seconds. *Default:* `30`

**OAuth Device Flow**

- ``OAuth Client ID`` *oauth_client_id*

  Set the Client ID from your GitHub OAuth App. Supports Device Flow. *Secret*

- ``Scopes`` *oauth_scopes*

  List the space-separated OAuth scopes. *Default:* `repo read:org read:user user:email`

- ``Open browser automatically`` *oauth_open_browser*

  Automatically open the verification URL in the default browser. *Default:* `True`

- ``Auto-start auth when required`` *oauth_auto_begin*

  Start Device Flow automatically when a command requires a token. *Default:* `True`

**Tokens**

- ``(auto) OAuth access token`` *gh_access_token*

  Store OAuth access token for Device/Web. *Secret*

- ``PAT token (optional)`` *pat_token*

  Provide a Personal Access Token (classic or fine-grained) for authentication. *Secret*

- ``Auth scheme`` *auth_scheme*

  Choose the authentication scheme: `Bearer` or `Token` (use `Token` for PAT).

**Convenience Cache**

- ``(auto) User ID`` *user_id*

  Cache User ID after `gh_me` or authentication.

- ``(auto) Username`` *username*

  Cache username after `gh_me` or authentication.

**Commands**

- **Auth**

  * ``gh_device_begin``: Begin OAuth Device Flow.
  * ``gh_device_poll``: Poll for access token using device code.
  * ``gh_set_pat``: Set Personal Access Token.

- **Users**

  * ``gh_me``: Get authenticated user details.
  * ``gh_user_get``: Retrieve user information by username.

- **Repositories**

  * ``gh_repos_list``: List all repositories.
  * ``gh_repo_get``: Get details for a specific repository.
  * ``gh_repo_create``: Create a new repository.
  * ``gh_repo_delete``: Delete an existing repository. (*Disabled by default*)

- **Contents**

  * ``gh_contents_get``: Get file or directory contents.
  * ``gh_file_put``: Create or update a file via Contents API.
  * ``gh_file_delete``: Delete a file via Contents API.

- **Issues**

  * ``gh_issues_list``: List issues in a repository.
  * ``gh_issue_create``: Create a new issue.
  * ``gh_issue_comment``: Comment on an issue.
  * ``gh_issue_close``: Close an existing issue.

- **Pull Requests**

  * ``gh_pulls_list``: List all pull requests.
  * ``gh_pull_create``: Create a new pull request.
  * ``gh_pull_merge``: Merge an existing pull request.

- **Search**

  * ``gh_search_repos``: Search for repositories.
  * ``gh_search_issues``: Search for issues and pull requests.
  * ``gh_search_code``: Search for code across repositories.




Google (Gmail, Drive, Calendar, Contacts, YT, Keep, Docs, Maps, Colab)
----------------------------------------------------------------------

The plugin integrates with various Google services, enabling features such as email management, calendar events, contact handling, and document manipulation through Google APIs.


**Gmail**

* Listing recent emails from Gmail.
* Listing all emails from Gmail.
* Searching emails in Gmail.
* Retrieving email details by ID in Gmail.
* Sending an email via Gmail.

**Google Calendar**

* Listing recent calendar events.
* Listing today's calendar events.
* Listing tomorrow's calendar events.
* Listing all calendar events.
* Retrieving calendar events by a specific date.
* Adding a new event to the calendar.
* Deleting an event from the calendar.

**Google Keep**

* Listing notes from Google Keep.
* Adding a new note to Google Keep.

**Google Drive**

* Listing files from Google Drive.
* Finding a file in Google Drive by its path.
* Downloading a file from Google Drive.
* Uploading a file to Google Drive.

**YouTube**

* Retrieving information about a YouTube video.
* Retrieving the transcript of a YouTube video.

**Google Contacts**

* Listing contacts from Google Contacts.
* Adding a new contact to Google Contacts.

**Google Docs**

* Creating a new document.
* Retrieving a document.
* Listing documents.
* Appending text to a document.
* Replacing text in a document.
* Inserting a heading in a document.
* Exporting a document.
* Copying from a template.

**Google Maps**

* Geocoding an address.
* Reverse geocoding coordinates.
* Getting directions between locations.
* Using the distance matrix.
* Text search for places.
* Finding nearby places.
* Generating static map images.

**Google Colab**

* Listing notebooks.
* Creating a new notebook.
* Adding a code cell.
* Adding a markdown cell.
* Getting a link to a notebook.
* Renaming a notebook.
* Duplicating a notebook.

**Options**

- ``Google credentials.json (content)`` *credentials*

  Paste the JSON content of your OAuth client or Service Account. This is mandatory for the plugin to access your Google services. *Secret:* Yes

- ``OAuth token store (auto)`` *oauth_token*

  Automatically stores and updates the refresh token necessary for Google service access. *Secret:* Yes

- ``Use local server for OAuth`` *oauth_local_server*

  Run a local server for the installed app OAuth flow to simplify the authentication process. *Default:* `True`

- ``OAuth local port (0=random)`` *oauth_local_port*

  Specify the port for `InstalledAppFlow.run_local_server`. A value of `0` lets the system choose a random available port. *Default:* `0`

- ``Scopes`` *oauth_scopes*

  Define space-separated OAuth scopes for services like Gmail, Calendar, Drive, Contacts, YouTube, Docs, and Keep. Extend scopes to include Keep services if needed. 

- ``Impersonate user (Workspace DWD)`` *impersonate_user*

  Optionally provide a subject for service account domain-wide delegation.

- ``YouTube API Key (optional)`` *youtube_api_key*

  If provided, allows fetching public video information without needing OAuth tokens. *Secret:* Yes

- ``Allow unofficial YouTube transcript`` *allow_unofficial_youtube_transcript*

  Enables the use of `youtube-transcript-api` for transcripts when official captions are unavailable. *Default:* `False`

- ``Keep mode`` *keep_mode*

  Determines the mode for accessing Keep: `official`, `unofficial`, or `auto`. *Default:* `auto`

- ``Allow unofficial Keep`` *allow_unofficial_keep*

  Use `gkeepapi` as a fallback for Keep services, requiring `keep_username` and `keep_master_token`. *Default:* `True`

- ``Keep username (unofficial)`` *keep_username*

  Set the email used for `gkeepapi`.

- ``Keep master token (unofficial)`` *keep_master_token*

  Provide the master token for `gkeepapi` usage, ensuring secure handling. *Secret:* Yes

- ``Google Maps API Key`` *google_maps_api_key*

  Necessary for accessing Google Maps features like Geocoding, Directions, and Distance Matrix. *Secret:* Yes

- ``Maps API Key (alias)`` *maps_api_key*

  Alias for `google_maps_api_key` for backward compatibility. *Secret:* Yes

**Integration Commands**

- Gmail: Manage your emails by listing recent messages, searching Gmail, sending and receiving emails through specific commands.

- Calendar: Access your Google Calendar to retrieve events or manage them by adding or deleting entries.

- Keep: List or add notes using Google Keep, utilizing either official or unofficial methods as per the settings.

- Drive: Perform file operations on Google Drive, including listing files, uploading, downloading, or finding files by path.

- YouTube: Retrieve video information and transcripts, with the option to use unofficial transcripts if enabled.

- Contacts: List or add contacts within your Google account, defining specific fields for detailed contact management.

- Google Docs: Create, retrieve, or manipulate Google Docs, supporting various document operations.

- Google Maps: Utilize services like Geocoding addresses, fetching directions, and conducting place-related searches with provided APIs.

- Google Colab: Manage Colab notebooks on Google Drive, supporting creating, renaming, duplicating, and listing operations.


Image Generation (inline)
-------------------------

The plugin integrates ``DALL-E 3`` image generation with any chat mode. Simply enable it and request an image in Chat mode, using a standard model such as ``GPT-4``. The plugin does not require the ``+ Tools`` option to be enabled.

**Options**

- ``Prompt`` *prompt*

The prompt is used to generate a query for the ``DALL-E`` image generation model, which runs in the background.


Mailer
-------

Enables the sending, receiving, and reading of emails from the inbox. Currently, only SMTP is supported. More options coming soon.

**Options**

- ``From (email)`` *from_email*

From (email), e.g. me@domain.com

- ``Tool: send_mail`` *cmd.send_mail*

Allows ``send_mail`` command execution. If enabled, model will be able to sending emails.

- ``Tool: receive_emails`` *cmd.receive_emails*

Allows ``receive_emails`` command execution. If enabled, model will be able to receive emails from the server.

- ``Tool: get_email_body`` *cmd.get_email_body*

Allows ``get_email_body`` command execution. If enabled, model will be able to receive message body from the server.

- ``SMTP Host`` *smtp_host*

SMTP Host, e.g. smtp.domain.com

- ``SMTP Port (Inbox)`` *smtp_port_inbox*

SMTP Port, default: 995

- ``SMTP Port (Outbox)`` *smtp_port_outbox*

SMTP Port, default: 465

- ``SMTP User`` *smtp_user*

SMTP User, e.g. user@domain.com

- ``SMTP Password`` *smtp_password*

SMTP Password.


Mouse And Keyboard
-------------------

Introduced in version: `2.4.4` (2024-11-09)

**WARNING: Use this plugin with caution - allowing all options gives the model full control over the mouse and keyboard**

The plugin allows for controlling the mouse and keyboard by the model. With this plugin, you can send a task to the model, e.g., "open notepad, type something in it" or "open web browser, do search, find something."

Plugin capabilities include:

* Get mouse cursor position
* Control mouse cursor position
* Control mouse clicks
* Control mouse scroll
* Control the keyboard (pressing keys, typing text)
* Making screenshots

The ``+ Tools`` option must be enabled to use this plugin.

**Options:**

**General**

- ``Prompt`` *prompt*

Prompt used to instruct how to control the mouse and keyboard.

- ``Enable: Allow mouse movement`` *allow_mouse_move*

Allows mouse movement. *Default:* `True`

- ``Enable: Allow mouse click`` *allow_mouse_click*

Allows mouse click. *Default:* `True`

- ``Enable: Allow mouse scroll`` *allow_mouse_scroll*

Allows mouse scroll. *Default:* `True`

- ``Enable: Allow keyboard key press`` *allow_keyboard*

Allows keyboard typing. *Default:* `True`

- ``Enable: Allow making screenshots`` *allow_screenshot*

Allows making screenshots. *Default:* `True`

- ``Tool: mouse_get_pos`` *cmd.mouse_get_pos*

Allows ``mouse_get_pos`` command execution. *Default:* `True`

- ``Tool: mouse_set_pos`` *cmd.mouse_set_pos*

Allows ``mouse_set_pos`` command execution. *Default:* `True`

- ``Tool: make_screenshot`` *cmd.make_screenshot*

Allows ``make_screenshot`` command execution. *Default:* `True`

- ``Tool: mouse_click`` *cmd.mouse_click*

Allows ``mouse_click`` command execution. *Default:* `True`

- ``Tool: mouse_move`` *cmd.mouse_move*

Allows ``mouse_move`` command execution. *Default:* `True`

- ``Tool: mouse_scroll`` *cmd.mouse_scroll*

Allows ``mouse_scroll`` command execution. *Default:* `True`

- ``Tool: keyboard_key`` *cmd.keyboard_key*

Allows ``keyboard_key`` command execution. *Default:* `True`

- ``Tool: keyboard_type`` *cmd.keyboard_type*

Allows ``keyboard_type`` command execution. *Default:* `True`


Real Time
----------

This plugin automatically adds the current date and time to each system prompt you send. 
You have the option to include just the date, just the time, or both.

When enabled, it quietly enhances each system prompt with current time information before sending it to model.

**Options**

- ``Append time`` *hour*

If enabled, it appends the current time to the system prompt. *Default:* `True`

- ``Append date`` *date*

If enabled, it appends the current date to the system prompt. *Default:* `True` 

- ``Template`` *tpl*

Template to append to the system prompt. The placeholder ``{time}`` will be replaced with the 
current date and time in real-time. *Default:* `Current time is {time}.`


Serial port / USB
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

Port connection speed, in bps. *Default:* ``9600``

- ``Timeout`` *timeout*

Timeout in seconds. *Default:* ``1``

- ``Sleep`` *sleep*

Sleep in seconds after connection. *Default:* ``2``

- ``Tool: Send text commands to USB port`` *cmd.serial_send*

Allows ``serial_send`` command execution". *Default:* `True`

- ``Tool: Send raw bytes to USB port`` *cmd.serial_send_bytes*

Allows ``serial_send_bytes`` command execution. *Default:* `True`

- ``Tool: Read data from USB port`` *cmd.serial_read*

Allows ``serial_read`` command execution. *Default:* `True`




Slack
-----

The Slack plugin integrates with the Slack Web API, enabling interaction with Slack workspaces through the application. This plugin supports OAuth2 for authentication, which allows for seamless integration with Slack services, enabling actions such as posting messages, retrieving users, and managing conversations.

* Retrieving a list of users.
* Listing all conversations.
* Accessing conversation history.
* Retrieving conversation replies.
* Opening a conversation.
* Posting a message in a chat.
* Deleting a chat message.
* Uploading files to Slack.

The plugin can be configured with various options to customize connectivity and feature access.

**Options**

- ``API base`` *api_base*

Set the base URL for Slack's API. *Default:* `https://slack.com/api`

- ``OAuth base`` *oauth_base*

Set the base URL for OAuth authorization. *Default:* `https://slack.com`

- ``HTTP timeout (s)`` *http_timeout*

Specify the request timeout in seconds. *Default:* `30`

**OAuth2 (Slack)**

- ``OAuth2 Client ID`` *oauth2_client_id*

Provide the Client ID from your Slack App. This field is secret.

- ``OAuth2 Client Secret`` *oauth2_client_secret*

Provide the Client Secret from your Slack App. This field is secret.

- ``Redirect URI`` *oauth2_redirect_uri*

Specify the redirect URI that matches one in your Slack App. *Default:* `http://127.0.0.1:8733/callback`

- ``Bot scopes (comma-separated)`` *bot_scopes*

Define the scopes for the bot token. *Default:* `chat:write,users:read,...`

- ``User scopes (comma-separated)`` *user_scopes*

Specify optional user scopes for user token if required.

**Tokens/cache**

- ``(auto/manual) Bot token`` *bot_token*

Input or obtain the bot token automatically or manually. This field is secret.

- ``(auto) User token (optional)`` *user_token*

Get the user token if user scopes are required. This field is secret.

- ``(auto) Refresh token`` *oauth2_refresh_token*

Store refresh token if rotation is enabled. This field is secret.

- ``(auto) Expires at (unix)`` *oauth2_expires_at*

Automatically calculate the token expiry time.

- ``(auto) Team ID`` *team_id*

Cache the Team ID after auth.test or OAuth.

- ``(auto) Bot user ID`` *bot_user_id*

Cache the Bot user ID post OAuth exchange.

- ``(auto) Authed user ID`` *authed_user_id*

Cache the authenticated user ID after auth.test/OAuth.

- ``Auto-start OAuth when required`` *oauth_auto_begin*

Enable automatic initiation of OAuth flow if a command needs a token. *Default:* `True`

- ``Open browser automatically`` *oauth_open_browser*

Open the authorize URL in default browser. *Default:* `True`

- ``Use local server for OAuth`` *oauth_local_server*

Activate local HTTP server to capture redirect. *Default:* `True`

- ``OAuth local timeout (s)`` *oauth_local_timeout*

Set time to wait for redirect with code. *Default:* `180`

- ``Success HTML`` *oauth_success_html*

Specify HTML displayed on successful local callback.

- ``Fail HTML`` *oauth_fail_html*

Specify HTML displayed on failed local callback.

- ``OAuth local port (0=auto)`` *oauth_local_port*

Set local HTTP port; must be registered in Slack App. *Default:* `8733`

- ``Allow fallback port if busy`` *oauth_allow_port_fallback*

Fallback to a free local port if preferred port is busy. *Default:* `True`

**Commands**

- ``slack_oauth_begin``

Begin the OAuth2 flow and return the authorize URL.

- ``slack_oauth_exchange``

Exchange authorization code for tokens.

- ``slack_oauth_refresh``

Refresh token if rotation is enabled.

- ``slack_auth_test``

Test authentication and retrieve IDs.

- ``slack_users_list``

List workspace users (contacts).

- ``slack_conversations_list``

List channels/DMs visible to the token.

- ``slack_conversations_history``

Fetch channel/DM history.

- ``slack_conversations_replies``

Fetch a thread by root ts.

- ``slack_conversations_open``

Open or resume DM or MPDM.

- ``slack_chat_post_message``

Post a message to a channel or DM.

- ``slack_chat_delete``

Delete a message from a channel or DM.

- ``slack_files_upload``

Upload a file via external flow and share in Slack.


System Prompt Extra (append)
-----------------------------

The plugin appends additional system prompts (extra data) from a list to every current system prompt. You can enhance every system prompt with extra instructions that will be automatically appended to the system prompt.

**Options**

- ``Prompts`` *prompts*

List of extra prompts - prompts that will be appended to system prompt. 
All active extra prompts defined on list will be appended to the system prompt in the order they are listed here.


System (OS)
-----------

The plugin provides access to the operating system and executes system commands.

**Options:**

**General**

- ``Auto-append CWD to sys_exec`` *auto_cwd*

Automatically append current working directory to ``sys_exec`` command. *Default:* ``True``

- ``Tool: sys_exec`` *cmd.sys_exec*

Allows ``sys_exec`` command execution. If enabled, provides system commands execution. *Default:* ``True``





Telegram
---------

The plugin enables integration with Telegram for both bots and user accounts through the ``Bot API`` and the ``Telethon`` library respectively. It allows sending and receiving messages, managing chats, and handling updates.

* Sending text messages to a chat or channel.
* Sending photos with an optional caption to a chat or channel.
* Sending documents or files to a chat or channel.
* Retrieving information about a specific chat or channel.
* Polling for updates in bot mode.
* Downloading files using a file identifier.
* Listing contacts in user mode.
* Listing recent dialogs or chats in user mode.
* Retrieving recent messages from a specific chat or channel in user mode.

**Options**

- ``Mode`` *mode*

  Choose the mode of operation. *Default:* `bot`

  Available modes:

  * Bot (via ``Bot API``)
  * User (via ``Telethon``)

- ``API base (Bot)`` *api_base*

  Base URL for the Telegram Bot API. *Default:* `https://api.telegram.org`

- ``HTTP timeout (s)`` *http_timeout*

  Timeout in seconds for HTTP requests. *Default:* `30`

**Bot Options**

- ``Bot token`` *bot_token*

  Token obtained from BotFather for authentication.

- ``Default parse_mode`` *default_parse_mode*

  Default parse mode for sending messages. *Default:* `HTML`

  Available modes:

  * HTML
  * Markdown
  * MarkdownV2

- ``Disable link previews (default)`` *default_disable_preview*

  Option to disable link previews by default. *Default:* `False`

- ``Disable notifications (default)`` *default_disable_notification*

  Option to disable message notifications by default. *Default:* `False`

- ``Protect content (default)`` *default_protect_content*

  Option to protect the content by default. *Default:* `False`

- ``(auto) last update id`` *last_update_id*

  Automatically stored ID after using tg_get_updates.

**User Options (Telethon)**

- ``API ID (user mode)`` *api_id*

  ID required for user authentication. Get from: `https://my.telegram.org`

- ``API Hash (user mode)`` *api_hash*

  Hash required for user authentication. Get from: `https://my.telegram.org`

- ``Phone number (+CC...)`` *phone_number*

  Phone number used to send login code in user mode.

- ``(optional) 2FA password`` *password_2fa*

  Password for two-step verification if enabled.

- ``(auto) Session (StringSession)`` *user_session*

  Session string saved after successful login in user mode.

- ``Auto-begin login when needed`` *auto_login_begin*

  Automatically send login code if authentication is needed and not available. *Default:* `True`

**Commands**

- ``tg_login_begin``

  Begin Telegram user login (sends code to phone).

- ``tg_login_complete``

  Complete login with code and optional 2FA password.

- ``tg_logout``

  Log out and clear saved session.

- ``tg_mode``

  Return current mode (bot|user).

- ``tg_me``

  Get authorized identity using Bot getMe or User get_me.

- ``tg_send_message``

  Send text message to chat/channel.

- ``tg_send_photo``

  Send photo to chat/channel.

- ``tg_send_document``

  Send document/file to chat/channel.

- ``tg_get_chat``

  Get chat info by id or @username.

- ``tg_get_updates``

  Poll updates in bot mode, automatically store last_update_id.

- ``tg_download_file``

  Download file by file_id in bot mode.

- ``tg_contacts_list``

  List contacts in user mode.

- ``tg_dialogs_list``

  List recent dialogs or chats in user mode.

- ``tg_messages_get``

  Get recent messages from a chat in user mode.


Vision (inline)
----------------

The plugin integrates vision capabilities across all chat modes, not just Vision mode. Once enabled, it allows the model to seamlessly switch to vision processing in the background whenever an image attachment or vision capture is detected.

**Tip:** When using ``Vision (inline)`` by utilizing a plugin in standard mode, such as ``Chat`` (not ``Vision`` mode), the ``+ Vision`` special checkbox will appear at the bottom of the Chat window. It will be automatically enabled any time you provide content for analysis (like an uploaded photo). When the checkbox is enabled, the vision model is used. If you wish to exit the vision model after image analysis, simply uncheck the checkbox. It will activate again automatically when the next image content for analysis is provided.

**Options**

- ``Model`` *model*

The model used to temporarily provide vision capabilities. *Default:* `gpt-4-vision-preview`.

- ``Prompt`` *prompt*

The prompt used for vision mode. It will append or replace current system prompt when using vision model.

- ``Replace prompt`` *replace_prompt*

Replace whole system prompt with vision prompt against appending it to the current prompt. *Default:* `False`

- ``Tool: capturing images from camera`` *cmd.camera_capture*

Allows `capture` command execution. If enabled, model will be able to capture images from camera itself. The `+ Tools` option must be enabled. *Default:* `False`

- ``Tool: making screenshots`` *cmd.make_screenshot*

Allows `screenshot` command execution. If enabled, model will be able to making screenshots itself. The `+ Tools` option must be enabled. *Default:* `False`


Voice Control (inline)
----------------------

The plugin provides voice control command execution within a conversation.

See the ``Accessibility`` section for more details.


Web Search
-----------

**PyGPT** lets you connect model to the internet and carry out web searches in real time as you make queries.

To activate this feature, turn on the ``Web Search`` plugin found in the ``Plugins`` menu.

Web searches are provided by ``Google Custom Search Engine`` and ``Microsoft Bing`` APIs and can be extended with other search engine providers. 

**Options**

- `Provider` *provider*

Choose the provider. *Default:* `Google`

Available providers:

- Google
- Microsoft Bing

**Google**

To use this provider, you need an API key, which you can obtain by registering an account at:

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

**Options**

- ``Google Custom Search API KEY`` *google_api_key*

You can obtain your own API key at https://developers.google.com/custom-search/v1/overview

- ``Google Custom Search CX ID`` *google_api_cx*

You will find your CX ID at https://programmablesearchengine.google.com/controlpanel/all - remember to enable "Search on ALL internet pages" option in project settings.

**Microsoft Bing**

- ``Bing Search API KEY`` *bing_api_key*

You can obtain your own API key at https://www.microsoft.com/en-us/bing/apis/bing-web-search-api

- ``Bing Search API endpoint`` *bing_endpoint*

API endpoint for Bing Search API, default: https://api.bing.microsoft.com/v7.0/search

**General options**


- ``Number of pages to search`` *num_pages*

Number of max pages to search per query. *Default:* `10`

- ``Max content characters`` *max_page_content_length*

Max characters of page content to get (0 = unlimited). *Default:* `0`

- ``Per-page content chunk size`` *chunk_size*

Per-page content chunk size (max characters per chunk). *Default:* `20000`

- ``Disable SSL verify`` *disable_ssl*

Disables SSL verification when crawling web pages. *Default:* `False`

- ``Use raw content (without summarization)`` *raw*

Return raw content from web search instead of summarized content. Provides more data but consumes more tokens. *Default:* `True`

- ``Timeout`` *timeout*

Connection timeout (seconds). *Default:* `5`

- ``User agent`` *user_agent*

User agent to use when making requests. *Default:* `Mozilla/5.0`.

- ``Max result length`` *max_result_length*

Max length of the summarized or raw result (characters). *Default:* `50000`

- ``Max summary tokens`` *summary_max_tokens*

Max tokens in output when generating summary. *Default:* `1500`

- ``Tool: web_search`` *cmd.web_search*

Allows `web_search` command execution. If enabled, model will be able to search the Web. *Default:* `True`

- ``Tool: web_url_open`` *cmd.web_url_open*

Allows `web_url_open` command execution. If enabled, model will be able to open specified URL and summarize content. *Default:* `True`

- ``Tool: web_url_raw`` *cmd.web_url_raw*

Allows `web_url_raw` command execution. If enabled, model will be able to open specified URL and get the raw content. *Default:* `True`

- ``Tool: web_request`` *cmd.web_request*

Allows `web_request` command execution. If enabled, model will be able to send any HTTP request to specified URL or API endpoint. *Default:* `True`

- ``Tool: web_extract_links`` *cmd.web_extract_links*

Allows `web_extract_links` command execution. If enabled, model will be able to open URL and get list of all links from it. *Default:* `True`

- ``Tool: web_extract_images`` *cmd.web_extract_images*

Allows `web_extract_images` command execution. If enabled, model will be able to open URL and get list of all images from it.. *Default:* `True`


**Advanced**

- ``Model used for web page summarize`` *summary_model*

Model used for web page summarize. *Default:* `gpt-3.5-turbo-1106`

- ``Summarize prompt`` *prompt_summarize*

Prompt used for web search results summarize, use {query} as a placeholder for search query

- ``Summarize prompt (URL open)`` *prompt_summarize_url*

Prompt used for specified URL page summarize


**Indexing**

- ``Tool: web_index`` *cmd.web_index*

Allows `web_index` command execution. If enabled, model will be able to index pages and external content using LlamaIndex (persistent index). *Default:* `True`

- ``Tool: web_index_query`` *cmd.web_index_query*

Allows `web_index_query` command execution. If enabled, model will be able to quick index and query web content using LlamaIndex (in-memory index). *Default:* `True`

- ``Auto-index all used URLs using LlamaIndex`` *auto_index*

If enabled, every URL used by the model will be automatically indexed using LlamaIndex (persistent index). *Default:* `False`

- ``Index to use`` *idx*

ID of index to use for web page indexing (persistent index). *Default:* `base`


X/Twitter
----------

The X/Twitter plugin integrates with the X platform, allowing for comprehensive interactions such as tweeting, retweeting, liking, media uploads, and more. This plugin requires OAuth2 authentication and offers various configuration options to manage API interactions effectively.

* Retrieve user details by providing their username.
* Fetch user information using their unique ID.
* Access recent tweets from a specific user.
* Search for recent tweets using specific keywords or hashtags.
* Create a new tweet and post it on the platform.
* Remove an existing tweet from your profile.
* Reply to a specific tweet with a new comment.
* Quote a tweet while adding your own comments or thoughts.
* Like a tweet to show appreciation or support.
* Remove a like from a previously liked tweet.
* Retweet a tweet to share it with your followers.
* Undo a retweet to remove it from your profile.
* Hide a specific reply to a tweet.
* List all bookmarked tweets for easy access.
* Add a tweet to your bookmarks for later reference.
* Remove a tweet from your bookmarks.
* Upload media files such as images or videos for tweeting.
* Set alternative text for uploaded media for accessibility.

**Options**

- ``API base`` *api_base*

  Base API URL. *Default:* `https://api.x.com`

- ``Authorize base`` *authorize_base*

  Base URL for OAuth authorization. *Default:* `https://x.com`

- ``HTTP timeout (s)`` *http_timeout*

  Requests timeout in seconds. *Default:* `30`

**OAuth2 PKCE**

- ``OAuth2 Client ID`` *oauth2_client_id*

  Client ID from X Developer Portal. *Secret*

- ``OAuth2 Client Secret (optional)`` *oauth2_client_secret*

  Only for confidential clients. *Secret*

- ``Confidential client (use Basic auth)`` *oauth2_confidential*

  Enable if your App is confidential. *Default:* `False`

- ``Redirect URI`` *oauth2_redirect_uri*

  Must match one of the callback URLs in your X App. *Default:* `http://127.0.0.1:8731/callback`

- ``Scopes`` *oauth2_scopes*

  OAuth2 scopes for Authorization Code with PKCE. *Default:* `tweet.read users.read like.read like.write tweet.write bookmark.read bookmark.write tweet.moderate.write offline.access`

- ``(auto) code_verifier`` *oauth2_code_verifier*

  Generated by x_oauth_begin. *Secret*

- ``(auto) state`` *oauth2_state*

  Generated by x_oauth_begin. *Secret*

- ``(auto) Access token`` *oauth2_access_token*

  Stored user access token. *Secret*

- ``(auto) Refresh token`` *oauth2_refresh_token*

  Stored user refresh token. *Secret*

- ``(auto) Expires at (unix)`` *oauth2_expires_at*

  Auto-calculated expiry time.

**App-only Bearer (optional for read-only)**

- ``App-only Bearer token (optional)`` *bearer_token*

  Optional app-only bearer for read endpoints. *Secret*

**Convenience cache**

- ``(auto) User ID`` *user_id*

  Cached after x_me or oauth exchange.

- ``(auto) Username`` *username*

  Cached after x_me or oauth exchange.

- ``Auto-start OAuth when required`` *oauth_auto_begin*

  Start PKCE flow automatically if needed. *Default:* `True`

- ``Open browser automatically`` *oauth_open_browser*

  Open authorize URL in default browser. *Default:* `True`

- ``Use local server for OAuth`` *oauth_local_server*

  Capture redirect using a local server. *Default:* `True`

- ``OAuth local timeout (s)`` *oauth_local_timeout*

  Time to wait for redirect with code. *Default:* `180`

- ``Success HTML`` *oauth_success_html*

  HTML displayed on local callback success.

- ``Fail HTML`` *oauth_fail_html*

  HTML displayed on local callback error.

- ``OAuth local port (0=auto)`` *oauth_local_port*

  Local HTTP port for callback. *Default:* `8731`

- ``Allow fallback port if busy`` *oauth_allow_port_fallback*

  Use a free port if the preferred port is busy. *Default:* `True`

**Commands**

**Auth**

- ``x_oauth_begin``

  Begin OAuth2 PKCE flow.

- ``x_oauth_exchange``

  Exchange authorization code for tokens.

- ``x_oauth_refresh``

  Refresh access token using refresh_token.

**Users**

- ``x_me``

  Get authorized user information.

- ``x_user_by_username``

  Lookup user by username.

- ``x_user_by_id``

  Lookup user by ID.

**Timelines / Search**

- ``x_user_tweets``

  Retrieve user Tweet timeline.

- ``x_search_recent``

  Perform recent search within the last 7 days.

**Tweet CRUD**

- ``x_tweet_create``

  Create a new Tweet/Post.

- ``x_tweet_delete``

  Delete a Tweet by ID.

- ``x_tweet_reply``

  Reply to a Tweet.

- ``x_tweet_quote``

  Quote a Tweet.

**Actions**

- ``x_like``

  Like a Tweet.

- ``x_unlike``

  Unlike a Tweet.

- ``x_retweet``

  Retweet a Tweet.

- ``x_unretweet``

  Undo a retweet.

- ``x_hide_reply``

  Hide or unhide a reply to your Tweet.

**Bookmarks**

- ``x_bookmarks_list``

  List bookmarks.

- ``x_bookmark_add``

  Add a bookmark.

- ``x_bookmark_remove``

  Remove a bookmark.

**Media**

- ``x_upload_media``

  Upload media and return media_id.

- ``x_media_set_alt_text``

  Attach alt text to uploaded media.

