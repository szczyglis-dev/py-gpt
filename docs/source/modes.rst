Modes
=====

Chat
-----

In **PyGPT**, this mode lets you chat with models such as ``GPT-6 Astra``, ``GPT-5.6``, ``Claude``, ``Gemini``, ``Grok``, ``Sonar (Perplexity)``, ``DeepSeek``, and many others, including local models running through ``Ollama``.

The Chat mode supports regular conversations as well as more advanced tasks, including calling tools, executing Python code, using external integrations through MCP, searching the web, uploading and analyzing attachments, working with images, and generating new images. Depending on the selected model and enabled tools, it can also perform multi-step tasks that combine several of these capabilities in a single conversation.

PyGPT, in this and other modes, can use native SDKs provided by popular AI providers such as OpenAI, Google, Anthropic, and xAI. It also supports OpenAI-compatible ``Chat Completions API`` endpoints, custom providers, and providers available through LlamaIndex integrations. Both cloud-based and locally hosted models are supported, allowing PyGPT to work with a wide range of commercial, self-hosted, and local AI backends.


   Currently built-in native clients:

   - Anthropic SDK
   - OpenAI SDK
   - Google GenAI SDK
   - xAI SDK

The main window is divided into several sections: tabs at the top, the main chat area in the center, the user input at the bottom, conversation history on the left, and the Toolbox with additional tools and options on the right. PyGPT also supports split-screen mode, allowing you to work with multiple conversations side by side.

.. image:: images/v2_mode_chat.png
   :width: 800

At the bottom of the chat window, PyGPT also shows an estimated number of tokens that will be sent to the model, as well as the number of tokens used for each generated response.

**Attachments:** You can attach and upload files from the input area. See :doc:`Files and Attachments <attachments>` for supported formats and attachment modes.

.. image:: images/attachment.png
   :width: 400

**RAG:** At the bottom of the toolbox, use the ``RAG`` selector to choose an index for additional context. When a valid index is selected, Chat is routed from the normal native/OpenAI-compatible SDK path to the LlamaIndex RAG runtime automatically. Select ``---`` to use the normal Chat provider path. See :doc:`indexing` for RAG modes, indexing, project indexes, vector stores, and retrieval configuration.

.. image:: images/rag.png
   :width: 400

**Vision:** If the selected model is multimodal and supports image input, vision is available natively by default. For models without native vision support, enable the ``Vision (inline)`` plugin to automatically route image analysis through a configured vision-capable model.

Images can be analyzed in real time from attachments, the camera enabled from the ``Audio / Video`` menu, or screenshots captured directly from the application. You can also use the built-in drawing tool to quickly sketch, annotate images, add arrows and markings, and send the result directly for analysis.

.. image:: images/v3_vision_chat.png
   :width: 800

**Image generation:** If you want to generate images directly in chat, enable the ``Image generation (inline)`` plugin in the Plugins menu. The plugin allows you to generate images in Chat mode.

For supported models/providers, you can alternatively enable the provider-side image-generation remote tool in ``Config -> Settings -> Remote Tools``. When available, this lets the model generate images natively without the inline plugin.

Agents
----------------

**Agents** is PyGPT's multi-agent work mode for tasks that benefit from delegation, parallel execution, tool use, verification, and specialist workers. It uses a dedicated runtime built on LlamaIndex agent workflows and is separate from the older ``Agent (LlamaIndex)`` and ``Agent (OpenAI)`` modes, as well as from the separate ``Autonomous mode``.

The **Workflow** selector below the system prompt controls how the workflow operates. The default workflow is **Chat**.

Agent modes
^^^^^^^^^^^

**Chat**
   The default mode. The primary agent responds directly and can delegate tasks to workers when useful.

**Orchestrator**
   Coordinates specialist workers for structured, multi-step tasks. The default limit is ``16`` workers; set **Max workers (Chat / Orchestrator)** to ``0`` for no limit.

