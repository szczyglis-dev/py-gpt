Plugins
=======

Overview
-------------------------

**PyGPT** can be enhanced with plugins that add tools, integrations, automation, multimodal features, and additional context directly to conversations.

The following plugins are currently available:

* ``API calls`` - connects models to external services through user-defined API endpoints, request methods, parameters, and payloads.
* ``Audio input`` - adds speech recognition and microphone input using providers such as OpenAI Whisper, local Whisper, Google, Bing, and xAI Grok Voice.
* ``Audio output`` - enables speech synthesis for every received response using providers such as OpenAI, Microsoft Azure, Google, Eleven Labs, and xAI.
* ``Autonomous mode`` - runs an autonomous multi-step conversation loop inside standard chat modes and can cooperate with other enabled plugins to complete tasks.
* ``Canvas (inline)`` - interactive browser/canvas workspace for live HTML/CSS/JavaScript rendering, page interaction, annotations, external websites, Playwright automation, and a local preview server. It works independently of the global ``Tools`` switch.
* ``Bitbucket`` - connects to Bitbucket Cloud for repository, file, issue, pull request, workspace, and account operations.
* ``Chat history (inline)`` - gives models access to saved conversation history and calendar day notes, including reading, searching, creating, and updating stored entries.
* ``Crontab / Task scheduler`` - lets models create and manage scheduled prompts and tasks using cron-based schedules.
* ``Custom commands`` - exposes user-defined system commands and scripts as callable tools with configurable arguments and execution rules.
* ``Experts (inline)`` - exposes enabled Expert presets through the regular ``expert_call`` tool in supported chat modes; Experts run as regular agents on the same Agents v2 runtime used by Agents.
* ``Extra system prompt`` - automatically appends reusable custom instructions or additional context to the active system prompt.
* ``Facebook`` - connects to the Facebook Graph API for working with pages, posts, photos, and related account information.
* ``Files I/O`` - gives models controlled access to local files and directories for reading, writing, copying, moving, downloading, searching, and indexing data.
* ``GitHub`` - connects to GitHub for repository, file, issue, pull request, code search, and account operations.
* ``Google`` - integrates Gmail, Drive, Calendar, Contacts, Keep, Docs, Maps, Colab, and YouTube so models can work with Google services from conversations.
* ``Image generation (inline)`` - adds image generation and editing directly to conversations using a separately configured image model without requiring a mode change.
* ``Jev / System One (inline)`` - integrates TypeSafe AI Jev for fast, typed semantic decisions over structured state, including classification, routing, selection, verification, and scoring.
* ``Mailer`` - provides email access through configured mail services, including sending and reading messages where supported.
* ``MCP`` - connects models to external Model Context Protocol servers and exposes discovered remote tools through stdio, SSE, or Streamable HTTP transports.
* ``Memory (inline)`` - maintains compact database-backed long-term memory plus raw keyed memory, with a global scope outside projects and an isolated memory scope for each project.
* ``Mouse and keyboard`` - lets models control the mouse and keyboard, capture screenshots, and interact with the desktop or supported sandbox environment.
* ``OpenStreetMap`` - adds geocoding, place search, routing, and map utilities based on OpenStreetMap services.
* ``Python interpreter`` - lets models execute Python or IPython code on the host, in the built-in uv-managed CPython runtime, or in Docker, with mutually exclusive standard-Python/IPython tool sets and project-aware working directories.
* ``RAG (inline)`` - adds RAG and LlamaIndex retrieval to standard conversations, allowing models to use indexed files, project indexes, and stored context as additional knowledge.
* ``Real time`` - appends the current date and/or time to system prompts so models can receive up-to-date local time context.
* ``Serial port / USB`` - gives models access to configured serial and USB devices for reading data and sending commands.
* ``Server (SSH/FTP)`` - connects to remote servers through SSH, SFTP, or FTP for command execution, file transfers, and filesystem operations.
* ``Slack`` - connects to Slack workspaces for reading conversations, managing messages, working with users, and transferring files.
* ``System (OS)`` - executes system commands on the host, in the built-in uv-managed runtime, or in Docker, with project-aware runtime paths.
* ``Telegram`` - connects to Telegram bots or user accounts for messaging, chat access, contacts, media, and file transfers.
* ``Tuya (IoT)`` - connects to Tuya Cloud so models can inspect, search, and control supported smart-home and IoT devices.
* ``TwelveLabs`` - adds video understanding and multimodal embeddings using TwelveLabs Pegasus and Marengo models.
* ``Vision (inline)`` - provides a fallback vision model when the selected chat model does not support image input; models with native vision handle images directly.
* ``Voice control (inline)`` - lets spoken commands trigger configured PyGPT actions directly while a conversation is active.
* ``Web search`` - adds real-time web search, webpage retrieval, crawling, and external-content indexing using supported search providers and LlamaIndex loaders.
* ``Wikipedia`` - provides Wikipedia search, article lookup, summaries, geographic discovery, and random-page access.
* ``Wolfram Alpha`` - adds computational knowledge, symbolic and numeric mathematics, unit conversions, matrix operations, and generated plots through Wolfram Alpha.
* ``X/Twitter`` - connects to X for searching and reading posts, publishing content, managing interactions, bookmarks, and media.

**Tip:** Inline plugins work independently of the ``Tools`` switch in the toolbox. Once enabled, they remain active throughout the conversation and can provide their functionality automatically when applicable.

Creating Your Own Plugins
-------------------------

You can create your own plugin for **PyGPT** at any time. The plugin can be written in Python and then registered with the application just before launching it. All plugins included with the app are stored in the ``plugin`` directory - you can use them as coding examples for your own plugins.

PyGPT can be extended with:

* custom plugins
* custom LLMs
* custom vector store providers
* custom data loaders
* custom audio input providers
* custom audio output providers
* custom web search engine providers
* custom agents (LlamaIndex or OpenAI Agents)

See the section ``Extending PyGPT / Adding a custom plugin`` for more details.

API calls
----------

The API calls plugin turns user-defined HTTP endpoints into model-callable tools. Configure GET/POST parameters, JSON templates, headers and placeholders to connect a conversation to your own REST APIs.
**Options**


- **Your custom API calls** *cmds* - You can provide custom API calls on the list here.

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

- **Disable SSL verify** *disable_ssl* - Controls TLS certificate verification for outgoing API requests. Disable verification only for endpoints that require it. *Default:* ``False``

- **Timeout** *timeout* - Maximum time to wait for the remote API connection before the request fails. *Default:* ``5``

- **User agent** *user_agent* - HTTP User-Agent header sent with requests. *Default:* ``Mozilla/5.0``

**Tools**

Each enabled API definition is exposed as a tool using its configured **Name**. For example, the bundled example is exposed as ``search_wiki``.


Audio input
------------

The Audio input plugin captures microphone audio and converts speech to text for chat input and voice commands. It supports OpenAI Whisper, local Whisper, Google, Google Cloud, Google GenAI, Microsoft Bing and xAI Grok Voice, with configurable device, language and recognition behavior.

**Options**

- **Provider** *provider* - Selects the speech-to-text backend used for microphone transcription. *Default:* ``Whisper``

Available providers:

* Whisper (via ``OpenAI API``)
* Whisper (local model) - not available in compiled and Snap versions, only Python/PyPi version
* Google (via ``SpeechRecognition`` library)
* Google Cloud (via ``SpeechRecognition`` library)
* Microsoft Bing (via ``SpeechRecognition`` library)
* Google GenAI
* xAI Grok Voice

**Whisper (API)**

- **Model** *whisper_model* - Selects the OpenAI Whisper model used for API transcription. *Default:* ``whisper-1``

**Whisper (local)**

- **Model** *whisper_local_model* - Selects the local Whisper model size/checkpoint used for on-device transcription. *Default:* ``base``

Available models: https://github.com/openai/whisper

- **Custom model name override** *whisper_local_model_custom* - Optional custom model name or local checkpoint path. When set, it overrides the model selected above. *Default:* ``empty``

- **Keep model in RAM** *whisper_local_keep_in_memory* - Keep the local Whisper model loaded between transcriptions. Disable this to reduce RAM usage at the cost of reloading it from the local cache for each transcription. *Default:* ``True``

**Google**

- **Additional keywords arguments** *google_args* - Additional keyword arguments passed to ``r.recognize_google(audio, **kwargs)``.

**Google Cloud**

- **Additional keywords arguments** *google_cloud_args* - Additional keyword arguments passed to ``recognize_google_cloud(audio, **kwargs)``. The default list contains ``language=en-US``.

**Google GenAI**

- **Model** *google_genai_audio_model* - Gemini model used for audio transcription. *Default:* ``gemini-2.5-flash``

- **System Prompt** *google_genai_audio_prompt* - System instruction used to guide transcription output.

**xAI Grok Voice**

- **Sample rate (Hz)** *xai_voice_audio_sample_rate* - PCM input sample rate. *Default:* ``16000``
- **System Prompt** *xai_voice_system_prompt* - system instruction used to guide transcription output.
- **Region (optional)** *xai_voice_region* - optional regional endpoint such as ``us-east-1``; empty uses the global endpoint.
- **Chunk size (ms)** *xai_voice_chunk_ms* - WebSocket audio chunk size. *Default:* ``200``

**Bing**

- **Additional keywords arguments** *bing_args* - Additional keyword arguments passed to ``r.recognize_bing(audio, **kwargs)``.

**General options**

- **Auto send** *auto_send* - Automatically send recognized speech as input text after recognition. *Default:* ``True``

- **Advanced mode** *advanced* - Enable only if you want to use advanced mode and the settings below. Do not enable this option if you just want to use the simplified mode (default). *Default:* ``False``

**Advanced mode options**

- **Timeout** *timeout* - The duration in seconds that the application waits for voice input from the microphone. *Default:* ``5``

- **Phrase max length** *phrase_length* - Maximum duration for a voice sample (in seconds).  *Default:* ``10``

- **Min energy** *min_energy* - Minimum threshold multiplier above the noise level to begin recording. *Default:* ``1.3``

- **Adjust for ambient noise** *adjust_noise* - Calibrates the microphone energy threshold against current ambient noise before recognition. *Default:* ``True``

- **Continuous listen** *continuous_listen* - Experimental: continuous listening - do not stop listening after a single input. Warning: This feature may lead to unexpected results and requires fine-tuning with the rest of the options! If disabled, listening must be started manually using the ``Microphone`` icon on the right side of the input field. *Default:* ``False``

- **Wait for response** *wait_response* - Delays the next listening cycle until the current model response has finished. *Default:* ``True``

- **Magic word** *magic_word* - Requires the configured wake phrase before captured speech is accepted as input. *Default:* ``False``

- **Reset Magic word** *magic_word_reset* - Reset the magic word status after it is received (the magic word will need to be provided again). *Default:* ``True``

- **Magic words** *magic_words* - List of magic words to initiate listening (Magic word mode must be enabled). *Default:* ``OK, Okay, Hey GPT, OK GPT``

- **Magic word timeout** *magic_word_timeout* - he number of seconds the application waits for magic word. *Default:* ``1``

- **Magic word phrase max length** *magic_word_phrase_length* - The minimum phrase duration for magic word. *Default:* ``2``

- **Prefix words** *prefix_words* - List of words that must initiate each phrase to be processed. For example, you can define words like "OK" or "GPT"—if set, any phrases not starting with those words will be ignored. Insert multiple words or phrases separated by commas. Leave empty to deactivate.  *Default:* ``empty``

- **Stop words** *stop_words* - List of words that will stop the listening process. *Default:* ``stop, exit, quit, end, finish, close, terminate, kill, halt, abort``

Options related to Speech Recognition internals:

- **energy_threshold** *recognition_energy_threshold* - Represents the energy level threshold for sounds. *Default:* ``300``

- **dynamic_energy_threshold** *recognition_dynamic_energy_threshold* - Represents whether the energy level threshold (see recognizer_instance.energy_threshold) for sounds should be automatically adjusted based on the currently ambient noise level while listening. *Default:* ``True``

- **dynamic_energy_adjustment_damping** *recognition_dynamic_energy_adjustment_damping* - Represents approximately the fraction of the current energy threshold that is retained after one second of dynamic threshold adjustment. *Default:* ``0.15``

- **pause_threshold** *recognition_pause_threshold* - Represents the minimum length of silence (in seconds) that will register as the end of a phrase. *Default:* ``0.8``

- **adjust_for_ambient_noise: duration** *recognition_adjust_for_ambient_noise_duration* - The duration parameter is the maximum number of seconds that it will dynamically adjust the threshold for before returning. *Default:* ``1``

Options reference: https://pypi.org/project/SpeechRecognition/1.3.1/

Audio output
-------------------------

The Audio output plugin reads model responses aloud. Choose OpenAI, Azure, Google Cloud, Google GenAI, ElevenLabs or xAI TTS and configure the provider-specific voice, model, language and credentials.

To enable voice synthesis, activate the ``Audio output`` plugin in the ``Plugins`` menu or enable ``Output: Speech synthesis`` in the **Audio** section of the ``Audio / Video`` menu (both options enable the same plugin).

**Options**

- **Provider** *provider* - Selects the text-to-speech backend used to synthesize model responses. *Default:* ``OpenAI TTS``

Available providers:

* OpenAI TTS
* Microsoft Azure TTS
* Google TTS
* Google GenAI TTS
* Eleven Labs TTS
* xAI TTS

**OpenAI Text-To-Speech**

- **Model** *openai_model* - Selects the OpenAI TTS model used for speech synthesis. *Default:* ``tts-1``. Available options:

* tts-1
* tts-1-hd


- **Voice** *openai_voice* - Selects the OpenAI TTS voice. *Default:* ``alloy``. Available voices:

* alloy
* echo
* fable
* onyx
* nova
* shimmer


**Microsoft Azure Text-To-Speech**

- **Azure API Key** *azure_api_key* - Here, you should enter the API key, which can be obtained by registering for free on the following website: https://azure.microsoft.com/en-us/services/cognitive-services/text-to-speech

- **Azure Region** *azure_region* - You must also provide the appropriate region for Azure here. *Default:* ``eastus``

- **Voice (EN)** *azure_voice_en* - Here you can specify the name of the voice used for speech synthesis for English. *Default:* ``en-US-AriaNeural``

- **Voice (non-English)** *azure_voice_pl* - Here you can specify the name of the voice used for speech synthesis for other non-english languages. *Default:* ``pl-PL-AgnieszkaNeural``

**Google Text-To-Speech**

- **Google Cloud Text-to-speech API Key** *google_api_key* - You can obtain your own API key at: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com

- **Voice** *google_voice* - Specify voice. Voices: https://cloud.google.com/text-to-speech/docs/voices

- **Language code** *google_lang* - Language code used for synthesis. *Default:* ``en-US``. Language codes: https://cloud.google.com/speech-to-text/docs/speech-to-text-supported-languages

**Google GenAI Text-To-Speech**

- **Model** *google_genai_tts_model* - Gemini TTS model. *Default:* ``gemini-2.5-flash-preview-tts``

- **Voice** *google_genai_tts_voice* - Gemini TTS voice name; values are case-sensitive. *Default:* ``Kore``

**Eleven Labs Text-To-Speech**

- **Eleven Labs API Key** *eleven_labs_api_key* - You can obtain your own API key at: https://elevenlabs.io/speech-synthesis

- **Voice ID** *eleven_labs_voice* - Voice ID. Voices: https://elevenlabs.io/voice-library

- **Model** *eleven_labs_model* - Specify model. Models: https://elevenlabs.io/docs/speech-synthesis/models

**xAI Text-To-Speech**

- **Voice** *xai_tts_voice* - Grok Voice name (Ara, Rex, Sal, Eve, Leo). *Default:* ``Ara``
- **Sample rate (Hz)** *xai_tts_sample_rate* - PCM output sample rate. *Default:* ``24000``
- **System Prompt** *xai_tts_instructions* - Instruction controlling speaking style. *Default:* ``neutral, clear, verbatim TTS instruction``
- **File container** *xai_tts_file_container* - ``wav`` or ``raw``. *Default:* ``wav``
- **Region (optional)** *xai_tts_region* - optional regional endpoint; empty uses the global endpoint.


If speech synthesis is enabled, a voice will be additionally generated in the background while generating a response via model.

Autonomous mode
-------------------------


.. warning::
   **Please use autonomous mode with caution!** - this mode, when connected with other plugins, may produce unexpected results!

The Autonomous mode plugin activates the iterative Autonomous loop inside supported standard chat modes. Instead of simulating a conversation with itself, the model keeps working on the original user request across successive passes. It can perform another action, inspect tool results, verify earlier work, refine the result, and continue until the configured run-control rules stop it.

The Autonomous mode plugin uses the normal PyGPT tool flow, so it can cooperate with other enabled plugins such as Web search, Files I/O, Python interpreter, image generation, and other integrations. Provider-native function/tool calls are used according to the normal global/model configuration rather than a separate Autonomous setting.

**Options**

You can adjust the number of Autonomous loop iterations in the ``Plugins / Settings...`` menu under the following option:

- **Iterations** *iterations* - *Default:* ``3``

.. warning::
   Setting this option to ``0`` activates an **infinite loop** which can generate a large number of requests and cause very high token consumption, so use this option with caution!

- **Prompts** *prompts* - Editable list of prompts used to instruct how to handle autonomous mode, you can create as many prompts as you want. First active prompt on list will be used to handle autonomous mode.

