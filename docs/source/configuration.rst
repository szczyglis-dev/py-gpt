Configuration
=============

Settings
--------
The following basic options can be modified directly within the application:

.. code-block:: ini

   Config -> Settings...


.. image:: images/v2_settings.png
   :width: 400

The options below mirror the current application settings defined in ``settings.json``. Provider- and feature-specific options are grouped by the same tabs used in the Settings window.

**General**

* ``Clear input on send``: When enabled, clears the input field when sending a message. Default: True.

* ``Application environment (os.environ)``: Additional environment vars to set on application start.

* ``Show tray icon``: Restart required. Tray icon provides additional features like "Ask with screenshot" or "Open notepad". Default: True.

* ``Minimize to tray on exit``: Tray icon enabled is required for this option to work. Default: False.

* ``Rendering engine``: Restart of the application is required for this option to take effect.

* ``OpenGL hardware acceleration``: WebEngine / Chromium rendering engine only. Default: True.

* ``Use proxy``: Enable this option to use a proxy for connections to APIs. Default: False.

* ``Proxy address``: Optional proxy for API SDKs, e.g. http://proxy.example.com or socks5://user:pass@host:port.

* ``Memory Limit``: Renderer memory limit; set to 0 to disable. If > 0, the app will try to free memory after the limit is reached. Accepted formats: 3.5GB, 2GB, 2048MB, 1_000_000. Minimum: 2GB. Default: 2.5GB.

**API Keys**

*OpenAI*

* ``OpenAI API key``: Required for the OpenAI API. If you wish to use custom endpoints or local APIs, then you may enter any value here.

* ``OpenAI ORGANIZATION KEY``: The organization's API key/identifier, optional for use within the application.

* ``API Endpoint``: OpenAI API (or compatible) endpoint URL, default: https://api.openai.com/v1.

* ``Use Responses API in Chat mode``: Use Responses API instead of ChatCompletions API in Chat mode. Default: True.

* ``Use Responses API in Chat with Files mode (LlamaIndex)``: Use Responses API instead of ChatCompletions API in Chat with Files mode (LlamaIndex). OpenAI models only. Default: True.

*Google*

* ``Google API key``: Required for the Google API and Gemini models.

* ``API Endpoint``: Google API endpoint URL, default: https://generativelanguage.googleapis.com/v1beta/openai.

* ``Use native API SDK``: Use native GenAI SDK instead of compatible OpenAI client. Default: True.

* ``Use VertexAI``: Enable to use VertexAI in Google GenAI SDK. Default: False.

* ``Google Cloud project``: Provide your Google Cloud project name.

* ``Google Cloud location``: Provide your Google Cloud project location, default: us-central1.

* ``Google Application credentials (path)``: Absolute path to credentials.json, e.g. /home/user/credentials.json.

*Anthropic*

* ``Anthropic API key``: Required for the Anthropic API and Claude models.

* ``API Endpoint``: Anthropic API endpoint URL, default: https://api.anthropic.com/v1.

* ``Use native API SDK``: Use native Anthropic SDK instead of compatible OpenAI client. Default: True.

*HuggingFace*

* ``HuggingFace API key``: Required for the HuggingFace API.

* ``Router API Endpoint``: API Endpoint for HuggingFace Router provider (OpenAI compatible ChatCompletions). Default: https://router.huggingface.co/v1.

*DeepSeek*

* ``DeepSeek API key``: Required for the DeepSeek API.

* ``API Endpoint``: Deepseek API endpoint URL, default: https://api.deepseek.com/v1.

*xAI*

* ``xAI API key``: Required for the xAI API and Grok models.

* ``Management API key``: xAI Management API key. Required for Collections management via Remote vector stores tool.

* ``API Endpoint``: xAI API endpoint URL. Default: https://api.x.ai/v1.

* ``Use native API SDK``: Use native xAI SDK instead of compatible OpenAI client. Default: True.

*Azure OpenAI*

* ``OpenAI API version``: Azure OpenAI API version, e.g. 2023-07-01-preview.

* ``API Endpoint``: Azure OpenAI API endpoint, https://<your-resource-name>.openai.azure.com/.

*Perplexity*

* ``Perplexity API key``: Required for the Perplexity API.

* ``API Endpoint``: Perplexity API endpoint URL, default: https://api.perplexity.ai.

*Mistral AI*

* ``Mistral AI API key``: Required for the Mistral AI API.

* ``API Endpoint``: Mistral AI API endpoint URL, default: https://api.mistral.ai/v1.

*VoyageAI*

* ``VoyageAI API key``: Required for the Voyage API - embeddings for Anthropic and DeepSeek API.

*OpenRouter*

* ``OpenRouter API key``: Required for the OpenRouter API.

* ``API Endpoint``: OpenRouter API endpoint URL, default: https://openrouter.ai/api/v1.

*Forge*

* ``Forge API Key``: Required for Forge API.

* ``API Endpoint``: Forge API endpoint URL, default: https://api.forge.tensorblock.co/v1.

*Eden AI*

* ``Eden AI API key``: Required for the Eden AI API.

* ``API Endpoint``: Eden AI API endpoint URL, default: https://api.edenai.run/v3.