**Swarm**
   Launches a group of workers and reports aggregate progress. If no worker count is requested, the orchestrator chooses a small team. Swarm has no built-in worker-count limit.

.. warning::
   Large swarms can generate high API/token usage and many concurrent tool operations. Use a reasonable worker count, especially when tools can modify files or execute commands.

Autonomous execution
^^^^^^^^^^^^^^^^^^^^

The selected workflow continues across intermediate checkpoints until it completes, needs user input, is stopped, or reaches a configured limit. Agents can use available tools, inspect results and verify work before returning the final response.

Iteration limits apply to internal agent cycles rather than user conversation turns. Reaching a limit may return incomplete work; ``0`` disables the corresponding application-level limit.

Swarm collaboration
^^^^^^^^^^^^^^^^^^^

Swarm workers can exchange messages, share findings and coordinate work while the workflow is running. Peer messages are treated as worker output, not as user instructions or authorization.

Agent Workflows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Open ``Config -> Agent Workflows...`` or use the settings icon in the Agents toolbox. The built-in **Chat**, **Orchestrator**, and **Swarm** profiles cannot be deleted. Their prompts can be customized, while their runtime type remains fixed.

Use **New** to create a custom profile with a name, system prompt, and **Runtime**: **Primary agent**, **Orchestrator**, or **Swarm**. The selected runtime controls how the profile delegates work and which workflow tools are available.

Custom profiles use only the prompt you provide. **From defaults** loads the built-in prompt for the selected runtime as a starting point. Older custom profiles without a runtime setting continue to use **Orchestrator**.

The editor also includes a Help reference for workflow tools and runtime context placeholders.

Agent Workflow monitor
^^^^^^^^^^^^^^^^^^^^^^

The built-in **Agent Workflow** tool provides a real-time view of an active Agents run. It groups the primary agent/orchestrator and worker agents into a readable tree and shows timestamped run events such as status updates, worker creation, task execution and tool calls. Tool rows can be expanded to inspect input/output, and each agent exposes a **Details** panel with the runtime metadata available for that agent, including prompts and task/input information.

Open the monitor from ``Tools -> Agent Workflow`` or pin it as an output tab. It is included in the default second-column tab layout and is revealed automatically on the first actual Agents run.

The monitor is runtime-only. Every new top-level agent run clears the previous view automatically, and **Clear view** can clear it manually. The tool does not replace persisted conversation history, the full-workflow rendering option, or Debug workflow logging.

Project rules with AGENTS.md
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Agents supports optional project-specific instructions in ``AGENTS.md``. Before processing the user's input, the top-level main agent checks for ``%workdir%/AGENTS.md`` in the active conversation's data workdir. If the file exists and is not empty, its UTF-8 content is appended to the main agent system prompt as additional project rules.

The workdir is resolved from the conversation that started the run, including a custom project data workdir, rather than from whichever project happens to be selected later in the UI. The file is read once for that run and is not stored in the conversation database. A symbolic link that resolves outside the active workdir is ignored.

``AGENTS.md`` rules are intentionally applied only to the top-level **Agents** main agent. They are not automatically injected into worker agents or into Experts, even though Experts reuse the Agents v2 runtime. Put shared operational instructions in the main ``AGENTS.md`` and explicitly pass any worker-specific requirements when delegating work.

Tools and provider capabilities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Agents can use both local and provider-side capabilities:

* **Local tools** from enabled PyGPT plugins can be made available to the primary agent/orchestrator and workers.
* **Remote tools** exposed by the selected provider can be made available when supported by the provider/model and enabled in PyGPT.
* Local and remote tools can be enabled or disabled independently in the Agents preset with ``Allow local tools`` and ``Allow remote tools``.
* Models with native function calling use it when available. For compatible models without native function calling, the runtime can use a ReAct agent as a fallback.

Local plugin execution is integrated with the normal PyGPT command/tool system, so enabled plugins can provide filesystem access, Python interpreter, system commands, web search, custom commands, integrations, and other capabilities according to their own configuration and security restrictions.

