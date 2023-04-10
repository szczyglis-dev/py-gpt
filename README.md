Current release: **0.9.0** | Build: **2023.04.09** | Official website: https://pygpt.net | Docs: https://pygpt.readthedocs.io


### **Download compiled versions for Windows 10, 11 and Linux** here: https://pygpt.net

# PYGPT

## What is PYGPT?

**PYGPT** is a desktop application that allows you to talk to OpenAI\'s
artificial intelligence models such as **GPT4** and **GPT3** using your
own computer and `OpenAI API`. It allows you to talk in chat mode and in
completion mode, as well as generate images using **DALL-E 2**.
Moreover, the application has implemented context memory support,
context storage, history of contexts, which can be restored at any time
and e.g. continue the conversation from point in history, and also has a
convenient and intuitive system of presets that allows you to quickly
and pleasantly create and manage your prompts.

![app1](https://user-images.githubusercontent.com/61396542/230803425-5035ccd8-50d9-4fef-9774-8843cf3ce5b0.jpg)

You can download compiled application for Windows and Linux on: https://pygpt.net/#download

## Features

- desktop application for `Windows` and `Linux`, written in Python
- works similar to `ChatGPT`, but locally (on desktop)
- 3 modes of operation: chatbot, text completion and image generation
- supports multiple models: `GPT4` and `GPT3`
- handles and stores full context of the conversation (short-term
  memory)
- stores the history of contexts with the ability to return to
  previous context (long-term memory)
- allows you to easily manage prompts with handly editable presets
- intuitive operation and interface
- allows you to use all the powerful features of `GPT4` and `GPT3`
- no knowledge of using AI models required
- enables easy and convenient generation of images using `DALL-E 2`
- has the ability to support future OpenAI models
- fully configurable
- built-in tokens usage calculation
- it\'s open source, source code is available on `GitHub`
- **uses the user\'s API key**

The application is free, open source and runs on PC with `Windows 10`,
`Windows 11` and `Linux`. The full **Python** source code is available
on `GitHub`.

**PYGPT uses the user\'s API key - to use the application, you must have
a registered OpenAI account and your own API key.**


# Requirements

## Supported systems

PYGPT requires a PC with Windows 10, 11 or Linux. It does not require
installation - to run it, just download the archive with the appropriate
version from the download page and then extract it and run the
application included in it.

## Python version

The second way to run is to download the source code from GitHub and run
the application using the Python interpreter (at least version 3.9).

## Other requirements

To operate, you need an Internet connection (for API connection),
registered OpenAI account and an active API key, which must be entered
in the program.


# Quick Start

## Setting-up OpenAI API KEY

During the first run, you must configure your API key in the
application.

To do this, enter the menu:

``` ini
Config -> Settings...
```

and then paste the API key into the `OpenAI API KEY` field.

![api](https://user-images.githubusercontent.com/61396542/230803433-4ff0dac3-634e-4133-ab51-79b69c43d5a5.jpg)


The API key can be obtained by registering on the OpenAI website:

<https://platform.openai.com>

Your API keys will be available here:

<https://platform.openai.com/account/api-keys>

**Note:** the ability to use models in the application depends on the
API user\'s access to a given model!

# Chatbot and completion (GPT3, GPT4)

## Chatbot

This is the default mode of operation and works very similarly to
**ChatGPT**. The mode allows you to talk to models such as **GPT3**,
**GPT3.5** and **GPT4**. You can switch between the currently used model
at any time.

In the middle window of the application there is a chat window, and
below it there is a field for the text entered by the user (prompt). On
the right side of the application window, you can conveniently define
your own system prompt for the model at any time, or create a preset
with a prompt and save it, for example, for later use. This allows you
to easily and quickly switch between different starting configurations
for the model, and allows you to conveniently experiment with the whole
thing.

Under the chat window and above the input window, the calculated amount
of tokens that will be used to perform a given query is always shown in
real time.

![chat](https://user-images.githubusercontent.com/61396542/230803437-90ad1bd1-dad8-48c3-86d8-c8123943443e.jpg)

## Text Completion

This is a more advanced and capable mode that allows more extensive use
of the **GPT3** model. It works similarly to a chat, but it allows for
more configuration and has more features than a regular chat. In this
mode, you can use the model for more tasks, such as completing text,
simulating conversation as various persons, analyzing text, and many
more.

As in the chat mode, here on the right there are convenient presets,
thanks to which you can freely configure the model and quickly switch
between different configurations.

This mode additionally has fields in which you can enter a name for the
AI and for the user. This allows, for example, to simulate a
conversation as two fictitious actors, if so defined in the start
prompt. Thanks to these options, it is possible, for example, to
simulate a conversation between e.g. Batman and the Joker. ;)

![batman](https://user-images.githubusercontent.com/61396542/230803444-5c960da8-6a53-47cb-9c23-54cefa7f498f.jpg)

In this mode, models from the `davinci` family - included in the
**GPT3** - are available.

# Context and memory

## Short and long-term memory

The application allows you to conduct a conversation in a continuous
mode, allowing you to use a long context. The entire context of the
conversation is stored on the application side and is automatically
attached to all sent to AI messages (prompts). You can also return to
the context of a given conversation at any time - the application allows
you to continue previous conversations and saves the history of the
entire conversation, which can be easily restored and continued from
this point.

## Handling multiple contexts

On the left side of the screen there is a list of saved contexts, you
can add any number of contexts there and conveniently switch between
them and easily return to previous conversations at any time.

![context](https://user-images.githubusercontent.com/61396542/230803455-81d78a08-cad5-45c3-b346-4dd3293abb5d.jpg)

Context support can be turned off in the settings, use the option:

``` ini
Config -> Settings -> Use context 
```

## Clearing history

To clear whole memory (all contexts) use the menu option:

``` ini
File -> Clear history...
```

## Context storage

On the application side, the context is stored in the user\'s directory
in `JSON` files. In addition, all history is also saved to `.txt` files,
which makes it easy to read.

# Presets

## What is preset?

Presets are used to store different configurations and to use these
configurations at any time. The preset includes the selected mode of
operation (chat, completion or image generation), initialization
(system) message, name for AI, username and conversation \"temperature\"
(the higher the value, the more abstract the model behaves, and the
lower the value, the more deterministic it behaves).

You can add as many presets as you want and you can switch between them
at any time. You can also duplicate them and use some presets to create
others based on them.

![preset](https://user-images.githubusercontent.com/61396542/230803464-8aaed56a-6275-43b4-9d8b-558f2c1e697d.jpg)


## Example usage

The application contains several sample presets that allow you to
familiarize yourself with the mechanism of their use.


# Images generation (DALL-E 2)

## DALL-E 2

PYGPT allows you to quickly and easily generate images using `DALL-E 2`.
Generating images resembles a chat conversation - the prompt sent by the
user initiates image generation, then downloading it, saving it on the
computer and displaying it on the screen.

## Multiple variants

You can generate up to **4 different variants** for a given prompt in
one go. To set the required number of variants that you want to be
generated, use the slider located in the corner on the right at the
bottom of the screen (appears in place of the slider with the
conversation temperature when switching to the image generation mode).

![dalle](https://user-images.githubusercontent.com/61396542/230803477-8ca3b13b-080d-4acc-9f19-fc2f1762e8e4.jpg)

## Images storage

The image generated in this way can then be easily saved anywhere on the
disk (just right-click on it), deleted or displayed in full size in the
browser.

**Tip:** with presets, you can save prepared prompts and use them later
when generating subsequent images.

All queries are saved in the history, thanks to which you can return to
a given session at any time and use old queries to, for example,
generate new content.


# Tokens calculation

## Input tokens

Calculation of tokens is implemented in the application. The application
tries to predict the number of tokens that will be used for a given
query and shows this information in real time to the user. Thanks to
this, you can get better control over the tokens used. The application
shows information on how many tokens will be used for the prompt itself,
how much for the system prompt, how much for additional data and how
many tokens will be used in the context (memory of previous entries).

![tokens1](https://user-images.githubusercontent.com/61396542/230803483-df959697-dfe2-4ac5-a61d-8b296062e7ef.jpg)

## Total tokens

After receiving a response from the model, the actual amount of total
tokens used to query the model is shown.

![tokens2](https://user-images.githubusercontent.com/61396542/230803489-ed322d63-e647-4f8f-9ee3-a7200effda24.jpg)

# Configuration

## Settings

The following basic options can be modified from the application level:

``` ini
Config -> Settings...
```

![api](https://user-images.githubusercontent.com/61396542/230803433-4ff0dac3-634e-4133-ab51-79b69c43d5a5.jpg)

- **Temperature** - defines the temperature of the conversation, the
  lower the value, the more deterministic the model behaves, the higher
  the value, the more abstract

- **Top-p** - a parameter similar to temperature, for details please
  refer to the documentation on the OpenAI website

- **Frequency Penalty** - as above

- **Presence Penalty** - as above

- **Use context** - enables or disables the use of context (memory of
  previous conversation components). When this option is disabled,
  context is not saved or used during the conversation

- **Store history** - enables or disables saving conversation history
  and context. History is not written to disk after shutdown

- **Store time in history** - enables or disables adding timestamps to
  files. txt with history, saved in the \"history\" directory in the
  user\'s home directory

- **Context threshold** - specifies the reserve of tokens required to
  execute next prompt. If we are approaching the capacity of the model
  (e.g. if the model allows 4096 tokens), this value will be used when
  approaching the limit to leave place for the next answer.

- **Max output tokens** - defines the maximum number of tokens to be
  generated by the model in response

- **Max total tokens** - defines the maximum number of tokens that the
  application can send to the model, including the entire context of the
  conversation. It should be less than or equal to the model\'s maximum
  capacity. By setting this limit, you can reduce the size of the
  context attached to sent messages.

- **Font size** - allows you to set the font size in the chat window.

- **OpenAI API KEY** - API key that you need to paste into the
  application

## JSON files

The configuration is stored in JSON files, which allows for easy manual
modification outside the application itself. Configuration files are
installed in the user\'s home directory in the subdirectory:

``` ini
{HOME_DIR}/.config/pygpt-net/
```


# Advanced configuration

## Manual configuration

You can manually edit configuration files in the directory:

``` ini
{HOME_DIR}/.config/pygpt-net/
```

- **config.json** - contains the main configuration

- **models.json** - contains models configuration

- **context.json** - contains an index of contexts

- **context** - directory with contexts, `.json` files

- **history** - directory with history, `.txt` files

- **img** - directory with images generated with DALL-E, `.png` files

- **presets** - directory with presets, `.json` files

## Translations / locale

`ini` files with locales are placed in the directory:

``` ini
./data/locale
```

Above directory is automatically read when the application starts -
prepare your own new translation and save it under a name, e.g.:

``` ini
locale.es.ini   
```

will automatically add the language to the language selection menu in
the application.


# Updates

## Updating PYGPT

The application has a built-in update notification. If there is a newer
version with new features, you will be informed in the application
window.

Simply download the new version and use it instead of the current one,
all configuration such as context and history will survive between
versions and will be available in the newly installed version.


# Plugins and audio (coming soon)

## Next realeases

Support for plug-ins and voice recognition and synthesis will be added
in future versions of the application.


# CHANGELOG

## v0.9.0 (2023.04.09)

- initial release



# Credits

**Official website:** <https://pygpt.net>

**Documentation:** <https://pygpt.readthedocs.io>

**GitHub:** <https://github.com/szczyglis-dev/py-gpt>

**Author:** Marcin Szczygliński (Poland, UE)

**Contact:** <info@pygpt.net>

**License:** MIT License

