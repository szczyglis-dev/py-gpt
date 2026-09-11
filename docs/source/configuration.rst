Configuration
=============

Settings
--------
The following basic options can be modified directly within the application:

.. code-block:: ini

   Config -> Settings...


.. image:: images/v2_settings.png
   :width: 400

The options below follow the current Settings UI metadata from ``settings.json`` and the packaged fresh-install defaults from ``config.json``. Provider- and feature-specific options are grouped by the same tabs used in the Settings window.

General
~~~~~~~

* ``Clear input on send``: Clears the message editor immediately after a message is submitted, so the next message starts with an empty input field. Disable it if you want the sent text to remain available for editing or reuse. Default: True.

* ``Show tray icon``: Starts PyGPT with a system-tray icon and exposes tray actions such as opening the notepad or asking with a screenshot. A restart is required after changing this option. Default: True.

* ``Minimize to tray on exit``: Keeps PyGPT running in the system tray when the main window is closed instead of terminating the application. The tray icon must also be enabled. Default: False.

* ``Rendering engine``: Determines which chat-output renderer PyGPT uses: the normal ``WebEngine / Chromium`` renderer provides full HTML/CSS/JavaScript output, while the ``legacy`` value uses the simpler Markdown renderer for compatibility and troubleshooting. The value is applied at startup, so changing it requires a restart.

* ``OpenGL hardware acceleration``: Controls GPU acceleration for the Chromium/WebEngine renderer; when disabled, PyGPT starts Chromium with the ``--disable-gpu`` flag. Disable it if WebEngine shows driver-related crashes, graphical corruption, or other GPU rendering problems; it has no effect on the legacy renderer. Default: True.

* ``Use proxy``: Routes supported outbound API/SDK connections through the proxy configured below instead of connecting directly. Enable it when your network requires an HTTP/SOCKS proxy or when you deliberately want provider traffic to use one. Default: False.

* ``Proxy address``: Specifies the proxy URL used by supported API clients when ``Use proxy`` is enabled. It may include the scheme, host, port, and optional credentials, for example ``http://proxy.example.com`` or ``socks5://user:pass@host:port``.

* ``Application environment (os.environ)``: Defines environment variables that PyGPT adds to its process environment during startup. Use this for provider SDKs, local model servers, proxies, or integrations that read configuration from environment variables.

* ``Memory Limit``: Sets the memory threshold used by the renderer memory-management logic. When the renderer exceeds the configured threshold, PyGPT attempts to release renderer resources; set ``0`` to disable this mechanism. Accepted formats include ``3.5GB``, ``2GB``, ``2048MB`` and raw byte values; the minimum enabled limit is 2 GB. Default: 2.5GB.

API Keys
~~~~~~~~

OpenAI
^^^^^^

* ``OpenAI API key``: Supplies the credential PyGPT uses to authenticate OpenAI API requests. For OpenAI-compatible local/custom endpoints that do not validate a real OpenAI key, any non-empty placeholder may be sufficient if the client requires a key value.

* ``OpenAI ORGANIZATION KEY``: Supplies the optional OpenAI organization identifier used when creating OpenAI API clients. Leave it empty unless requests on your account must be associated with a specific organization.

* ``API Endpoint``: Sets the base URL used for OpenAI requests. Change it when connecting to an OpenAI-compatible gateway or self-hosted endpoint instead of the public OpenAI API. Default: ``https://api.openai.com/v1``.

* ``Use the Responses API in Chat mode``: Sends OpenAI Chat-mode requests through the Responses API instead of Chat Completions. This enables Responses-specific capabilities and remote tools where supported by the selected model. Default: True.

* ``Use the Responses API in Chat with Files mode (LlamaIndex)``: Makes OpenAI-backed Chat with Files/LlamaIndex requests use the Responses API rather than Chat Completions. It affects only OpenAI models and allows the LlamaIndex path to use Responses-specific behavior where supported. Default: True.

Google
^^^^^^

* ``Google API key``: Supplies the credential used to authenticate Gemini Developer API requests. It is used for Google model calls unless you switch the native Google SDK to Vertex AI authentication.

* ``API Endpoint``: Sets the Google API base URL used by the OpenAI-compatible Google client path. Normally this should remain at the public Gemini compatibility endpoint unless you use a custom gateway. Default: ``https://generativelanguage.googleapis.com/v1beta/openai``.

* ``Use native API SDK``: Uses Google's native Gen AI SDK for Gemini requests instead of the OpenAI-compatible client path. Keep it enabled for native Google features and tool support; disable it only when you intentionally need the compatibility endpoint. Default: True.

* ``Use Vertex AI``: Routes native Google Gen AI SDK requests through Vertex AI rather than the standard Gemini Developer API. When enabled, the Google Cloud project, location, and credentials settings below are used for authentication and routing. Default: False.

* ``Google Cloud project``: Identifies the Google Cloud project used for Vertex AI requests. It is used only when ``Use Vertex AI`` is enabled.

* ``Google Cloud location``: Selects the Google Cloud region used for Vertex AI model requests. It is used only with Vertex AI and must match a region where the requested model is available. Default: ``us-central1``.

* ``Google Application credentials (path)``: Points to the Google service-account/application credentials JSON used to authenticate Vertex AI requests. Enter an absolute path to the credentials file, for example ``/home/user/credentials.json``.

Anthropic
^^^^^^^^^

* ``Anthropic API key``: Supplies the credential used to authenticate Anthropic/Claude API requests. It is passed to the configured Anthropic client when Anthropic models are selected.

* ``API Endpoint``: Sets the Anthropic API base URL. Change it only when Anthropic traffic must go through a compatible proxy or gateway. Default: ``https://api.anthropic.com/v1``.

* ``Use native API SDK``: Uses Anthropic's native SDK and request format for Claude instead of the OpenAI-compatible client path. Keep it enabled to use Anthropic-native features and tools supported by PyGPT. Default: True.

HuggingFace
^^^^^^^^^^^

* ``Hugging Face API key``: Supplies the Hugging Face access token used to authenticate requests to Hugging Face-hosted inference/router services. The token must have access to the models/endpoints you select.

* ``Router API Endpoint``: Sets the base URL for Hugging Face Router requests made through its OpenAI-compatible Chat Completions interface. Change it only if you use a compatible proxy or alternate router endpoint. Default: ``https://router.huggingface.co/v1``.

DeepSeek
^^^^^^^^

* ``DeepSeek API key``: Supplies the credential used to authenticate requests to the configured DeepSeek API endpoint. It is used whenever a DeepSeek provider model is selected.

* ``API Endpoint``: Sets the base URL used for DeepSeek model requests. Change it when using a DeepSeek-compatible gateway instead of the public endpoint. Default: ``https://api.deepseek.com/v1``.

xAI
^^^

* ``xAI API key``: Supplies the inference credential used to authenticate xAI/Grok model requests. Collection-management operations use the separate Management API key instead.

* ``Management API key``: Supplies the separate xAI Management API credential used for collection-management operations. It is not the normal inference key and is required when PyGPT creates, lists, or manages xAI Collections through the Remote vector stores tooling.

* ``API Endpoint``: Sets the base URL used for xAI/Grok inference requests. Change it only when routing xAI traffic through a compatible gateway. Default: ``https://api.x.ai/v1``.

* ``Use native API SDK``: Uses xAI's native SDK and request format instead of the OpenAI-compatible client path. Keep it enabled for xAI-native features and remote tools supported by PyGPT. Default: True.

