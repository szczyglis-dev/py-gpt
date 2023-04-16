# PYGPT

Current release: **0.9.5** (build: **2023.04.16**) | Official website: https://pygpt.net | Docs: https://pygpt.readthedocs.io

PyPi: https://pypi.org/project/pygpt-net

### **Compiled versions for Windows 10, 11 and Linux**: https://pygpt.net/#download

## What is PYGPT?

**PYGPT** is a desktop application that allows you to talk to OpenAI\'s
LLM models such as **GPT4** and **GPT3** using your own computer and `OpenAI API`. 
It allows you to talk in chat mode and in completion mode, as well as generate images 
using **DALL-E 2**. PYGPT also adds access to the Internet for GPT via Google Custom 
Search API and Wikipedia API and includes voice synthesis using Microsoft Azure 
Text-to-Speech API. Moreover, the application has implemented context memory support,
context storage, history of contexts, which can be restored at any time
and e.g. continue the conversation from point in history, and also has a
convenient and intuitive system of presets that allows you to quickly
and pleasantly create and manage your prompts. Plugins support is also available.

![app1](https://user-images.githubusercontent.com/61396542/230803425-5035ccd8-50d9-4fef-9774-8843cf3ce5b0.jpg)

You can download compiled version for Windows and Linux at: https://pygpt.net/#download

## Features

- desktop application for `Windows` and `Linux`, written in Python
- works similar to `ChatGPT`, but locally (on desktop)
- 3 modes of operation: chatbot, text completion and image generation
- supports multiple models: `GPT4` and `GPT3`
- handles and stores full context of the conversation (short-term
  memory)
- adds access to the Internet for GPT via Google Custom Search API and Wikipedia API
- includes voice synthesis using Microsoft Azure Text-to-Speech API
- stores the history of contexts with the ability to return to
  previous context (long-term memory)
- allows you to easily manage prompts with handly editable presets
- intuitive operation and interface
- allows you to use all the powerful features of `GPT4` and `GPT3`
- no knowledge of using AI models required
- enables easy and convenient generation of images using `DALL-E 2`
- has the ability to support future OpenAI models
- fully configurable
- plugins support
- built-in token usage calculation
- it\'s open source, source code is available on `GitHub`
- **uses the user\'s API key**

The application is free, open source and runs on PC with `Windows 10`,
`Windows 11` and `Linux`. The full **Python** source code is available
on `GitHub`.

**PYGPT uses the user\'s API key - to use the application, you must have
a registered OpenAI account and your own API key.**


# Requirements

## Supported systems (compiled version)

PYGPT requires a PC with Windows 10, 11 or Linux. Just download the installer or 
archive with the appropriate version from the download page and then extract it 
or install it and run the application.

## Python version (source code)

The second way to run is to download the source code from GitHub and run
the application using the Python interpreter (at least version 3.9). 
You can also install application from PyPi (using "pip install").

### PyPi (pip)

1. Create virtual environment:

```commandline
python -m venv venv
source venv/bin/activate
```

2. Install from PyPi:

``` commandline
pip install pygpt-net
```

3. Once installed run the command to start the application:

``` commandline
pygpt
```

**Troubleshooting**: 

If you have problems with xcb plugin with newer versions of PySide on Linux, e.g. like this:

```commandline
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.
```

...then try downgrading PySide to `PySide6-Essentials==6.4.2`:

```commandline
pip install PySide6-Essentials==6.4.2
```

### Running from GitHub source code

1. Clone git repository or download .zip file:

```commandline
git clone https://github.com/szczyglis-dev/py-gpt.git
cd py-gpt
```

2. Create virtual environment:

```commandline
python -m venv venv
source venv/bin/activate
```

3. Install requirements:

```commandline
pip install -r requirements.txt
```

4. Run the application:

```commandline
cd src/pygpt_net
python app.py
```

**Tip**: you can use `PyInstaller` to create a compiled version of
the application for your system.

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


# Image generation (DALL-E 2)

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

## Image storage

The image generated in this way can then be easily saved anywhere on the
disk (just right-click on it), deleted or displayed in full size in the
browser.

**Tip:** with presets, you can save prepared prompts and use them later
when generating subsequent images.

All queries are saved in the history, thanks to which you can return to
a given session at any time and use old queries to, for example,
generate new content.

## Plugins

The application allows you to use plugins to extend its functionality.

Currently, the following plugins are available:

- **Web Search** - adds access to the Internet using Google Custom Search Engine and Wikipedia API

- **Audio (Azure)** - adds voice synthesis using Microsoft Azure Text-to-Speech API

- **Self Loop** - allows run GPT in a self-loop, which allows you to
  generate a continuous conversation between AI <> AI. In this mode model talks to itself.

- **Real Time** - auto-append current date and time to the prompt. It tells
  the model what time it is in real time.

### Plugin: Web Search

PYGPT allows you to **connect GPT to the internet** and use web search during any query in real time.

**Note: This feature is available in experimental form. It also uses additional tokens during operation to perform the entire procedure described below!**

This is enabled by a plug-in called **Web Search** - enable it in the "Plugins" menu.

The search is done automatically (in background) using the Google Custom Search Engine API and the Wikipedia API. 
To use Google Search, you need an API key - you can get it by registering account on the website:

https://developers.google.com/custom-search/v1/overview

After registering an account, create a new project and then select it from the list of available projects:

https://programmablesearchengine.google.com/controlpanel/all

After selecting the project, you need to enable the "Whole Internet search" option in its settings, and then copy two things into PYGPT:

- Api Key
- CX ID

These data must be configured in the appropriate fields in the "Plugins / Settings..." menu:

![plugin_web](https://user-images.githubusercontent.com/61396542/232334238-7f1a5769-59d4-41da-99cc-f86bda3fc2b1.png)

### How does internet search work in PYGPT?

**Step 1)**

At the beginning, PYGPT retrieves the current prompt from the user.
Then it tries to transform this prompt into a form more accessible to the search engine, i.e. by extract all keywords and edit the prompt so that it is best understood by the search engine. For this purpose, a connection to the "gpt-3.5-turbo" model is initiated in the background with the task of generating a reworded version for the given prompt for use in the search engine. To create a reworded version of the prompt, you can use the entire context of the conversation (all previous entries in the conversation), or only the current prompt - this option can be enabled or disabled in the plugin settings:

**- Use context memory when rebuilding question to search engine** (rebuild_question_context)

Default: `True`

Creating a reworded version of the prompt can be disabled at any time - to use the original prompt, disable the creation of a new query in the settings using the option:

**- Rebuild question to search engine** (rebuild_question)

Default: `True`

When this option is disabled, the reworded version of the query will not be generated and the original query will be used.

The content of the query used by GPT3.5 when generating a more understood version of the prompt can be configured in the fields:

**- Question build prompt** (prompt_question)

Default: `Today is {time}. You are providing single best query for search in Google based on the questionand context of whole conversation and nothing more in the answer.`

This is a system prompt sent to GPT3.5. When parsing this setting, placeholder {time} is replaced with the current time.


**- Question prefix prompt** (prompt_question_prefix)

Default: `Prepare single query for this question and put it in <query>: `

This is the prefix appended to the user's query and then sent to GPT. 
The result of executing the above will be a response with a redacted query content returned between `<query></query>`

**Example:**

If the user is having a conversation about a movie like "Terminator", 
then in the last sentence they will ask "What was the last part?" then the system will try to rewrite it in the form:

`<query>The title of the last part of the Terminator movie</query>`

Then the content between the `<query>` tags is extracted and will be used to build a query to the search engine.


**Step 2)**

