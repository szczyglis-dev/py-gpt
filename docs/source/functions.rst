Functions and commands
======================

**INFO:** From version ``2.2.20`` PyGPT uses native API function calls by default. You can go back to internal syntax (described below) by switching off option ``Config -> Settings -> Prompts -> Use native API function calls``. Native API function calls are available in Chat, Completion and Assistant modes only (using OpenAI API).

In background, **PyGPT** uses an internal syntax to define commands and their parameters, which can then be used by the model and executed on the application side or even directly in the system. This syntax looks as follows (example command below):

.. code-block:: json

	~###~{"cmd": "send_email", "params": {"quote": "Why don't skeletons fight each other? They don't have the guts!"}}~###~

It is a JSON object wrapped between ``~###~``. The application extracts the JSON object from such formatted text and executes the appropriate function based on the provided parameters and command name. Many of these types of commands are defined in plugins (e.g., those used for file operations or internet searches). You can also define your own commands using the ``Custom Commands`` plugin, or simply by creating your own plugin and adding it to the application.

**Tip:** The ``+ Tools`` option checkbox must be enabled to allow the execution of commands from plugins. Disable the option if you do not want to use commands, to prevent additional token usage (as the command execution system prompt consumes additional tokens).

.. image:: images/v2_code_execute.png
   :width: 400

When native API function calls are disabled, a special system prompt responsible for invoking commands is added to the main system prompt if the ``+ Tools`` option is active.

However, there is an additional possibility to define your own commands and execute them with the help of GPT.
These are functions - defined on the OpenAI API side and described using JSON objects. You can find a complete guide on how to define functions here:

https://platform.openai.com/docs/guides/function-calling

https://cookbook.openai.com/examples/how_to_call_functions_with_chat_models

PyGPT offers compatibility of these functions with commands used in the application. All you need to do is define the appropriate functions using the syntax required by OpenAI, and PyGPT will do the rest, translating such syntax on the fly into its own internal format.

You can define functions for modes: ``Chat`` and ``Assistants``.
Note that - in Chat mode, they should be defined in ``Presets``, and for Assistants, in the ``Assistant`` settings.

**Example of usage:**

1) Chat

Create a new Preset, open the Preset edit dialog and add a new function using ``+ Function`` button with the following content:

**Name:** ``send_email``

**Description:** ``Sends a quote using email``

**Params (JSON):**

.. code-block:: json

	{
	        "type": "object",
	        "properties": {
	            "quote": {
	                "type": "string",
	                "description": "A generated funny quote"
	            }
	        },
	        "required": [
	            "quote"
	        ]
	}


Then, in the ``Custom Commands`` plugin, create a new command with the same name and the same parameters:

**Command name:** ``send_email``

**Instruction/prompt:** ``send mail`` *(don't needed, because it will be called on OpenAI side)*

**Params list:** ``quote``

**Command to execute:** ``echo "OK. Email sent: {quote}"``

At next, enable the ``+ Tools`` option and enable the plugin.

Ask GPT in Chat mode:

.. code-block:: ini

	Create a funny quote and email it

In response you will receive prepared command, like this:

.. code-block:: ini

	~###~{"cmd": "send_email", "params": {"quote": "Why do we tell actors to 'break a leg?' Because every play has a cast!"}}~###~

After receiving this, PyGPT will execute the system ``echo`` command with params given from ``params`` field and replacing ``{quote}`` placeholder with ``quote`` param value.

As a result, response like this will be sent to the model:

.. code-block:: ini

	[{"request": {"cmd": "send_email"}, "result": "OK. Email sent: Why do we tell actors to 'break a leg?' Because every play has a cast!"}]


2) Assistant

In this mode (via Assistants API), it should be done similarly, with the difference that here the functions should be defined in the assistant's settings.

With this flow you can use both forms - OpenAI and PyGPT - to define and execute commands and functions in the application. They will cooperate with each other and you can use them interchangeably.