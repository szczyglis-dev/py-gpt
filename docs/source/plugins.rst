Plugins
=======

The application can be enhanced with plugins to add new features.

The following plugins are currently available, and GPT can use them instantly:

* ``Command: Google Web Search`` - allows searching the internet via the `Google Custom Search Engine`.
* ``Command: Files I/O`` - grants access to the local filesystem, enabling GPT to read and write files, as well as list and create directories.
* ``Command: Code Interpreter`` - responsible for generating and executing Python code, functioning much like the `Code Interpreter` on `ChatGPT`, but locally. This means GPT can interface with any script, application, or code. The plugin can also execute system commands, allowing GPT to integrate with your operating system. Plugins can work in conjunction to perform sequential tasks; for example, the `Files` plugin can write generated Python code to a file, which the `Code Interpreter` can execute it and return its result to GPT.
* ``Audio Output (Microsoft Azure)`` - provides voice synthesis using the Microsoft Azure Text To Speech API.
* ``Audio Output (OpenAI TTS)`` - provides voice synthesis using the `OpenAI Text To Speech API`.
* ``Audio Input (OpenAI Whisper)`` - offers speech recognition through the `OpenAI Whisper API`.
* ``Self Loop`` - creates a self-loop mode, where GPT can generate a continuous conversation between two AI instances, effectively talking to itself.
* ``Real Time`` - automatically adds the current date and time to prompts, informing the model of the real-time moment.