In this step, a connection to the search engine API is made and a query is sent to the Google Custom Search API.
The results may contain many pages, therefore the number of pages to be returned by the search engine and to be processed should be defined in advance, the option is used for this:

**- Number of max pages to search per query** (num_pages)

Default: `1`

You can specify here how many pages with results should be crawled in the Google search process.
**Note:** the more pages will be returned, the more data will be used for processing and the execution time of the whole procedure will be longer.

During the search process, queries are made to Google and Wikipedia.
The results are sorted from the most recent to the most terrible, and if the page found first on Google leads to Wikipedia, the Wikipedia API is automatically used to speed up the whole process.

The use of both Google and Wikipedia APIs can be enabled or disabled in the options:

**- Use Google Custom Search** (use_google)

Default: `True`

**- Use Wikipedia** (use_wikipedia)

Default: `True`

You can enable or disable individual searches.

To specify the maximum amount of text to be processed from each page, you can use the following options:

**- Max characters of page content to get (0 = unlimited)** (max_page_content_length)

Default: `1000`

The above determines how many characters from each found page should be processed to generate a summary in the next step. 
If "0" is given, it means no limit. The parameter applies to the already processed version, 
with only the text extracted from the page (this is done using the "BeautifulSoup" module - 
the text contained in the `<p>` tags is processed).