**Layout**

* ``Style (chat)``: WebEngine / Chromium rendering engine only. Default: chatgpt.

* ``Chat output window zoom``: WebEngine / Chromium rendering engine only. Default: 1.0.

* ``Font size (chat plain-text, notepads)``: Tip: You can change the font size using CTRL + Mouse Wheel. Default: 16.

* ``Font size (input)``: Tip: You can change the font size using CTRL + Mouse Wheel. Default: 16.

* ``Font size (ctx list)``: Adjusts the font size in the contexts list. Default: 12.

* ``Font size (toolbox)``: Adjusts the font size in the toolbox on the right. Default: 12.

* ``Layout density``: Adjusts the density of layout elements. Default: -1.

* ``DPI factor``: Restart of the application is required for this option to take effect. Default: 1.0.

* ``DPI Scaling``: Restart of the application is required for this option to take effect. Default: True.

* ``Auto-collapse user message (px)``: Auto-collapse user message after N pixels of height, set to 0 to disable auto-collapse. Default: 1500.

* ``Display tips (help descriptions)``: Displays help tips and option descriptions. Default: True.

* ``Store dialog window positions``: Enables storing and restoring dialog window positions. Default: True.

*Code syntax*

* ``Code syntax highlight``: WebEngine / Chromium rendering engine only. Default: github-dark.

* ``Disable syntax highlight``: Disables syntax highlighting in code blocks. Default: False.

* ``Highlight every N line (real-time)``: Syntax highlight: highlight every N line in stream. Default: 5.

* ``Highlight every N chars (real-time)``: Syntax highlight: highlight every N chars in stream. Default: 1000.

* ``Max lines to highlight (real-time)``: Syntax highlight: max lines to highlight in stream, 0 to disable. Default: 100.

* ``Max lines to highlight (static)``: Syntax highlight: max lines to highlight in static content, 0 to disable. Default: 3000.

* ``Max chars to highlight (static)``: Syntax highlight: max chars to highlight in static content, 0 to disable. Default: 350000.

**Files and attachments**

* ``Store attachments in the workdir upload directory``: Enable to store a local copy of uploaded attachments for future use. Default: True.

* ``Store images, captures, and uploads in the data directory``: Enable to store everything in a single data directory. Default: False.

* ``Allow images as additional context``: If enabled, images can be used as additional context. Default: False.

* ``Append attachment only once (mode: always)``: If enabled, the sent attachment will be appended once to the sending message, rather than appended every time to the input prompt as additional context. Force mode - affects all models. Default: False.

* ``Append attachment only once (mode: only if available, auto-detect)``: If enabled, the sent attachment will be appended once to the sending message, if the selected model and API handle the storage of sent messages on the server side. This may optimize token usage by sending attachments only once. Default: True.

* ``Model for attachment content summary``: Model to use when generating a summary for the content of a file when the Summary option is selected. Default: gpt-4o-mini.

* ``Model for querying index``: Model to use for preparing query and querying the index when the RAG option is selected. Default: gpt-4o-mini.

* ``Use history in RAG query``: When enabled, the content of the entire conversation will be used when preparing a query if mode is RAG or Summary. Default: True.

* ``RAG limit``: Only if the option 'Use history in RAG query' is enabled. Specify the limit of how many recent entries in the conversation will be used when generating a query for RAG. 0 = no limit. Default: 3.

* ``Directory for file downloads``: Subdirectory for downloaded files, e.g. in Assistants mode, inside "data". Default: download.

**Context**

* ``Contexts per load (0 = all)``: Number of contexts loaded at a time in the context list. When you scroll to the bottom of the list, the next batch is loaded automatically. Set to 0 to load all contexts at once. Default: 1000.

* ``Model used for auto-summary``: Choose a model used for summarizing the context and preparing the title on the conversation list on the left. Default: gpt-4o-mini.

* ``Context auto-summary``: Enable automatic summarization of the context on the conversation list on the left. Default: True.

* ``Show context groups on top of the context list``: Displays context groups at the top of the context list. Default: True.

* ``Show date separators on the context list``: Shows date separators on the context list. Default: True.

* ``Show date separators in groups on the context list``: Shows date separators inside context groups. Default: True.

* ``Show date separators in pinned items on the context list``: Shows date separators for pinned context items. Default: False.

* ``Use context (memory)``: Toggles the use of conversation context (memory of previous inputs). Default: True.

* ``Store history``: Toggles conversation history storage. Default: True.

* ``Store time in history``: Chooses whether timestamps are added to history text files. Default: True.

* ``Lock incompatible modes``: Creates a new context when switching to an incompatible mode within an existing context. Default: True.

* ``Search also in conversation content, not only in titles``: Enable search also in context items' content. Default: True.

* ``Show LlamaIndex sources``: If enabled, sources used will be displayed in the response (if available, it will not work in streamed chat). Default: True.

* ``Show Code Interpreter output``: If enabled, output from the code interpreter in the Assistant API will be displayed in real-time (in stream mode). Default: True.

* ``Show reasoning in real-time``: Show provider reasoning/thinking while the response is being generated. Default: True.