- **Auto-stop after goal is reached** *auto_stop* - If enabled, the model can terminate the autonomous run early when the original goal is complete. If disabled, the internal completion-control tool is not exposed and the run continues until the iteration limit or an external/manual stop. *Default:* ``True``

- **Always continue** *always_continue* - Keeps the loop open-ended and asks the model to continue with additional useful in-scope work instead of voluntarily finishing. Enabling it automatically disables Auto-stop and ignores the normal iteration limit until the run is stopped externally. Enabling Auto-stop disables Always continue. *Default:* ``False``

- **Dynamic continuous prompt** *dynamic_continue* - After each completed pass, performs a hidden, tool-free call to the same selected model. This second call acts as a judge: it receives the original user input plus the configured tail of recent Autonomous Assistant responses, evaluates what is still missing or worth improving, and returns the instruction used for the next pass. The generated instruction is displayed in the live conversation as a localized ``Judge:`` pseudo-input and is not treated as a new user turn. If the judge call fails or returns an empty instruction, the normal static continuation prompt is used. *Default:* ``True``

- **Responses to judge** *dynamic_continue_messages* - Number of the most recent Autonomous Assistant responses included in each hidden judge request. The original user input is always included. Set ``0`` to include all Assistant responses produced since that input. Multiple tool/text fragments belonging to the same Autonomous provider pass are grouped as one response for this limit. *Default:* ``3``

- **Reverse roles between iterations** *reverse_roles* - Only for Completion mode. If enabled, this option reverses the roles (AI <> user) with each iteration. For example, if in the previous iteration the response was generated for "Batman," the next iteration will use that response to generate an input for "Joker." *Default:* ``True``


.. _plugin-canvas-web-html:

Canvas (inline)
---------------


The **Canvas (inline)** plugin provides a persistent browser/canvas runtime that the model can control directly from a conversation. It is intended for interactive HTML/CSS/JavaScript prototyping, live UI work, browser-based demos, external webpages, visual verification, annotations, and local web-project previews. As an inline plugin, it works independently of the global ``Tools`` switch.

The runtime is scoped to its own viewport. Canvas mouse and keyboard actions do not use the global desktop pointer or keyboard. The model should prefer DOM inspection and stable selectors over raw coordinates whenever possible, and use screenshots when visual verification matters.

Backends and runtime rules
~~~~~~~~~~~~~~~~~~~~~~~~~~

* **QWebEngine is the default backend.** It uses the Chromium-based browser embedded in PyGPT and requires no separate browser automation setup.
* **Playwright is opt-in.** Enable **Use sandbox (Playwright)** in the plugin settings before a tool can request the Playwright backend. If the setting is disabled, requests for ``sandbox=true`` are ignored and QWebEngine is used.
* The Canvas runtime is persistent. Closing the visible Canvas tab does not destroy the background browser session.
* Browser input is scoped to the Canvas viewport and uses a virtual model cursor. Global OS mouse/keyboard control should not be used for work that can be completed inside Canvas.
* Prefer ``canvas_inspect`` and its ``data-pygpt-ref`` selectors before coordinate-based clicking. DOM selectors are generally more stable than visual coordinates.
* Use ``canvas_screenshot`` when appearance matters or after a visual change that should be verified.
* Use ``get_user_painter_image`` when the user refers to a drawing, sketch, markup, or image created or edited in PyGPT's Painter tab. It captures Painter, not the Canvas browser, into shared runtime temporary storage. In Agents it returns only the path. Outside Agents it also returns only the path when Files I/O is enabled, so the model can call ``attach_runtime_file`` explicitly; without Files I/O it falls back to the same automatic runtime-only attachment transport.
* ``canvas_set_html`` can render a complete HTML/CSS/JavaScript document directly. Relative assets are resolved from ``base_url`` or, when omitted, from the current PyGPT data/work directory.
* User annotations are explicit feedback about the current page. Read and apply them before making further UI changes when annotations are present.
* The local preview server listens on loopback only. It is intended for previewing local projects rather than exposing a public web service.

Options
~~~~~~~

**Use sandbox (Playwright)**
   Enables the isolated Playwright browser backend. When disabled, Canvas always uses the built-in QWebEngine browser and does not try to launch Playwright. *Default:* ``False``.

**Playwright engine**
   Selects the Playwright browser engine: ``chromium``, ``firefox``, or ``webkit``. *Default:* ``chromium``.

**Playwright browsers directory**
   Optional ``PLAYWRIGHT_BROWSERS_PATH`` override. Leave empty to use the Playwright default. *Default:* empty.

**Playwright browser args**
   Optional comma-separated launch arguments passed to Chromium/Playwright. This is an advanced option. *Default:* empty.

**Default viewport width**
   Default Canvas viewport width in pixels. *Default:* ``1280``. *Range:* ``320`` to ``7680``.

**Default viewport height**
   Default Canvas viewport height in pixels. *Default:* ``800``. *Range:* ``240`` to ``4320``.

**Auto-open browser in split screen**
   On the first model-driven browser open in an application session, creates/focuses the Canvas tab in the second column and reveals split screen. If the user later collapses split screen, it is not forced open again in that session. *Default:* ``True``.

**Expose user annotations to the model**
   Appends pending Canvas/browser annotations to the runtime system prompt. *Default:* ``True``.

**Maximum annotations**
   Maximum number of annotations retained in the current browser session. *Default:* ``30``. *Range:* ``1`` to ``200``.

**Console log limit**
   Maximum number of browser console entries retained in memory. This is an advanced option. *Default:* ``200``. *Range:* ``10`` to ``2000``.

Canvas tools
~~~~~~~~~~~~

``canvas_open``
   Open or navigate the canvas/web browser runtime. Input is scoped to this canvas viewport only. The plugin setting 'Use sandbox (Playwright)' is the master switch for Playwright; when it is disabled, this command always uses QWebEngine even if sandbox=true is requested. resolution may be '1280x800', '390x844', or omitted.

   Parameters:
   * ``url`` (``str``, optional) - URL, file path or relative path to open.
   * ``resolution`` (``str``, optional) - Optional WIDTHxHEIGHT, e.g. 1280x800 or 390x844.
   * ``sandbox`` (``bool``, optional) - Request the isolated Playwright backend when the plugin setting 'Use sandbox (Playwright)' is enabled. Otherwise this is ignored and QWebEngine is used.

``canvas_change_resolution``
   Change the canvas/web browser viewport. orientation=portrait keeps the shorter edge as width; landscape keeps the longer edge as width.

   Parameters:
   * ``width`` (``int``, required) - Viewport width.
   * ``height`` (``int``, required) - Viewport height.
   * ``orientation`` (``str``, optional) - auto|portrait|landscape.

``canvas_set_html``
   Render arbitrary HTML/CSS/JavaScript in the current canvas/web browser runtime. Relative assets resolve against base_url; when omitted, the current PyGPT data/work directory is used.

   Parameters:
   * ``html`` (``str``, required) - HTML/CSS/JS document.
   * ``base_url`` (``str``, optional) - Optional base URL or local directory.

``canvas_get_html``
   Get the current canvas/web browser URL and serialized HTML document.

   Parameters: none.

``canvas_current``
   Get the current canvas/web browser runtime state: URL, title, backend, viewport, history, virtual cursor, UI surface, server and annotations.

   Parameters: none.

``canvas_close``
   Close the canvas tab in the PyGPT application. This closes the visible canvas UI only; it does not destroy the background canvas/web browser runtime session.

   Parameters: none.

``canvas_prev``
   Navigate the canvas/web browser to the previous history entry.

   Parameters: none.

``canvas_next``
   Navigate the canvas/web browser to the next history entry.

   Parameters: none.

``canvas_reload``
   Reload the current canvas/web browser document.

   Parameters: none.

``canvas_screenshot``
   Capture the current canvas/web browser viewport including the model's virtual cursor. The screenshot is attached to the current tool context so vision-capable models can inspect it.

   Parameters:
   * ``path`` (``str``, optional) - Optional output path.
   * ``full_page`` (``bool``, optional) - Full page when Playwright backend is active.

``get_user_painter_image``
   Capture the current drawing/sketch made by the user in the PyGPT **Painter** tab. The full logical Painter canvas is saved independently of the current Painter zoom level in the shared runtime temporary directory. In Agents the tool returns only the runtime path. Outside Agents it returns only the path when Files I/O is enabled; use ``attach_runtime_file`` with that path for native vision inspection. If Files I/O is unavailable outside Agents, PyGPT automatically uses the same runtime-only attachment transport as ``attach_runtime_file``. The image is never added to the persistent chat attachment list. This is separate from ``canvas_screenshot``, which captures the Canvas/web-browser viewport.

   Parameters: none.

``canvas_inspect``
   Inspect the canvas/web browser DOM. By default returns visible interactive elements with stable data-pygpt-ref selectors, labels, text and bounding boxes. Use before coordinate clicking whenever possible.

   Parameters:
   * ``selector`` (``str``, optional) - Optional CSS selector; omit for interactive elements.
   * ``limit`` (``int``, optional) - Maximum elements.

``canvas_click``
   Click inside the canvas/web browser only. Prefer selector/ref from canvas_inspect; coordinates are viewport pixels.

   Parameters:
   * ``selector`` (``str``, optional) - CSS selector or [data-pygpt-ref=...].
   * ``x`` (``int``, optional) - Viewport X.
   * ``y`` (``int``, optional) - Viewport Y.
   * ``button`` (``str``, optional) - left|middle|right.
   * ``count`` (``int``, optional) - Click count.

``canvas_hover``
   Move the model's virtual cursor/hover inside the canvas/web browser viewport.

   Parameters:
   * ``selector`` (``str``, optional) - Optional CSS selector.
   * ``x`` (``int``, optional) - Viewport X.
   * ``y`` (``int``, optional) - Viewport Y.

``canvas_type``
   Focus an element and type text in the canvas/web browser.

   Parameters:
   * ``selector`` (``str``, optional) - Optional CSS selector; otherwise currently focused element.
   * ``text`` (``str``, required) - Text to type.
   * ``clear`` (``bool``, optional) - Clear existing value first.
   * ``press_enter`` (``bool``, optional) - Press Enter after typing.

``canvas_key``
   Send a keyboard key/chord to the canvas/web browser only, e.g. Enter, Escape, Tab, Control+A.

   Parameters:
   * ``key`` (``str``, required) - Key or Playwright-style chord.

``canvas_scroll``
   Scroll the canvas/web browser. dx/dy are CSS/viewport pixels; positive dy scrolls down.

   Parameters:
   * ``dx`` (``int``, optional) - Horizontal delta.
   * ``dy`` (``int``, optional) - Vertical delta.
   * ``x`` (``int``, optional) - Optional pointer X before scroll.
   * ``y`` (``int``, optional) - Optional pointer Y before scroll.

``canvas_drag``
   Drag inside the canvas/web browser from one viewport point to another.

   Parameters:
   * ``x1`` (``int``, required) - Start X.
   * ``y1`` (``int``, required) - Start Y.
   * ``x2`` (``int``, required) - End X.
   * ``y2`` (``int``, required) - End Y.

``canvas_wait``
   Wait for a selector or a short amount of time inside the canvas/web browser runtime.

   Parameters:
   * ``seconds`` (``float``, optional) - Seconds to wait when selector is omitted.
   * ``selector`` (``str``, optional) - Optional CSS selector to wait for.
   * ``timeout`` (``float``, optional) - Selector timeout in seconds.

``canvas_eval``
   Evaluate JavaScript in the current canvas/web browser page and return a JSON-serializable result. Execution is scoped to that page.

   Parameters:
   * ``javascript`` (``str``, required) - JavaScript expression or function body.

``canvas_select``
   Select an option in a <select> element in the canvas/web browser and dispatch normal input/change events.

   Parameters:
   * ``selector`` (``str``, required) - CSS selector for the select element.
   * ``value`` (``str``, optional) - Option value.
   * ``label`` (``str``, optional) - Visible option label.
   * ``index`` (``int``, optional) - Zero-based option index.

``canvas_check``
   Set a checkbox/radio state in the canvas/web browser.

   Parameters:
   * ``selector`` (``str``, required) - CSS selector.
   * ``checked`` (``bool``, optional) - Desired checked state; defaults to true.

``canvas_upload``
   Upload a host file into an <input type=file> in the canvas/web browser. This is Playwright-only and the path is validated by PyGPT file security before use.

   Parameters:
   * ``selector`` (``str``, required) - CSS selector for input[type=file].
   * ``path`` (``str``, required) - File path.

``canvas_console``
   Get recent JavaScript console messages and page errors from the canvas/web browser.

   Parameters:
   * ``clear`` (``bool``, optional) - Clear stored console after reading.
   * ``limit`` (``int``, optional) - Maximum entries returned.

Annotations
~~~~~~~~~~~

``canvas_annotations``
   Get annotations/selections explicitly left by the user on the current canvas/web browser session.

   Parameters:
   * ``clear`` (``bool``, optional) - Clear annotations after reading.

``canvas_clear_annotations``
   Clear all canvas/web browser annotations.

   Parameters: none.

Local preview server
~~~~~~~~~~~~~~~~~~~~

``web_server_start``
   Start a lightweight loopback-only static HTTP server rooted in a directory. Use it to preview websites/apps from the PyGPT working directory in the canvas/web browser without adding another package.

   Parameters:
   * ``path`` (``str``, optional) - Directory to serve; defaults to current PyGPT data/work directory.
   * ``port`` (``int``, optional) - Loopback port, 0 chooses a free port.
   * ``open`` (``bool``, optional) - Open the server root in the canvas/web browser.
   * ``sandbox`` (``bool``, optional) - Use Playwright if opening the server.

``web_server_current``
   Get current lightweight preview server state and base URL.

   Parameters: none.

``web_server_stop``
   Stop the lightweight preview server.

   Parameters: none.

Security and practical notes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Canvas can execute JavaScript and interact with webpages. Treat untrusted pages and scripts with the same caution as other browser content. Playwright provides a separate browser automation backend but does not make arbitrary web content trustworthy. The preview server is intentionally loopback-only.

For an overview and usage examples, see :doc:`canvas`.

Bitbucket
---------

The Bitbucket plugin exposes Bitbucket Cloud repositories, files, issues, pull requests, workspaces and account information as tools. Authentication can use an App Password or bearer token.


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

- **API base** *api_base* - Define the base URL for the Bitbucket Cloud API. *Default:* ``https://api.bitbucket.org/2.0``

- **HTTP timeout (s)** *http_timeout* - Set the timeout for HTTP requests in seconds. *Default:* ``30``

**Auth options**

- **Auth mode** *auth_mode* - Selects which Bitbucket credential type is used for API requests. *Default:* ``auto``

  Available modes:
  * auto
  * basic
  * bearer

- **Username** *bb_username* - Provide your Bitbucket username (handle, not email).

- **App Password** *bb_app_password* - Specify your Bitbucket App Password (Basic). This option is secret.

- **Bearer token** *bb_access_token* - Enter the OAuth access token (Bearer). This option is secret.

**Cached convenience**

- **(auto) User UUID** *user_uuid* - Cached after using the `bb_me` command.

- **(auto) Username** *username* - Cached after using the `bb_me` command.

**Tools**

*Auth*

- ``bb_auth_set_mode`` - Set the authentication mode: auto|basic|bearer.

- ``bb_set_app_password`` - Set App Password credentials including username and app password.

- ``bb_set_bearer`` - Set the Bearer authentication token.

- ``bb_auth_check`` - Run diagnostics to show authentication results for `/user`.

*User Management*

- ``bb_me`` - Retrieve details for the authenticated user.

- ``bb_user_get`` - Fetch user information by username.

- ``bb_workspaces_list`` - List all accessible workspaces.

*Repositories Management*

- ``bb_repos_list`` - Display a list of repositories.

- ``bb_repo_get`` - Fetch details of a specific repository.

- ``bb_repo_create`` - Create a new repository in a specified workspace.

- ``bb_repo_delete`` - Delete a repository (requires confirmation).

*Contents Management*

- ``bb_contents_get`` - Retrieve file or directory contents from a repository.

- ``bb_file_put`` - Create or update a file in a repository.

- ``bb_file_delete`` - Delete specified files within a repository.

*Issues Management*

- ``bb_issues_list`` - List issues in a repository.

- ``bb_issue_create`` - Create a new issue within a repository.

- ``bb_issue_comment`` - Add a comment to an existing issue.

- ``bb_issue_update`` - Update details of an existing issue.

*Pull Requests Management*

- ``bb_prs_list`` - Display a list of pull requests.

- ``bb_pr_create`` - Create a new pull request.

- ``bb_pr_merge`` - Merge an existing pull request.

*Search Functionality*

- ``bb_search_repos`` - Search repositories using Bitbucket Query Language (BBQL).

Chat history (inline)
----------------------------------

The Chat history (inline) plugin lets the model search and read saved conversations and work with calendar day notes, including creating and updating notes.

Example prompts:

* Show me today's note.
* Save a new note for today.
* Update today's note with...
* Show me yesterday's conversations.
* Show me the contents of conversation ID 123.

Conversation references are integrated with ``@mentions``. Type ``@`` to select a saved conversation, or reference it directly by numeric ID, for example ``@123``. PyGPT retrieves information from that conversation relevant to the current request and adds it as context automatically. Conversation mentions work independently of whether the Chat history plugin is enabled. See :doc:`attachments` for details.

**Options**

- **Model** *model_summarize* - Model used to summarize retrieved conversation content. *Default:* ``gpt-4o-mini``

- **Max summary tokens** *summary_max_tokens* - Maximum output-token budget for generated summaries. *Default:* ``1500``