Azure OpenAI
^^^^^^^^^^^^

* ``OpenAI API version``: Selects the Azure OpenAI REST API version appended to Azure requests. Set it to a version supported by your Azure deployment, for example ``2023-07-01-preview``.

* ``API Endpoint``: Sets the Azure OpenAI resource endpoint used for requests. Replace the placeholder with your Azure resource hostname, for example ``https://<your-resource-name>.openai.azure.com/``.

Perplexity
^^^^^^^^^^

* ``Perplexity API key``: Supplies the credential used to authenticate Perplexity/Sonar API requests. It is used when a Perplexity provider model is selected.

* ``API Endpoint``: Sets the base URL used for Perplexity/Sonar requests. Change it only when using a compatible proxy or gateway. Default: ``https://api.perplexity.ai``.

Mistral AI
^^^^^^^^^^

* ``Mistral AI API key``: Supplies the credential used to authenticate Mistral AI API requests. It is passed to the Mistral-compatible client for models using this provider.

* ``API Endpoint``: Sets the base URL used for Mistral AI requests. Change it only when using a compatible proxy or gateway. Default: ``https://api.mistral.ai/v1``.

VoyageAI
^^^^^^^^

* ``Voyage AI API key``: Authenticates requests to Voyage AI embedding models. PyGPT can use Voyage embeddings with provider/model combinations such as Anthropic or DeepSeek when that embedding backend is selected.

OpenRouter
^^^^^^^^^^

* ``OpenRouter API key``: Supplies the credential used to authenticate model requests routed through OpenRouter. The models available to PyGPT depend on the permissions and providers available to that OpenRouter account.

* ``API Endpoint``: Sets the OpenRouter base URL used for model requests. Change it only when routing OpenRouter-compatible traffic through another gateway. Default: ``https://openrouter.ai/api/v1``.

Forge
^^^^^

* ``Forge API Key``: Supplies the credential used to authenticate requests to the configured Forge provider endpoint. It is used for models assigned to the Forge provider.

* ``API Endpoint``: Sets the Forge provider base URL used by PyGPT. Change it only when connecting through an alternate Forge-compatible gateway. Default: ``https://api.forge.tensorblock.co/v1``.

Eden AI
^^^^^^^

* ``Eden AI API key``: Supplies the credential used to authenticate Eden AI requests. It is used for models and features routed through the Eden AI provider.

* ``API Endpoint``: Sets the Eden AI base URL used for requests. Change it only when your deployment requires another compatible endpoint. Default: ``https://api.edenai.run/v3``.

Layout
~~~~~~

* ``Style (chat)``: Selects the visual stylesheet used to render conversation messages in the Chromium/WebEngine chat view. It changes the appearance of rendered chat content without changing model behavior and has no effect on non-WebEngine output. Default: ``chatgpt``.

* ``Chat output window zoom``: Scales the entire Chromium/WebEngine chat page, including rendered text, code blocks, images, and message controls. Use it to enlarge or shrink chat output independently of the individual font-size settings. Default: 1.0.

* ``Font size (chat plain text, notepads)``: Sets the base font size for plain-text chat output and notepad/editor views. It can also be adjusted interactively with ``Ctrl`` + mouse wheel in supported views. Default: 16.

* ``Font size (input)``: Sets the font size of the main message input editor. It can also be adjusted interactively with ``Ctrl`` + mouse wheel while the input has focus. Default: 16.

* ``Font size (context list)``: Sets the text size used for conversations, projects, separators, and related entries in the context list on the left. Default: 12.

* ``Font size (toolbox)``: Sets the text size used by controls and entries in the toolbox panel on the right side of the main window. Default: 12.

* ``Layout density``: Changes the spacing and compactness of application UI elements. Lower values make the interface denser while higher values add more padding and spacing; the change is applied to the active layout. Default: -1.

* ``DPI factor``: Applies an additional scaling factor to the application UI for high-DPI or unusually scaled displays. Increase it when controls and text are too small after normal system scaling; a restart is required. Default: 1.0.

* ``DPI Scaling``: Enables Qt high-DPI scaling so the interface follows display scaling on high-resolution monitors. Disable it only when automatic DPI handling causes incorrect sizing; a restart is required. Default: True.

* ``Auto-collapse user message (px)``: Automatically collapses very tall user-message blocks after they exceed the configured rendered height, keeping long pasted inputs from dominating the chat view. Set ``0`` to keep all user messages fully expanded. Default: 1500.

* ``Display tips (help descriptions)``: Shows contextual help text and descriptions next to configurable options throughout the interface. Disable it for a more compact settings UI once you are familiar with the controls. Default: True.

* ``Store dialog window positions``: Remembers the geometry/position of supported dialog windows and restores them the next time they are opened. Disable it if you prefer dialogs to use their default placement each time. Default: True.

Code syntax
^^^^^^^^^^^

* ``Code syntax highlighting``: Selects the syntax-highlighting theme applied to rendered code blocks in the Chromium/WebEngine chat view and supported code-output panels. It changes presentation only, not code execution. Default: ``darcula``.

* ``Disable syntax highlighting``: Renders code blocks without token-level syntax coloring. This can reduce rendering work for very large outputs or avoid highlighting issues with unusual code; the code content itself is unchanged. Default: False.

* ``Highlight every Nth line (real-time)``: Controls how often streaming code is re-highlighted as new lines arrive. Larger values reduce renderer work during long code streams at the cost of less frequent visual updates. Default: 5.

* ``Highlight every N chars (real-time)``: Adds a character-count trigger for re-running syntax highlighting while code is streaming. Larger values reduce update frequency and can improve performance on large streamed responses. Default: 1000.

* ``Max lines to highlight (real-time)``: Limits syntax highlighting during streaming to code blocks up to the configured number of lines. Blocks above the limit are left unhighlighted while streaming to avoid expensive repeated rendering; set ``0`` to disable the limit. Default: 100.

* ``Max lines to highlight (static)``: Limits syntax highlighting after a response is complete to code blocks up to the configured line count. Use a lower value if very large code blocks make final rendering slow; set ``0`` to disable the limit. Default: 3000.

* ``Max chars to highlight (static)``: Adds a character-count ceiling for syntax highlighting of completed code blocks. Very large blocks beyond the limit are rendered without token coloring to protect UI responsiveness; set ``0`` to disable the limit. Default: 350000.

Files and attachments
~~~~~~~~~~~~~~~~~~~~~

* ``Store attachments in the workdir upload directory``: Copies uploaded attachments into PyGPT-managed upload storage so the files remain available after the original upload action. With ``Store images, captures, and uploads in the data directory`` disabled, this is the base-profile ``upload`` directory. With that option enabled, upload storage follows the active runtime ``data`` workdir, including a custom project data workdir. Disable this option if you do not want PyGPT to keep its own persistent copy. Default: True.

* ``Store images, captures, and uploads in the data directory``: Stores generated images, screenshots/captures, and uploaded files under the active runtime ``data`` tree instead of using their normal dedicated base-profile locations. If the active conversation belongs to a project with a custom data workdir, these files follow that project directory. When disabled, ``img``, ``capture`` and ``upload`` remain in their normal base-profile locations even if the project uses a custom data workdir. The internal ``tmp`` directory is never redirected by this option. Default: False.

* ``Allow images as additional context``: Allows images attached to earlier context items to be reused as additional visual context in later model requests. Disable it when images should be considered only in the message where they were explicitly attached. Default: False.