* ``Hide reasoning after response``: Hide reasoning when normal response tokens start arriving. When disabled, keep reasoning visible until generation ends. Default: True.

* ``Use extra context output``: If enabled, plain text output (if available) from command results will be displayed alongside the JSON output. Default: True.

* ``Open URLs in built-in browser``: Enable this option to open all URLs in the built-in browser (Chromium) instead of an external browser. Default: False.

**Remote tools**

Remote tools are available only when supported by the selected provider/API mode. The exact set of tools depends on the provider and its native SDK.

*OpenAI*

* ``Web Search``: Enable Web Search remote tool - Responses API only. Default: True.

* ``Image generation``: Enable Image generation remote tool - Responses API only. Default: False.

* ``Code Interpreter``: Enable Code Interpreter remote tool - Responses API only. Default: False.

* ``Remote MCP``: Enable MCP remote tool - Responses API only. Default: False.

* ``Remote MCP configuration``: Configuration in JSON format (will be used in request).

* ``File search``: Enable File Search remote tool - Responses API only. Default: False.

* ``File search vector store IDs``: Vector store IDs, separated by comma (,).

*Google*

* ``Web Search``: Enable Web Search remote tool. Default: True.

* ``Google Maps``: Enable Google Maps remote tool. Default: False.

* ``Code Interpreter``: Enable Code Interpreter remote tool. Default: False.

* ``URL Context``: Enable URL Context remote tool. Default: False.

* ``File search``: Enable File Search remote tool - Responses API only. Default: False.

* ``File search vector store IDs``: Vector store IDs, separated by comma (,).

*Anthropic*

* ``Web Search``: Enable Web Search remote tool. Default: True.

* ``Web Fetch``: Enable Web Fetch remote tool. Default: False.

* ``Code Execution``: Enable Code Execution remote tool. Default: False.

* ``Remote MCP``: Enable MCP remote tool/connector. Default: False.

* ``Remote MCP configuration (tools)``: Configuration in JSON format (will be used in request).

* ``Remote MCP configuration (mcp_servers)``: Configuration in JSON format (will be used in request).

*xAI*

* ``Web Search``: Enable Web Search remote tool. Default: True.

* ``X Search``: Enable X Search remote tool. Default: False.

* ``Code Execution``: Enable Code Execution remote tool. Default: False.

* ``Remote MCP``: Enable MCP remote tool - Responses API only. Default: False.

* ``Remote MCP configuration``: Configuration in JSON format (will be used in request).

* ``Collections Search``: Enable Collections Search remote tool. Default: False.

* ``Collection IDs``: Collection IDs, separated by comma (,) NOTE: Management API key is required for managing collections in Remote vector stores tool.

**Models**

* ``Max output tokens``: Set to 0 to disable the limit. Default: 0.

* ``Max total tokens``: Set to 0 to disable the limit. Default: 0.

* ``RPM limit``: Specify the limit of maximum requests per minute (RPM), 0 = no limit. Default: 60.

* ``Context threshold``: Tokens reserved for responses. Default: 200.

* ``Temperature``: Controls response randomness; lower values are more deterministic and higher values are more varied. Default: 1.0.

* ``Top-p``: Controls response diversity using nucleus sampling. Default: 1.0.

* ``Frequency Penalty``: Decreases the likelihood of repetition in the model's responses. Default: 0.0.

* ``Presence Penalty``: Discourages the model from repeatedly returning to topics already mentioned. Default: 0.0.

**Prompts**

* ``Use native API function calls``: If enabled, the application will use native API function calls instead of the internal pygpt format and the command prompts from below will not be used. Chat and Assistants modes ONLY. Default: True.

* ``Command execute: instruction``: Placeholders: {schema}, {extra}.

* ``Command execute: extra footer (non-Assistant modes)``: Extra footer appended after the commands JSON schema in non-Assistant modes.

* ``Command execute: extra footer (Assistant mode only)``: Additional instructions to separate local commands from the remote environment that is already configured in the Assistants.

* ``Context: auto-summary (system prompt)``: System prompt used for automatic context summarization.

* ``Context: auto-summary (user message)``: Placeholders: {input}, {output}.

* ``Agent: evaluation prompt in loop [LlamaIndex] - % score``: Prompt used to response evaluation when Loop / evaluate option is enabled (score).

* ``Agent: evaluation prompt in loop [LlamaIndex] - % complete``: Prompt used to response evaluation when Loop / evaluate option is enabled (percent).

* ``Agent: system instruction [Legacy]``: Prompt to instruct how to handle autonomous mode.

* ``Agent: continue [Legacy]``: Prompt sent to automatically continue the conversation.

* ``Agent: continue (always, more steps) [Legacy]``: Prompt sent to always automatically continue the conversation (more reasoning).

* ``Agent: goal update [Legacy]``: Prompt to instruct how to update the current goal status.

* ``Expert: Master prompt``: Instruction (system prompt) for Master expert on how to handle slave experts. Instructions for slave experts are given from their presets.

* ``Image generation``: Prompt for generating prompts for image model (if raw-mode is disabled). Image / Video modes only.

* ``Video generation``: Prompt for generating prompts for video model (if raw-mode is disabled). Image / Videos mode only.

**Images and video**