- **Max contexts to retrieve** *ctx_items_limit* - Max items in context history list to retrieve in one query. 0 = no limit. *Default:* ``30``

- **Per-context items content chunk size** *chunk_size* - Per-context content chunk size (max characters per chunk). *Default:* ``100000 chars``

**Options (advanced)**

- **Prompt: conversation extraction** *prompt_tag_summary* - Prompt used for query-focused extraction from previous conversation chunks, including conversation ``@ID`` references and history retrieval tools.

- **Prompt: conversation reduction** *prompt_tag_reduce* - Prompt used to merge multiple extracted chunks from long previous conversations into one compact result.

**Tools**

- ``get_ctx_list_in_date_range`` - List saved conversations from a specified date range.
- ``get_ctx_content_by_id`` - Retrieve summarized content from a saved conversation by ID.
- ``count_ctx_in_date`` - Count saved conversations in a specified date range.
- ``get_day_note`` - Read the calendar note for a specified date.
- ``add_day_note`` - Create a calendar note for a specified date.
- ``update_day_note`` - Update an existing calendar day note.
- ``remove_day_note`` - Remove a calendar day note.

Crontab / Task scheduler
------------------------

The Crontab / Task scheduler plugin lets the model create, inspect and manage scheduled prompts and tasks using cron expressions.

.. image:: images/v2_crontab.png
   :width: 800

**Options**

- **Your tasks** *crontab* - Add your cron-style tasks here. They will be executed automatically at the times you specify in the cron-based job format. If you are unfamiliar with Cron, consider visiting the Cron Guru page for assistance: https://crontab.guru

Number of active tasks is always displayed in a tray dropdown menu:

- **Create a new context on job run** *new_ctx* - Starts each scheduled job in a new conversation instead of reusing the current context. *Default:* ``True``

- **Show notification on job run** *show_notify* - Shows a desktop/tray notification whenever the scheduled job starts. *Default:* ``True``

Custom commands
------------------------

The Custom commands plugin turns your own shell commands, scripts and applications into model-callable tools. Each command can define its arguments, usage instruction and execution rules; a tutorial command is included as an example:

**Options**

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

**Tools**

Each enabled custom command is exposed as a tool using its configured **name**.


Experts (inline)
-----------------

The Experts (inline) plugin makes enabled Expert presets available in supported chat modes through the regular ``expert_call`` tool. When the current model delegates a task, the selected Expert is executed as a regular agent by the same **Agents v2 runtime** used by **Agents**, and its final response is returned directly as the tool result.

Use **Experts** mode to define, configure, enable, or disable Expert presets. Once an Expert is enabled, you can simply ask for it by name in the conversation, for example: ``Ask the Python programmer expert to review this code.`` The model can then call ``expert_call`` automatically.

See the ``Work modes -> Experts`` section for more details.

**Tools**

- ``expert_call`` - Delegate a self-contained task to an enabled Expert and return its result.

Extra system prompt
-----------------------------

The Extra system prompt plugin appends selected reusable instructions or context to the active system prompt, making the same guidance available on every request.

**Options**

- **Prompts** *prompts* - List of extra prompts - prompts that will be appended to system prompt. All active extra prompts defined on list will be appended to the system prompt in the order they are listed here.

Facebook
--------

The Facebook plugin exposes Facebook Graph API operations for pages, posts and media, including publishing, deleting and uploading content. Authentication uses OAuth2.

* Retrieving basic information about the authenticated user.
* Listing all Facebook pages the user has access to.
* Setting a specified Facebook page as the default.
* Retrieving a list of posts from a Facebook page.
* Creating a new post on a Facebook page.
* Deleting a post from a Facebook page.
* Uploading a photo to a Facebook page.

**Options**

- **Graph API Version** *graph_version* - Specify the API version. *Default:* ``v21.0``

- **API Base** *api_base* - Base address for the Graph API. The version will be appended automatically.

- **Authorize Base** *authorize_base* - Base address for OAuth authorization. The version will be appended automatically.

- **HTTP Timeout (s)** *http_timeout* - Set the timeout for HTTP requests in seconds. *Default:* ``30``

**OAuth2 (PKCE) Settings**

- **App ID (client_id)** *oauth2_client_id* - Provide your Facebook App ID.

- **App Secret (optional)** *oauth2_client_secret* - Required for long-lived token exchange unless using PKCE. *Secret*

- **Confidential Client** *oauth2_confidential* - Use `client_secret` on exchange instead of `code_verifier`.

- **Redirect URI** *oauth2_redirect_uri* - Matches one of the valid OAuth Redirect URIs in your Meta App.

- **Scopes** *oauth2_scopes* - Space-separated authorized permissions.

- **(auto) nonce** *oauth2_nonce* - Generated automatically by ``fb_oauth_begin`` for the OIDC flow. This is an internal cached value and normally should not be edited manually. *Secret*

- **User Access Token** *oauth2_access_token* - Stores user access token. *Secret*

**Cache**

- **User ID** *user_id* - Cached after calling `fb_me` or OAuth exchange.

- **User Name** *user_name* - Cached after calling `fb_me` or OAuth exchange.

- **Default Page ID** *fb_page_id* - Selected via `fb_page_set_default`.

- **Default Page Name** *fb_page_name* - Selected via `fb_page_set_default`.

- **Default Page Access Token** *fb_page_access_token* - Cached with `fb_page_set_default` or on demand. *Secret*

**OAuth UX Options**

- **Auto-start OAuth** *oauth_auto_begin* - Automatically begin PKCE flow when commands need a user token.

- **Open Browser Automatically** *oauth_open_browser* - Open authorization URL in the default web browser.

- **Use Local Server for OAuth** *oauth_local_server* - Start a local HTTP server to capture redirect.

- **OAuth Local Timeout (s)** *oauth_local_timeout* - Duration to wait for a redirect with code. *Default:* ``180``

- **Success HTML** *oauth_success_html* - HTML displayed on successful local callback.

- **Fail HTML** *oauth_fail_html* - HTML displayed on callback error.

- **OAuth Local Port** *oauth_local_port* - Set the local HTTP port; should be above 1024 and allowed in the app. *Default:* ``8732``

- **Allow Fallback Port** *oauth_allow_port_fallback* - Choose a free local port if the preferred port is busy or forbidden.

**Tools**

- ``fb_oauth_begin`` - Start OAuth2 (PKCE) flow and return the authorization URL.

- ``fb_oauth_exchange`` - Trades authorization code for a user access token.

- ``fb_token_extend`` - Exchange a short-lived token for a long-lived token; requires app secret.

- ``fb_me`` - Retrieve the authorized user's profile.

- ``fb_pages_list`` - List pages the user manages with details like ID, name, and access token.

- ``fb_page_set_default`` - Cache name and access token for a default page.

- ``fb_page_posts`` - Retrieve the page's feed (posts).

- ``fb_page_post_create`` - Publish a post with optional text, links, and photos.

- ``fb_page_post_delete`` - Remove a specified page post.

- ``fb_page_photo_upload`` - Upload a photo to a page from a local path or URL.

Files I/O
------------------

The Files I/O plugin gives the model file and directory tools for reading, writing, copying, moving, downloading, searching and indexing content on the local filesystem. The ``cwd`` tool reports the active conversation data directory.

The effective filesystem scope is controlled in ``Config -> Settings -> Security -> General``. Read and write restrictions can be configured independently; disabling them allows Files I/O to access paths outside the active data directory, including the host filesystem. **Warning:** broader filesystem access can expose or modify sensitive files, so enable it only when required and only for trusted workflows.

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
* Querying files using LlamaIndex
* Searching for files and directories

If a file being created (with the same name) already exists, a prefix including the date and time is added to the file name.

**Options**

**General**


- **Use data loaders** *use_loaders* - Use data loaders from LlamaIndex for file reading (the ``read_file`` tool). *Default:* ``True``

**Indexing**


- **Model for query in-memory index** *model_tmp_query* - Model used to query the temporary in-memory index through ``query_file``. *Default:* ``gpt-4o-mini``


- **Use project index if in use** *use_project_index* - When enabled and the current conversation belongs to a project, persistent file indexing targets that project's isolated ``Current project`` index instead of the configured global file index. Outside a project, the configured index is used normally. *Default:* ``True``

- **Index to use when indexing files** *idx* - ID of the normal index to use for persistent file indexing when no active project index is selected. *Default:* ``base``

- **Auto index reading files** *auto_index* - If enabled, every time file is read, it will be automatically indexed (persistent index). *Default:* ``False``

- **Only index reading files** *only_index* - If enabled, file will be indexed without return its content on file read (persistent index). *Default:* ``False``

**Tools**

- ``send_file`` - Send a local filesystem file back to the conversation as an attachment.
- ``read_file`` - Read file contents from the filesystem within the configured security scope.
- ``append_file`` - Append text to an existing text-based file.
- ``save_file`` - Create or overwrite text-based files.
- ``delete_file`` - Delete files from the filesystem within the configured security scope.
- ``list_files`` - List files and directories in a path.
- ``list_dir`` - List files and directories in the selected directory.
- ``download_file`` - Download remote files to a local filesystem path within the configured security scope.
- ``rmdir`` - Remove directories.
- ``copy_file`` - Copy files.
- ``copy_dir`` - Recursively copy directories.
- ``move`` - Move or rename files and directories.
- ``is_dir`` - Test whether a path is a directory.
- ``is_file`` - Test whether a path is a file.
- ``file_exists`` - Test whether a file or directory exists.
- ``file_size`` - Read a file size.
- ``file_info`` - Read file metadata and path information.
- ``find`` - Search the filesystem for files and directories within the configured security scope.
- ``cwd`` - Query the active data working directory.
- ``query_file`` - Build a temporary in-memory index for one file and query it with LlamaIndex.
- ``file_index`` - Add files or directories to a persistent LlamaIndex index.

GitHub
------

The GitHub plugin exposes repositories, files, issues, pull requests, searches and account operations through the GitHub API. Authenticate with a Personal Access Token or OAuth Device Flow.

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

- **API base** *api_base* - Configure the base URL for GitHub's API. *Default:* ``https://api.github.com``

- **Web base** *web_base* - Set the GitHub website base URL. *Default:* ``https://github.com``

- **API version header** *api_version* - Specify the API version for requests. *Default:* ``2022-11-28``

- **HTTP timeout (s)** *http_timeout* - Define timeout for API requests in seconds. *Default:* ``30``

**OAuth Device Flow**

- **OAuth Client ID** *oauth_client_id* - Set the Client ID from your GitHub OAuth App. Supports Device Flow. *Secret*

- **Scopes** *oauth_scopes* - List the space-separated OAuth scopes. *Default:* ``repo read:org read:user user:email``

- **Open browser automatically** *oauth_open_browser* - Automatically open the verification URL in the default browser. *Default:* ``True``

- **Auto-start auth when required** *oauth_auto_begin* - Start Device Flow automatically when a command requires a token. *Default:* ``True``

- **(auto) Granted scopes** *oauth_scope_granted* - Scopes returned after successful authorization. This value is maintained automatically.

**Tokens**

- **(auto) OAuth access token** *gh_access_token* - Store OAuth access token for Device/Web. *Secret*

- **PAT token (optional)** *pat_token* - Provide a Personal Access Token (classic or fine-grained) for authentication. *Secret*

- **Auth scheme** *auth_scheme* - Choose the authentication scheme: `Bearer` or `Token` (use `Token` for PAT).

**Cache**

- **(auto) User ID** *user_id* - Cache User ID after `gh_me` or authentication.

- **(auto) Username** *username* - Cache username after `gh_me` or authentication.

**Tools**

*Auth*

- ``gh_device_begin`` - Begin OAuth Device Flow.
- ``gh_device_poll`` - Poll for access token using device code.
- ``gh_set_pat`` - Set Personal Access Token.

*Users*

- ``gh_me`` - Get authenticated user details.
- ``gh_user_get`` - Retrieve user information by username.

*Repositories*

- ``gh_repos_list`` - List all repositories.
- ``gh_repo_get`` - Get details for a specific repository.
- ``gh_repo_create`` - Create a new repository.
- ``gh_repo_delete`` - Delete an existing repository. (*Disabled by default*).

*Contents*

- ``gh_contents_get`` - Get file or directory contents.
- ``gh_file_put`` - Create or update a file via Contents API.
- ``gh_file_delete`` - Delete a file via Contents API.

*Issues*

- ``gh_issues_list`` - List issues in a repository.
- ``gh_issue_create`` - Create a new issue.
- ``gh_issue_comment`` - Comment on an issue.
- ``gh_issue_close`` - Close an existing issue.

*Pull Requests*

- ``gh_pulls_list`` - List all pull requests.
- ``gh_pull_create`` - Create a new pull request.
- ``gh_pull_merge`` - Merge an existing pull request.

*Search*

- ``gh_search_repos`` - Search for repositories.
- ``gh_search_issues`` - Search for issues and pull requests.
- ``gh_search_code`` - Search for code across repositories.

Google (Gmail, Drive, Calendar, Contacts, YT, Keep, Docs, Maps, Colab)
----------------------------------------------------------------------

The Google plugin exposes Gmail, Drive, Calendar, Contacts, Keep, Docs, Maps, Colab and YouTube tools so the model can work with Google data and services from a conversation.


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

- **Google credentials.json (content)** *credentials* - Paste the JSON content of your OAuth client or Service Account. This is mandatory for the plugin to access your Google services. *Secret:* Yes

- **OAuth token store (auto)** *oauth_token* - Automatically stores and updates the refresh token necessary for Google service access. *Secret:* Yes

- **Use local server for OAuth** *oauth_local_server* - Run a local server for the installed app OAuth flow to simplify the authentication process. *Default:* ``True``

- **OAuth local port (0=random)** *oauth_local_port* - Specify the port for `InstalledAppFlow.run_local_server`. A value of `0` lets the system choose a random available port. *Default:* ``0``

- **Scopes** *oauth_scopes* - Define space-separated OAuth scopes for services like Gmail, Calendar, Drive, Contacts, YouTube, Docs, and Keep. Extend scopes to include Keep services if needed.

- **Impersonate user (Workspace DWD)** *impersonate_user* - Optionally provide a subject for service account domain-wide delegation.

- **YouTube API Key (optional)** *youtube_api_key* - If provided, allows fetching public video information without needing OAuth tokens. *Secret:* Yes

- **Allow unofficial YouTube transcript** *allow_unofficial_youtube_transcript* - Enables the use of `youtube-transcript-api` for transcripts when official captions are unavailable. *Default:* ``False``

- **Keep mode** *keep_mode* - Determines the mode for accessing Keep: `official`, `unofficial`, or `auto`. *Default:* ``auto``

- **Allow unofficial Keep** *allow_unofficial_keep* - Use `gkeepapi` as a fallback for Keep services, requiring `keep_username` and `keep_master_token`. *Default:* ``True``

- **Keep username (unofficial)** *keep_username* - Set the email used for `gkeepapi`.

- **Keep master token (unofficial)** *keep_master_token* - Provide the master token for `gkeepapi` usage, ensuring secure handling. *Secret:* Yes

- **Google Maps API Key** *google_maps_api_key* - Necessary for accessing Google Maps features like Geocoding, Directions, and Distance Matrix. *Secret:* Yes

- **Maps API Key (alias)** *maps_api_key* - Alias for `google_maps_api_key` for backward compatibility. *Secret:* Yes

**Tools**

*Gmail*

- ``gmail_list_recent`` - List n newest Gmail messages.
- ``gmail_list_all`` - List all Gmail messages (paginated).
- ``gmail_search`` - Search Gmail.
- ``gmail_get_by_id`` - Get Gmail message by ID.
- ``gmail_send`` - Send Gmail message.

*Calendar*

- ``calendar_events_recent`` - Upcoming events (from now).
- ``calendar_events_today`` - Events for today (UTC day bounds).
- ``calendar_events_tomorrow`` - Events for tomorrow (UTC day bounds).
- ``calendar_events_all`` - All events in range.
- ``calendar_events_by_date`` - Events for date or date range.
- ``calendar_add_event`` - Add calendar event.
- ``calendar_delete_event`` - Delete event by ID.

*Keep*

- ``keep_list_notes`` - List notes (Keep).
- ``keep_add_note`` - Add note (Keep).

*Drive*

- ``drive_list_files`` - List Drive files.
- ``drive_find_by_path`` - Find Drive file by path.
- ``drive_download_file`` - Download Drive file.
- ``drive_upload_file`` - Upload local file to Drive.

*YouTube*

- ``youtube_video_info`` - Get YouTube video info.
- ``youtube_transcript`` - Get YouTube transcript.

*Contacts*

- ``contacts_list`` - List contacts.
- ``contacts_add`` - Add new contact.

*Google Docs*

- ``docs_create`` - Create Google Doc.
- ``docs_get`` - Get Google Doc (structure + plain text).
- ``docs_list`` - List Google Docs.
- ``docs_append_text`` - Append text to Google Doc.
- ``docs_replace_text`` - Replace all text occurrences in Google Doc.
- ``docs_insert_heading`` - Insert heading at end of Google Doc.
- ``docs_export`` - Export Google Doc to file.
- ``docs_copy_from_template`` - Make a copy of template Google Doc.

*Google Maps*

- ``maps_geocode`` - Geocode an address.
- ``maps_reverse_geocode`` - Reverse geocode coordinates.
- ``maps_directions`` - Get directions between origin and destination.
- ``maps_distance_matrix`` - Distance Matrix for origins and destinations.
- ``maps_places_textsearch`` - Places Text Search.
- ``maps_places_nearby`` - Nearby Places.
- ``maps_static_map`` - Generate Static Map image.