* ``Make attachments available in the whole project``: When enabled, attachments added to a chat in a project are available in all chats in that project. When disabled, attachments remain available only in the chat where they were added. Default: False.

* ``Append attachment only once (mode: always)``: If enabled, the sent attachment will be appended once to the sending message, rather than appended every time to the input prompt as additional context. Force mode - affects all models. Default: False.

* ``Append attachment only once (mode: only if available, auto-detect)``: If enabled, the sent attachment will be appended once to the sending message, if the selected model and API handle the storage of sent messages on the server side. This may optimize token usage by sending attachments only once. Default: True.

* ``Model for attachment content summary``: Model to use when generating a summary for the content of a file when the Summary option is selected. Default: gpt-4o-mini.

* ``Model for querying index``: Model to use for preparing query and querying the index when the RAG option is selected. Default: gpt-4o-mini.

* ``Use history in RAG query``: When enabled, the content of the entire conversation will be used when preparing a query if mode is RAG or Summary. Default: True.

* ``RAG limit``: Only if the option 'Use history in RAG query' is enabled. Specify the limit of how many recent entries in the conversation will be used when generating a query for RAG. 0 = no limit. Default: 3.

* ``Directory for file downloads``: Chooses the subdirectory under the active runtime ``data`` directory where files downloaded by PyGPT tools and integrations are saved. For a project with a custom data workdir, the subdirectory is created below that project directory; otherwise it is relative to the shared profile ``data`` directory. Default: ``download``.

Context
~~~~~~~

* ``Contexts per load (0 = all)``: Number of contexts loaded at a time in the context list. When you scroll to the bottom of the list, the next batch is loaded automatically. Set to 0 to load all contexts at once. Default: 1000.

* ``Model used for auto-summary``: Selects the model that generates automatic conversation summaries/titles used in the context list. This model is called separately from the active chat model when auto-summary is enabled. Default: ``gpt-4o-mini``.

* ``Context auto-summary``: Automatically generates a short summary/title for conversations so the context list can show a meaningful label instead of relying only on the first message. The model is selected by ``Model used for auto-summary``. Default: True.

* ``Show projects at the top of the context list``: Keeps project containers grouped before ordinary conversations in the left context list. Disable it to let projects follow the normal list ordering. Default: True.

* ``Show date separators in the context list``: Groups ordinary conversations under relative age/date headers in the context list, making older items easier to scan. Disable it to display a continuous list without those separators. Default: True.

* ``Show date separators in projects in the context list``: Groups conversations inside each project under relative age/date headers. Disable it if project contents should be shown as one uninterrupted list. Default: True.

* ``Show date separators in pinned items in the context list``: Adds relative age/date headers within the pinned-conversations area. It is disabled by default so pinned items remain a compact continuous group. Default: False.

* ``Use context (memory)``: Includes previous messages from the current conversation when building new model requests, allowing the model to follow the ongoing dialogue. Disable it to send each new interaction without prior conversational context. Default: True.

* ``Store history``: Persists conversation contexts to PyGPT storage so they can be reopened after the application is restarted. Disable it for sessions that should not be retained in the normal history. Default: True.

* ``Store time in history``: Writes message timestamps into exported/stored history text where supported, preserving when individual exchanges occurred. Disable it if history text should contain message content without time metadata. Default: True.

* ``Lock incompatible modes``: Prevents an existing conversation from being reused when you switch to a mode whose context format is incompatible with it. PyGPT creates a new context instead, avoiding mixed-mode history that a provider or mode cannot correctly consume. Default: True.

* ``Search conversation content as well as titles``: Extends context-list search from conversation titles/metadata to the text of stored messages. This finds more matches but can require more work on large histories. Default: True.

* ``Show LlamaIndex sources``: Appends the source nodes/documents returned by LlamaIndex retrieval to the rendered answer when source metadata is available. Source display is not available on every streamed-response path, so it may appear only after non-streamed retrieval responses. Default: True.

* ``Show Code Interpreter output``: Displays the execution results returned by provider-side Code Interpreter tools as part of the conversation. Disable it if you want the tool to run but do not want its raw/auxiliary output rendered in chat. Default: True.


* ``Show reasoning in real-time``: Displays reasoning/thinking content exposed by supported providers while a response is streaming. It affects only what PyGPT renders in the UI; providers that do not expose reasoning have nothing to show. Default: True.

* ``Hide reasoning after response``: Collapses/hides the live reasoning panel as soon as ordinary answer tokens begin arriving. Disable it if you want exposed provider reasoning to remain visible until the complete response finishes. Default: True.

* ``Use extra context output``: Renders the human-readable/plain-text part of tool or command results in addition to their structured JSON payload when both forms are available. Disable it if you prefer to see only the structured tool output. Default: True.

* ``Open URLs in built-in browser``: Opens clicked links inside PyGPT's built-in Chromium browser rather than handing them to the operating system's default browser. Disable it to use your normal external browser. Default: False.

Remote tools
~~~~~~~~~~~~

Remote tools are provider-hosted capabilities that the model can invoke during a response. A toggle only makes a tool available to the request; the selected model, provider SDK, and API mode must also support it.

OpenAI
^^^^^^

* ``Web Search``: Makes OpenAI's provider-side Web Search tool available so supported models can retrieve current information from the web while answering. It is available on the Responses API path only. Default: True.

* ``Image generation``: Exposes OpenAI's provider-side image-generation tool to compatible Responses API models, allowing image creation to be invoked as part of an ordinary tool-using conversation. Default: False.

* ``Code Interpreter``: Exposes OpenAI's hosted Code Interpreter to compatible Responses API models so they can execute code in the provider environment and return computed results or generated files. Default: False.

* ``Remote MCP``: Allows compatible OpenAI Responses API models to connect to remote MCP servers and invoke the tools exposed by those servers. The connection/tool definition is taken from ``Remote MCP configuration``. Default: False.

* ``Remote MCP configuration``: Supplies the JSON MCP tool/server configuration included in OpenAI requests when Remote MCP is enabled. Use the request shape expected by the OpenAI Responses API, including the server URL/label and any approval or allowed-tool settings you need.

* ``File search``: Makes OpenAI's hosted File Search tool available to compatible Responses API models. It searches the OpenAI vector stores listed below rather than PyGPT's local LlamaIndex indexes. Default: False.

* ``File search vector store IDs``: Lists the OpenAI vector-store IDs that File Search may query. Enter multiple IDs separated by commas; PyGPT sends them with the provider-side File Search tool definition.

* ``Computer use``: Allows supported OpenAI models to request screen, mouse, and keyboard interactions through PyGPT's Computer Use flow. Enable it only when you want the model to operate the configured computer environment. Default: False.

Google
^^^^^^

* ``Web Search``: Makes Google's provider-side web-search/grounding capability available to supported Gemini models, allowing them to incorporate current web information into a response. This is used through the supported native Google API path. Default: True.

* ``Google Maps``: Makes Google Maps grounding available to supported Gemini models so they can use place and map information while answering. Availability depends on the selected model and Google API mode. Default: False.

* ``Code Interpreter``: Makes Google's provider-hosted code-execution tool available to supported Gemini models. The model can run code remotely and use the execution result as part of its response. Default: False.

* ``URL Context``: Allows supported Gemini models to fetch and use the contents of supplied URLs as provider-side context. This lets the provider process referenced pages without PyGPT first injecting their full content locally. Default: False.