Settings
^^^^^^^^

Agent-related application settings are available under ``Settings -> Agents and experts``. The **Agents** section contains settings intended for this workflow. ``Show full tool-chain in Agents`` is disabled by default. When enabled, the final response stores and displays the complete chain of normal tool calls performed during the workflow, with a separate expandable Request/Response pair for each tool call. Internal orchestration and worker-management tools are excluded.

The global ``Chats -> Render -> Display tool calls JSON`` option must also be enabled for expandable request/response blocks to be shown. If it is disabled, tool execution remains unchanged and live tool activity is represented by one aggregated ``Tool/Tools`` status row.

``Display full agent workflow`` is disabled by default. When enabled, completed Agents turns keep the full visible sequence of persisted agent partial responses in the chat, followed by the final response, both immediately after completion and after reloading the conversation. When disabled, completed turns are collapsed to the authoritative final response only. This setting controls UI rendering only; it does not change what is stored in the database or the separate ``Restore full workflow history on next request`` policy used for model-facing history.

``Restore full workflow history on next request`` controls how completed Agents turns are replayed to the main agent on later requests. It is enabled by default for backward compatibility. When enabled, PyGPT rebuilds the ordered workflow from durable partials and restores intermediate main-agent output together with persisted worker results. This provides richer continuity but can use substantially more input tokens. When disabled, PyGPT restores only the authoritative final response from each completed Agents turn. The full workflow remains stored in the database and available to the UI; it is simply omitted from later model-facing history, reducing token usage at the cost of less detailed workflow context.

The same policy is used by the live history token estimate and by Advanced Context Handling when it sizes and snapshots durable history for checkpoints. With final-response-only history selected, those checkpoint snapshots use the final response rather than reintroducing the full stored workflow. Compact rolling memory created inside a currently running long workflow remains available so Advanced Context Handling can keep that active run coherent.

The runtime worker-count and iteration limits are configurable in the same section:

* ``Max iterations (Chat / Orchestrator)`` - main-agent iteration limit for Chat and Orchestrator. Default: ``48``.
* ``Max workers (Chat / Orchestrator)`` - maximum number of worker agents that can be created in Chat and Orchestrator workflows. Default: ``16``; set ``0`` for unlimited. This setting does not limit Swarm size.
* ``Max iterations (Swarm)`` - main-agent/orchestrator iteration limit for Swarm. Default: ``4096``.
* ``Worker max iterations`` - per-worker iteration limit in all Agents modes. Default: ``24``.

For every limit, ``0`` means **unlimited**. The three iteration settings control internal agent reasoning/tool-call cycles, not user conversation turns; the worker limit controls how many worker agents may be created in a Chat or Orchestrator workflow. Higher or unlimited values may substantially increase API calls, token consumption, execution time, and tool activity. Swarm keeps its separately declared worker count and is not constrained by the Chat/Orchestrator worker limit.

Options specific to older agent implementations are kept in the **Options** tab. ``Display full agent output in chat view`` controls full output rendering for legacy agent modes, while ``Display a tray notification when the goal is achieved`` controls legacy agent completion notifications. These options do not control the Agents tool-chain display.

RAG, attachments and artifacts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a valid index is selected in the Agents preset, a ``query_index`` RAG tool is exposed to the workflow. User attachments and extracted attachment context are shared with the active workflow and its workers. When the selected model supports image input, current image attachments are also supplied as native image blocks.

Files, images, URLs and attachments produced by workers, local tools, or supported provider-side tools are collected by the runtime and propagated to the main user-visible response.

Memory
^^^^^^

The user-facing primary agent or orchestrator keeps hidden conversation history across turns in the current conversation/preset. This history is subject to the normal PyGPT/model token-window policy. For completed Agents turns, the ``Restore full workflow history on next request`` setting determines whether later requests receive the full persisted workflow or only the final response. Worker memory inside the active workflow is runtime-local and can be retained when the same worker is reused during that workflow.