*Image*

* ``Image size``: Sets the image resolution used for generation; available values depend on the selected model.

* ``Image quality``: Sets image generation quality; available values depend on the selected model.

* ``Prompt generation model``: LLM used to refine your prompt before image generation (not the image model). Default: gpt-4o.

*Video*

* ``Aspect ratio``: Frame aspect ratio (e.g., 16:9, 9:16, 1:1); availability depends on the selected model.

* ``Video duration``: Clip length in seconds; limits may vary by model.

* ``FPS``: Frames per second (e.g., 24, 25, 30); may be rounded or ignored by the model.

* ``Seed``: Optional random seed for reproducible results; leave empty for random.

* ``Generate audio``: Include synthesized background audio if supported by the model. Default: False.

* ``Video resolution``: Target output resolution (e.g., 720p, 1080p); availability depends on the model.

* ``Prompt enhancement model``: LLM used to refine your prompt before video generation (not the video model). Default: gemini-2.5-flash.

**Vision and camera**

*Camera*

* ``Camera Device``: Select a camera device for real-time video capture. Default: 0.

* ``Capture width (in pixels)``: Sets the camera capture width in pixels. Default: 1280.

* ``Capture height (in pixels)``: Sets the camera capture height in pixels. Default: 720.

* ``Capture quality (%)``: Sets JPEG quality for captured camera images, in percent. Default: 95.

**Audio**

*Devices*

* ``Audio Input Backend``: Select the audio input backend. Default: native.

* ``Audio Input Device``: Select the audio device for Microphone input. Default: 0.

* ``Audio Output Backend``: Select the audio output backend. Default: native.

* ``Audio Output Device``: Select the audio device for audio output. Default: 0.

* ``Channels``: Input channels, default: 1.

* ``Sampling Rate``: Sampling rate, default: 44100.

*Options*

* ``Recording timeout``: Timeout (seconds) for auto-stop recording, 0 to disable, default: 120.

* ``Continuous recording auto-transcribe interval``: Interval in seconds for auto-transcribe audio chunk, default: 10.

* ``Continuous Audio Recording (Chunks)``: Enable recording in chunks for long audio recordings in notepad (voice notes). Default: False.

* ``Enable timeout in continuous mode``: Enables the recording timeout while continuous recording mode is active. Default: False.

* ``VAD prefix padding (in ms)``: Sets VAD prefix padding in milliseconds for real-time audio mode. Default: 300.

* ``VAD end silence (in ms)``: Sets VAD end-silence duration in milliseconds for real-time audio mode. Default: 2000.

* ``Audio notify microphone listening start/stop``: Plays an audio notification when microphone listening starts or stops. Default: False.

*Cache*

* ``Enable Cache``: Enable audio caching for speech synthesis generation. Default: True.

* ``Max files to store``: Max number of cached audio files stored to disk. Default: 1000.

**Indexes / LlamaIndex**

* ``Indexes``: List of configured indexes.

*Vector Store*

* ``Vector Store``: Selects the vector store used by LlamaIndex. Default: SimpleVectorStore.

* ``Vector Store (**kwargs)``: Additional keyword arguments (**kwargs), such as API keys, for the Vector Store provider. These arguments will be passed to the provider; please refer to the LlamaIndex API reference for a list of required arguments for the specified Vector Store.

*Chat*

* ``Chat mode``: Check LlamaIndex documentation for help. Default: context.

* ``Use ReAct agent for tool calls in Chat with Files mode.``: If enabled, the ReAct agent will be used if the option "+Tools" is enabled. Default: False.

* ``Auto-retrieve additional context``: If enabled, additional context will be retrieved with every query and appended to system prompt. Default: True.

*Embeddings*

* ``Embeddings provider``: Selects the global embeddings provider used for indexing and Chat with Files. Default: openai.

* ``RPM limit``: Limit for embeddings API calls - specify the limit of maximum requests per minute (RPM), 0 = no limit. Default: 60.

* ``Embeddings provider ENV vars``: Environment to set up before embedding provider initialization, such as API keys, etc. Use {config_key} as a placeholder to use the value from the application configuration.

* ``Global embeddings provider **kwargs``: Additional keyword arguments (**kwargs), such as model name, for the embeddings provider instance. These arguments will be passed to the provider instance; please refer to the LlamaIndex API reference for a list of required arguments for the specified embeddings provider.

* ``Default embedding providers for attachments``: Define embedding model by provider to use in attachments.

*Indexing*

* ``Recursive directory indexing``: Enables recursive directory indexing. Default: True.

* ``Replace old document versions in the index during re-indexing``: If enabled, previous versions of documents will be deleted from the index when the newest versions are indexed. Default: True.

* ``Excluded file extensions``: File extensions to exclude if no data loader for this extension, separated by comma.

* ``Force exclude files``: If enabled, the exclusion list will be applied even when the data loader for the extension is active. Default: False.

* ``Stop indexing when an error occurs``: If enabled, indexing will be stopped when any error occurs. Default: True.

* ``Custom metadata to append/replace to indexed documents (files)``: Define custom metadata key => value fields for specified file extensions, separate extensions by comma. Allowed placeholders: {path}, {relative_path} {filename}, {dirname}, {relative_dir} {ext}, {size}, {mtime}, {date}, {date_time}, {time}, {timestamp}.