* ``File search``: Makes Google's provider-side File Search capability available when the selected Google API/model supports it. The tool searches the Google file-search stores identified below rather than PyGPT's local LlamaIndex indexes. Default: False.

* ``File search vector store IDs``: Lists the Google file-search/vector-store IDs that the remote File Search tool may query. Enter multiple IDs separated by commas.

* ``Remote MCP``: Enables Google Remote MCP through the Interactions API. In the current PyGPT implementation this remote tool is wired only into **Research** mode (Google Deep Research / Interactions API path); it is not currently used by normal Google Chat or other modes. Default: False.

* ``Remote MCP configuration``: Supplies one MCP server definition or a JSON list of server definitions for Google Interactions API requests. Entries use ``type: "mcp_server"`` and must provide a server ``url``. Streamable HTTP MCP servers are supported; SSE endpoints are not supported by this Google path.

* ``Computer use``: Allows supported Gemini Computer Use models to request screen, mouse, and keyboard actions through PyGPT's Computer Use flow. It has no effect for Google models that do not expose Computer Use. Default: False.

Anthropic
^^^^^^^^^

* ``Web Search``: Makes Anthropic's provider-side Web Search tool available to supported Claude models so they can retrieve current web information during a response. Default: True.

* ``Web Fetch``: Makes Anthropic's provider-side Web Fetch tool available so supported Claude models can retrieve the contents of specific web pages during a response. Default: False.

* ``Code Execution``: Makes Anthropic's hosted code-execution environment available to supported Claude models, allowing them to run code and use the execution result in the answer. Default: False.

* ``Remote MCP``: Allows supported Anthropic models to use tools exposed by configured remote MCP servers/connectors. The toolset and server definitions are taken from the two JSON fields below. Default: False.

* ``Remote MCP configuration (tools)``: Defines the JSON ``tools`` payload sent with Anthropic MCP-enabled requests. Use it to declare the MCP toolsets/connectors the model is allowed to invoke.

* ``Remote MCP configuration (mcp_servers)``: Defines the JSON ``mcp_servers`` payload sent to Anthropic, including the remote MCP server names, URLs, authentication, and other provider-supported connection parameters.

* ``Computer use``: Allows supported Claude Computer Use models to request screen, mouse, and keyboard interactions through PyGPT's Computer Use flow. It is ignored by models without Computer Use support. Default: False.

xAI
^^^

* ``Web Search``: Makes xAI's provider-side Web Search capability available to supported Grok models so they can retrieve web results while answering. Default: True.

* ``X Search``: Gives supported Grok models provider-side search access to X content as a separate retrieval source. Enable it when posts/results from X should be available to the model. Default: False.

* ``Code Execution``: Makes xAI's hosted code-execution environment available to supported Grok models, allowing them to run code and use the result during a response. Default: False.

* ``Remote MCP``: Allows compatible xAI Responses API models to connect to remote MCP servers and invoke their exposed tools. The server definition is taken from ``Remote MCP configuration``. Default: False.

* ``Remote MCP configuration``: Supplies the JSON MCP server/tool configuration included in xAI requests when Remote MCP is enabled. Use the request shape supported by the xAI Responses API.

* ``Collections Search``: Lets supported Grok models search xAI-hosted Collections during a response. Only the collection IDs configured below are exposed to the search tool. Default: False.

* ``Collection IDs``: Lists the xAI Collection IDs that Collections Search may query; separate multiple IDs with commas. A separate xAI Management API key is required for collection-management operations in the Remote vector stores tool.

Models
~~~~~~

* ``Max output tokens``: Caps the number of tokens PyGPT asks the model to generate in a single response where the provider/API supports an output-token limit. Set ``0`` to avoid applying an application-level cap. Default: 0.

* ``Max total tokens``: Sets an application-level ceiling for the total token budget used when preparing a request, including conversation context and output allowance where applicable. Set ``0`` to disable this extra limit and rely on the model/provider context window. Default: 0.

* ``RPM limit``: Limits how many model API requests PyGPT may issue per minute, helping avoid provider rate-limit errors during automated or repeated calls. Set ``0`` to disable PyGPT-side RPM limiting. Default: 60.

* ``Context threshold``: Reserves part of the model context window for the generated answer instead of filling the entire window with prompt/history tokens. Increasing it can reduce how much old context is included but leaves more room for completion. Default: 200.

* ``Temperature``: Sets the sampling temperature sent to models that support it. Lower values bias generation toward more predictable token choices, while higher values increase variation; some reasoning models/providers may ignore or restrict this parameter. Default: 1.0.

* ``Top-p``: Sets the nucleus-sampling probability mass sent to models that support it. Lower values restrict generation to a smaller high-probability token set; leave it at ``1.0`` to avoid applying nucleus filtering. Default: 1.0.

* ``Frequency Penalty``: Penalizes tokens in proportion to how often they have already appeared, reducing repeated words/phrases on providers that support this parameter. Positive values increase the penalty; unsupported models may ignore it. Default: 0.0.

* ``Presence Penalty``: Penalizes tokens once they have appeared at all, encouraging the model to introduce new tokens/topics on providers that support this parameter. Positive values increase the effect. Default: 0.0.

Prompts
~~~~~~~

* ``Use native API function calls``: Uses provider-native tool/function calling in Chat mode whenever the selected model/provider supports it. When disabled, PyGPT falls back to its legacy text-based command format and uses the command prompts configured below. Default: True.

* ``Command execution: instruction``: Defines the main instruction used when PyGPT asks a model to emit tool calls in the legacy text-based command format instead of native API function calls. ``{schema}`` is replaced with the available command schema and ``{extra}`` with the configured footer.

* ``Command execution: extra footer``: Appends additional instructions to the legacy/internal tool-call prompt after the generated command schema. Use it to customize how models should format or choose internal PyGPT commands when native function calling is not used.

* ``Legacy command execution footer``: Provides an additional compatibility instruction used by older assistant/tool execution flows. It affects only legacy paths that still build command prompts instead of relying entirely on native provider tool calls.


* ``Context: auto-summary (system prompt)``: Defines the system instruction sent to the auto-summary model when PyGPT generates a conversation summary/title for the context list. Editing it changes the style and rules of generated summaries.

* ``Context: auto-summary (user message)``: Defines the user-message template used for automatic context summarization. ``{input}`` and ``{output}`` are replaced with conversation content before the summary request is sent.

* ``Agent: evaluation prompt in loop [LlamaIndex] - % score``: Defines the LlamaIndex legacy-agent evaluation prompt that asks the evaluator to score the current result during a loop. The score is used to decide whether another improvement/evaluation step is needed.

* ``Agent: evaluation prompt in loop [LlamaIndex] - % complete``: Defines the legacy LlamaIndex evaluation prompt that estimates how complete the current result is. The returned completion percentage participates in the agent loop's stop/continue decision.

* ``Agent: system instruction [Legacy]``: Sets the base system instruction used by the legacy autonomous-agent implementation. It defines how that agent should approach goals, use available tools, and continue its work.

* ``Agent: continue [Legacy]``: Defines the follow-up instruction used when the legacy autonomous agent needs another iteration after an intermediate response. It tells the model to continue working toward the current goal rather than end the run.

* ``Agent: continue (always, more steps) [Legacy]``: Defines the stronger continuation instruction used by legacy agent flows configured to keep iterating for additional reasoning/work. It is sent between iterations to request another step even when the previous response appears mostly complete.

* ``Agent: goal update [Legacy]``: Defines how the legacy autonomous agent should report and update progress toward its current goal. PyGPT uses this prompt when maintaining the goal state between iterations.