Worker lifecycle by mode
^^^^^^^^^^^^^^^^^^^^^^^^

**Chat**
   The primary agent delegates individual tasks to workers when useful. The normal interaction remains a direct chat with the primary agent, so the full worker-management lifecycle is not the main user-facing workflow.

**Orchestrator**
   The orchestrator explicitly manages workers with operations for creating, updating, running, inspecting, waiting for, stopping, and removing them. The workflow cannot be finalized while required worker activity remains unresolved.

**Swarm**
   Swarm extends the orchestrator lifecycle with swarm initialization and aggregate swarm-status reporting. The runtime tracks the requested swarm size, numbers workers for status output, and reports collective progress while the swarm is active.

Recommended use cases
^^^^^^^^^^^^^^^^^^^^^

Use **Chat** for general agent conversations and tasks where delegation is occasional. Use **Orchestrator** for controlled multi-stage work such as coding and file operations, research with independent verification, RAG-assisted tasks, implementation plus testing, or workflows that combine several tools. Use **Swarm** only when a task genuinely benefits from many parallel, independent workers and you intentionally want to choose the swarm size yourself.

Agent Skills
^^^^^^^^^^^^

**Agent Skills** extend Agents with reusable ``SKILL.md`` instruction packages containing procedures, references, scripts and assets. Enabled skills are discovered from compact metadata and loaded only when needed. See :doc:`skills` for installation, supported formats, runtime behavior and security notes.

Realtime + audio
----------------
This mode provides native, low-latency voice conversations with **OpenAI Realtime**, **Google Gemini Live**, and **xAI Grok** real-time models. Audio is streamed directly between PyGPT and the selected provider without the regular audio input/output plugins.

The audio toolbox provides two options for controlling voice turns:

* **Auto (VAD)** - enables automatic voice activity detection. While you speak, microphone audio is streamed to the active real-time model/provider, which detects when speech starts and when you stop speaking. The turn is then committed automatically and the model can respond without requiring you to manually stop the recording.
* **Loop** - automatically starts microphone recording again after the model finishes playing its audio response. This enables continuous back-and-forth voice conversation without having to click the microphone button before every next turn. When used together with **Auto (VAD)**, each new turn can start automatically and end automatically when you stop speaking.


Research
--------

## Research

**Research** is a provider-aware mode designed for models and APIs specialized in web research, information gathering, and deep-research workflows. It is intended for tasks that require searching multiple sources, collecting and comparing information, and producing more comprehensive, source-grounded answers.

Depending on the selected model and provider, PyGPT can use Perplexity Sonar research models as well as other provider-specific research paths, including Google Deep Research through the **Interactions API**. The exact workflow, available tools, and research capabilities depend on the selected provider and model.

.. warning::
   Regular tool calls are temporarily disabled in **Research** mode. RAG can still be selected, but support is provider/model-dependent and may not work correctly with some research models or provider-specific research APIs. Verify the response when indexed RAG context is required.


Completion
----------
An older mode of operation that allows working in the standard text completion mode. However, it allows for a bit more flexibility with the text by enabling you to initiate the entire discussion in any way you like.

Similar to chat mode, on the right-hand side of the interface, there are convenient presets. These allow you to fine-tune instructions and swiftly transition between varied configurations and pre-made prompt templates.

Additionally, this mode offers options for labeling the AI and the user, making it possible to simulate dialogues between specific characters - for example, you could create a conversation between Batman and the Joker, as predefined in the prompt. This feature presents a range of creative possibilities for setting up different conversational scenarios in an engaging and exploratory manner.


Image and video generation
--------------------------

**PyGPT** enables quick and easy image and video generation using models such as ``gpt-image``, ``Imagen``, ``Gemini``, ``Nano Banana``, and ``Grok`` for images, as well as ``Veo`` and ``Sora`` for video.