* ``Custom metadata to append/replace to indexed documents (web/external content)``: Define custom metadata key => value fields for specified external data loaders. Allowed placeholders: {date}, {date_time}, {time}, {timestamp} + {data loader args}.

*Data loaders*

* ``Additional keyword arguments (**kwargs) for data loaders``: Additional keyword arguments (**kwargs), such as settings, API keys, for the data loader. These arguments will be passed to the loader; please refer to the PyGPT documentation or LlamaHub loaders reference for a list of allowed arguments for the specified data loader. One argument per single row.

* ``Use local models in Video/Audio and Image (vision) loaders``: Enable usage of local models in Video/Audio and Image (vision) loaders. If disabled, the Image (vision) loader uses the image model configured in the ``Chat with Files (LlamaIndex, inline)`` plugin, while Video/Audio transcription uses the speech-recognition provider configured in the ``Audio Input`` plugin. Local models work only in the Python version (not compiled/Snap). Default: False.

*Update*

* ``Auto-index DB in real-time (in the background of conversation)``: Enables automatic conversation-context indexing in the background. Default: False.

* ``ID of the index for auto-indexing``: Selects the index used for automatic context indexing. Default: base.

* ``Enable auto-index in modes``: Available modes: chat, llama_index, audio, research, completion, img, vision, assistant, agent_llama, agent, expert.

**Agents and experts**

*Agents*

* ``Max steps (per iteration)``: Max steps in one iteration before goal achieved. Default: 10.

* ``Max evaluation steps in loop``: Set the maximum evaluation steps to achieve the final result, 0 = infinity. Default: 3.

* ``Model for evaluation``: Model used for evaluation with score/percentage (loop). If not selected, then current active model will be used.

* ``Append and compare previous evaluation prompt in next evaluation``: If enabled, previous improvement prompt will be checked in next eval in loop. Default: False.

* ``Split response messages``: Split response messages into separate context items in OpenAI Agents mode. Default: True.

*General*

* ``Auto retrieve additional context from RAG``: Auto retrieve additional context from RAG at the beginning if the index is provided. Default: False.

* ``Display full agent output in chat view``: If enabled, then full output from agent will be displayed in chat window if agent is enabled. Default: True.

* ``Display a tray notification when the goal is achieved.``: Displays a tray notification when an agent finishes or achieves its goal. Default: False.

*Autonomous*

* ``Sub-mode for agents``: Sub-mode to use in Agent (Autonomous) mode. Default: chat.

* ``Index to use``: Only if sub-mode is Chat with Files, choose the index to use in Autonomous and Experts modes. Default: base.

* ``Use native API function calls``: If enabled, the application will use native API function calls instead of the internal pygpt format and the command prompts will not be used. Autonomous agent mode only. Default: False.

* ``Use Responses API in Agent mode``: Use Responses API instead of ChatCompletions API in Agent (autonomous) mode. OpenAI models only. Default: False.

*Experts*

* ``Sub-mode for experts``: Sub-mode to use for Experts. Default: chat.

* ``Use agent for expert reasoning``: If enabled, expert will use the agent when generating response and calling tools. Default: True.

* ``Use native API function calls``: If enabled, the application will use native API function calls instead of the internal pygpt format and the command prompts will not be used. Experts only. Default: False.

* ``Use Responses API in Experts mode (master)``: Use Responses API instead of ChatCompletions API in Experts (master model). OpenAI models only. Default: False.

* ``Use Responses API in Experts (slaves)``: Use Responses API instead of ChatCompletions API for Expert instances (slave models). OpenAI models only. Default: False.

**Accessibility**

* ``Enable voice control (using microphone)``: Enables voice control using the microphone and configured voice commands. Default: False.

* ``Model``: Model to use for command recognition in voice control. Default: gpt-4o-mini.

* ``Use voice synthesis to describe events on the screen.``: Uses speech synthesis to describe application events shown on screen. Default: False.

* ``Audio notify voice command execution``: Plays an audio notification when a recognized voice command is executed. Default: True.

* ``Use audio output cache``: If enabled, all static audio outputs will be cached on the disk instead of being generated every time. Default: True.

* ``Control shortcut keys``: Setup keyboard shortcuts and voice commands to control the application using voice and microphone.

* ``Blacklist for voice synthesis event descriptions (ignored events)``: Add to this list all the actions that should not be described using audio synthesis.

* ``Voice control actions blacklist``: Disable actions in voice control; add actions to the blacklist to prevent execution through voice commands.

**Security**

Security settings control host-side filesystem access, system commands used by plugins, and confirmation of provider-flagged Computer Use operations. These controls apply only to **non-sandbox** execution. When a plugin command or Computer Use action runs in a configured sandbox, the Security restrictions below are bypassed because the sandbox provides its own isolation.

*General*

* ``Restrict plugin file reads to working directory``: When enabled, plugin-mediated reads of local files are limited to the current workdir ``data`` directory. The application-owned internal ``tmp`` directory is also allowed so built-in temporary workflows such as IPython and Canvas can operate. Default: True.