* ``Expert: Master prompt``: Instruction (system prompt) for Master expert on how to handle slave experts. Instructions for slave experts are given from their presets.

* ``Image generation``: Defines the instruction given to the prompt-enhancement LLM before an image-generation request when raw prompt mode is not used. It controls how the user's request is expanded or reformulated for the image model.

* ``Video generation``: Defines the instruction given to the prompt-enhancement LLM before a video-generation request when raw prompt mode is not used. It controls how the user request is rewritten for the selected video model.

Images and video
~~~~~~~~~~~~~~~~

Image
^^^^^

* ``Image size``: Selects the requested output dimensions/aspect preset sent to the image-generation provider. Only values supported by the currently selected image model are effective.

* ``Image quality``: Selects the quality tier/quality hint sent with image-generation requests. Supported values and their effect on latency or cost depend on the selected image model.

* ``Prompt generation model``: Selects the text model used to expand/refine the user's image prompt before the final request is sent to the image generator. It does not choose the image-generation model itself. Default: ``gpt-4o``.

Video
^^^^^

* ``Aspect ratio``: Sets the requested width-to-height ratio for generated video frames, such as ``16:9``, ``9:16`` or ``1:1``. Unsupported ratios may be rejected or ignored by the selected video model.

* ``Video duration``: Requests the target clip length, in seconds, from the selected video model. Provider/model limits determine which durations are accepted.

* ``FPS``: Requests the output frame rate for generated videos. Providers may restrict the accepted values or ignore/normalize the request when a model uses a fixed frame rate.

* ``Seed``: Sends an optional random seed to video models that support deterministic seeding. Reusing the same seed can make generations more repeatable; leave it empty to let the provider choose randomness.

* ``Generate audio``: Requests an audio track together with the generated video when the selected provider/model supports native audio generation. Models without this capability ignore or reject the option. Default: False.

* ``Video resolution``: Selects the requested output resolution, such as ``720p`` or ``1080p``. The actual accepted resolutions and possible cost/latency differences depend on the video model.

* ``Prompt enhancement model``: Selects the text model used to expand/refine a user prompt before it is sent to the video generator. It does not select the video-generation model itself. Default: ``gemini-2.5-flash``.

Vision and camera
~~~~~~~~~~~~~~~~~

Camera
^^^^^^

* ``Camera Device``: Chooses which camera PyGPT opens for live capture/snapshot features. The numeric value corresponds to the camera device index exposed by the system. Default: 0.

* ``Capture width (in pixels)``: Requests the horizontal resolution used when PyGPT captures frames from the selected camera. The device/driver may substitute the nearest supported resolution. Default: 1280.

* ``Capture height (in pixels)``: Requests the vertical resolution used when PyGPT captures frames from the selected camera. The device/driver may substitute the nearest supported resolution. Default: 720.

* ``Capture quality (%)``: Controls JPEG compression quality when camera frames are saved or passed through image-based workflows. Higher values preserve more detail but create larger images. Default: 95.

Audio
~~~~~

Devices
^^^^^^^

* ``Audio Input Backend``: Chooses the implementation PyGPT uses to capture microphone audio. The available backends depend on the operating system and installed audio components. Default: ``native``.

* ``Audio Input Device``: Selects the microphone/input device used for recording and voice-control features. Device identifiers come from the currently selected input backend. Default: 0.

* ``Audio Output Backend``: Chooses the implementation PyGPT uses for playback and speech-synthesis output. Available backends depend on the operating system and installed audio components. Default: ``native``.

* ``Audio Output Device``: Selects the speaker/headphone device used for generated speech and other application audio. Device identifiers come from the currently selected output backend. Default: 0.

* ``Channels``: Sets the number of audio channels captured from the microphone. ``1`` records mono audio and is appropriate for speech recognition in most cases. Default: 1.

* ``Sampling Rate``: Sets the microphone capture sample rate in samples per second. Higher values preserve more high-frequency detail but increase audio data size and processing work. Default: 44100.

Options
^^^^^^^

* ``Recording timeout``: Automatically stops a non-continuous microphone recording after the configured number of seconds, preventing accidental indefinitely open recordings. Set ``0`` to disable the timeout. Default: 120.

* ``Continuous recording auto-transcribe interval``: Sets how often continuous recording is split into a chunk and sent for transcription. Shorter intervals produce text sooner but cause more frequent transcription calls. Default: 10 seconds.

* ``Continuous Audio Recording (Chunks)``: Keeps long notepad/voice-note recordings running by processing them as consecutive chunks instead of one monolithic recording. Each chunk can be transcribed while recording continues. Default: False.

* ``Enable timeout in continuous mode``: Applies the normal recording timeout to continuous/chunked recording as well. Leave it disabled if continuous recording should keep running until explicitly stopped. Default: False.

* ``VAD prefix padding (in ms)``: Keeps this amount of audio immediately before Voice Activity Detection marks speech as started. The padding helps prevent the first syllable of an utterance from being clipped. Default: 300 ms.

* ``VAD end silence (in ms)``: Defines how long Voice Activity Detection must observe silence before treating the current utterance as finished. Lower values respond faster; higher values tolerate longer pauses while speaking. Default: 2000 ms.

* ``Audio notification for microphone listening start/stop``: Plays a short audible cue when microphone capture begins or ends, making it easier to know when PyGPT is actively listening without watching the UI. Default: False.

Cache
^^^^^

* ``Enable Cache``: Caches generated speech/audio output on disk so repeated static utterances can be replayed without calling the synthesis provider again. This can reduce latency and API usage for repeated notifications. Default: True.

* ``Max files to store``: Limits how many generated audio files PyGPT retains in the speech-output cache. Older cache entries can be discarded as the limit is exceeded, preventing unbounded disk growth. Default: 1000.

Indexes / LlamaIndex
~~~~~~~~~~~~~~~~~~~~

* ``Indexes``: List of configured indexes. Removing an entry from this list does not delete data already stored in the vector store; use ``Clear and truncate`` for permanent deletion.

Vector Store
^^^^^^^^^^^^

* ``Vector Store``: Selects the storage backend in which LlamaIndex writes and queries document embeddings. Changing it determines where indexed vectors are persisted and which provider-specific connection options may be required. Default: ``SimpleVectorStore``.

* ``Vector Store (**kwargs)``: Additional keyword arguments (**kwargs), such as API keys, for the Vector Store provider. These arguments will be passed to the provider; please refer to the LlamaIndex API reference for a list of required arguments for the specified Vector Store.

Chat
^^^^

* ``Chat mode``: Selects the LlamaIndex chat-engine mode used by Chat with Files, which determines how retrieved context and conversation history are combined when generating an answer. ``context`` is the default general-purpose mode. Default: ``context``.

* ``Use ReAct agent for tool calls in Chat with Files mode.``: When ``+Tools`` is enabled in Chat with Files, routes tool use through a LlamaIndex ReAct agent rather than the normal tool-call path. Enable it only when you specifically want ReAct-style tool planning in this mode. Default: False.

* ``Auto-retrieve additional context``: Runs retrieval for every Chat with Files query and injects the matching indexed content into the model context automatically. Disable it if retrieval should happen only through an explicit agent/tool path. Default: True.

Embeddings
^^^^^^^^^^

* ``Embeddings provider``: Chooses the default embedding backend used to convert text into vectors for indexing and retrieval. Attachment-specific provider mappings can override this global choice. Default: ``openai``.