Generating images and videos works similarly to a chat conversation: you provide a prompt, the selected model generates the requested media, and PyGPT downloads, saves, and displays the result in the application. In ``Image and video`` mode, you can either send a raw prompt directly to the model or ask PyGPT to prepare and optimize the prompt for you.


.. image:: images/v3_img.png
   :width: 800


To generate images directly inside a chat, enable **Image generation (inline)** in the Plugins menu.

For supported models/providers, you can also enable remote image generation in ``Config -> Settings -> Remote Tools``. If enabled, image generation is available natively in supported work modes without the inline plugin.

**Tip:** To use ``Imagen`` models you must enable ``Use Vertex AI`` in ``Config -> Settings -> API Keys -> Google -> Advanced options``.

**Remix, Edit, or Extend**

To remix or extend from a previous image or video instead of creating a new one from scratch, enable the ``Remix/Extend`` option checkbox in the toolbox. The last generated image or video in the current context will be used as a reference for your prompt, allowing you to request changes to the generated content. If the ``Remix/Extend`` option is enabled, uploading an image attachment as a reference will not take effect.

**Raw mode**

There is an option for switching prompt generation mode.

If **Raw Mode** is enabled, a model will receive the prompt exactly as you have provided it.
If **Raw Mode** is disabled, a model will generate the best prompt for you based on your instructions.

**Image storage**

Generated images and videos are automatically saved to the working directory, under the ``img`` or ``video`` folder depending on the media type. You can also quickly save generated media to another location, open a preview, view it in full size, or remove it when it is no longer needed.

By default, images are stored in the base-profile ``img`` directory. If **Store images, captures, and uploads in the workdir data directory** is enabled, generated images are stored under the active ``data`` workdir instead, including a custom project data workdir when one is active.

Computer use
-------------

.. warning::
   **Computer use can give the model full control of your computer.** The model can move the mouse, type, click, open applications, read visible content, and perform actions with your user permissions. Use this mode only for tasks you trust and supervise sensitive operations.

Computer use lets supported models operate the desktop or browser through mouse and keyboard actions.


PyGPT uses the selected provider's native ``Computer use`` capability when supported by the current model (OpenAI, Google, or Anthropic), combined with the built-in ``Mouse and keyboard`` integration.

**Example of use:**

.. code-block:: ini

   Click on the Start Menu to open it, search for the Notepad in the list, and run it.

You can change the environment in which the navigation mode operates by using the list at the bottom of the toolbox.

**Available Environments:**

* Browser
* Linux
* Windows
* Mac

You can run this mode in a browser sandbox powered by ``Playwright``. The Playwright package and at least one browser engine must be installed in an environment accessible to PyGPT. For example, to install Chromium:

.. code-block:: ini

   pip install playwright
   playwright install chromium

You can install another supported engine instead with ``playwright install firefox`` or ``playwright install webkit``.

Then open ``Plugins -> Settings -> Mouse and keyboard -> Sandbox (Playwright)`` and configure the sandbox:

* set ``Engine`` to the installed browser engine, for example ``chromium``;
* leave ``Browsers directory`` empty when using Playwright's default browser location, or set it to the custom directory where the Playwright browsers are installed;
* optionally configure ``Headless mode``, browser arguments, home URL and viewport size.

Finally, enable the ``Sandbox`` switch in the Computer use toolbox when you want Computer use to run inside the Playwright browser sandbox.

.. tip::
   **DO NOT** enable the ``Mouse and keyboard`` plugin in ``Computer use`` mode — it is already connected to ``Computer use`` mode in the background.

Experts
-------

**Experts** lets you define reusable, specialized agents as presets and delegate tasks to them from a normal conversation. Experts are powered by regular agents from the same **Agents v2 runtime** that powers **Agents**. There is no separate legacy execution engine for an Expert.