*Google Colab*

- ``colab_list_notebooks`` - List Colab notebooks on Drive.
- ``colab_create_notebook`` - Create new Colab notebook.
- ``colab_add_code_cell`` - Add code cell to notebook.
- ``colab_add_markdown_cell`` - Add markdown cell to notebook.
- ``colab_get_link`` - Get Colab edit link.
- ``colab_rename`` - Rename notebook.
- ``colab_duplicate`` - Duplicate notebook.

Image generation (inline)
-------------------------

The Image generation (inline) plugin adds an ``image`` tool to chats so the current model can delegate image creation or editing to the image-generation model configured in the plugin. It works independently of the global ``Tools`` switch.

**Options**

- **Model** *model* - Image-generation model used by the plugin. *Default:* ``gpt-image-2.5-flare``

- **Prompt** *prompt* - Image-generation instructions that can be appended to the current system prompt. They tell the current model when and how to use the ``image`` tool.

- **Append image prompt to system prompt** *append_prompt* - If enabled, the plugin appends the configured image-generation instructions to the system prompt. Disable it if you want the ``image`` tool to remain available without adding the extra image-generation instructions. *Default:* ``True``

**Tools**

- ``image`` - Generate or edit an image using the image-generation model configured in the plugin.

Jev / System One (inline)
-------------------------

The **Jev / System One (inline)** plugin integrates `TypeSafe AI Jev <https://typesafe.ai/>`_, the first public **System One Model**. Jev is not a chat or text-generation model. Instead, it evaluates structured state and returns typed, machine-readable decisions that can be used directly by the current model or by a larger tool workflow.

Jev is useful when the possible output is constrained in advance but the decision itself requires semantic judgment, for example:

- classifying or routing a message into one of several known categories,
- selecting one value from a defined set of candidates,
- deciding whether a condition is likely true or false,
- verifying or judging model/tool output,
- assigning an ordered score, severity, priority, or rubric level,
- evaluating several independent decisions over the same input state in one request.

Jev exposes three System One decision primitives:

- **Choice** - selects one option from a predefined set and returns a typed choice together with probability/confidence information.
- **Score** - evaluates an item against an ordered scale and returns a structured score with distribution/confidence information.
- **Noul** - evaluates a yes/no condition and returns its probability rather than generating prose.

Because the output space is declared before the request, Jev is intended for bounded decisions and automation rather than open-ended writing, conversational responses, or free-form reasoning. The plugin is inline, so once enabled it works independently of the global **Tools** switch.

Configuration
^^^^^^^^^^^^^

Before using the plugin, configure the TypeSafe credentials in:

.. code-block:: ini

   Config -> Settings -> API Keys -> Jev

The available API settings are:

- **Jev API key** - TypeSafe API key used to authenticate requests. The ``TYPESAFE_API_KEY`` environment variable can be used instead.
- **API base** - Base URL for the TypeSafe API. *Default:* ``https://api.typesafe.ai``. The ``TYPESAFE_BASE_URL`` environment variable can override it.

The model used by the plugin is configured separately in:

.. code-block:: ini

   Plugins -> Settings -> Jev / System One

**Options**

- **Model** *model* - Jev model ID used for System One requests. *Default:* ``jev-latest``

How it works
^^^^^^^^^^^^

The plugin exposes one tool, ``jev_evaluate``. The current model supplies a shared ``state`` object plus one or more named ``questions``. PyGPT sends them to TypeSafe's ``/v1/systemone`` endpoint and returns the raw typed JSON result to the model.

Multiple independent questions should be grouped into one request when they evaluate the same state. This lets Jev make several bounded decisions without requiring separate chat-model calls.

**Tool**

- ``jev_evaluate`` - Evaluate structured data with Jev / System One.

  - ``state`` - structured JSON object containing the data to evaluate. Unstructured source text can be placed in fields such as ``text``, ``message``, or ``document``.
  - ``questions`` - object keyed by stable question IDs. Each question defines ``type`` (``choice``, ``score``, or ``noul``), ``instructions``, and the criteria required by that primitive.

For ``choice``, ``criteria`` is an option-to-description object. For ``score``, ``criteria`` is an ordered list of 2-10 levels. For ``noul``, optional ``criteria`` can describe the ``true`` and ``false`` outcomes.

Example request shape:

.. code-block:: json

   {
     "state": {
       "message": "Refund never arrived.",
       "customer_tier": "pro"
     },
     "questions": {
       "intent": {
         "type": "choice",
         "instructions": "Classify the support intent.",
         "criteria": {
           "refund": "Refund issue",
           "other": "Other"
         }
       },
       "needs_attention": {
         "type": "noul",
         "instructions": "Does this request require support attention?"
       }
     }
   }

You normally do not need to construct this JSON manually. Enable the plugin and ask the current model to use Jev when a task benefits from a bounded semantic decision, for example:

.. code-block:: text

   Use Jev to classify this support message as billing, refund, technical, or other, and estimate whether it needs urgent attention.

API reference: https://docs.typesafe.ai/api

Mailer
-------

The Mailer plugin provides email tools for sending messages and accessing configured mailbox operations. Configure the mail server, account credentials and individual mail tools in the plugin settings.

**Options**

- **From (email)** *from_email* - From (email), e.g. me@domain.com


- **SMTP Host** *smtp_host* - SMTP Host, e.g. smtp.domain.com

- **SMTP Port (Inbox)** *smtp_port_inbox* - SMTP port used for incoming mail. *Default:* ``995``

- **SMTP Port (Outbox)** *smtp_port_outbox* - SMTP port used for outgoing mail. *Default:* ``465``

- **SMTP User** *smtp_user* - SMTP User, e.g. user@domain.com

- **SMTP Password** *smtp_password* - SMTP Password.

**Tools**

- ``send_mail`` - Send email through the configured mail account.
- ``receive_emails`` - Retrieve messages from the configured mailbox.
- ``get_email_body`` - Retrieve the body of a selected email message.

MCP
---

The MCP plugin connects PyGPT to Model Context Protocol servers over stdio, Streamable HTTP or SSE, discovers their tools and exposes allowed tools to the model. Discovery results can be cached and filtered per server.

To configure MCP connections, use ``Config -> MCP...`` or ``Plugins -> Settings -> MCP``. For easier setup and management, use **MCP Connectors** from ``Config -> MCP... -> Connectors...`` to browse, import and manage connector definitions. See :doc:`connectors` for more details.

How it works
^^^^^^^^^^^^

- You define one or more MCP servers in the plugin settings.
- For every active server, the plugin discovers its tools and exposes them to the model.
- Each exposed tool name is derived from the server label and tool name in the form ``label__tool``. Names are sanitized to ``[a-zA-Z0-9_-]`` and kept under 64 characters; long names are shortened with a hash when needed.
- If ``allowed_commands`` is set, only tools matching its comma-separated names or wildcard patterns are exposed.
- If ``disabled_commands`` is set, tools matching its comma-separated names or wildcard patterns are hidden.
- Discovery results can be cached (TTL) so you don’t re-fetch the list on every prompt.
- When the model chooses a tool, the plugin opens a session to the appropriate server and calls it with typed arguments mapped from JSON Schema.

Adding a new MCP server
^^^^^^^^^^^^^^^^^^^^^^^

Click **ADD** and configure the server:

* **active** - Enable or disable the server. Imported connectors are disabled until explicitly enabled.
* **label** - Short server name used in exposed tool names (``label__tool``). Unsupported characters are replaced automatically.
* **server_address** - Server command or URL. Examples:

  * stdio: ``stdio: uv run server fastmcp_quickstart stdio`` or ``stdio: python /path/to/your_mcp_server.py --stdio``
  * Streamable HTTP: ``http://localhost:8000/mcp`` or ``https://your-host.tld/mcp``
  * SSE: ``http://localhost:8000/sse``, ``sse://your-host.tld/sse`` or ``sse+https://your-host.tld/sse``

* **transport** - Transport type: ``auto``, ``stdio``, ``http`` or ``sse``. ``auto`` detects the transport from ``server_address``.
* **authorization** - Optional ``Authorization`` header value for HTTP/SSE, for example ``Bearer YOUR_TOKEN``. An explicit value takes precedence over other Authorization sources.
* **env** - JSON object with environment variables passed to a stdio server process. Values may reference existing environment variables.
* **headers** - JSON object with HTTP/SSE request headers. Header values may reference environment variables.
* **env_http_headers** - JSON object mapping HTTP header names to environment variable names, for example ``{"X-API-Key": "MY_API_KEY"}``.
* **bearer_token_env_var** - Environment variable containing a bearer token. When set, its value is sent as ``Authorization: Bearer <token>`` unless an explicit Authorization value overrides it.
* **cwd** - Working directory for a stdio server process.
* **allowed_commands** - Optional comma-separated allow list of MCP tool names or wildcard patterns. When set, only matching tools are exposed.
* **disabled_commands** - Optional comma-separated deny list of MCP tool names or wildcard patterns. Matching tools are hidden.
* **startup_timeout_sec** - Optional timeout, in seconds, for starting and initializing the MCP connection. Leave empty to use the built-in default.
* **tool_timeout_sec** - Optional timeout, in seconds, for individual MCP tool calls. Leave empty to use the built-in default.
* **source** - Informational source/origin of the server definition, used by the connector manager. It does not change MCP execution.
* **extra** - Optional JSON metadata preserved for imported/vendor-specific connector fields. It is not used as executable MCP configuration.

After saving and enabling the server, its discovered tools become available in chats.

Example: quickstart via stdio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- label: ``quickstart``
- server_address: ``stdio: uv run server fastmcp_quickstart stdio``
- allowed_commands: (leave empty)
- disabled_commands: (leave empty)
- active: ``ON``

Discovered tools might look like:

.. code-block:: json

  [
    {
      "cmd": "quickstart__echo",
      "instruction": "Echo a message back (server: quickstart)",
      "params": [{ "name": "message", "type": "str", "description": "[required]" }],
      "enabled": true
    }
  ]

Example: remote docs server (HTTP/SSE)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- label: ``deepwiki``
- server_address: ``https://example.com/mcp`` (or SSE: ``https://example.com/sse``)
- authorization: ``Bearer YOUR_TOKEN`` (if required)
- allowed_commands: ``read_wiki_structure, read_wiki_contents, ask_question``
- active: ``ON``

The model will see tools like:

.. code-block:: json

  [
    {
      "cmd": "deepwiki__read_wiki_structure",
      "instruction": "Get a list of documentation topics for a GitHub repository (server: deepwiki)",
      "params": [
        { "name": "repoName", "type": "str", "description": "GitHub repository: owner/repo (e.g. \"facebook/react\") [required]" }
      ],
      "enabled": true
    },
    {
      "cmd": "deepwiki__read_wiki_contents",
      "instruction": "View documentation about a GitHub repository (server: deepwiki)",
      "params": [
        { "name": "repoName", "type": "str", "description": "GitHub repository: owner/repo (e.g. \"facebook/react\") [required]" }
      ],
      "enabled": true
    },
    {
      "cmd": "deepwiki__ask_question",
      "instruction": "Ask any question about a GitHub repository (server: deepwiki)",
      "params": [
        { "name": "repoName", "type": "str", "description": "GitHub repository: owner/repo (e.g. \"facebook/react\") [required]" },
        { "name": "question", "type": "str", "description": "The question to ask about the repository [required]" }
      ],
      "enabled": true
    }
  ]

Caching (Tools Cache)
^^^^^^^^^^^^^^^^^^^^^
**Options**


- **Cache tools list** *tools_cache_enabled* - cache discovered tools so they do not have to be rediscovered for every prompt. *Default:* ``True``
- **Cache TTL (seconds)** *tools_cache_ttl* - how long the tool list remains valid per server. *Default:* ``300``
- The plugin automatically invalidates the cache if you change server configuration (label, address, authorization, allow/deny lists).
- To force refresh immediately, toggle a server off/on or modify any of its fields and save.

**Tools**

Tools are discovered dynamically from active MCP servers. Their system names use the ``label__tool`` format, for example ``quickstart__echo``.


Transports
^^^^^^^^^^

- stdio: best for local processes started by PyGPT; no network involved.
- Streamable HTTP: recommended for production; uses a duplex HTTP stream.
- SSE: fully supported; useful for servers exposing an SSE endpoint.
- The plugin detects the transport from ``server_address`` automatically.

Security notes
^^^^^^^^^^^^^^

- ``authorization`` is sent as the ``Authorization`` header to HTTP/SSE servers; put the exact value you need (e.g., ``Bearer <token>``).
- Only connect to servers you trust. Tools can perform actions as implemented by the server.
- Keep labels short and non-sensitive (labels are visible in tool names and logs).

Memory (inline)
---------------

The Memory (inline) plugin gives the model persistent memory beyond normal chat history. It provides three related mechanisms:

* **Compact long-term memory** - one global memory outside projects and one isolated memory row for each project. This memory is intended for durable, reusable facts/state and can be updated automatically with a configured model.
* **Keyed memory** - raw database-backed key/value records in ``memory_keys``. Values are stored exactly as supplied and are never summarized or rewritten by the memory-update model. Keys are isolated between global and per-project scopes.
* **Conversation continuation notes** - compact notes in ``memory_ctx`` scoped to exactly one conversation (one ``ctx_meta``). These notes are used to preserve goals, decisions, completed work, constraints, findings and pending work across context-window rollover. They are separate from both global memory and project memory.

Because Memory is an inline plugin, it works independently of the ``Tools`` switch in the toolbox. Once enabled, its active commands can be exposed to the model regardless of the global ``Tools`` switch.

After a completed conversation turn, the plugin can asynchronously update the active global/project compact memory with the configured model. The updater treats memory as a canonical compact state rather than an append-only log: related facts are merged contextually, duplicates are consolidated, newer information can supersede obsolete entries, and routine or transient details are discarded. Outside projects, the update prompt focuses on durable information about the user. Inside a project, it keeps project-oriented durable state.

Conversation continuation notes are different: they belong only to the current conversation and are not automatically shared with other chats. When the experimental ``Advanced context handling`` feature is enabled, PyGPT core can update these notes automatically as older turns are checkpointed. Agents also uses them as the persistent continuation block for the main agent's rolling context. The core Agents context tools remain available in advanced-context mode even when the Memory plugin itself is disabled; enabling Memory exposes the same ``memory_ctx_*`` operations through the plugin's inline command set as well.

**Options**

- **Memory update model** *model_update* - Model used for automatic end-of-context global/project memory updates and, when enabled, for refining manual ``memory_add`` calls. It is not the model that selects ordinary conversation history.

- **Maximum memory characters** *max_chars* - Target maximum size of the global/project compact memory in characters. The model is asked to stay within this limit. *Default:* ``15000``. Storage allows an additional ``300``-character safety margin before hard truncation, so the default hard safety limit is ``15300`` characters. This setting does not control ``memory_ctx`` continuation-note size; that is configured under ``Settings -> Context -> Maximum continuation note characters``.

- **Refine memory before adding** *refine_add* - Applies only to manual ``memory_add`` calls. When enabled, the configured memory update model merges and rewrites the added information into the existing global/project memory instead of blindly appending raw text. Automatic end-of-context memory updates are always refined by the model regardless of this setting. *Default:* ``True``.

- **Auto attach memory to every conversation** *auto_attach* - Automatically appends the active global or project compact memory to the system prompt in a ``<context_memory>...</context_memory>`` block. It does not auto-attach keyed records or ``memory_ctx`` notes. *Default:* ``False``.

- **Auto attach memory only in projects** *auto_attach_project* - Automatically appends the project compact memory to the system prompt when the current conversation belongs to a project. It does not expose global memory as a fallback inside a project. *Default:* ``True``.

- **Search memory key content** *key_search_content* - Controls ``memory_key_search``. Key names are always searched with ``LIKE '%query%'``. When this option is enabled, stored key content is searched with the same ``LIKE`` expression as well. *Default:* ``False`` to avoid scanning stored content unless explicitly requested.

**Tools**

**Compact global/project memory**

- ``memory_get`` - Read the complete compact memory for the current global/project scope. Enabled by default.
- ``memory_add`` - Selectively adds highly important, durable information. When refinement is enabled, the update model merges it contextually with existing memory instead of appending duplicate facts. Disabled by default.
- ``memory_update`` - Replace the complete compact memory content for the current scope. Disabled by default.
- ``memory_clear`` - Clear the current compact memory. The model must first ask the user for explicit confirmation and may call the command only after confirmation. Enabled by default.

**Keyed memory**

- ``memory_key_get`` - Read raw keyed-memory records by one key or a list of keys. Enabled by default.
- ``memory_key_add`` - Create a new keyed record. It never overwrites an existing key and stores ``content`` exactly as provided, without LLM processing. Enabled by default.
- ``memory_key_append`` - Append ``content`` exactly as provided to an existing keyed record; no separator is inserted automatically. Enabled by default.
- ``memory_key_update`` - Replace the raw content of an existing keyed record. Enabled by default.
- ``memory_key_list`` - Return only the key names for the current scope; it does not return content. Enabled by default.
- ``memory_key_search`` - Return matching keyed records. It always searches key names and also searches content only when ``Search memory key content`` is enabled. Enabled by default.
- ``memory_key_remove`` - Remove one key or a list of keys from the current scope. Enabled by default.

The keyed operations never fall back from project memory to global memory. A conversation inside a project sees only that project's keyed records, while a conversation outside projects sees only global keyed records.

**Conversation continuation notes**