* ``RPM limit``: Throttles embedding requests issued during indexing/retrieval to the configured number per minute, helping stay within provider rate limits. Set ``0`` to disable PyGPT-side throttling. Default: 100.

* ``Embeddings provider ENV vars``: Defines environment variables that are set before the selected embedding provider is initialized, for example credentials or provider-specific endpoints. A ``{config_key}`` placeholder is replaced with the matching value from PyGPT configuration.

* ``Global embeddings provider **kwargs``: Additional keyword arguments (**kwargs), such as model name, for the embeddings provider instance. These arguments will be passed to the provider instance; please refer to the LlamaIndex API reference for a list of required arguments for the specified embeddings provider.

* ``Default embedding providers for attachments``: Maps model providers to the embedding provider/model that should be used when attachments are indexed for RAG. This lets, for example, attachment retrieval use a provider-appropriate embedding backend instead of the global default.

File indexing
^^^^^^^^^^^^^

* ``Recursive directory indexing``: When a directory is indexed, also walks its subdirectories and includes matching files found below the selected directory. Disable it to index only files directly inside the chosen folder. Default: True.

* ``Replace old document versions in the index during re-indexing``: Removes previously indexed chunks for a document before storing its newly indexed version, preventing stale and current versions from coexisting in retrieval results. Disable it only if you intentionally want historical versions retained. Default: True.

* ``Excluded file extensions``: Lists file extensions that should be skipped by directory/file indexing when no active data loader explicitly handles them. Separate multiple extensions with commas.

* ``Force exclude files``: Makes the excluded-extension list authoritative even when a configured data loader could otherwise process that file type. Use it to block specific extensions from indexing under all loader configurations. Default: False.

* ``Stop indexing when an error occurs``: Aborts the current indexing job on the first file/loader error instead of continuing with the remaining items. Disable it when partial indexing is preferable to failing the whole batch. Default: True.

* ``Custom metadata to add to or replace in indexed documents (files)``: Adds or overrides metadata fields on file-derived LlamaIndex documents, optionally scoped by file extension. Values can be generated from placeholders such as ``{path}``, ``{filename}``, ``{ext}``, ``{size}``, ``{mtime}``, and date/time placeholders before documents are written to the index.

* ``Custom metadata to add to or replace in indexed documents (web/external content)``: Adds or overrides metadata fields on documents produced by web/external data loaders. Values may reference date/time placeholders and loader arguments, allowing metadata to be derived from the source configuration before indexing.

Context indexing
^^^^^^^^^^^^^^^^

* ``Conversation auto-indexing``: Controls automatic indexing of stored conversation context. Available values are ``Off``, ``Auto-index all conversations``, and ``Auto-index only in projects``. Default: Off.

* ``Use isolated index per project``: When enabled, conversations inside projects are indexed into a separate isolated project index. When disabled, project conversations use the selected global auto-indexing indexes. Default: True.

* ``Indexes for global auto-indexing``: Multi-select list of one or more configured indexes used for global conversation auto-indexing. This option does not apply to isolated project indexes. Default: base.

* ``Enable auto-indexing in modes``: Restricts automatic conversation indexing to the selected PyGPT modes. A conversation is auto-indexed only when the global/project auto-indexing policy is enabled and its current mode is included here.

Data loaders
^^^^^^^^^^^^

* ``Additional keyword arguments (**kwargs) for data loaders``: Additional keyword arguments (**kwargs), such as settings, API keys, for the data loader. These arguments will be passed to the loader; please refer to the PyGPT documentation or LlamaHub loaders reference for a list of allowed arguments for the specified data loader. One argument per single row.

* ``Use local models in Video/Audio and Image (vision) loaders``: Enable usage of local models in Video/Audio and Image (vision) loaders. If disabled, the Image (vision) loader uses the image model configured in the ``Chat with Files (RAG, inline)`` plugin, while Video/Audio transcription uses the speech-recognition provider configured in the ``Audio input`` plugin. Local models work only in the Python version (not compiled/Snap). Default: False.

Clear and truncate
^^^^^^^^^^^^^^^^^^

Use this tab to permanently remove all data from a selected stored index or to truncate all tracked project indexes. Removing an entry from the normal ``Indexes`` list does not delete vector-store data. Destructive truncate operations require confirmation.

See :doc:`indexing` for the complete description of global context indexing, isolated project indexes, ``Current project``, project lifecycle, and index cleanup.

Agents and experts
~~~~~~~~~~~~~~~~~~

Chat with Agents
^^^^^^^^^^^^^^^^

* ``Automatically retrieve additional context from RAG``: Performs an initial retrieval from the configured index before a Chat with Agents run and supplies the matching RAG context to the workflow. Disable it if the agent should begin without automatic retrieval and obtain context only through explicit tools. Default: True.

* ``Show full tool-chain in Chat with Agents``: When enabled, the final Chat with Agents response stores and displays the full sequence of normal tool calls executed across the workflow. Each tool call is shown as its own expandable item with Request and Response data. Internal orchestration and worker-management tools are excluded. Default: False.

* ``Max iterations (Chat / Orchestrator)``: Maximum number of main-agent iterations in Chat and Orchestrator modes. Set ``0`` for no application-level iteration limit. Default: ``48``.

* ``Max iterations (Swarm)``: Maximum number of main-agent/orchestrator iterations in Swarm mode. Set ``0`` for no application-level iteration limit. Default: ``4096``.

* ``Worker max iterations``: Maximum number of iterations for each worker agent in any Chat with Agents mode. Set ``0`` for no application-level iteration limit. Default: ``24``.

An iteration is an internal reasoning/tool-call cycle, not a user message turn. Increasing or disabling these limits can increase latency, token/API usage, and tool execution. This is especially important in Swarm because Swarm has no worker-count limit.

Agents
^^^^^^

* ``Max steps (per iteration)``: Limits how many action/reasoning steps a legacy LlamaIndex agent may perform within one iteration while working toward its goal. Raising it allows more work per iteration but can increase latency and API usage. Default: 10.

* ``Max evaluation steps in loop``: Limits how many evaluate/improve cycles a legacy agent may perform before returning its final result. Set ``0`` for no application-level evaluation-loop limit. Default: 3.

* ``Model for evaluation``: Selects the model that judges intermediate legacy-agent results during evaluation loops. If no model is selected, PyGPT reuses the currently active model for the evaluation step.

* ``Append and compare the previous evaluation prompt in the next evaluation``: Carries the previous evaluator feedback/improvement instruction into the next evaluation cycle so the evaluator can compare progress against earlier guidance. This can improve continuity across multi-step refinement loops. Default: False.

* ``Split response messages``: Stores separate assistant messages produced by the OpenAI Agents flow as separate conversation context items instead of merging them into one item. This affects how multi-message agent output is represented in history. Default: True.

Autonomous
^^^^^^^^^^

* ``Sub-mode for agents``: Chooses the underlying interaction mode used by the Autonomous agent, such as standard Chat or Chat with Files. The choice determines which context/tool/index pipeline the autonomous loop runs on. Default: ``chat``.

* ``Index to use``: Selects the LlamaIndex index queried by Autonomous and Experts when their sub-mode is Chat with Files. It is ignored for sub-modes that do not use an index. Default: ``base``.

* ``Use native API function calls``: Uses provider-native function/tool calls inside Autonomous agent mode instead of PyGPT's legacy text command format. When enabled, the legacy command prompts are not used for the autonomous tool-call path. Default: False.