* ``Restrict plugin file writes to working directory``: When enabled, plugin-mediated writes, modifications, moves, and deletes are limited to the current workdir ``data`` directory (plus the application-owned internal ``tmp`` directory). Default: False.

* ``Enable system commands whitelist``: When enabled, non-sandbox plugin commands may execute only command names listed in the whitelist for the current operating system. Command names are separated by commas or semicolons. When enabled, the whitelist takes precedence over the blacklist. Default: False.

*Computer use*

* ``Halt on potentially unsafe operation``: Non-sandbox only. When enabled, Computer Use pauses before an operation that the API provider flags as requiring user confirmation. PyGPT displays a warning in the chat and waits until the user types ``continue``. The paused mouse/keyboard action is executed only after that confirmation, and only then is the provider safety check acknowledged back to the API. When disabled, provider safety checks are acknowledged automatically as before. Sandbox execution is not affected. Default: True.

*Linux / Windows / macOS*

* ``System commands whitelist``: Per-OS comma- or semicolon-separated list of executable/command names allowed for non-sandbox plugin execution. Each OS tab is pre-populated with common file-listing, inspection, and text-processing commands (for example ``ls``, ``cat``, ``grep``, ``sed`` on Linux/macOS, and ``dir``, ``type``, ``findstr`` on Windows).

* ``System commands blacklist``: Per-OS comma- or semicolon-separated list of executable/command names blocked for non-sandbox plugin execution when the whitelist is disabled. The default blacklist is empty to preserve existing behavior.

If access is blocked, the plugin returns a ``Permission denied`` result that points to ``Settings -> Security``. The checks are shared by filesystem-capable plugins and host-side command execution, including Files I/O, Web Search file upload/download paths, System (OS), Custom Commands, Code Interpreter host execution, server transfers, and integrations that upload or save local files.

.. important::

   These settings are application-level guards, not a process sandbox. Arbitrary host code (for example Python code intentionally executed outside the sandbox) may use operating-system APIs directly. For process-level isolation, use the plugin sandbox; sandbox execution is intentionally not filtered by these Security settings.

**Personalize**

* ``About You``: Provide information about yourself, e.g., "My name is... I'm 30 years old, I'm interested in..." This will be included in the model's system prompt. WARNING: Please do not use AI as a "friend". Real-life friendship is better than using an AI as a friendship replacement. DO NOT become emotionally involved in interactions with an AI.

* ``Enable in Modes``: Select the modes where the personalized "about" prompt will be used.

**Updates**

* ``Check for updates on start``: Checks for application updates when PyGPT starts. Default: True.

* ``Check for updates in the background``: Checks for application updates periodically in the background. Default: True.

**Debug**

* ``Show debug menu``: Enables the debug/developer menu. Default: False.

* ``Log Level``: Tip: Running application with --debug=1 or --debug=2 command line arguments overwrites this settings and force enables logging to %workdir%/app.log file. Log levels: 1 = INFO, 2 = DEBUG.

* ``Log and debug context``: Enables logging and debugging of context input/output. Default: True.

* ``Log and debug events``: Enables logging of event dispatch. Default: False.

* ``Log plugin usage to console``: Enables plugin usage logging in the console. Default: False.

* ``Log image and video generation to console``: Enables image/video-generation usage logging in the console. Default: False.

* ``Log attachments usage to console``: Enables attachment usage logging in the console. Default: False.

* ``Log LlamaIndex usage to console``: Enables LlamaIndex usage logging in the console. Default: False.

* ``Log Realtime sessions to console``: Enables Realtime session logging in the console. Default: False.

* ``Log Assistants usage to console``: Enables Assistants API usage logging in the console. Default: False.

*General*

* ``Log Agents usage to console``: Enables agent usage logging in the console. Default: False.

JSON files
-----------
The configuration is stored in JSON files for easy manual modification outside of the application. 
These configuration files are located in the user's work directory within the following subdirectory:

.. code-block:: ini

   {HOME_DIR}/.config/pygpt-net/


Manual configuration
---------------------
You can manually edit the configuration files in this directory (this is your work directory):

.. code-block:: ini

   {HOME_DIR}/.config/pygpt-net/

* ``assistants.json`` - stores the list of assistants.
* ``attachments.json`` - stores the list of current attachments.
* ``config.json`` - stores the main configuration settings.
* ``models.json`` - stores models configurations.
* ``cache`` - a directory for audio cache.
* ``capture`` - a directory for captured images from camera and screenshots
* ``css`` - a directory for CSS stylesheets (user override)
* ``history`` - a directory for context history in ``.txt`` format.
* ``idx`` - ``LlamaIndex`` indexes
* ``img`` - a directory for generated images saved by the application.
* ``locale`` - a directory for locales (user override)
* ``data`` - a directory for data files and files downloaded/generated by models.
* ``presets`` - a directory for presets stored as ``.json`` files.
* ``upload`` - a directory for local copies of attachments coming from outside the workdir
* ``tmp`` - application-managed temporary files (for example audio input, Canvas, Code Interpreter/IPython and Transcript working files); this is not the user-facing model output directory.
* ``db.sqlite`` - a database with contexts, notepads and indexes data records
* ``app.log`` - a file with error and debug log