**Step 3)**

After fetching the search results and extracting the text from the found pages, a summary of the found text is performed. For this purpose, all found content is divided into smaller parts, so-called the chunks and so split batches are then used to get a summary which will then be made available to GPT in the main chat window. The "gpt-3.5-turbo" model is used for summarization, and the whole process takes place in the background.

In the process of summarization, all chunks obtained from the downloaded content are sent to GPT one by one.
The system prompt is also used, which can be changed in the settings in the option:

**- Summarize prompt** (prompt_summarize)

Default: `Summarize this text from website into 3 paragraphs trying to find the most important content which will help answering for question: `


The size of each data chunk can be determined using the option:

**- Per-page content chunk size (max characters per chunk)** (chunk_size)

Default: `10000`

This is the maximum number of characters that make up each chunk.

The maximum number of tokens to be generated at the output of the summarization process for each chunk can be changed in the option:

**- Max summary tokens** (summary_max_tokens)

Default: `1500`

This chunked content is then sent to GPT3.5 chunk by chunk along with the system prompt described above. The content summarized in this way is then combined into one collective text string and only then the whole summed up in this way is transferred to the main conversation window in the form of information that will be attached to the system prompt.

**Step 4)**

In the last step, a system prompt is prepared, enriched with the already found and summarized content.
The summarized content is attached to the system prompt by adding a phrase that can be configured in the option:

**- System append prompt** (prompt_system)

Default: `Use this summary text to answer the question or try to answer without it if summary text do not have sufficient info: `

The summary content is then added to the above at the end, and the system prompt prepared in this way is only sent until the next answer in the main conversation is obtained.

The maximum length (in characters) of a system prompt prepared in this way can be changed in the option:

**- System append prompt max length** (prompt_system_length)

Default: `1500`

**Step 5)**

In the main conversation, the system prompt is modified, and GPT receives additional information that it can use when generating a response to the user's query.

**Note:** Please note that this option is currently in experimental version, and please note that it uses additional tokens for the process of generating a modified query and summarizing the content downloaded from the Internet! You should always track the amount of tokens actually used in the statement on the OpenAI website.

### Plugin: Audio (Azure)

PYGPT implements voice synthesis using the **Microsoft Azure Text-To-Speech** API.
This feature require your own Microsoft Azure API Key. 
You can get API KEY for free from here: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech


To enable voice synthesis, enable the "Audio (Azure)" plugin in the "Plugins" menu or enable the "Voice" option in the "Audio" menu (both items in the menu lead to the same thing).

To use speech synthesis, you must first configure the audio plugin by providing the Azure API key and the appropriate Region in the configuration.

This can be done using the "Plugins / Settings..." menu and selecting the "Audio (Azure)" tab:

![plugin_azure](https://user-images.githubusercontent.com/61396542/232334272-88f1871e-04ff-4658-912f-2c977d049272.png)

**Options:**

**- Azure API Key** (azure_api_key)

Here you should enter the API key, which can be obtained by registering for free on the website: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech

**- Azure Region** (azure_region)

Default: `eastus`

The appropriate region for Azure must be provided here.


**- Voice (EN)** (voice_en)

Default: `en-US-AriaNeural`

Here you can specify the name of the voice used for speech synthesis for English


**- Voice (PL)** (voice_pl)

Default: `pl-PL-AgnieszkaNeural`

Here you can specify the name of the voice used for speech synthesis for the Polish language.

If speech synthesis is enabled, a voice will be additionally generated in the background while generating a reply via GPT.


### Plugin: Self Loop

The plugin allows you to enable the "talk with yourself" mode - in this mode GPT starts a conversation with itself.
You can run such a loop with any number of iterations, then during the course of such a loop the model will answer questions asked by itself, having a conversation with itself. This mode works in both Chat and Completion modes, however, for better effect in Completion mode, you can define appropriate names (roles) for each party to the conversation.

When initiating the mode, you should also prepare the system prompt properly, e.g. informing GPT that it is talking to itself. It's worth experimenting for yourself.

The number of iterations for the conversation with yourself can be set in the "Plugins / Settings..." menu in the option:

**- Iterations** (iterations)

Default: `3`


**Additional options:**

**- Clear context output** (clear_output)

Default: `True`

The option clears the previous answer in context (it is then used as input during the next pass)


**- Reverse roles between iterations** (reverse_roles)

Default: `True`

If enabled, it reverses the roles (AI <> user) during each pass, i.e. if in the previous pass the answer was generated for the role "Batman", then in the next pass this answer will be used to generate the same input for the role "Joker".


### Plugin: Real Time

This plugin allows you to automatically attach information about the current date and time to each sent system promt. You can specify whether to include only the date, time, or both.

If the plugin is enabled, each system prompt is enriched in the background with information that transfers the current time to GPT.

**Options:**

**- Append time** (hour)

Default: `True`

If enabled, it appends the current time to the system prompt.


**- Append date** (date)

Default: `True`

If enabled, it appends the current date to the system prompt.


**- Template** (tpl)

Default: `Current time is {time}.`

Template to append to system prompt. Placeholder {time} will be replaced with current date and time in real-time.

# Token usage calculation

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
  
- **OpenAI ORGANIZATION KEY** - Organization API key (optional)

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


## Next releases

Support for voice recognition will be added in future versions of the application.

## DISCLAIMER

This application is not affiliated with OpenAI in any way.
Author is not responsible for any damage caused by the use of this application.
Application is provided as is, without any warranty.
Please also remember about tokens usage - always check the number of tokens used by 
the model on OpenAI website and use the application responsibly.
Enabled plugins (like e.g. Web Search) may use additional tokens,
not listed in main window. Always control your real token usage on OpenAI website.

# CHANGELOG

## v0.9.5 (2023.04.16)

- added web plugin (adds access to the Internet using Google Custom Search Engine and Wikipedia API)
- added voice output plugin (adds voice synthesis using Microsoft Azure)

## v0.9.4 (2023.04.15)

- added plugins support

## v0.9.3 (2023.04.14)

- packed into PyPI package

## v0.9.2 (2023.04.12)

- added theme color settings
- small UI fixes

## v0.9.1 (2023.04.11)

- added organization key configuration (by @kaneda2004, PR#1)
- added config versions patching

## v0.9.0 (2023.04.09)

- initial release

# Credits and links

**Official website:** <https://pygpt.net>

**Documentation:** <https://pygpt.readthedocs.io>

**GitHub:** <https://github.com/szczyglis-dev/py-gpt>

**PyPI:** <https://pypi.org/project/pygpt-net>

**Author:** Marcin Szczygliński (Poland, UE)

**Contact:** <info@pygpt.net>

**License:** MIT License