* ``Use the Responses API in Agent mode``: Routes OpenAI Autonomous-agent requests through the Responses API rather than Chat Completions. This enables Responses-native behavior and remote tools where supported by the selected model. Default: True.

Experts
^^^^^^^

* ``Sub-mode for experts``: Chooses the underlying mode used when expert instances perform their work, for example standard Chat or Chat with Files. The selected sub-mode determines which context/index pipeline each expert uses. Default: ``chat``.

* ``Use agent for expert reasoning``: Runs expert instances through the agent/tool-execution loop instead of using a single direct model response. This allows an expert to perform multi-step reasoning and tool calls before returning its result to the master. Default: True.

* ``Use native API function calls``: Uses provider-native function/tool calls inside Experts mode instead of PyGPT's legacy text command format. When enabled, expert tool calls no longer depend on the legacy command prompts. Default: False.

* ``Use the Responses API in Experts mode (master)``: Routes the OpenAI master model in Experts mode through the Responses API instead of Chat Completions. It affects only the master/orchestrating request path. Default: False.

* ``Use the Responses API in Experts mode (slaves)``: Routes OpenAI expert/slave instances through the Responses API instead of Chat Completions. It does not change the API used by the master unless the separate master option is also enabled. Default: False.

Legacy
^^^^^^

* ``Display full agent output in chat view``: Controls whether the complete output from legacy agent modes is rendered in the chat view. This setting is kept for older agent implementations and does not control the Chat with Agents tool-chain display. Default: True.

* ``Display a tray notification when the goal is achieved.``: Shows a system tray notification when a legacy agent finishes or achieves its goal. This setting does not control Chat with Agents workflow status or tool-chain rendering. Default: False.

Accessibility
~~~~~~~~~~~~~

* ``Enable voice control (using the microphone)``: Listens for configured voice commands through the selected microphone and maps recognized commands to PyGPT actions. Voice control remains inactive when this option is disabled. Default: False.

* ``Model``: Selects the model used to interpret transcribed speech as PyGPT voice-control commands. It is used for command recognition, not for the normal chat response. Default: ``gpt-4o-mini``.

* ``Use voice synthesis to describe events on the screen.``: Speaks supported UI/application events through the configured text-to-speech output, providing audible feedback without requiring the screen to be read visually. Events on the blacklist below are skipped. Default: False.

* ``Audio notification for voice command execution``: Plays an audible cue when a recognized voice-control command begins execution, confirming that PyGPT accepted the spoken command. Default: True.

* ``Use audio output cache``: Reuses disk-cached audio for repeated static accessibility/voice-output phrases instead of synthesizing the same phrase again. This reduces repeated TTS calls and response latency at the cost of local cache storage. Default: True.

* ``Control shortcut keys``: Opens/configures the mapping between PyGPT actions and keyboard shortcuts used by accessibility/voice-control workflows. The same action mapping is used when recognized voice commands trigger application commands.

* ``Blacklist for voice synthesis event descriptions (ignored events)``: Lists application events that should remain silent even when spoken event descriptions are enabled. Use it to suppress repetitive or unhelpful announcements without disabling voice synthesis globally.

* ``Voice control action blacklist``: Lists PyGPT actions that voice control is not permitted to execute. This lets you keep voice control enabled while blocking sensitive, disruptive, or unwanted commands.

Security
~~~~~~~~

Security settings control host-side filesystem access, system commands used by plugins, and confirmation of provider-flagged Computer Use operations. These controls apply only to **non-sandbox** execution. When a plugin command or Computer Use action runs in a configured sandbox, the Security restrictions below are bypassed because the sandbox provides its own isolation.

General
^^^^^^^

* ``Restrict plugin file reads to working directory``: When enabled, plugin-mediated reads of local files are limited to the active conversation's runtime ``data`` directory. For a project with a custom data workdir, the project directory is used; otherwise the shared profile ``data`` directory is used. The application-owned internal ``tmp`` directory from the base profile is also allowed so built-in temporary workflows such as IPython and Canvas can operate. Default: True.

* ``Restrict plugin file writes to working directory``: When enabled, plugin-mediated writes, modifications, moves, and deletes are limited to the active conversation's runtime ``data`` directory (plus the application-owned base-profile ``tmp`` directory). Default: True.

* ``Enable system command whitelist``: When enabled, non-sandbox plugin commands may execute only command names listed in the whitelist for the current operating system. Command names are separated by commas or semicolons. When enabled, the whitelist takes precedence over the blacklist. Default: False.

Computer use
^^^^^^^^^^^^

* ``Halt on potentially unsafe operation``: Non-sandbox only. When enabled, Computer Use pauses before an operation that the API provider flags as requiring user confirmation. PyGPT displays a warning in the chat and waits until the user types ``continue``. The paused mouse/keyboard action is executed only after that confirmation, and only then is the provider safety check acknowledged back to the API. When disabled, provider safety checks are acknowledged automatically as before. Sandbox execution is not affected. Default: True.

Linux
^^^^^

* ``System command whitelist``: Defines the comma- or semicolon-separated executable/command names allowed for non-sandbox plugin execution on Linux when the whitelist is enabled. The default list contains common file-listing, inspection, and text-processing commands such as ``ls``, ``cat``, ``grep``, and ``sed``.

* ``System command blacklist``: Defines executable/command names blocked for non-sandbox plugin execution on Linux when the whitelist is disabled. Separate names with commas or semicolons. The default blacklist is empty to preserve existing behavior.

Windows
^^^^^^^

* ``System command whitelist``: Defines the comma- or semicolon-separated executable/command names allowed for non-sandbox plugin execution on Windows when the whitelist is enabled. The default list contains common commands such as ``dir``, ``type``, and ``findstr``.

* ``System command blacklist``: Defines executable/command names blocked for non-sandbox plugin execution on Windows when the whitelist is disabled. Separate names with commas or semicolons. The default blacklist is empty to preserve existing behavior.

macOS
^^^^^

* ``System command whitelist``: Defines the comma- or semicolon-separated executable/command names allowed for non-sandbox plugin execution on macOS when the whitelist is enabled. The default list contains common file-listing, inspection, and text-processing commands such as ``ls``, ``cat``, ``grep``, and ``sed``.

* ``System command blacklist``: Defines executable/command names blocked for non-sandbox plugin execution on macOS when the whitelist is disabled. Separate names with commas or semicolons. The default blacklist is empty to preserve existing behavior.

If access is blocked, the plugin returns a ``Permission denied`` result that points to ``Settings -> Security``. The checks are shared by filesystem-capable plugins and host-side command execution, including Files I/O, Web search file upload/download paths, System (OS), Custom commands, Code interpreter (v2) host execution, server transfers, and integrations that upload or save local files.

.. important::

   These settings are application-level guards, not a process sandbox. Arbitrary host code (for example Python code intentionally executed outside the sandbox) may use operating-system APIs directly. For process-level isolation, use the plugin sandbox; sandbox execution is intentionally not filtered by these Security settings.

Personalize
~~~~~~~~~~~

* ``About You``: Provide information about yourself, e.g., "My name is... I'm 30 years old, I'm interested in..." This will be included in the model's system prompt. WARNING: Please do not use AI as a "friend". Real-life friendship is better than using an AI as a friendship replacement. DO NOT become emotionally involved in interactions with an AI.

* ``Enable in Modes``: Chooses which PyGPT modes receive the text from ``About You`` in their system context. Modes not selected here operate without the personalization block even when ``About You`` contains text.