Setting the Working Directory Using Command Line Arguments
----------------------------------------------------------

To set the current working directory using a command-line argument, use:

.. code-block:: ini

   python3 ./run.py --workdir="/path/to/workdir"

or, for the binary version:

.. code-block:: ini

   pygpt.exe --workdir="/path/to/workdir"
   

Translations / locale
-----------------------
Locale `.ini` files are located in the directory:

.. code-block:: ini

   ./data/locale


This directory is automatically scanned when the application launches. To add a new translation, 
create and save the file with the appropriate name, for example:

.. code-block:: ini

   locale.es.ini  


This will add Spanish as a selectable language in the application's language menu.

**Overwriting CSS and locales with Your Own Files:**

You can also overwrite files in the ``locale`` and ``css`` app directories with your own files in the user directory. 
This allows you to overwrite language files or CSS styles in a very simple way - by just creating files in your working directory.


.. code-block:: ini

   {HOME_DIR}/.config/pygpt-net/


* `locale` - a directory for locales in ``.ini`` format.
* `css` - a directory for CSS styles

**Adding Your Own Fonts**

You can add your own fonts and use them in CSS files. To load your own fonts, you should place them in the ``%workdir%/fonts`` directory. Supported font types include: ``otf``, ``ttf``.
You can see the list of loaded fonts in ``Debug / Config``.

**Example:**

.. code-block:: ini

   %workdir%
   |_css
   |_data
   |_fonts
      |_MyFont
        |_MyFont-Regular.ttf
        |_MyFont-Bold.ttf
        |...
        

.. code-block:: console

   pre {{
       font-family: 'MyFont';
   }}

Data Loaders
------------

**Configuring data loaders**

In the ``Settings -> LlamaIndex -> Data loaders`` section you can define the additional keyword arguments to pass into data loader instance.

In most cases, an internal LlamaIndex loaders are used internally. 
You can check these base loaders e.g. here:

Files loaders: https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-file/llama_index/readers/file

Web loaders: https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-web

.. tip::
   To index an external data or data from the Web just ask for it, by using ``Web Search`` plugin, e.g. you can ask the model with ``Please index the youtube video: URL to video``, etc. The data loader for the specified content will be chosen automatically.

Allowed additional keyword arguments for built-in data loaders (files):

**CSV Files**  (file_csv)

* ``concat_rows`` - bool, default: ``True``
* ``encoding`` - str, default: ``utf-8``

**HTML Files** (file_html)

* ``tag`` - str, default: ``section``
* ``ignore_no_id`` - bool, default: ``False``

**Image (vision)**  (file_image_vision)

This loader can operate in two modes: local model and API.

If local mode is enabled, a local vision model is used. Local mode requires the Python/PyPi version of
the application and is not available in compiled or Snap versions.

If API mode (default) is selected, the loader uses the image model configured in
``Plugins -> Settings -> Chat with Files (LlamaIndex, inline) -> Image model`` (default: ``gpt-4o``).

.. note::
   API mode sends the image to the configured API model and may incur provider/API usage costs.

Local mode requires ``torch``, ``transformers``, ``sentencepiece`` and ``Pillow`` and uses
``Salesforce/blip2-opt-2.7b`` to describe images.

* ``keep_image`` - bool, default: ``False``
* ``local_prompt`` - str, default: ``Question: describe what you see in this image. Answer:``
* ``api_prompt`` - str, default: ``Describe what is visible in the image, do it as accurately as possible, including a comprehensive description of all details`` - Prompt used in API mode
* ``api_model`` - str, default: ``gpt-4o`` - Fallback API model; inside PyGPT this is set from the plugin's ``Image model`` option
* ``api_tokens`` - int, default: ``1000`` - Max output tokens in API mode

**IPYNB Notebook files** (file_ipynb)

* ``parser_config`` - dict, default: ``None``
* ``concatenate`` - bool, default: ``False``

**Markdown files** (file_md)

* ``remove_hyperlinks`` - bool, default: ``True``
* ``remove_images`` - bool, default: ``True``

**PDF documents** (file_pdf)

* ``return_full_document`` - bool, default: ``False``

**Video/Audio**  (file_video_audio)

This loader can operate in two modes: local model and provider-based transcription.

If local mode is enabled, the local ``Whisper`` model is used. Local mode requires the Python/PyPi
version of the application and is not available in compiled or Snap versions.

If local mode is disabled (default), transcription is delegated to the provider currently configured in
the ``Audio Input`` plugin. For example, when ``Whisper (via OpenAI API)`` is selected there, the loader
uses that provider and its configured model.

.. note::
   Provider-based transcription may incur API usage costs depending on the selected ``Audio Input`` provider.

Local mode requires ``torch`` and ``openai-whisper`` and uses the local Whisper model.

* ``model_version`` - str, default: ``base`` - Local Whisper model to use; available models: https://github.com/openai/whisper

**XML files** (file_xml)

* ``tree_level_split`` - int, default: ``0``

Allowed additional keyword arguments for built-in data loaders (Web and external content):

**Bitbucket**  (web_bitbucket)

