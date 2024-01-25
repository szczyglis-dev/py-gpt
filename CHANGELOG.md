# CHANGELOG

# 2.0.118 (2024-01-25)

- Added "Show tray icon" option in "Settings"
- Added launcher arguments
- Updated docs
- Small fixes

# 2.0.117 (2024-01-24)

- Added a new feature to the `Command: Files I/O` plugin - `Get and upload file as attachment`. It lets automatically read files from `data` folder and send them as attachments - just ask to send a file as an attachment and the model will send it to itself (like sending an image for analysis). Option is disabled by default in the plugin`s settings.
- Added a new plugin: `Command: Serial port / USB`. This plugin lets you read and send any commands to USB ports (so you can control robots now ;) ).
- Made it possible to use URLs for images when not using the vision feature.
- Fixed saving and reloading prompts in Assistant mode.
- Removed display of empty external images from the output.

# 2.0.116 (2024-01-24)

- Fixed font color in light themes
- Fixed layout display on Windows systems
- Theme, Language and Debug menus moved to Config menu - feature [#10](https://github.com/szczyglis-dev/py-gpt/issues/10)
- Added Developer section in Settings
- Fixed list options editing
- Refactored code and updated tests

# 2.0.115 (2024-01-22)

- Added token recalculation after the attachments list is changed and upon copy/pasting into the input field.
- Added descriptions to the settings.
- Improved the "Copy selected text to..." option.

# 2.0.114 (2024-01-21)

- Fixed broken CSS on Windows
- Added support for Vector Store databases: `Chroma`, `Elasticsearch`, `Pinecone` and `Redis` (beta)
- Added config options for selecting and configuring Vector Store providers
- Added ability to extend PyGPT with custom Vector Store providers
- Added commands to the `Vision (inline)` plugin: get camera capture and make screenshot. Options must be enabled in the plugin settings. When enabled, they allow the model to capture images from the camera and make screenshots itself.
- Added `Query index only (without chat)` option to `Chat with files` mode.
- Added stream mode support to query index mode in `Chat with files`.

# 2.0.113 (2024-01-20)

- Added %workdir% placeholder to attachments and images files paths storage for more flexibility in moving data between environments
- Refactored base plugin options handling

# 2.0.112 (2024-01-19)

- Fixed image variants slider in image mode
- Fixed vision checkbox visibility
- Fixed user directory path when handling different directories/symlinks
- Added config option for disable opening image dialog after image generate
- Added Scheduled tasks entry in taskbar dropdown
- Added * (asterisk) indicator after date modified if newer than last indexed time
- Date of modified in file explorer changed to format YYYY-MM-DD HH:MM:SS

# 2.0.111 (2024-01-19)

- Fixed: opening files and directories in Snap and Windows versions
- Fixed: camera capture handling between mode switch
- Added: info about snap connect camera in Snap version (if not connected)
- Added: missing app/tray icon in compiled versions

# 2.0.110 (2024-01-19)

- Fixed bug: history file clear on ctx remove - Issue [#9](https://github.com/szczyglis-dev/py-gpt/issues/9)
- Vision inline allowed in modes: Langchain and Chat with files (llama-index)
- Event names moved to Event class

# 2.0.109 (2024-01-18)

- Fixed bug: float inputs value update behaviour - Issue [#8](https://github.com/szczyglis-dev/py-gpt/issues/8)
- Added: plugin description tooltips - Issue [#7](https://github.com/szczyglis-dev/py-gpt/issues/7)
- Added: focus window on "New context..." in tray - Issue [#13](https://github.com/szczyglis-dev/py-gpt/issues/13)
- Added: Ask with screenshot option to tray menu - Issue [#11](https://github.com/szczyglis-dev/py-gpt/issues/11)
- Added: Open Notepad option to tray menu - Issue [#14](https://github.com/szczyglis-dev/py-gpt/issues/14)

# 2.0.108 (2024-01-16)

- Added confirmation dialogs on indexing
- Added missing translations
- Updated dependencies: openai, cryptography, certifi, urllib, jinja

# 2.0.107 (2024-01-16)

- Fixed model change in vision plugin
- Fixed completion API error
- Removed deprecated davinci and replaced with 3.5-turbo-instruct model

# 2.0.106 (2024-01-15)

- Added "undo" action in drawing window
- Refactored locale handling
- Improved locale and theme overriding

# 2.0.105 (2024-01-15)

- Extended `Theme` menu with new options
- `Index (llama-index)` mode changed name to `Chat with files` mode
- Refactored theme controller
- Fixed model config providing to llama-index mode

# 2.0.104 (2024-01-14)

- Langchain support refactored and fixed
- Added editor for models
- Added options for customize arguments and environment vars passed to langchain and llama providers
- Added context length limit in modes: langchain and llama-index
- Models configuration integrated between GPT/Langchain/Llama-index

# 2.0.103 (2024-01-13)

- Llama-index mode, now integrated with context from the database, streaming, plugins, and more, can be utilized as any other mode and is no longer limited to just querying indexes.

# 2.0.102 (2024-01-13)

- Added presets for llama-index mode
- Added custom system prompt in llama-index mode
- Added option to use online data loaders in settings
- Added hiding of chat footer in non-chat tabs
- Added missing libraryfor epub data loader

# 2.0.101 (2024-01-13)

- User interface improvements
- Added help tips

# 2.0.100 (2024-01-13)

- Llama-index integrated with database - you can now indexing all conversations and use them as additional context
- Added support for multiple indexes at once
- Added configuration for llama-indexes
- Data-dir in home directory changed name from 'output' to 'data'

# 2.0.99 (2024-01-12)

- Added configuration sections in settings dialog
- Added translations to file explorer
- Langchain migrated to langchain community
- Config patchers moved to separated classes
- Fixed some UI issues

# 2.0.98 (2024-01-12)

- UI fixes

# 2.0.97 (2024-01-11)

- DALL-E config fix

# 2.0.96 (2024-01-11)

- Added integration with Llama-index (experimental): you can now index/embed files from the data directory and use them as additional data in context.
- Added an inline plugin for Llama-index (allows providing additional context from Llama-index in any chat mode).
- Built-in file loaders: text files, pdf, csv, md, docx, json, epub, xlsx
- Added a new mode: Index (llama-index), it is a mode for querying the index directly.
- Improved DALL-E 3 configuration, 16:9 images set as default, added config option for standard and HD mode.
- Improved drawing mode.

# 2.0.95 (2024-01-10)

- Added capture from camera feature in image drawing mode

# 2.0.94 (2024-01-10)

- Improved drawing: added canvas, image load/save, store and restore drawing on start and more
- Improved dict option editor: added type fields

# 2.0.93 (2024-01-10)

- Added painter (simple image drawing) - it allows to quick draw images and provide them into vision model
- Small UI fixes

# 2.0.92 (2024-01-10)

- Fixed bug with system prompt append from main window
- Added editor for list options (via RMB -> Edit...)
- User/AI names and temperature removed from main window
- UI fixes

# 2.0.91 (2024-01-09)

- Added new plugin: Crontab / Task scheduler: the plugin provides cron-based job scheduling - you can now schedule tasks/prompts to be sent at any time using cron-based syntax for task setup.
- Added combo-box to configuration option types
- Fixed incorrect contexts count in date calculation when timezone is different from UTC
- Fixed incorrect paragraph formatting after command DIV in the last line of response
- Other small fixes and improvements

# 2.0.90 (2024-01-08)

- Fixed config load defaults bug
- Refactored configurations core
- Small UI fixes

# 2.0.89 (2024-01-07)

- Added secondary, extended prompt to autonomous mode configuration (it allows quick switching between standard and more extended reasoning).
- Fixed user input disappearance in history when appending inside autonomous mode.

# 2.0.88 (2024-01-07)

- Added color labels to context items (you can now mark item on list with 'Set label color...' context menu option)
- Improved storage of notepad and calendar items

# 2.0.87 (2024-01-07)

- Fixed paragraph formatting and font color.
- Implemented automatic database backup creation prior to all migrations.
- Added functionality to search contexts using both fields in a single query: search string and date range.

# 2.0.86 (2024-01-07)

- Fixed window state saving on exit
- Added focus on input on creating new context

## 2.0.85 (2024-01-07)

- Improved Autonomous mode
- Added synchronous command execution from plugins, which now allows the Autonomous mode to use the output of other plugins (such as access to the websearch engine, access to filesystem and code execution or generating images in DALL-E) and retrieve and use response from them internally
- Fixed system prompt for Autonomous mode: resolved the problem of command generation interruptions between responses, and incorporated the capability for user to send additional instructions and update goals in real-time
- Fixed loss of selection on the modes and models list in Autonomous mode

## 2.0.84 (2024-01-06)

- The "Self-Loop" plugin has been completely redesigned, improved, and renamed to the Autonomous Mode, which enables the launch of autonomous reasoning in a looped AI-with-AI conversation mode.
- A system prompt option has been added to the plugin configuration with instructions for the autonomous mode.
- Auto-stop after goal is reached option is added also to plugin settings.

## 2.0.83 (2024-01-06)

- Added calendar, day notes (memos) and color labels
- Added context search filter by date (days selected in calendar)
- Added 'clear' icon in search input
- Small fixes and improvements

## 2.0.82 (2024-01-05)

- Plain text append scroll fix

## 2.0.81 (2024-01-05)

- Added Edit context menu option in models list (JSON file edit)
- Fixed link color in light theme css
- Fixed font color restore when switching to plain text

## 2.0.80 (2024-01-05)

- Added Plain Text checkbox at the bottom of chat window
- Removed datetime append when copying text to notepad
- Improved plain-text mode

## 2.0.79 (2024-01-05)

- Fixed bug: notepad save/load content from DB

## 2.0.78 (2024-01-05)

- Improved markdown formatting
- Output text renderers moved to separated modules
- Added plain-text render option in settings
- Vision inline disabled in unsupported modes (Image generation and Assistant) and hidden in Vision (always enabled here)
- Updated OpenAI Chat Completion API

## 2.0.77 (2024-01-05)

- Fixed inline plugins disable when pausing command plugins by unchecking 'Execute commands' checkbox
- Added real-time image appending into chat window when generating images in Image Generation mode
- Added automatic creation of context after deletion from the list when no other context is selected
- Updated docs

## 2.0.76 (2024-01-04)

- Markdown post-process changed from markdown extension to BS4 html parser.

## 2.0.75 (2024-01-04)

- Improved default theme for markdown styling
- Added "Check for updates on start-up" config option in updater dialog
- Added custom CSS stylesheets editor in Config menu
- Added password show/hide in password/secret input fields (click on the right corner of input reveals plain text)
- Fixed JSON files editing (added data reloading after save to prevent overwrite on exit)
- Added tests for plugins and extended tests for core/controllers

## 2.0.74 (2024-01-03)

- Fixed timestamp position when appending input to the chat window.
- Extended the Markdown parser with an extension for converting `li` to `p` (it allows copying lists bullets with Ctrl-C).
- Added notebook titles to the "Copy to..." context menu.
- Added an "Open file" option in the file explorer and attachments list.

## 2.0.73 (2024-01-03)

- Fixed vision prompt appending
- Improved inline vision: removed the "keep" option and added a vision indicator with a checkbox for quickly enabling/disabling the vision model if needed (will auto-enable when an image is provided if the plugin is active)

## 2.0.72 (2024-01-02)

- Fixed markdown / HTML formatting
- Added config option "Use color theme in chat window" in main settings
- Added configuration for system prompt to use with vision in Vision Inline plugin settings

## 2.0.71 (2024-01-01)

- Added Markdown and HTML formatting in the chat window (beta version)
- Added the display of images, files and URLs internally in the chat window
- Added fully integration with images, attachments, and files inside the chat window
- Added vision capture and image generation directly into the chat window (via the DALL-E Inline plugin)
- Improved audio speech generation (eliminated the silence that prematurely truncated the previous audio output before generating the next speech synthesis)

## 2.0.70 (2023-12-31)

- Added commands part strip from speech generation
- Added img check for links sending to vision in auto mode

## 2.0.69 (2023-12-31)

- Added a new plugin: GPT-4 Vision (inline - in any chat). Plugin integrates vision capabilities with any chat mode, not just Vision mode. When the plugin is enabled, the model temporarily switches to vision in the background when an image attachment or vision capture is provided.


## 2.0.68 (2023-12-31)

- Added a new plugin: DALL-E 3 Image Generation (inline) which enables image generation in any chat and mode, seamlessly in the background - just request an image from any model, like GPT-4, and it will generate it "inline."
- User Interface optimizations.
- Added type hints to the code.
- Fixed issue with sending attachments in Assistant mode.

## 2.0.67 (2023-12-30)

- Notepad restore fix

## 2.0.66 (2023-12-30)

- Added "Rename" option to Notepad Tabs (via RMB)
- Improved language switching

## 2.0.65 (2023-12-30)

- Image generation, vision capture and assistants run listeners moved to async threadpool
- Added saving state of scroll value in chat window
- Added search string save and restore
- Added input text save and restore
- Updated tests and code cleanup
- Added translations (only main app): DE, ES, FR, IT, UA 
- Small fixes and optimizations

## 2.0.64 (2023-12-29)

- Commands and plugins execution moved to asynchronous native QT threadpool
- Improved theme switching
- Improved debugger window
- Small fixes and optimizations

# 2.0.63 (2023-12-28)

- Fixed context append bug
- Improved layout resize

## 2.0.62 (2023-12-28)

- Fixed date display on context list
- Added mode display in context tooltips
- Added "Contexts list records limit" config option in settings
- Added tokens calculator tooltips

## 2.0.61 (2023-12-28)

- DALL-E multiple messages in one context fix

## 2.0.60 (2023-12-28)

- Message append fix

## 2.0.59 (2023-12-28)

- Storage of context has been changed from JSON files to SQLite database, automatic migration is included - you will not lose your existing data after update :)
- Added "Search" functionality for contexts and a search input at the bottom.
- Updated contexts now automatically land at the top of the list.
- Added the ability to store more information about each context.
- Integration of searching, utilizing SQLite, and vector database search coming soon.
- Improved DALL-E image generation.

## 2.0.58 (2023-12-27)

- Code refactor
- Added stream response mode to Vision mode
- Added token calculation to Langchain mode
- Optimizations and small fixes

## 2.0.57 (2023-12-26)

- Added threadpool for async workers handling
- Fixed segmentation fault error on app exit
- Refactored class names

## 2.0.56 (2023-12-25)

- Reorganized project structure
- Relative imports changed to absolute imports
- Updated core paths
- Fixed plugin response hanging
- Fixed recursion problem in error logger
- Fixed platform module name

## 2.0.55 (2023-12-25)

- Fixed max model ctx tokens 

## 2.0.54 (2023-12-25)

- Updater new version check moved to post-setup
- Fixed default assistant preset
- Added link to Snap Store to updater window

## 2.0.52 (2023-12-25)

- Added DPI option in settings: enable/disable and scale factor
- Fixed font-size change with mouse scroll on notepad window

## 2.0.51 (2023-12-25)

- Added auto-content truncate before tokens limit exceeded
- Added dynamic max tokens switching
- Fixed real-time tokens calculation

## 2.0.50 (2023-12-25)

- Fixed async logging
- Updated tests

## 2.0.49 (2023-12-24)

- Fixed crash on async command call
- Fixed UI issues
- Added data providers
- Refactored classes

## 2.0.48 (2023-12-23)

- Added custom errors handler with logging.

## 2.0.47 (2023-12-23)

- Added "Copy to Notepad/Input" to the context menu for selected text.
- Added an option to read selected text using speech synthesis in the Notepad window.
- Added a configurable number of notepads.
- Refactored UI classes.
- Added a thread-safe plugin debugger/logger.
- Fixed UI issues.

## 2.0.46 (2023-12-22)

- Improved tokens calculation (added extra tokens from plugins to real-time calculation)
- Added new context menu option to selected text in output/input: "Read with speech synthesis"

## 2.0.45 (2023-12-22)

- Added "light" themes
- Fixed tokens calculation
- Updated tests

## 2.0.44 (2023-12-21)

- Fixed language switch in plugins settings

## 2.0.43 (2023-12-21)

- PyGPT publicated at Snap Store: https://snapcraft.io/pygpt
- Added link to Snap Store in app menu

## 2.0.42 (2023-12-20)

- Audio output library changed to `PyGame` mixer (instead of `PyDub`)
- Added `PyGame` as a dependency and removed `PyDub` and `simpleaudio` dependencies
- Added audio input/output stop immediately on plugin disable

## 2.0.41 (2023-12-20)

- Added "sandbox" feature to the Code Interpreter – it allows the use of any Docker image as an environment for code and commands execution.
- Context auto-summary moved to an async thread.
- Command execution moved to an async thread.

## 2.0.40 (2023-12-19)

- Totally improved material themes support
- Added QSS-configurable themes to chat output window and code highlighter
- Added ability to overriding styles per any theme in user directory
- Fixed UI layout elements
- Fixed DPI issues in Windows systems

## 2.0.39 (2023-12-18)

- Fixed dialogs closing with the Esc key
- Added an indicator for "can append to context in this mode"
- Added functionality to fetch filenames from the API when importing files uploaded to Assistants
- Enabled switching to newly created Assistants after creation
- Optimized class structure

## 2.0.38 (2023-12-18)

- Multi-language support added to plugins
- Implemented feature to override locale and CSS files by overwriting them in the home directory
- Bug fixes

## 2.0.37 (2023-12-18)

- Fixed prompt typing in real-time on the right toolbox
- Added toolbox font change option
- Simplified custom plugins and wrappers for LLMs application (see Docs for more details)
- Bug fixes
- UI fixes

## 2.0.36 (2023-12-18)

- Improved plugins handling
- Added Event Dispatcher and event-based system

## 2.0.35 (2023-12-18)

- Fixed lists focus lost and selection disappearing
- Added clickable links to API keys pages
- Added scroll position store in notepads
- Auto auto-switch to preset after create
- Assistants files and thread moved to external classes
- UI fixes
- Code fixes

## 2.0.34 (2023-12-17)

- Added option "Lock incompatible modes" to prevent mixing of incompatible contexts.
- Added PyPI link to the About menu. 

## 2.0.33 (2023-12-17)

- Fixed dialog's save/update button handlers
- Fixed uploaded files reload in assistants
- Fixed focus loss on assistants list
- Fixed Output Files header
- Fixed UI
- Added delete confirmation to dictionary options
- Added context change lock before response generation
- Added allowed types for contexts
- Added a link to the documentation in the menu
- Added saving state of opened advanced options in plugins
- Disabled mouse scroll on sliders

## 2.0.32 (2023-12-16)

- Added real-time font-size change with CTRL + mouse scroll in input, output and notepad windows
- Increased allowed font-size to 42
- Fixed line display in plugin settings

## 2.0.31 (2023-12-16)

- Speech recognition (Whisper) small fixes, optimization and improvements
- Added advanced internal options to speech recognition config

## 2.0.30 (2023-12-15)

- Speech recognition and synthesis fixes and improvements
- Fixed and improved speech recognition via Whisper
- Fixed and improved voice synthesis via OpenAI TTS and MS Azure
- Added new options to speech recognition: magic words, stop words, auto-send and wait for response
- Added new more intuitive voice input/output control panel in UI

## 2.0.29 (2023-12-14)

- Added config and plugin options getters/setters
- Changed logo
- Small UI fixes

## 2.0.28 (2023-12-14)

- Added new hidden Credentials/API Key field type (asterisks against plain-text)
- Simplified presets editing
- Fixed Assistants function management
- Improved UI
- Improved settings editing

## 2.0.27 (2023-12-14)

- Added specified "url open" command to Web Search plugin
- Added additional advanced options to above plugins
- Improved Web Search and Commands Execution
- Improved updater and config patcher
- Improved command execution logging

## 2.0.26 (2023-12-13)

- Added advanced config options for plugins
- Added additional file operations to Files I/O plugin

## 2.0.25 (2023-12-13)

- Added advanced settings
- Added clear on capture config option
- Added capture quality config option
- Added launcher shortcuts
- Improved plugins
- Improved WebSearch
- Optimized commands response
- Fixed UI issues

## 2.0.24 (2023-12-12)

- Fixed empty string in tokens calculator
- Added attachments reset before auto-capture from camera

## 2.0.23 (2023-12-12)

- Improved python code execution

## 2.0.22 (2023-12-12)

- Fix: env API KEY name for Langchain mode

## 2.0.21 (2023-12-12)

- Simplified assistant configuration
- Added assistant configuration validation
- Improved UI
- Improved language switcher

## 2.0.20 (2023-12-11)

- Improved Assistants API
- Added assistant uploaded files storage
- Added assistant uploaded files management
- Added assistant remote functions management
- Fixed "open in directory" option on Windows in DALL-E image generation
- Improved attachments and file upload management
- Improved UI and more

## 2.0.19 (2023-12-10)

- Optimized DALL-E prompt generator helper

## 2.0.18 (2023-12-10)

- Config fix

## 2.0.17 (2023-12-10)

- Small fixes

## 2.0.16 (2023-12-10)

- Added multiple cameras config
- Added DALL-E prompt generation RAW MODE ON/OFF switch
- Improved camera handling

## 2.0.15 (2023-12-10)

- Added camera release / disable on camera off

## 2.0.14 (2023-12-10)

- Added real-time video capture from camera in "Vision" mode

## 2.0.13 (2023-12-10)

- Fixed path resolving in "open in directory" option on Windows OS
- Added real-time apply of "layout density" (after "save changes" in Settings)
- Default "layout density" changed to 0
- Updated locale

## 2.0.12 (2023-12-09)

- Improved system commands execution

## 2.0.11 (2023-12-09)

- Small fixes

## 2.0.10 (2023-12-09)

- Updated locale

## 2.0.9 (2023-12-09)

- Added `Command: Custom Commands` feature; plugin allows to easily create and execute custom commands
- Added new features to `Command: Files I/O`: downloading files, copying files and dirs, moving files and dirs

## 2.0.8 (2023-12-08)

- Improved Web Search plugin

## 2.0.7 (2023-12-08)

- Improved code execution with Code Interpreter / Files I/O plugins

## 2.0.6 (2023-12-08)

- Added layout density configuration

## 2.0.5 (2023-12-08)

- Added support for external CSS
- Added custom fonts support
- Improved material theme support

## 2.0.4 (2023-12-08)

- Added configuration options for plugins: Files I/O, Code Interpreter
- UI fixes

## 2.0.3 (2023-12-07)

- Python code execution fix

## 2.0.2 (2023-12-07)

- Added python command template settings
- Added layout state restore
- Refactored settings
- Improved settings window
- Bugfixes

## 2.0.1 (2023-12-07)

- Fixed settings dialog initialization
- Fixed models.json migration
- Added enter key behaviour settings
- Added font size settings for input and context list
- Added ctx auto-summary settings
- Added python command plugin settings

## 2.0.0 (2023-12-05)

New features in version 2.0.0:

- Added support for new models: GPT-4 Turbo, GPT-4 Vision, and DALL-E 3
- Integrated Langchain with support for any model it provides
- Assistants API and simple assistant configuration setup
- Vision and image analysis capabilities through GPT-4 Vision
- Image generation with DALL-E 3
- File and attachment support including upload, download, and management
- New built-in notepad feature
- Multiple assistants support
- Command execution support
- Filesystem access allows GPT to read and write files
- Asynchronous (stream) mode added
- Local Python code interpreter that enables code execution by GPT
- System command executions directly from GPT
- Voice synthesis provided via Microsoft Azure TTS and OpenAI TTS (Text-To-Speech)
- Voice recognition provided by OpenAI Whisper
- Automatic summarization of context titles
- Upgraded Web Browser plugin
- More precise token calculation functionality
- Added output markup highlight
- Improved UX
- Bug fixes
- Plus additional enhancements and expanded capabilities

## 0.9.6 (2023.04.16)

- Added real-time logger
- Improved debug mode

## 0.9.5 (2023.04.16)

- Added web plugin (adds access to the Internet using Google Custom Search Engine and Wikipedia API)
- Added voice output plugin (adds voice synthesis using Microsoft Azure)

## 0.9.4 (2023.04.15)

- Added plugins support

## 0.9.3 (2023.04.14)

- Packed into PyPI package

## 0.9.2 (2023.04.12)

- Added theme color settings
- Small UI fixes

## 0.9.1 (2023.04.11)

- Added organization key configuration (by @kaneda2004, PR#1)
- Added config versions patching

## 0.9.0 (2023.04.09)

- Initial release