Custom providers
~~~~~~~~~~~~~~~~

* ``Custom providers``: A runtime list of model providers compatible with the OpenAI Chat Completions API. Each row contains ``Provider name``, ``API base URL``, and ``API key``. Entries are stored in ``config.json`` as ``api_custom_providers`` and are registered immediately after Settings are saved.

  Custom providers appear in model provider selectors and in ``Config -> Models -> Import``. Normal Chat requests use the native OpenAI SDK against the configured base URL. Chat with Files uses LlamaIndex ``OpenAILike``. The model importer reads the OpenAI-compatible ``/models`` endpoint.

Updates
~~~~~~~

* ``Check for updates at startup``: Performs an update/version check when PyGPT launches and can inform you when a newer release is available. Disable it to avoid the startup check. Default: True.

* ``Check for updates in the background``: Periodically performs update/version checks while PyGPT is running, so new releases can be detected without restarting the application. Default: True.

Debug
~~~~~

* ``Show debug menu``: Makes the developer/debug menu and its diagnostic actions visible in the application UI. It is intended for troubleshooting and development rather than normal use. Default: False.

* ``Log Level``: Controls the verbosity of application logging: ``1`` records INFO-level diagnostics and ``2`` records DEBUG-level detail. Starting PyGPT with ``--debug=1`` or ``--debug=2`` overrides this setting and forces logging to ``%workdir%/app.log``.

* ``Log and debug context``: Writes conversation-context input/output diagnostics to the configured logs/console, helping trace what context is being built and processed. Because context can contain user data, disable or protect logs when debugging is not required. Default: True.

* ``Log and debug events``: Logs application event dispatch and handling, which is useful for tracing UI/controller workflows and plugin hooks. It can be noisy during normal use. Default: False.

* ``Log plugin usage to console``: Prints plugin invocation/activity diagnostics to the console so plugin execution can be traced during development or troubleshooting. Default: False.

* ``Log image and video generation to console``: Prints image- and video-generation request/activity diagnostics to the console. Use it to troubleshoot provider calls and generation flow. Default: False.

* ``Log attachments usage to console``: Prints attachment-processing decisions and related activity to the console, helping diagnose upload, extraction, RAG, or native-attachment handling. Default: False.

* ``Log Agents usage to console``: Prints general agent execution diagnostics to the console, including activity from agent workflows not covered by the more specialized Chat with Agents logging options. Default: False.

* ``Log Chat with Agents workflow``: Logs a concise Chat with Agents workflow trace, including orchestration events, tool names, statuses, waits, and response previews without full prompts or large payloads. Default: False.

* ``Chat with Agents verbose (log full flow to console)``: Logs the complete Chat with Agents orchestration flow, including system prompts, tool calls, worker state, RAG context, inputs, and outputs. This may contain sensitive data. Default: False.

* ``Log LlamaIndex usage to console``: Prints LlamaIndex indexing, retrieval, and query-flow diagnostics to the console. Enable it when troubleshooting Chat with Files or vector-store behavior. Default: False.

* ``Log Realtime sessions to console``: Prints lifecycle and provider diagnostics for Realtime/audio sessions to the console. This is useful for connection, streaming, and event troubleshooting. Default: False.

* ``Log legacy API usage to console``: Prints diagnostics for older/legacy API and assistant execution paths that are still supported for compatibility. Enable it when debugging those paths specifically. Default: False.

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

* ``attachments.json`` - stores the list of current attachments.
* ``config.json`` - stores the main configuration settings.
* ``models.json`` - stores models configurations.
* ``cache`` - a directory for audio cache.
* ``capture`` - the base-profile directory for captured images from camera and screenshots; when consolidated data storage is enabled, captures are stored under the active runtime ``data`` workdir instead.
* ``css`` - a directory for CSS stylesheets (user override)
* ``history`` - a directory for context history in ``.txt`` format.
* ``idx`` - ``LlamaIndex`` indexes
* ``img`` - the base-profile directory for generated images; when consolidated data storage is enabled, generated images are stored under the active runtime ``data`` workdir instead.
* ``locale`` - a directory for locales (user override)
* ``data`` - the shared/default directory for data files and files downloaded/generated by models. A project may override only this logical directory with its own runtime data workdir.
* ``presets`` - a directory for presets stored as ``.json`` files.
* ``upload`` - the base-profile directory for local copies of attachments; when consolidated data storage is enabled, upload storage is placed under the active runtime ``data`` workdir instead.
* ``tmp`` - application-managed temporary files (for example audio input, Canvas, Code interpreter (v2)/IPython and Transcript working files); this directory always remains in the base profile workdir and is never replaced by a project data workdir.
* ``db.sqlite`` - a database with contexts, notepads and indexes data records
* ``app.log`` - a file with error and debug log

Project data workdirs
~~~~~~~~~~~~~~~~~~~~~

The directory above is the **profile/application workdir**. Projects do not
replace it. A project can override only the logical ``data`` directory used by
conversations assigned to that project.

When creating a project, ``Use shared workdir`` is enabled by default. Disable
it to choose a custom project data directory. For an existing project use
``RMB -> Edit``. The project item tooltip shows the effective directory.
Conversations outside projects and projects using the shared workdir continue to
use ``<profile workdir>/data``.

This runtime override is used by the Files view, Files I/O, Code interpreter (v2),
filesystem-aware tools, file-download paths and Docker ``/data`` mappings. It
does **not** relocate ``config.json``, ``models.json``, ``db.sqlite``, ``tmp``,
``cache``, ``css``, ``locale``, fonts, logs or other profile-level paths.
``tmp`` always remains in the base profile workdir. ``img``, ``capture`` and
``upload`` follow the project data workdir only when ``Store images, captures,
and uploads in the data directory`` is enabled; otherwise they remain in their
base-profile locations.

Internally, portable paths written as ``%workdir%/data/...`` are resolved
against the active conversation's data root at runtime. Other ``%workdir%``
paths keep their normal profile-level meaning.


Setting the Working Directory Using Command Line Arguments
----------------------------------------------------------

To set the base profile/application working directory using a command-line argument, use:

.. code-block:: ini

   python3 ./run.py --workdir="/path/to/workdir"

or, for the binary version:

.. code-block:: ini

   pygpt.exe --workdir="/path/to/workdir"

This command-line option changes the whole profile/application workdir. It is
different from a project's custom data workdir, which overrides only the
logical ``data`` directory for conversations in that project.
   

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

.. _configuration-data-loaders:

Data Loaders
------------

**Configuring data loaders**

In the ``Settings -> Indexes / LlamaIndex -> Data loaders`` section you can define the additional keyword arguments to pass into data loader instance.

In most cases, an internal LlamaIndex loaders are used internally. 
You can check these base loaders e.g. here:

Files loaders: https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-file/llama_index/readers/file

Web loaders: https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-web

.. tip::
   To index an external data or data from the Web just ask for it, by using ``Web search`` plugin, e.g. you can ask the model with ``Please index the youtube video: URL to video``, etc. The data loader for the specified content will be chosen automatically.

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
``Plugins -> Settings -> Chat with Files (RAG, inline) -> Image model`` (default: ``gpt-4o``).

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
the ``Audio input`` plugin. For example, when ``Whisper (via OpenAI API)`` is selected there, the loader
uses that provider and its configured model.

.. note::
   Provider-based transcription may incur API usage costs depending on the selected ``Audio input`` provider.

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