* ``username`` - str, default: `None`
* ``api_key`` - str, default: `None`
* ``extensions_to_skip`` - list, default: `[]`

**ChatGPT Retrieval**  (web_chatgpt_retrieval)

* ``endpoint_url`` - str, default: `None`
* ``bearer_token`` - str, default: `None`
* ``retries`` - int, default: `None`
* ``batch_size`` - int, default: `100`

**Google Calendar** (web_google_calendar)

* ``credentials_path`` - str, default: `credentials.json`
* ``token_path`` - str, default: `token.json`

**Google Docs** (web_google_docs)

* ``credentials_path`` - str, default: `credentials.json`
* ``token_path`` - str, default: `token.json`

**Google Drive** (web_google_drive)

* ``credentials_path`` - str, default: `credentials.json`
* ``token_path`` - str, default: `token.json`
* ``pydrive_creds_path`` - str, default: `creds.txt`

**Google Gmail** (web_google_gmail)

* ``credentials_path`` - str, default: `credentials.json`
* ``token_path`` - str, default: `token.json`
* ``use_iterative_parser`` - bool, default: `False`
* ``max_results`` - int, default: `10`
* ``results_per_page`` - int, default: `None`

**Google Keep** (web_google_keep)

* ``credentials_path`` - str, default: `keep_credentials.json`

**Google Sheets** (web_google_sheets)

* ``credentials_path`` - str, default: `credentials.json`
* ``token_path`` - str, default: `token.json`

**GitHub Issues**  (web_github_issues)

* ``token`` - str, default: `None`
* ``verbose`` - bool, default: `False`

**GitHub Repository**  (web_github_repository)

* ``token`` - str, default: `None`
* ``verbose`` - bool, default: `False`
* ``concurrent_requests`` - int, default: `5`
* ``timeout`` - int, default: `5`
* ``retries`` - int, default: `0`
* ``filter_dirs_include`` - list, default: `None`
* ``filter_dirs_exclude`` - list, default: `None`
* ``filter_file_ext_include`` - list, default: `None`
* ``filter_file_ext_exclude`` - list, default: `None`

**Microsoft OneDrive**  (web_microsoft_onedrive)

* ``client_id`` - str, default: `None`
* ``client_secret`` - str, default: `None`
* ``tenant_id`` - str, default: `consumers`

**Sitemap (XML)**  (web_sitemap)

* ``html_to_text`` - bool, default: `False`
* ``limit`` - int, default: `10`

**SQL Database**  (web_database)

* ``uri`` - str, default: `None`

You can provide a single URI in the form of: ``{scheme}://{user}:{password}@{host}:{port}/{dbname}``, or you can provide each field manually:

* ``scheme`` - str, default: `None`
* ``host`` - str, default: `None`
* ``port`` - str, default: `None`
* ``user`` - str, default: `None`
* ``password`` - str, default: `None`
* ``dbname`` - str, default: `None`

**Twitter/X posts**  (web_twitter)

* ``bearer_token`` - str, default: `None`
* ``num_tweets`` - int, default: `100`

Vector stores
-------------

**Available vector stores** (provided by ``LlamaIndex``):

* ChromaVectorStore
* ElasticsearchStore
* PineconeVectorStore
* QdrantVectorStore
* RedisVectorStore
* SimpleVectorStore

You can configure selected vector store by providing config options like ``api_key``, etc. in ``Settings -> Indexes / LlamaIndex`` window. 

Arguments provided here (on list: ``Vector Store (**kwargs)`` in ``Advanced settings`` will be passed to selected vector store provider. You can check keyword arguments needed by selected provider on LlamaIndex API reference page: 

https://docs.llamaindex.ai/en/stable/api_reference/storage/vector_store.html

Which keyword arguments are passed to providers?

For ``ChromaVectorStore`` and ``SimpleVectorStore`` all arguments are set by PyGPT and passed internally (you do not need to configure anything). 
For other providers you can provide these arguments:

**ElasticsearchStore**

Keyword arguments for ElasticsearchStore(``**kwargs``):

* ``index_name`` (default: current index ID, already set, not required)
* any other keyword arguments provided on list


**PineconeVectorStore**

Keyword arguments for Pinecone(``**kwargs``):

* ``api_key``
* index_name (default: current index ID, already set, not required)

**QdrantVectorStore**

Keyword arguments for QdrantVectorStore(``**kwargs``):

* ``url`` - str, default: `http://localhost:6333`
* ``api_key`` - str, default: `None` (for Qdrant Cloud)
* ``collection_name`` (default: current index ID, already set, not required)
* any other keyword arguments provided on list

**RedisVectorStore**

Keyword arguments for RedisVectorStore(``**kwargs``):

* ``index_name`` (default: current index ID, already set, not required)
* any other keyword arguments provided on list


You can extend list of available providers by creating custom provider and registering it on app launch.

By default, you are using chat-based mode when using ``Chat with Files``.
If you want to only query index (without chat) you can enable ``Query index only (without chat)`` option.


**Adding custom vector stores and offline data loaders**

You can create a custom vector store provider or data loader for your data and develop a custom launcher for the application. 

See the section ``Extending PyGPT / Adding a custom Vector Store provider`` for more details.