- ``memory_ctx_get`` - Read compact continuation notes for the current conversation only. Enabled by default.
- ``memory_ctx_add`` - Append one concise continuation note to the current conversation. Each addition is stored on a new line. Use it for important state that should survive history compaction, not for routine chatter. Enabled by default.
- ``memory_ctx_replace`` - Replace the complete continuation-note state for the current conversation. Use it to consolidate stale or duplicated notes. It does not modify global/project memory. Enabled by default.

``memory_ctx`` stores one row per conversation metadata record and tracks the compacted-history checkpoint/generation used by advanced context handling. Deleting or rewinding conversation history also invalidates the corresponding continuation state where required so stale compacted state is not replayed as newer history.

.. note::

   ``Advanced context handling`` is experimental and is configured in ``Config -> Settings -> Context``. The Memory plugin can access conversation continuation notes, but the core checkpoint/rolling-context mechanism is not dependent on the plugin being enabled.

Mouse and keyboard
-------------------

.. warning::
   **Use this plugin with caution - allowing all options gives the model full control over the mouse and keyboard**

The Mouse and keyboard plugin gives the model desktop interaction tools for pointer movement, clicks, scrolling, keyboard input and screenshots. It can also provide the browser interaction backend used by Computer use.

Plugin capabilities include:

* Get mouse cursor position
* Control mouse cursor position
* Control mouse clicks
* Control mouse scroll
* Control the keyboard (pressing keys, typing text)
* Making screenshots

The ``Tools`` switch must be enabled to use this plugin.

**Options**

**General**

- **Prompt** *prompt* - Prompt used to instruct how to control the mouse and keyboard.

- **Enable: Allow mouse movement** *allow_mouse_move* - Lets the model move the mouse pointer. *Default:* ``True``

- **Enable: Allow mouse click** *allow_mouse_click* - Lets the model press mouse buttons at the current or requested position. *Default:* ``True``

- **Enable: Allow mouse scroll** *allow_mouse_scroll* - Lets the model scroll the active window or page. *Default:* ``True``

- **Enable: Allow keyboard key press** *allow_keyboard* - Lets the model send keyboard input, including text and key combinations. *Default:* ``True``

- **Enable: Allow making screenshots** *allow_screenshot* - Lets the model capture screenshots for visual inspection. *Default:* ``True``

- **Auto-focus on the window** *auto_focus* - Clicks/focuses the target window before keyboard typing. *Default:* ``False``


**Sandbox (Playwright)**

- **Browsers directory** *sandbox_path* - path to the Playwright browser installation; leave empty to use the default.
- **Engine** *sandbox_engine* - Playwright browser engine: ``chromium``, ``firefox``, or ``webkit``. *Default:* ``chromium``
- **Headless mode** *sandbox_headless* - run the Playwright browser without a visible window. *Default:* ``False``
- **Browser args** *sandbox_args* - additional comma-separated browser arguments. *Default:* ``--disable-extensions, --disable-file-system``
- **Home URL** *sandbox_home* - browser home page. *Default:* ``https://duckduckgo.com``
- **Viewport width** *sandbox_viewport_w* - viewport width in pixels. *Default:* ``1440``
- **Viewport height** *sandbox_viewport_h* - viewport height in pixels. *Default:* ``900``