Each enabled Expert is exposed to the current conversation as a regular ``expert_call`` tool. The main model can call it in exactly the same way as other tools: it selects an Expert, passes an instruction, waits for the agent to complete the task, and receives the Expert's final response directly as the tool result.

In **Experts** mode, the main conversation follows the normal **Chat** tool flow. Enabled local tools from plugins and supported remote provider tools remain available according to the usual Chat configuration, while ``expert_call`` adds the ability to delegate work to specialized agents.

Each Expert uses its own preset configuration, including its model/provider, system prompt, local and remote tool permissions, and optional RAG index. Because Experts run on the same runtime as **Agents**, they use the same agent and tool infrastructure. Each Expert also keeps an isolated hidden child context inside the parent conversation, so repeated calls to the same Expert can retain that Expert's own conversation memory without mixing it with the memory of other Experts.

How to use Experts
~~~~~~~~~~~~~~~~~~

1. Switch to **Experts** mode and create or edit an Expert preset. Give it a clear ID/name and specialized instructions, then enable it.
2. Start a conversation in **Experts** mode, or enable the **Experts (inline)** plugin to make the same Experts available in another supported chat mode.
3. Ask the model to use the Expert in natural language. For example:

.. code-block:: ini

   Ask the Python programmer expert to review this code and suggest a fix.

The main model can then invoke ``expert_call`` automatically, use the returned result in its own answer, and call other tools or Experts if the task requires it. You do not need to manually start a separate Expert session. Defining and enabling the Expert is enough for it to become available to the model.

Experts can be activated or deactivated from the preset list using the RMB context menu and the ``Enable/Disable`` actions. Only enabled Experts are exposed through ``expert_call``.

The **Experts (inline)** plugin does not implement a separate Expert engine. It exposes the same ``expert_call`` tool in supported chat modes and executes the selected Expert through the same **Agents / Agents v2** runtime.


Autonomous mode
---------------

``Autonomous mode`` is a single-agent loop for tasks that should continue across multiple model passes without requiring a new user message after every step. The same model keeps working on the original request, reviews the accumulated result, performs additional useful work or verification, and continues until the run is stopped by its configured rules. It does not create or orchestrate worker agents.

The current implementation is **Chat-backed**. Autonomous requests use the same bridge, provider routing, API selection, native tool/function-call settings, and normal tool execution flow as standard ``Chat``.

RAG / index routing
~~~~~~~~~~~~~~~~~~~

Autonomous uses the same global ``RAG`` selector shown at the bottom of the toolbox. If no index is selected, it follows normal Chat routing. Selecting a valid index routes the run through the LlamaIndex RAG runtime with that index. Select ``---`` to keep normal Chat routing.

Run controls
~~~~~~~~~~~~

* **Max run steps (iterations)** limits the number of autonomous model passes. Set it to ``0`` for an unlimited loop. Tool calls and their results are handled inside the normal tool flow and do not represent a separate user turn.
* **Auto-stop** allows the agent to terminate the run early when it determines that the original goal is complete, or when a run-control condition requires stopping. When Auto-stop is disabled, the agent is not given the internal completion-control tool; the loop is then governed by the configured run limit or a manual/application stop.
* **Always continue** keeps the run open-ended and instructs the agent to continue exploring useful in-scope refinements instead of voluntarily finishing. Enabling it automatically disables Auto-stop and ignores the configured iteration limit, so the run continues until it is stopped externally.
* **Dynamic continuous prompt** is enabled by default. After each completed Autonomous pass, PyGPT makes a hidden, tool-free call to the same selected model and uses it as a judge. The judge receives the original user input plus a configurable tail of recent Assistant responses from the current Autonomous run, identifies the highest-value remaining correction, verification, or refinement, and returns only the instruction for the next pass. That instruction is displayed in the live conversation as a localized ``Judge:`` pseudo-input, but it does not create a new user turn. If the judge call fails or returns an empty result, PyGPT falls back to the normal static continuation prompt.
* **Responses to judge** controls how many of the most recent Autonomous Assistant responses are included in that hidden judge request. The original user input is always included. The default is ``3``; set it to ``0`` to include every Assistant response produced since the current user input. Tool rounds belonging to one Autonomous provider pass are grouped into that pass rather than counted as separate judge responses.
* **Auto-stop** and **Always continue** are mutually exclusive. Enabling either one immediately disables the other; both may also be disabled.