The sandbox uses ``Playwright`` (https://playwright.dev/). The Playwright package and at least one browser engine must be installed in an environment accessible to PyGPT. For example, to install Chromium:

.. code-block:: ini

   pip install playwright
   playwright install chromium

You can install another supported engine instead with ``playwright install firefox`` or ``playwright install webkit``.

Configure the sandbox in ``Plugins -> Settings -> Mouse and keyboard -> Sandbox (Playwright)``:

* set ``Engine`` to the installed browser engine, for example ``chromium``;
* leave ``Browsers directory`` empty to use Playwright's default browser location, or set it when the browsers are installed in a custom directory;
* configure ``Headless mode``, browser arguments, home URL and viewport size as needed.

When using Computer use, enable the ``Sandbox`` switch in the Computer use toolbox to run browser interaction through this configured Playwright sandbox.

**Tools**

- ``mouse_get_pos`` - Read the current mouse pointer position.
- ``mouse_set_pos`` - Set the mouse pointer position.
- ``make_screenshot`` - Capture a screenshot of the desktop.
- ``mouse_click`` - Click mouse buttons.
- ``mouse_move`` - Move the mouse pointer.
- ``mouse_scroll`` - Scroll with the mouse.
- ``keyboard_key`` - Send individual keys and key combinations.
- ``keyboard_type`` - Type text through the keyboard.

OpenStreetMap
-------------

The OpenStreetMap plugin provides geocoding, place search, routing and map/tile utilities through OpenStreetMap-related services:

* Forward and reverse geocoding via Nominatim
* Search with optional near/bbox filters
* Routing via OSRM (driving, walking, cycling)
* Generate openstreetmap.org URL (center/zoom or bbox; optional marker)
* Utility helpers: open an OSM website URL centered on a point; download a single XYZ tile

By default no images are downloaded; commands return URLs. The ``osm_tile`` command saves tiles under ``data/openstreetmap/`` in the user data directory.

**Important notes and usage etiquette**

* Nominatim requires a proper User-Agent and recommends including a contact email. Set both in the plugin options.
* Public endpoints are community/demo services and not intended for heavy production use. If you need higher throughput, host your own services and set custom base URLs in options.
* Always provide attribution to OpenStreetMap contributors where required by the data license.

**Options**

- **HTTP timeout (s)** *http_timeout* - Maximum time to wait for OpenStreetMap service requests.

- **User-Agent** *user_agent* - HTTP User-Agent header sent to OpenStreetMap services.

- **Contact email (Nominatim)** *contact_email* - Contact email sent with Nominatim requests as recommended by the public service policy.

- **Accept-Language** *accept_language* - Preferred response language sent to OpenStreetMap services.

- **Nominatim base** *nominatim_base* - Base URL of the Nominatim geocoding service.

- **OSRM base** *osrm_base* - Base URL of the OSRM routing service.

- **Tile base** *tile_base* - Base URL template used to download OpenStreetMap tiles.

- **Default zoom** *map_zoom* - Default map zoom used when a tool call does not provide one.

- **Default width** *map_width* - Used only to estimate zoom for bbox (no image rendering).

- **Default height** *map_height* - Used only to estimate zoom for bbox (no image rendering).

**Tools**

- ``osm_geocode`` - Forward geocoding of free-text addresses/places using Nominatim. Supports optional country filtering and near/viewbox bounding. Each result includes ``map_url`` (openstreetmap.org link centered on the result with a marker).

  Parameters:
  - ``query`` (str, required)
  - ``limit`` (int, optional)
  - ``countrycodes`` (str, optional, e.g. ``pl,de``)
  - ``viewbox`` (str|list, optional) — ``minlon,minlat,maxlon,maxlat``
  - ``bounded`` (bool, optional)
  - ``addressdetails`` (bool, optional)
  - ``polygon_geojson`` (bool, optional)
  - ``near`` (str, optional) — address or ``lat,lon`` to bias results (creates a viewbox)
  - ``near_lat`` (float, optional), ``near_lon`` (float, optional), ``radius_m`` (int, optional)
  - ``zoom`` (int, optional) — zoom used for ``map_url`` (defaults to option ``Default zoom``)
  - ``layers`` (str, optional) — optional ``layers=`` value for OSM site URLs

- ``osm_reverse`` - Reverse geocoding for a given coordinate. Response includes ``map_url`` (openstreetmap.org link).

  Parameters:
  - ``lat`` (float) and ``lon`` (float) or ``point`` (str ``lat,lon``)
  - ``zoom`` (int, optional) — also used for ``map_url`` zoom
  - ``addressdetails`` (bool, optional)
  - ``layers`` (str, optional) — optional ``layers=`` value for OSM site URLs

- ``osm_search`` - Alias convenience wrapper for ``osm_geocode`` with the same parameters (results also include ``map_url``).

- ``osm_route`` - Plan a route via OSRM. Accepts addresses or coordinates for start/end and optional waypoints. Always returns ``map_url`` pointing to the openstreetmap.org Directions page (the route is drawn there). In addition:
  - mode=url — no OSRM call; returns only ``map_url`` (Directions) and waypoints,
  - mode=summary (default) — returns distance/duration (no geometry) + ``map_url``,
  - mode=full — can include compact geometry (``geometry_polyline6``) and optionally steps.

  If ``save_map`` is true, an additional ``preview_url`` (regular map view centered/bbox) is returned; it does not replace ``map_url``.

  Parameters:
  - ``start`` (str) or ``start_lat``/``start_lon``
  - ``end`` (str) or ``end_lat``/``end_lon``
  - ``waypoints`` (list, optional)
  - ``profile`` (str, optional) — ``driving`` | ``walking`` | ``cycling`` (default ``driving``)
  - ``mode`` (str, optional) — ``url`` | ``summary`` | ``full`` (default ``summary``)
  - ``include_geometry`` (bool, optional) — include compact geometry (polyline6) in ``full`` mode
  - ``include_steps`` (bool, optional) — include step-by-step (``full`` mode only)
  - ``alternatives`` (int, optional) — 0|1; if >0 treated as true for OSRM alternatives
  - ``max_polyline_chars`` (int, optional) — limit geometry string length (default 5000)
  - ``debug_url`` (bool, optional) — include OSRM request URL in the response
  - ``save_map`` (bool, optional) — build an additional ``preview_url`` (OSM map centered/bbox)
  - ``zoom`` (int, optional) — zoom for ``preview_url`` when applicable
  - ``layers`` (str, optional) — optional ``layers=`` for ``preview_url``
  - ``width`` (int, optional), ``height`` (int, optional) — used only to estimate bbox zoom
  - ``markers`` (list, optional) — for ``preview_url`` the first valid point is used as marker

  Deprecated/no-op parameters (kept for backward compatibility): ``out``, ``color``, ``weight``.

- ``osm_staticmap`` - Build an openstreetmap.org URL (center/zoom or bbox; optional marker). Only the first valid marker is used. ``width``/``height`` are used only to estimate zoom when a bbox is provided.

  Parameters:
  - ``center`` (str) or ``lat``/``lon`` (optional), ``zoom`` (int, optional)
  - ``bbox`` (list[4], optional) — ``minlon,minlat,maxlon,maxlat``
  - ``markers`` (list, optional) — candidates for a single marker; the first valid point is used
  - ``marker`` (bool, optional) — if true and no markers provided, place a marker at center
  - ``layers`` (str, optional) — optional ``layers=`` value
  - ``width`` (int), ``height`` (int) — used only to estimate zoom for bbox

- ``osm_bbox_map`` - Shortcut to build an openstreetmap.org URL from a bounding box.

  Parameters:
  - ``bbox`` (list[4], required) — ``minlon,minlat,maxlon,maxlat``
  - optional ``markers``, ``width``, ``height``

- ``osm_show_url`` - Build an openstreetmap.org URL centered at a point with a marker.

  Parameters:
  - ``point`` (str) or ``lat``/``lon``
  - ``zoom`` (int, optional)
  - ``layers`` (str, optional)

- ``osm_route_url`` - Build an openstreetmap.org Directions URL for start/end (the route is drawn on the page).

  Parameters:
  - ``start`` (str) / ``end`` (str) or coordinate pairs
  - ``mode`` (str, optional) — ``car`` | ``bike`` | ``foot``

- ``osm_tile`` - Download a single XYZ tile (z/x/y.png). Useful for diagnostics or custom composition. The file is saved under ``data/openstreetmap/`` by default.

  Parameters:
  - ``z`` (int), ``x`` (int), ``y`` (int), ``out`` (str, optional)

Python interpreter
-------------------------

The Python interpreter plugin gives the model and the Python/OS tool a Python/IPython runtime for code execution, package use and shell commands, with host, built-in and Docker backends.

**Executing Code**

The Python interpreter plugin provides local Python execution for model-generated code and for code started manually from the ``Python/OS`` window. It uses the active conversation's runtime ``data`` workdir, so a project with a custom data workdir is handled automatically. Execution can run directly on the host or through the selected sandbox backend. The ``Sandbox`` selector provides ``Disabled``, ``Built-in sandbox``, and ``Docker``.

The ``Use IPython`` option selects which Python tool set is exposed to the model:

* when enabled (default), only the IPython tools are exposed: ``ipython_exec``, ``ipython_sys_exec`` and ``ipython_kernel_restart``;
* when disabled, only the standard Python tools are exposed: ``python_exec``, ``python_exec_file`` and ``python_sys_exec``.

The two execution tool sets are never exposed together.

**IPython:** IPython is the recommended execution mode and keeps kernel state between calls, which is useful for iterative development and data analysis. It also supports IPython magic/shell syntax such as ``!pip install <package_name>``. Use ``ipython_exec`` for Python code and ``ipython_sys_exec`` for operating-system commands in the same runtime environment.

**Standard Python:** ``python_exec`` executes Python code directly. The model provides only the ``code`` argument; PyGPT handles the temporary script path internally. Use ``python_exec_file`` only when an existing Python file should be executed. ``python_sys_exec`` runs shell/system commands in the same selected host or sandbox runtime as the standard Python interpreter.

**Sandbox:** Select the backend in ``Plugins -> Settings -> Python interpreter -> General -> Sandbox``. Available modes are ``Disabled``, ``Built-in sandbox`` and ``Docker``. ``Built-in sandbox`` is the default mode for the Python interpreter plugin.

Execution and isolation rules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Disabled``
~~~~~~~~~~~~

``Disabled`` uses the host Python/IPython environment and executes shell commands on the host. There is no sandbox boundary. Host-side Security guards are still applied where a plugin operation explicitly passes through them (for example, command whitelist/blacklist checks for dedicated system-command tools and path checks for plugin-managed file arguments), but they do not intercept arbitrary filesystem, subprocess or network access performed by executed Python/IPython code itself. Treat code executed in this mode as normal code running with the OS permissions of the PyGPT process.

``Built-in sandbox``
~~~~~~~~~~~~~~~~~~~~

The built-in backend is a **separate execution environment**, not a filesystem or container security boundary. It is intended to keep model-executed Python and command-line tooling separate from the Python environment used to run PyGPT itself, without requiring Docker.

The built-in runtime is created under the base PyGPT profile workdir. The default layout is:

.. code-block:: text

   %workdir%/
   ├── data/                         # default conversation data workdir
   ├── tmp/                          # PyGPT application/interpreter temporary files
   └── sandbox/
       ├── runtime/                  # uv-managed CPython runtimes (Python 3.12)
       ├── cache/                    # uv package/runtime cache
       ├── python/                   # venv used by the Python interpreter plugin
       ├── os/                       # separate venv used by the System (OS) plugin
       └── state/
           ├── python/
           │   ├── home/             # HOME/USERPROFILE for Python built-in processes
           │   └── tmp/              # TMP/TEMP/TMPDIR for Python built-in processes
           └── os/
               ├── home/             # HOME/USERPROFILE for System built-in processes
               └── tmp/              # TMP/TEMP/TMPDIR for System built-in processes

``%workdir%`` above means the base profile workdir. A project's custom ``data`` workdir may be located elsewhere; it does not move the base ``sandbox`` directory.

For the Python plugin, both standard Python and IPython use ``%workdir%/sandbox/python``. The environment is provisioned by ``uv`` and has its own Python executable, ``pip`` and packages. PyGPT prepends this environment's ``bin``/``Scripts`` directory to ``PATH``, sets ``VIRTUAL_ENV`` to the built-in venv, disables the user site with ``PYTHONNOUSERSITE=1``, removes inherited ``PYTHONHOME``/``PYTHONPATH`` and uses the private ``state/python/home`` and ``state/python/tmp`` directories for HOME and temporary files. This prevents the built-in interpreter from accidentally using PyGPT's own virtual environment, but it is **environment separation only**.

Built-in packages and environment rebuild
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure persistent packages in ``Plugins -> Settings -> Python interpreter -> Built-in sandbox -> Packages to install``. Enter one Python package requirement per line, for example:

.. code-block:: text

   requests
   numpy==2.3.1
   pandas>=2.3

The default Python package list is:

.. code-block:: text

   jupyter
   ipykernel
   numpy
   pandas
   matplotlib
   scipy
   sympy
   scikit-learn
   pillow
   openpyxl
   xlsxwriter
   pypdf
   pdfminer.six
   pdfplumber
   pymupdf
   reportlab
   python-docx
   python-pptx
   requests
   beautifulsoup4
   lxml
   tabulate
   pyyaml

``pip``, ``setuptools``, ``wheel`` and ``pytest`` are installed as base packages and do not need to be added to the list.

Changing the list recreates the environment on the next built-in use. To rebuild immediately, use ``Tools -> Sandbox / Docker -> Re-create built-in venv for Python interpreter``.

.. important::
   Packages installed manually with ``pip`` are removed by a rebuild unless they are also added to ``Packages to install``.

The active conversation's ``data`` workdir is the process CWD. Normally this is ``%workdir%/data``. If the conversation belongs to a project with a custom data workdir, that project directory becomes the CWD automatically. Relative paths are resolved from this directory.

There is deliberately **no host filesystem restriction** in the built-in backend. Absolute paths remain host paths, and Python code, IPython code and shell commands can read or write any host location allowed to the OS account running PyGPT. The built-in process also uses the host network stack and runs with the same user privileges as PyGPT; it does not use a separate mount namespace, user namespace or network namespace. On Windows, child processes are additionally attached to a Job Object with kill-on-close/process-lifetime handling, but this does not restrict filesystem or network access.

Standard ``python_exec`` calls run in separate child processes. IPython uses a persistent kernel in the same built-in environment, so variables/imports remain available between calls until the kernel is restarted. ``python_sys_exec`` and ``ipython_sys_exec`` execute shell commands using the same built-in environment and CWD. On Unix-like systems the shell is ``/bin/sh``; on Windows it is ``cmd.exe``/``COMSPEC``.

The working-directory filesystem read/write restrictions are still bypassed for Built-in execution; this change does not add filesystem isolation. The system-command whitelist/blacklist is handled separately and **does apply** to the dedicated ``python_sys_exec`` and ``ipython_sys_exec`` tools in Built-in mode, using the whitelist/blacklist for the host operating system. This is an application-level command guard only: arbitrary Python/IPython code can still start processes itself (for example with ``subprocess`` or ``os.system``), so Built-in must still be treated as code with host-level filesystem/network access.

``Docker``
~~~~~~~~~~

Docker provides the actual container boundary and is the strongest isolation option supplied by these plugins. The active conversation's ``data`` workdir is mounted read/write at ``/mnt/data`` by the stock configuration and ``/mnt/data`` is used as the runtime CWD. Project-specific data workdirs are mapped automatically.

The container cannot see arbitrary host paths unless they are explicitly exposed through Docker volume mappings or by other Docker configuration. Adding custom entries to ``Docker volumes`` expands the host filesystem visible to the container. The default volume list exposes only the active runtime ``data`` workdir. The application-level ``%workdir%/sandbox`` and ``%workdir%/tmp`` directories are not mounted by the stock configuration.

The stock Docker images run as the unprivileged ``pygpt`` user by default. Passwordless ``sudo`` is available inside the stock container, and the IPython and standard-Python Docker settings have separate ``Run as root`` options. Root inside the container is still subject to the container boundary, but it can fully access any host volumes that have been mounted into that container. No host ports are published by the stock configuration unless entries are added to ``Docker ports``. Normal Docker networking may still allow outbound network access according to the Docker daemon/network configuration.

Docker isolation depends on the Docker daemon, image, privileges, capabilities and volume/port mappings configured by the user. Avoid mounting sensitive host directories or the Docker socket into model-controlled containers.

For the dedicated Python system-command tools (``python_sys_exec`` and ``ipython_sys_exec``), PyGPT checks the system-command whitelist/blacklist **before** sending the command to Docker. The stock Docker runtimes are Linux containers, so these checks use the ``Security -> Linux`` command list even when the PyGPT host is Windows or macOS. This does not inspect processes spawned indirectly by arbitrary Python/IPython code.

Docker installation: https://docs.docker.com/engine/install/

**Connecting Docker in the Snap version**:

To use the Docker sandbox in the Snap version, connect PyGPT to the Docker daemon:

.. code-block:: console

    $ sudo snap connect pygpt:docker-executables docker:docker-executables

.. code-block:: console

    $ sudo snap connect pygpt:docker docker:docker-daemon

**Python/OS window:** PyGPT includes the ``Python/OS`` tool for real-time Python and IPython execution. Click the ``<>`` icon above the input field to open it, use ``Tools -> Python / OS``, or pin it in a split/output tab. Code input/output is mirrored to this window when ``Connect to the Python/OS window`` is enabled. The same ``Use IPython`` setting controls manual execution from this window, so the UI and model-facing tool set use the same interpreter mode.

.. image:: images/v2_interpreter_icon.png
   :width: 600

.. image:: images/v2_python.png
   :width: 600

.. important::
   Host execution requires a working host Python/IPython environment. ``Built-in sandbox`` (the Python plugin default) creates its own uv-managed CPython environment on first use, but it does not restrict host filesystem or network access. ``Docker`` requires Docker and provides the strongest isolation. The system-command whitelist/blacklist applies to the dedicated Python system-command tools in all three execution modes.

   Docker installation: https://docs.docker.com/engine/install/

   Docker Desktop: https://docs.docker.com/desktop/

.. tip::
   Remember to enable the ``Tools`` switch to allow tools from plugins to be executed.

**Options**

**General**

- **Use IPython** *use_ipython* - Select the interpreter mode. When enabled, PyGPT exposes only the IPython tool set. When disabled, it exposes only the standard Python tool set. *Default:* ``True``

- **Sandbox** *sandbox* - Select the execution backend. ``Disabled`` executes in the host environment. ``Built-in sandbox`` uses a dedicated uv-managed CPython/IPython environment and separate processes, but does not restrict host filesystem or network access. ``Docker`` runs in a container and provides the strongest isolation of the available options. Filesystem Security restrictions keep their existing sandbox behavior, while the system-command whitelist/blacklist applies to ``python_sys_exec`` and ``ipython_sys_exec`` in every mode. *Default:* ``Built-in sandbox``

- **Connect to the Python/OS window** *attach_output* - Automatically attach code input/output to the Python/OS window. *Default:* ``True``

- **Max interpreter window entries** *output_max_entries* - Maximum number of input/output blocks kept in the interpreter window. Set to ``0`` for no limit. *Default:* ``10``

- **Always run code in a fresh kernel** *fresh_kernel* - If enabled, each IPython execution uses the same path as the interpreter's **Run in a fresh kernel** action instead of reusing the current kernel state. *Default:* ``False``


**Built-in sandbox**

- **Packages to install** *builtin_packages* - Python package requirements for the built-in environment, one per line. Base packages (``pip``, ``setuptools``, ``wheel`` and ``pytest``) are installed separately. Changes rebuild the environment on the next use. *Default:* ``built-in Python package set``


**IPython**

- **Run as root** *ipython_run_as_root* - Run the IPython Docker sandbox as root. When disabled, the stock image runs as the unprivileged ``pygpt`` user; passwordless ``sudo`` remains available for commands that require root privileges. This option applies when ``Sandbox`` is set to ``Docker``. *Default:* ``False``

- **Dockerfile for IPython kernel** *ipython_dockerfile* - Dockerfile used to build the IPython kernel image. You can customize it and rebuild the image via ``Tools -> Rebuild IPython Docker Image``.

- **Session Key** *ipython_session_key* - Session key used by the IPython kernel connection. It must match the key provided by the container configuration.

- **Docker image name** *ipython_image_name* - Custom Docker image name. *Default:* ``pygpt_ipython_kernel``

- **Docker container name** *ipython_container_name* - Custom Docker container name. *Default:* ``pygpt_ipython_kernel_container``

- **Connection address** *ipython_conn_addr* - *Default:* ``127.0.0.1``

- **Port: shell** *ipython_port_shell* - *Default:* ``5555``

- **Port: iopub** *ipython_port_iopub* - *Default:* ``5556``

- **Port: stdin** *ipython_port_stdin* - *Default:* ``5557``

- **Port: control** *ipython_port_control* - *Default:* ``5558``

- **Port: hb** *ipython_port_hb* - *Default:* ``5559``


**Python (legacy / standard Python)**

- **Run as root** *docker_run_as_root* - Run the standard Python Docker sandbox as root. When disabled, the stock image runs as the unprivileged ``pygpt`` user; passwordless ``sudo`` remains available for commands that require root privileges. This option applies when ``Sandbox`` is set to ``Docker``. *Default:* ``False``

- **Python command template** *python_cmd_tpl* - Python command template used to execute the temporary or selected Python file; use ``{filename}`` as the file-path placeholder. *Default:* ``python3 {filename}``

- **Dockerfile** *dockerfile* - Dockerfile used by the standard Python Docker backend. You can customize it and rebuild the image via ``Tools -> Rebuild Python (Legacy) Docker Image``.

- **Docker image name** *image_name* - Custom Docker image name. *Default:* ``pygpt_python_legacy``

- **Docker container name** *container_name* - Custom Docker container name. *Default:* ``pygpt_python_legacy_container``

- **Docker run command** *docker_entrypoint* - Command used to keep the standard Python container alive. *Default:* ``tail -f /dev/null``

- **Docker volumes** *docker_volumes* - Host-to-container volume mappings. The stock configuration maps the active conversation's runtime ``data`` workdir to ``/mnt/data``. If a project uses a custom data workdir, the Docker mapping is updated at runtime for that project. The application's base workdir and its non-data directories are not remapped.

- **Docker ports** *docker_ports* - Optional host-to-container port mappings. The default list is empty.


**Tools**

- ``ipython_exec`` - Execute Python code in the current IPython kernel. The tool accepts one required ``code`` parameter.
- ``ipython_sys_exec`` - Execute a shell/system command in the active IPython environment. The command is checked against the configured system-command whitelist/blacklist before execution in every backend. With ``Sandbox = Built-in sandbox`` it runs on the host OS using the built-in venv environment and the active data workdir as CWD; this mode does not restrict host filesystem access. With ``Sandbox = Docker`` the command runs inside the Docker runtime and uses the Linux command policy; with ``Sandbox = Disabled`` it runs in the host environment.
- ``ipython_kernel_restart`` - Restart the IPython kernel. Normally automatic recovery handles a kernel failure; this tool is intended for manual recovery when needed.
- ``python_exec`` - Execute Python code directly. The public tool accepts only the required ``code`` parameter; PyGPT manages the temporary script path internally.
- ``python_exec_file`` - Execute an existing Python file. The tool accepts the required ``path`` parameter.
- ``python_sys_exec`` - Execute a shell/system command in the standard Python runtime. The command is checked against the configured system-command whitelist/blacklist before execution in every backend. With ``Sandbox = Built-in sandbox`` it runs on the host OS using the built-in Python venv environment and the active data workdir as CWD; this mode does not restrict host filesystem access. With ``Sandbox = Docker`` the command runs inside the Docker backend and uses the Linux command policy; with ``Sandbox = Disabled`` it runs in the host environment.

RAG (inline)
------------

The RAG (inline) plugin lets standard chats query configured LlamaIndex indexes and inject retrieved context when needed. It can use the active project index automatically.

**Options**

- **Ask LlamaIndex first** *ask_llama_first* - When enabled, then `LlamaIndex` will be asked first, and response will be used as additional knowledge in prompt. When disabled, then `LlamaIndex` will be asked only when needed. **INFO: Disabled in autonomous mode (via plugin)!** *Default:* ``False``

- **Auto-prepare question before asking LlamaIndex first** *prepare_question* - When enabled, then question will be prepared before asking LlamaIndex first to create best query.

- **Model for question preparation** *model_prepare_question* - Model used to prepare question before asking LlamaIndex. *Default:* ``gpt-4o-mini``

- **Max output tokens for question preparation** *prepare_question_max_tokens* - Max tokens in output when preparing question before asking LlamaIndex. *Default:* ``500``

- **Prompt for question preparation** *syntax_prepare_question* - System prompt for question preparation.

- **Max characters in question** *max_question_chars* - Maximum query length for LlamaIndex; ``0`` disables the limit. *Default:* ``1000``

- **Append metadata to context** *append_meta* - Includes retrieved document metadata with the RAG context passed to the model. *Default:* ``False``

- **Model** *model_query* - Model used for querying ``LlamaIndex``. *Default:* ``gpt-4o-mini``

- **Image model** *model_image* - Vision model used by the Image (vision) data loader when API mode is active. *Default:* ``gpt-4o``

Audio/video transcription is configured separately in the ``Audio input`` plugin and uses the provider selected there.

- **Use project index if in use** *use_project_index* - When enabled and the current conversation belongs to a project, the plugin queries that project's isolated ``Current project`` index instead of the configured global indexes. Outside a project, the configured indexes are used normally. *Default:* ``True``

- **Index name** *idx* - Indexes to use outside an active project, or when project-index usage is disabled. If you want to use multiple indexes at once then separate them by comma. *Default:* ``base``

**Tools**

- ``get_context`` - Retrieve additional context from the configured index.

Real time
----------

The Real time plugin adds the current date, time or both to the system prompt, giving models explicit access to the local current time for each request.

**Options**

- **Append time** *hour* - Adds the current local time to the system prompt for each request. *Default:* ``True``

- **Append date** *date* - Adds the current local date to the system prompt for each request. *Default:* ``True``

- **Template** *tpl* - Template to append to the system prompt. The placeholder ``{time}`` will be replaced with the current date and time in real-time. *Default:* ``Current time is {time}.``

**Tools**

- ``get_time`` - Get the current date and time.

Serial port / USB
------------------

The Serial port / USB plugin lets the model exchange text or raw bytes with configured serial devices, such as Arduino boards and other controllers.

.. note::
   In the Snap version you must connect the interface first: https://snapcraft.io/docs/serial-port-interface

You can send commands to, for example, an Arduino or any other controllers using the serial port for communication.

Below is an example of co-operation with the following code uploaded to ``Arduino Uno`` and connected via USB:

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

- **USB port** *serial_port* - USB port name, e.g. /dev/ttyUSB0, /dev/ttyACM0, COM3, *Default:* ``/dev/ttyUSB0``

- **Connection speed (baudrate, bps)** *serial_bps* - Port connection speed, in bps. *Default:* ``9600``

- **Timeout** *timeout* - Timeout in seconds. *Default:* ``1``

- **Sleep** *sleep* - Sleep in seconds after connection. *Default:* ``2``

**Tools**

- ``serial_send`` - Send text commands to the configured serial port.
- ``serial_send_bytes`` - Send raw bytes to the configured serial port.
- ``serial_read`` - Read data from the configured serial port.

Server (SSH/FTP)
----------------

The Server (SSH/FTP) plugin provides remote command execution and file management over SSH, SFTP and FTP, including directory operations and file transfers.

The Server (SSH/FTP) plugin can be configured with various options to customize connectivity and feature access.

**Options**

- **Servers** *servers* - Define server configurations with credentials and server details. **The model does not access credentials, only names and ports.**

  - ``enabled`` - Enable or disable server configuration
  - ``name`` - Name of the server. **(visible for the model)**
  - ``host`` - Hostname of the server.
  - ``login`` - Login username.
  - ``password`` - Password for the connection (hidden).
  - ``port`` - Connection port (SSH by default). **(visible for the model)**
  - ``desc`` - Description of the server configuration.

- **Network timeout (s)** *net_timeout* - Set the timeout for network operations. *Default:* ``30``

- **Prefer system ssh/scp/sftp** *prefer_system_ssh* - Choose whether to use native ssh/scp/sftp binaries and system keys. *Default:* ``False``

- **ssh binary** *ssh_binary* - Specify the path to the ssh binary. *Default:* ``"ssh"``

- **scp binary** *scp_binary* - Specify the path to the scp binary. *Default:* ``"scp"``

- **sftp binary** *sftp_binary* - Specify the path to the sftp binary. *Default:* ``"sftp"``

- **Extra ssh options** *ssh_options* - Add extra options to be appended to ssh/scp commands. *Default:* ``""``

- **Paramiko: Auto add host keys** *ssh_auto_add_hostkey* - Enable automatic addition of host keys for Paramiko SSHClient. *Default:* ``True``

- **FTP/FTPS**

  * **FTP TLS default** *ftp_use_tls_default* - Choose whether to use FTP over TLS (explicit) by default. *Default:* ``False``

  * **FTP passive mode** *ftp_passive_default* - Set the default FTP mode to passive. *Default:* ``True``

- **Telnet**

  * **Telnet: login prompt** *telnet_login_prompt* - Expected prompt for username during Telnet login. *Default:* ``"login:"``

  * **Telnet: password prompt** *telnet_password_prompt* - Expected prompt for password input during Telnet login. *Default:* ``"Password:"``

  * **Telnet: shell prompt** *telnet_prompt* - Define the prompt used to delimit command output in Telnet. *Default:* ``"$ "``

- **SMTP**

  * **SMTP STARTTLS default** *smtp_use_tls_default* - Enable STARTTLS by default for SMTP connections. *Default:* ``True``

  * **SMTP SSL default** *smtp_use_ssl_default* - Enable SMTP over SSL by default. *Default:* ``False``

  * **Default From address** *smtp_from_default* - Default address used if 'from_addr' not provided in smtp_send command. *Default:* ``""``

**Tools**

- ``srv_exec`` - Execute remote shell command via SSH or Telnet.

- ``srv_ls`` - List remote directory contents using SFTP/FTP or SSH.

- ``srv_get`` - Download files from remote servers to local directories.

- ``srv_put`` - Upload local files to remote servers.

- ``srv_rm`` - Remove remote files or empty directories (non-recursive).

- ``srv_mkdir`` - Create directories on remote servers.

- ``srv_stat`` - Retrieve information about remote files, such as type, size, and last modification time.

- ``smtp_send`` - Send emails via SMTP, using the server configurations provided.

Slack
-----

The Slack plugin exposes workspace conversations, messages, users and file transfer operations through the Slack Web API. Authentication uses OAuth2.

* Retrieving a list of users.
* Listing all conversations.
* Accessing conversation history.
* Retrieving conversation replies.
* Opening a conversation.
* Posting a message in a chat.
* Deleting a chat message.
* Uploading files to Slack.

The Slack plugin can be configured with various options to customize connectivity and feature access.

**Options**

- **API base** *api_base* - Set the base URL for Slack's API. *Default:* ``https://slack.com/api``

- **OAuth base** *oauth_base* - Set the base URL for OAuth authorization. *Default:* ``https://slack.com``

- **HTTP timeout (s)** *http_timeout* - Specify the request timeout in seconds. *Default:* ``30``

**OAuth2 (Slack)**

- **OAuth2 Client ID** *oauth2_client_id* - Provide the Client ID from your Slack App. This field is secret.

- **OAuth2 Client Secret** *oauth2_client_secret* - Provide the Client Secret from your Slack App. This field is secret.

- **Redirect URI** *oauth2_redirect_uri* - Specify the redirect URI that matches one in your Slack App. *Default:* ``http://127.0.0.1:8733/callback``

- **Bot scopes (comma-separated)** *bot_scopes* - Define the scopes for the bot token. *Default:* ``chat:write,users:read,...``

- **User scopes (comma-separated)** *user_scopes* - Specify optional user scopes for user token if required.

**Tokens/cache**

- **(auto/manual) Bot token** *bot_token* - Input or obtain the bot token automatically or manually. This field is secret.

- **(auto) User token (optional)** *user_token* - Get the user token if user scopes are required. This field is secret.

- **(auto) Refresh token** *oauth2_refresh_token* - Store refresh token if rotation is enabled. This field is secret.

- **(auto) Expires at (unix)** *oauth2_expires_at* - Automatically calculate the token expiry time.

- **(auto) Team ID** *team_id* - Cache the Team ID after auth.test or OAuth.

- **(auto) Bot user ID** *bot_user_id* - Cache the Bot user ID post OAuth exchange.

- **(auto) Authed user ID** *authed_user_id* - Cache the authenticated user ID after auth.test/OAuth.

- **Auto-start OAuth when required** *oauth_auto_begin* - Enable automatic initiation of OAuth flow if a command needs a token. *Default:* ``True``

- **Open browser automatically** *oauth_open_browser* - Open the authorize URL in default browser. *Default:* ``True``

- **Use local server for OAuth** *oauth_local_server* - Activate local HTTP server to capture redirect. *Default:* ``True``

- **OAuth local timeout (s)** *oauth_local_timeout* - Set time to wait for redirect with code. *Default:* ``180``

- **Success HTML** *oauth_success_html* - Specify HTML displayed on successful local callback.

- **Fail HTML** *oauth_fail_html* - Specify HTML displayed on failed local callback.

- **OAuth local port (0=auto)** *oauth_local_port* - Set local HTTP port; must be registered in Slack App. *Default:* ``8733``

- **Allow fallback port if busy** *oauth_allow_port_fallback* - Fallback to a free local port if preferred port is busy. *Default:* ``True``

**Tools**

- ``slack_oauth_begin`` - Begin the OAuth2 flow and return the authorize URL.

- ``slack_oauth_exchange`` - Exchange authorization code for tokens.

- ``slack_oauth_refresh`` - Refresh token if rotation is enabled.

- ``slack_auth_test`` - Test authentication and retrieve IDs.

- ``slack_users_list`` - List workspace users (contacts).

- ``slack_conversations_list`` - List channels/DMs visible to the token.

- ``slack_conversations_history`` - Fetch channel/DM history.

- ``slack_conversations_replies`` - Fetch a thread by root ts.

- ``slack_conversations_open`` - Open or resume DM or MPDM.

- ``slack_chat_post_message`` - Post a message to a channel or DM.

- ``slack_chat_delete`` - Delete a message from a channel or DM.

- ``slack_files_upload`` - Upload a file via external flow and share in Slack.

System (OS)
-----------

The System (OS) plugin gives the model a ``sys_exec`` tool for running shell commands in the active data workdir. Commands can run on the host, in the built-in uv-managed environment, or in Docker.

System/OS execution and isolation rules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Disabled`` executes ``sys_exec`` in the host environment. The command runs with the privileges of the PyGPT process. The configured system-command whitelist/blacklist is checked before execution, using the policy for the host operating system.

``Built-in sandbox`` uses a dedicated uv-managed environment under ``%workdir%/sandbox/os``. It shares the same base built-in runtime infrastructure described in the Python interpreter section:

.. code-block:: text

   %workdir%/sandbox/
   ├── runtime/              # uv-managed CPython runtimes
   ├── cache/                # uv cache
   ├── python/               # Python interpreter plugin venv
   ├── os/                   # System (OS) plugin venv
   └── state/os/
       ├── home/             # HOME/USERPROFILE for built-in System commands
       └── tmp/              # TMP/TEMP/TMPDIR for built-in System commands

The System built-in venv is separate from the Python interpreter venv. Its ``bin``/``Scripts`` directory is placed first in ``PATH`` and it has its own packaging tools, so commands and packages installed into ``sandbox/os`` do not modify PyGPT's own Python environment or ``sandbox/python``.

Built-in packages and environment rebuild
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure persistent packages in ``Plugins -> Settings -> System (OS) -> Built-in sandbox -> Packages to install``, one Python package requirement per line. The editable list is empty by default; ``pip``, ``setuptools``, ``wheel`` and ``pytest`` are installed as base packages.

Changing the list recreates the environment on the next built-in use. To rebuild immediately, use ``Tools -> Sandbox / Docker -> Re-create built-in venv for System / OS plugin``.

.. important::
   Packages installed manually are removed by a rebuild unless they are also added to ``Packages to install``.

The active conversation's ``data`` workdir is used as the command CWD. Normally this is ``%workdir%/data``; a project's custom data workdir is used automatically when configured. Relative command paths therefore start from the active data workdir.

Despite its name, the System built-in backend is **not a filesystem sandbox**. Commands are started as separate host processes (``/bin/sh -c`` on Unix-like systems or ``cmd.exe``/``COMSPEC`` on Windows) with a private HOME/TMP and the built-in venv environment, but they run as the same OS user as PyGPT and can access the host filesystem and network according to that user's permissions. On Windows the process is additionally attached to a Job Object for process-lifetime handling; this does not restrict filesystem or network access.

The system-command whitelist/blacklist is **not bypassed** in ``Sandbox = Built-in sandbox``. ``sys_exec`` is checked before the child process starts, using the policy for the host operating system. Filesystem read/write restrictions remain separate and keep their existing sandbox behavior; Built-in still has normal host filesystem/network access with the PyGPT user's permissions.

``Docker`` runs ``sys_exec`` inside the configured container. Before the command enters the container, PyGPT checks it against the Linux system-command whitelist/blacklist because the stock System Docker image is Linux-based. The active conversation's runtime ``data`` directory is mounted read/write at ``/mnt/data`` and used as the command CWD. Project-specific data workdirs are mapped automatically. By default no other PyGPT workdir directories are mounted. Custom ``Docker volumes`` can expose additional host paths, and custom ``Docker ports`` can publish container ports. The stock image runs as the unprivileged ``pygpt`` user with passwordless ``sudo`` unless ``Run as root`` is enabled.

``sys_exec`` input/output is mirrored to the Python/OS window when **Connect to the Python/OS window** is enabled.

**Options**

**General**

- **Sandbox** *sandbox* - Select the execution backend. ``Disabled`` executes commands in the host environment. ``Built-in sandbox`` uses a dedicated uv-managed environment and separate process execution, but does not restrict host filesystem or network access. ``Docker`` requires Docker and provides the strongest isolation of the available options. The system-command whitelist/blacklist applies to ``sys_exec`` in every mode; Host/Built-in use the host OS policy and Docker uses the Linux policy. *Default:* ``Disabled``

- **Auto-append CWD to sys_exec** *auto_cwd* - Automatically append the current runtime working directory to ``sys_exec`` commands. On the host this is the active conversation's data workdir. In the Docker backend the runtime working directory is ``/mnt/data``. *Default:* ``True``

- **Connect to the Python/OS window** *attach_output* - Mirror ``sys_exec`` command input and output to the Python/OS window. *Default:* ``True``


**Built-in sandbox**

- **Packages to install** *builtin_packages* - Additional Python package requirements for the built-in System / OS environment, one per line. Base packages (``pip``, ``setuptools``, ``wheel`` and ``pytest``) are installed separately. Changes rebuild the environment on the next use. *Default:* ``empty``

**Sandbox (Docker backend)**

- **Run as root** *docker_run_as_root* - Run the Docker sandbox as root. When disabled, the stock image runs as the unprivileged ``pygpt`` user; passwordless ``sudo`` can be used for commands that require root privileges. *Default:* ``False``

- **Dockerfile** *dockerfile* - The Dockerfile used to build the sandbox image. The stock image is based on Python 3.12 Alpine, includes commonly used shell/network utilities, uses ``/mnt/data`` as the workdir, and runs as the unprivileged ``pygpt`` user by default. You can customize it and rebuild via ``Tools -> Rebuild Docker sandbox Images``.

- **Docker image name** *image_name* - Name of the Docker image used by the sandbox. *Default:* ``pygpt_system``

- **Docker container name** *container_name* - Name of the Docker container started for the sandbox. *Default:* ``pygpt_system_container``

- **Docker run command** *docker_entrypoint* - Command executed when starting the container (keeps the container alive). *Default:* ``tail -f /dev/null``

- **Docker volumes** *docker_volumes* - Host ↔ container volume mappings. By default, the active runtime ``data`` workdir on the host is mapped read/write to ``/mnt/data`` in the container. A custom project data workdir is therefore mounted automatically when a conversation from that project runs the tool.

  Structure of each item:

  - ``enabled`` (bool) – include this mapping
  - ``docker`` (text) – container path (e.g. ``/mnt/data``)
  - ``host`` (text) – host path (e.g. ``{workdir}``)

  Default: one runtime mapping of the active data workdir → ``/mnt/data``

- **Docker ports** *docker_ports* - Host ↔ container port mappings. You can specify protocol on the container side (e.g. ``8888/tcp``), otherwise TCP is assumed.

  Structure of each item:

  - ``enabled`` (bool) – include this mapping
  - ``docker`` (text) – container port (e.g. ``8888`` or ``8888/tcp``)
  - ``host`` (int) – host port (e.g. ``8888``)

  Default: empty list (no ports exposed)

**WinAPI (Windows)**

- **Enable WinAPI** *winapi_enabled* - Enables Windows Desktop/WinAPI integration (window management, input, screenshots) on Microsoft Windows. *Default:* ``True``

- **Keys: per-char delay (ms)** *win_keys_per_char_delay_ms* - Delay between characters when typing Unicode text with ``win_keys_text``. *Default:* ``2``

- **Keys: hold (ms)** *win_keys_hold_ms* - Hold duration for modifier keys (e.g., CTRL/ALT/SHIFT) in ``win_keys_send``. *Default:* ``50``

- **Keys: gap (ms)** *win_keys_gap_ms* - Gap between consecutive key taps in ``win_keys_send``. *Default:* ``30``

- **Drag: step delay (ms)** *win_drag_step_delay_ms* - Delay between intermediate mouse-move steps during ``win_drag``. *Default:* ``10``

Notes:

- WinAPI features are available only on Microsoft Windows.
- Window and area screenshots are saved as PNG files under the user data directory unless an absolute path is provided.

**Tools**

- ``sys_exec`` - Allows system command execution through the currently selected execution backend. Commands are checked against the configured system-command whitelist/blacklist before execution in Host, Built-in and Docker modes. Commands are non-interactive and should not wait for stdin.

Telegram
---------

The Telegram plugin provides messaging, chat, contact, media and file tools for Telegram bots and user accounts through the Bot API and Telethon.

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

- **Mode** *mode* - Selects Telegram **Bot API** mode or **User/Telethon** mode. *Default:* ``bot``

  Available modes:

  * Bot (via ``Bot API``)
  * User (via ``Telethon``)

- **API base (Bot)** *api_base* - Base URL for the Telegram Bot API. *Default:* ``https://api.telegram.org``

- **HTTP timeout (s)** *http_timeout* - Timeout in seconds for HTTP requests. *Default:* ``30``

**Bot Options**

- **Bot token** *bot_token* - Token obtained from BotFather for authentication.

- **Default parse_mode** *default_parse_mode* - Default parse mode for sending messages. *Default:* ``HTML``

  Available modes:

  * HTML
  * Markdown
  * MarkdownV2

- **Disable link previews (default)** *default_disable_preview* - Disables Telegram link previews for outgoing messages unless overridden per call. *Default:* ``False``

- **Disable notifications (default)** *default_disable_notification* - Sends Telegram messages silently by default unless overridden per call. *Default:* ``False``

- **Protect content (default)** *default_protect_content* - Enables Telegram content protection on outgoing messages by default. *Default:* ``False``

- **(auto) last update id** *last_update_id* - Automatically stored ID after using tg_get_updates.

**User Options (Telethon)**

- **API ID (user mode)** *api_id* - ID required for user authentication. Get from: `https://my.telegram.org`

- **API Hash (user mode)** *api_hash* - Hash required for user authentication. Get from: `https://my.telegram.org`

- **Phone number (+CC...)** *phone_number* - Phone number used to send login code in user mode.

- **(optional) 2FA password** *password_2fa* - Password for two-step verification if enabled.

- **(auto) Session (StringSession)** *user_session* - Session string saved after successful login in user mode.

- **Auto-begin login when needed** *auto_login_begin* - Automatically send login code if authentication is needed and not available. *Default:* ``True``

**Tools**

- ``tg_login_begin`` - Begin Telegram user login (sends code to phone).

- ``tg_login_complete`` - Complete login with code and optional 2FA password.

- ``tg_logout`` - Log out and clear saved session.

- ``tg_mode`` - Return current mode (bot|user).

- ``tg_me`` - Get authorized identity using Bot getMe or User get_me.

- ``tg_send_message`` - Send text message to chat/channel.

- ``tg_send_photo`` - Send photo to chat/channel.

- ``tg_send_document`` - Send document/file to chat/channel.

- ``tg_get_chat`` - Get chat info by id or @username.

- ``tg_get_updates`` - Poll updates in bot mode, automatically store last_update_id.

- ``tg_download_file`` - Download file by file_id in bot mode.

- ``tg_contacts_list`` - List contacts in user mode.

- ``tg_dialogs_list`` - List recent dialogs or chats in user mode.

- ``tg_messages_get`` - Get recent messages from a chat in user mode.

Tuya (IoT)
-----------

The Tuya (IoT) plugin lets the model list, inspect, search and control supported smart-home devices connected through Tuya Cloud.

* Provide your Tuya Cloud credentials to enable communication.
* Access and list all smart devices connected to your Tuya app account.
* Retrieve detailed information about each device, including its status and supported functions.
* Effortlessly search for devices by their names using cached data for quick access.
* Control devices by turning them on or off, toggle states, and set specific device parameters.
* Send custom commands to devices for more advanced control.
* Read sensor values and normalize them for easy interpretation.

**Options**

- **API base** *api_base* - Base URL for interacting with the Tuya API. *Default:* ``https://openapi.tuyaeu.com``

- **HTTP timeout (s)** *http_timeout* - Requests timeout duration in seconds. *Default:* ``30``

- **Language** *lang* - Language setting for API interactions. *Default:* ``en``

**Credentials**

- **Tuya Client ID** *tuya_client_id* - Client ID from the Tuya IoT Platform Cloud project. *Secret*

- **Tuya Client Secret** *tuya_client_secret* - Client secret from the Tuya IoT Platform Cloud project. *Secret*

- **Tuya UID (App Account)** *tuya_uid* - UID of the linked Tuya App account; required for listing devices.

**Automatically managed state**

The following plugin fields are maintained by the Tuya integration and normally should not be edited manually:

- **(auto) Access token** *tuya_access_token* - stored access token. *Secret*
- **(auto) Refresh token** *tuya_refresh_token* - stored refresh token when provided. *Secret*
- **(auto) Expires in (s)** *tuya_token_expires_in* - token lifetime in seconds.
- **(auto) Expire at (epoch s)** *tuya_token_expire_at* - expiration timestamp. *Default:* ``0``
- **(auto) Cached devices** *tuya_cached_devices* - cached device list used by name search. *Default:* ``[]``

**Tools**

*Auth*

- ``tuya_set_keys`` - Input your Tuya Cloud credentials to enable device interactions.

- ``tuya_set_uid`` - Set your Tuya App Account UID for managing device listings.

- ``tuya_token_get`` - Obtain an access token for authenticated API requests.

*Devices*

- ``tuya_devices_list`` - List all devices associated with your account UID, with options to paginate results.

- ``tuya_device_get`` - Retrieve detailed information for a specified device.

- ``tuya_device_status`` - Check the current status and data point values of a device.

- ``tuya_device_functions`` - Discover supported functions and data point codes for a specific device.

- ``tuya_find_device`` - Quickly locate devices using name-based searches from cached data.

*Control*

- ``tuya_device_set`` - Set specific data point values for a device or use multiple settings at once.

- ``tuya_device_send`` - Send a list of raw commands directly to a device for execution.

- ``tuya_device_on`` - Turn a device on with an optional switch code.

- ``tuya_device_off`` - Switch a device off, with automatic code detection if needed.

- ``tuya_device_toggle`` - Toggle a device's on/off state.

*Sensors*

- ``tuya_sensors_read`` - Read normalized sensor values from your connected devices.

TwelveLabs
----------

The TwelveLabs plugin brings native video understanding to PyGPT through the `TwelveLabs <https://twelvelabs.io>`_ API. The model can analyze videos with the ``Pegasus`` model and create multimodal embeddings with the ``Marengo`` model.

Provide your API key in the plugin settings, or set the ``TWELVELABS_API_KEY`` environment variable. You can grab a free API key at https://twelvelabs.io — there is a generous free tier.

**Options**

- **API Key** *api_key* - TwelveLabs API key; if empty, ``TWELVELABS_API_KEY`` is used.
- **Pegasus model** *pegasus_model* - model used for video analysis. *Default:* ``pegasus1.5``
- **Marengo model** *marengo_model* - model used for multimodal embeddings. *Default:* ``marengo3.0``
- **Max tokens** *max_tokens* - default maximum output tokens for Pegasus analysis. *Default:* ``2048``
- **Temperature** *temperature* - default Pegasus sampling temperature. *Default:* ``0.2``
- **Request timeout (s)** *timeout* - TwelveLabs API request timeout. *Default:* ``300``

**Tools**

- ``tl_analyze_video`` - Analyze/understand a video with Pegasus and answer a prompt about it (summary, description, Q&A). Accepts either a public video ``url`` or an already-indexed ``video_id``.

- ``tl_embed_text`` - Create a Marengo multimodal text embedding. The returned vector lives in the same space as Marengo video embeddings, which is useful for text-to-video search.

Vision (inline)
----------------

Models with native image input can analyze images directly in Chat; **Vision (inline) is not needed for them**. Use this plugin only as a fallback when the selected chat model does not support vision. In that case, image attachments, screenshots and camera captures are routed through the separately configured image-capable Chat model.

Camera capture is controlled from the main ``Audio / Video`` menu under **Video**. The fallback model list is filtered by ``Chat`` + image-input capability and can use any supported provider.

**Options**

- **Model** *model* - The image-capable Chat model used temporarily for image analysis. The list is filtered by capability rather than provider. *Default:* ``gpt-4o``.

- **Prompt** *prompt* - The prompt used for inline image analysis. It is appended to or replaces the current system prompt while the temporary image-capable model is used in Chat mode.

- **Replace prompt** *replace_prompt* - Replace the whole system prompt with the image-analysis prompt instead of appending it to the current prompt. *Default:* ``False``

**Tools**

- ``camera_capture`` - Capture an image from the configured camera. Disabled by default.
- ``make_screenshot`` - Capture a screenshot for image analysis. Disabled by default.

Voice control (inline)
----------------------

The Voice control (inline) plugin recognizes spoken PyGPT actions while you are in a conversation. An optional magic prefix can be required before a spoken action is treated as a voice command.

**Options**

- **Magic prefix for voice commands** *cmd_prefix* - optional phrase required before an inline voice command is accepted. *Default:* ``Execute voice command``

See the ``Accessibility`` section for more details.

Web search
-----------

The Web search plugin gives the model live web search, page retrieval and crawling tools using DuckDuckGo, Google Custom Search or Microsoft Bing. Retrieved web content can also be passed into LlamaIndex-based workflows where supported.

**Options**

- **Provider** *provider* - Selects the search engine used by the web search tools. *Default:* ``Google``

Available providers:

- DuckDuckGo
- Google
- Microsoft Bing

**DuckDuckGo**

DuckDuckGo does not require an API key. In source/PyPI installations it requires the ``duckduckgo-search`` or ``ddgs`` package.

- **Region (kl)** *ddg_region* - regional search setting, e.g. ``us-en``, ``pl-pl``, or ``wt-wt``. *Default:* ``us-en``
- **SafeSearch** *ddg_safesearch* - ``on``, ``moderate``, or ``off``. *Default:* ``off``
- **Time limit (df)** *ddg_timelimit* - ``d``, ``w``, ``m``, ``y``, or empty for any time. *Default:* ``empty``
- **Backend** *ddg_backend* - ``auto``, ``html``, or ``lite``. *Default:* ``html``

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

**Options**

- **Google Custom Search API KEY** *google_api_key* - You can obtain your own API key at https://developers.google.com/custom-search/v1/overview

- **Google Custom Search CX ID** *google_api_cx* - You will find your CX ID at https://programmablesearchengine.google.com/controlpanel/all - remember to enable "Search on ALL internet pages" option in project settings.

**Microsoft Bing**

- **Bing Search API KEY** *bing_api_key* - You can obtain your own API key at https://www.microsoft.com/en-us/bing/apis/bing-web-search-api

- **Bing Search API endpoint** *bing_endpoint* - API endpoint for Bing Search API. *Default:* ``https://api.bing.microsoft.com/v7.0/search``

**General options**

- **Number of pages to search** *num_pages* - Maximum number of search results/pages requested per query. *Default:* ``10``

- **Number of max URLs to open at once** *max_open_urls* - Maximum number of URLs that the plugin opens in one batch. *Default:* ``3``

- **Max content characters** *max_page_content_length* - Max characters of page content to get (0 = unlimited). *Default:* ``0``

- **Per-page content chunk size** *chunk_size* - Per-page content chunk size (max characters per chunk). *Default:* ``20000``

- **Disable SSL verify** *disable_ssl* - Controls TLS certificate verification while fetching web pages. Disable verification only when required by the target site. *Default:* ``True``

- **Use raw content (without summarization)** *raw* - Return raw content from web search instead of summarized content. Provides more data but consumes more tokens. *Default:* ``True``

- **Show thumbnail images** *img_thumbnail* - Fetch thumbnail images from opened websites when available. *Default:* ``True``

- **Timeout** *timeout* - Maximum time to wait for the remote API connection before the request fails. *Default:* ``5``

- **User agent** *user_agent* - User agent to use when making requests. *Default:* ``Mozilla/5.0``.

- **Max result length** *max_result_length* - Max length of the summarized or raw result (characters). *Default:* ``50000``

- **Max summary tokens** *summary_max_tokens* - Maximum output-token budget for generated summaries. *Default:* ``1500``


**Advanced**

- **Model used for web page summarize** *summary_model* - Model used for web page summarize. *Default:* ``gpt-4o-mini``

- **Summarize prompt** *prompt_summarize* - Prompt used for web search results summarize, use {query} as a placeholder for search query

- **Summarize prompt (URL open)** *prompt_summarize_url* - Prompt used for specified URL page summarize


**Indexing**


- **Auto-index all used URLs using LlamaIndex** *auto_index* - If enabled, every URL used by the model will be automatically indexed using LlamaIndex (persistent index). *Default:* ``False``

- **Index to use** *idx* - ID of index to use for web page indexing (persistent index). *Default:* ``base``

**Tools**

- ``web_search`` - Search the web with the selected search provider.
- ``web_url_open`` - Open a URL and return summarized page content.
- ``web_url_raw`` - Open a URL and return raw page content.
- ``web_request`` - Send HTTP requests to a URL or API endpoint.
- ``web_extract_links`` - Extract links from a web page.
- ``web_extract_images`` - Extract image URLs from a web page.
- ``web_index`` - Add web or external content to a persistent LlamaIndex index.
- ``web_index_query`` - Build a temporary in-memory index for web content and query it with LlamaIndex.

Wikipedia
----------

The Wikipedia plugin provides article search, summaries, full-page lookup, title suggestions, geographic discovery and random-page tools with configurable language handling.

* Set your preferred language for Wikipedia queries.
* Retrieve and check the current language setting.
* Explore a list of supported languages.
* Search for articles using keywords or get suggestions for queries.
* Obtain summaries and detailed page content.
* Discover articles by geographic location or randomly.
* Open articles directly in your web browser.

**Options**

- **Language** *lang* - Default Wikipedia language. *Default:* ``en``

- **Auto Suggest** *auto_suggest* - Uses Wikipedia title suggestions when an exact page title is not found. *Default:* ``True``

- **Follow Redirects** *redirect* - Follows Wikipedia redirects to the destination article automatically. *Default:* ``True``

- **Rate Limit** *rate_limit* - Enables request throttling to avoid sending Wikipedia API calls too quickly. *Default:* ``True``

- **User-Agent** *user_agent* - Custom User-Agent string for requests. *Default:* ``pygpt-net-wikipedia-plugin/1.0 (+https://pygpt.net)``

- **Summary Sentences** *summary_sentences* - Default number of sentences in summaries. *Default:* ``3``

- **Default Results Limit** *results_default* - Number of results for searches. *Default:* ``10``

- **Content Maximum Characters** *content_max_chars* - Maximum characters for page content. *Default:* ``5000``

- **Max List Items** *max_list_items* - Maximum items from article lists. *Default:* ``50``

- **Full Content by Default** *content_full_default* - Return full content by default. *Default:* ``False``

**Tools**

*Language*

- ``wp_set_lang`` - Set the language for Wikipedia queries.

- ``wp_get_lang`` - Retrieve current language setting.

- ``wp_languages`` - Get list of supported languages.

*Search / Suggest*

- ``wp_search`` - Search for articles using keywords.

- ``wp_suggest`` - Get title suggestions for queries.

*Read*

- ``wp_summary`` - Fetch a summary of a Wikipedia article.

- ``wp_page`` - Access full details of a Wikipedia article.

- ``wp_section`` - Get content of a specific article section.

*Discover*

- ``wp_random`` - Discover random Wikipedia article titles.

- ``wp_geosearch`` - Find articles near specific coordinates.

*Utilities*

- ``wp_open`` - Open articles in a web browser by title or URL.

Wolfram Alpha
-------------

Provides computational knowledge via Wolfram Alpha: short answers, full JSON pods, numeric and symbolic math (solve, derivatives, integrals), unit conversions, matrix operations, and plots rendered as images. Images are saved under ``data/wolframalpha/`` in the user data directory.

**Options**

- **API base** *api_base* - Base API URL. *Default:* ``https://api.wolframalpha.com``. Change only if you use a proxy/gateway.

- **HTTP timeout (s)** *http_timeout* - Request timeout in seconds.

- **Wolfram Alpha AppID** *wa_appid* - AppID used to authenticate requests. Stored as a secret. Get it from: https://developer.wolframalpha.com/portal/myapps/

- **Units** *units* - Preferred unit system for supported endpoints: ``metric`` or ``nonmetric``.

- **Simple background** *simple_background* - Background for Simple API images: ``white`` or ``transparent``.

- **Simple layout** *simple_layout* - Layout for Simple API images, e.g., ``labelbar`` or ``inputonly``.

- **Simple width** *simple_width* - Target width for Simple API images (pixels). Leave empty to use the service default.

**Tools**

- ``wa_short`` - Return a concise text answer suitable for quick facts and simple numeric results.

  Parameters:
  - ``query`` (str, required) — natural-language or math input.

- ``wa_spoken`` - Return a one-sentence, spoken-style answer.

  Parameters:
  - ``query`` (str, required)

- ``wa_simple`` - Render a compact result image (PNG/GIF) via the Simple API and save it to a file.

  Parameters:
  - ``query`` (str, required)
  - ``out`` (str, optional) — output path; if relative, saved under ``data/wolframalpha/``.
  - ``background`` (str, optional) — ``white`` | ``transparent``.
  - ``layout`` (str, optional) — e.g., ``labelbar`` | ``inputonly``.
  - ``width`` (int, optional) — target image width (px).

- ``wa_query`` - Run a full query and return pods as JSON (``queryresult.pods``). Can optionally download pod images.

  Parameters:
  - ``query`` (str, required)
  - ``format`` (str, optional) — e.g., ``plaintext,image``.
  - ``assumptions`` (list[str], optional) — repeated ``assumption`` parameters.
  - ``podstate`` (str, optional) — pod state id.
  - ``scantimeout`` (int, optional), ``podtimeout`` (int, optional)
  - ``maxwidth`` (int, optional) — max image width.
  - ``download_images`` (bool, optional) — if true, downloads pod images.
  - ``max_images`` (int, optional) — limit for downloaded images.

- ``wa_calculate`` - Evaluate or simplify an expression. Tries the short-answer endpoint first, then falls back to a full JSON query.

  Parameters:
  - ``expr`` (str, required)

- ``wa_solve`` - Solve one equation or a system of equations over a chosen domain.

  Parameters:
  - ``equation`` (str, optional) — single equation.
  - ``equations`` (list[str], optional) — list of equations.
  - ``var`` (str, optional) — single variable.
  - ``variables`` (list[str], optional) — variables set.
  - ``domain`` (str, optional) — ``reals`` | ``integers`` | ``complexes``.

- ``wa_derivative`` - Compute a derivative (with optional evaluation at a point).

  Parameters:
  - ``expr`` (str, required)
  - ``var`` (str, optional, default ``x``)
  - ``order`` (int, optional, default ``1``)
  - ``at`` (str, optional) — evaluation point, e.g., ``x=0``.

- ``wa_integral`` - Compute an indefinite or definite integral.

  Parameters:
  - ``expr`` (str, required)
  - ``var`` (str, optional, default ``x``)
  - ``a`` (str, optional) — lower bound (for definite integrals).
  - ``b`` (str, optional) — upper bound.

- ``wa_units_convert`` - Convert numeric values between units.

  Parameters:
  - ``value`` (str, required) — numeric value.
  - ``from`` (str, required) — source unit.
  - ``to`` (str, required) — target unit.

- ``wa_matrix`` - Perform matrix operations.

  Parameters:
  - ``op`` (str, optional, default ``determinant``) — ``determinant`` | ``inverse`` | ``eigenvalues`` | ``rank``.
  - ``matrix`` (list[list], required) — e.g., ``[[1,2],[3,4]]``.

- ``wa_plot`` - Generate a function plot as an image via the Simple API and save it to a file.

  Parameters:
  - ``func`` (str, required) — function, e.g., ``sin(x)``.
  - ``var`` (str, optional, default ``x``)
  - ``a`` (str, optional) — domain start.
  - ``b`` (str, optional) — domain end.
  - ``out`` (str, optional) — output path; relative paths go under ``data/wolframalpha/``.

X/Twitter
----------

The X/Twitter plugin exposes X tools for reading and searching posts, publishing, replying, quoting, likes, reposts, bookmarks and media uploads. Authentication uses OAuth2.

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

- **API base** *api_base* - Base API URL. *Default:* ``https://api.x.com``

- **Authorize base** *authorize_base* - Base URL for OAuth authorization. *Default:* ``https://x.com``

- **HTTP timeout (s)** *http_timeout* - Requests timeout in seconds. *Default:* ``30``

**OAuth2 PKCE**

- **OAuth2 Client ID** *oauth2_client_id* - Client ID from X Developer Portal. *Secret*

- **OAuth2 Client Secret (optional)** *oauth2_client_secret* - Only for confidential clients. *Secret*

- **Confidential client (use Basic auth)** *oauth2_confidential* - Enable if your App is confidential. *Default:* ``False``

- **Redirect URI** *oauth2_redirect_uri* - Must match one of the callback URLs in your X App. *Default:* ``http://127.0.0.1:8731/callback``

- **Scopes** *oauth2_scopes* - OAuth2 scopes for Authorization Code with PKCE. *Default:* ``tweet.read users.read like.read like.write tweet.write bookmark.read bookmark.write tweet.moderate.write offline.access``

- **(auto) code_verifier** *oauth2_code_verifier* - Generated by x_oauth_begin. *Secret*

- **(auto) state** *oauth2_state* - Generated by x_oauth_begin. *Secret*

- **(auto) Access token** *oauth2_access_token* - Stored user access token. *Secret*

- **(auto) Refresh token** *oauth2_refresh_token* - Stored user refresh token. *Secret*

- **(auto) Expires at (unix)** *oauth2_expires_at* - Auto-calculated expiry time.

**App-only Bearer (optional for read-only)**

- **App-only Bearer token (optional)** *bearer_token* - Optional app-only bearer for read endpoints. *Secret*

**Convenience cache**

- **(auto) User ID** *user_id* - Cached after x_me or oauth exchange.

- **(auto) Username** *username* - Cached after x_me or oauth exchange.

- **Auto-start OAuth when required** *oauth_auto_begin* - Start PKCE flow automatically if needed. *Default:* ``True``

- **Open browser automatically** *oauth_open_browser* - Open authorize URL in default browser. *Default:* ``True``

- **Use local server for OAuth** *oauth_local_server* - Capture redirect using a local server. *Default:* ``True``

- **OAuth local timeout (s)** *oauth_local_timeout* - Time to wait for redirect with code. *Default:* ``180``

- **Success HTML** *oauth_success_html* - HTML displayed on local callback success.

- **Fail HTML** *oauth_fail_html* - HTML displayed on local callback error.

- **OAuth local port (0=auto)** *oauth_local_port* - Local HTTP port for callback. *Default:* ``8731``

- **Allow fallback port if busy** *oauth_allow_port_fallback* - Use a free port if the preferred port is busy. *Default:* ``True``

**Tools**

*Auth*

- ``x_oauth_begin`` - Begin OAuth2 PKCE flow.

- ``x_oauth_exchange`` - Exchange authorization code for tokens.

- ``x_oauth_refresh`` - Refresh access token using refresh_token.

*Users*

- ``x_me`` - Get authorized user information.

- ``x_user_by_username`` - Lookup user by username.

- ``x_user_by_id`` - Lookup user by ID.

*Timelines / Search*

- ``x_user_tweets`` - Retrieve user Tweet timeline.

- ``x_search_recent`` - Perform recent search within the last 7 days.

*Tweet CRUD*

- ``x_tweet_create`` - Create a new Tweet/Post.

- ``x_tweet_delete`` - Delete a Tweet by ID.

- ``x_tweet_reply`` - Reply to a Tweet.

- ``x_tweet_quote`` - Quote a Tweet.

*Actions*

- ``x_like`` - Like a Tweet.

- ``x_unlike`` - Unlike a Tweet.

- ``x_retweet`` - Retweet a Tweet.

- ``x_unretweet`` - Undo a retweet.

- ``x_hide_reply`` - Hide or unhide a reply to your Tweet.

*Bookmarks*

- ``x_bookmarks_list`` - List bookmarks.

- ``x_bookmark_add`` - Add a bookmark.

- ``x_bookmark_remove`` - Remove a bookmark.

*Media*

- ``x_upload_media`` - Upload media and return media_id.

- ``x_media_set_alt_text`` - Attach alt text to uploaded media.