When the run limit is set to ``0``, PyGPT shows an infinite-loop confirmation because an unattended run can generate substantial API usage, token consumption, and repeated tool actions.

.. warning::
   Autonomous execution can perform repeated tool calls and external actions. Review enabled plugins and remote tools before starting a long or unlimited run, especially when file access, code/system execution, web actions, or other side effects are available.


Agent (LlamaIndex)
------------------

**Legacy mode — not recommended. Use the newer and more advanced ``Agents`` mode instead.**

This mode provides the older LlamaIndex-based agent workflows.

Includes built-in agents (Workflow):

* FunctionAgent
* ReAct
* Structured Planner (sub-tasks)
* Supervisor + worker


You can create your own types (workflows/patterns) using the built-in visual node-based editor found in the ``Tools -> Agent Builder (Legacy)``.

You can also create your own agent by creating a new provider that inherits from ``pygpt_net.provider.agents.base``.

**Tools and Plugins**

In this mode, all commands from active plugins are available (commands from plugins are automatically converted into tools for the agent on-the-fly).

**RAG - using indexes**

If an index is selected in the agent preset, a tool for reading data from the index is automatically added to the agent, creating a RAG automatically.

This legacy mode supports text input only; multimodal input is not available.

**Loop / Evaluate Mode**

You can run the agent in autonomous mode, in a loop, and with evaluation of the current output. When you enable the ``Loop / Evaluate`` checkbox, after the final response is given, the quality of the answer will be rated on a percentage scale of ``0% to 100%`` by another agent. If the response receives a score lower than the one expected (set using a slider at the bottom right corner of the screen, with a default value ``75%``), a prompt will be sent to the agent requesting improvements and enhancements to the response.

Setting the expected (required) score to ``0%`` means that the response will be evaluated every time the agent produces a result, and it will always be prompted to self-improve its answer. This way, you can put the agent in an autonomous loop, where it will continue to operate until it succeeds.

You can choose between two methods of evaluation:

- By the percentage of tasks completed
- By the accuracy (score) of the final response

You can set the limit of steps in such a loop by going to ``Settings -> Agents and experts -> Legacy agents -> Max evaluation steps in loop``. The default value is ``3``, meaning the agent will only make three attempts to improve or correct its answer. If you set the limit to zero, there will be no limit, and the agent can operate in this mode indefinitely (watch out for tokens!).

You can change the prompts used for evaluating the response in ``Settings -> Prompts -> Agent: response evaluation in loop [LlamaIndex]``. Here, you can adjust it to suit your needs, for example, by defining more or less critical feedback for the responses received.

Agent (OpenAI)
--------------

**Legacy mode — not recommended. Use the newer and more advanced ``Agents`` mode instead.**

This mode provides the older agent workflows built on the ``openai-agents`` library integrated into the application:

https://github.com/openai/openai-agents-python

It allows running agents for OpenAI models and models compatible with the OpenAI.

In this mode, you can use pre-configured Experts in Expert mode presets - they will be launched as agents (in the ``openai_agents_experts`` type, which allows launching one main agent and subordinate agents to which queries will be appropriately directed).

**Agent types (workflows/patterns):**

* ``Agent with experts`` - uses attached experts as sub-agents
* ``Agent with experts + feedback`` - uses attached experts as sub-agents + feedback agent in a loop
* ``Agent with feedback`` - single agent + feedback agent in a loop
* ``Planner`` - planner agent, 3 sub-agents inside: planner, base agent + feedback
* ``Research bot`` - researcher, 3 sub-agents inside: planner, searcher and writer as base agent
* ``Simple agent`` - a single agent.
* ``Evolve`` - in each generation (cycle), the best response from a given parent agent is selected; in the next generation, the cycle repeats.
* ``B2B`` - bot-to-bot communication, involving two bots interacting with each other while keeping a human in the loop.
* ``Supervisor + Worker`` - one agent (supervisor) acts as a bridge between the user and the second agent (worker). The user provides a query to the supervisor, who then sends instructions to the worker until the task is completed by the worker.

You can create your own types (workflows/patterns) using the built-in visual node-based editor found in the ``Tools -> Agent Builder (Legacy)``.

There are also predefined presets added as examples:

* ``Coder``
* ``Experts agent``
* ``Planner``
* ``Researcher``
* ``Simple agent``
* ``Writer with Feedback``
* ``2 bots``
* ``Supervisor + worker``

In the Agents (OpenAI) mode, all remote tools are available for the base agent according to the configuration in the Config -> Settings -> Remote tools menu.

Remote tools for experts can be selected separately for each expert in the preset configuration.

Local tools (from plugins) are available for agents and experts according to the enabled plugins, as in other modes.

In agents with feedback and plans, tools can be allowed in a preset configuration for each agent. They also have separate prompts that can be configured in presets.

**Description of how different types of agents work:**

Below is a pattern for how different types of agents work. You can use these patterns to create agents for different tasks by modifying the appropriate prompts in the preset for the specific task.

**Simple Agent**

* The agent completes its task and then stops working.

**Agent with Feedback**

* The first agent answers a question.
* The second agent (feedback) evaluates the answer and, if necessary, goes back to the first agent to enforce corrections.
* The cycle repeats until the feedback agent is satisfied with the evaluation.

**Agent with Experts**

* The agent completes the assigned task on its own or delegates it to the most suitable expert (another agent).

**Agent with Experts + Feedback**

* The first agent answers a question or delegates it to the most suitable expert.
* The second agent (feedback) evaluates and, if necessary, goes back to the first agent to enforce corrections.
* The cycle repeats until the feedback agent is satisfied with the evaluation.

**Research Bot**

* The first agent (planner) prepares a list of phrases to search.
* The second agent (search) finds information based on the phrases and creates a summary.
* The third agent (writer) prepares a report based on the summary.

**Planner**

* The first agent (planner) breaks down a task into sub-tasks and sends the list to the second agent.
* The second agent performs the task based on the prepared task list.
* The third agent, responsible for feedback, evaluates, requests corrections if needed, and sends the request back to the first agent. The cycle repeats.

**Evolve**

* You select the number of agents (parents) to operate in each generation (iteration).
* Each agent prepares a separate answer to a question.
* The best agent (producing the best answer) in a generation is selected by the next agent (chooser).
* Another agent (feedback) verifies the best answer and suggests improvements.
* A request for improving the best answer is sent to a new pair of agents (new parents).
* From this new pair, the best answer is selected again in the next generation, and the cycle repeats.

**B2B**

* A human provides a topic for discussion.
* Bot 1 generates a response and sends it to Bot 2.
* Bot 2 receives the response from Bot 1 as input, provides an answer, and sends the response back to Bot 1 as its input. This cycle repeats.
* The human can interrupt the loop at any time and update the entire discussion.


**Supervisor + Worker**

* A human provides a query to the Supervisor.
* The Supervisor prepares instructions for the Worker and sends them to the Worker.
* The Worker completes the task and returns the result to the Supervisor.
* If the task is completed, the Supervisor returns the result to the user. If not, the Supervisor sends another instruction to the Worker to complete the task or asks the user if there are any questions.
* The cycle repeats until the task is completed.

.. tip::
   Experts can be assigned and used in these legacy agent workflows where supported.

**Limitations:**

* When the `Computer use` tool is selected for an expert or when the `computer-use` model is chosen, all other tools will not be available for that model.
