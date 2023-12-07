Files and attachments
=====================

Input (upload)
-------
**PYGPT** makes it simple for users to upload files to the server and send them to the model for tasks like analysis, similar to attaching files in ``ChatGPT``. There's a separate ``Files`` tab next to the text input area specifically for managing file uploads. Users can opt to have files automatically deleted after each upload or keep them on the list for repeated use.

The attachment feature is available in both the ``Assistant`` and ``Vision`` modes.

.. image:: images/v2_file_input.png
   :width: 800



Output (download, generation)
---------------
**PYGPT** enables the automatic download and saving of files created by the model. This is carried out in the background, with the files being saved to an ``output`` folder located within the user's working directory. To view or manage these files, users can navigate to the ``Output`` tab which features a file browser for this specific directory. Here, users have the interface to handle all files sent by the AI.

This ``output`` directory is also where the application stores files that are generated locally by the AI, such as code files or any other outputs requested from the model. Users have the option to execute code directly from the stored files and read their contents, with the results fed back to the AI. This hands-off process is managed by the built-in plugin system and model-triggered commands.

The ``Command: Files I/O`` plugin takes care of file operations in the ``output`` directory, while the ``Command: Code Interpreter`` plugin allows for the execution of code from these files.

.. image:: images/v2_file_output.png
   :width: 800

To allow the model to manage files or python code execution, the ``Execute commands`` option must be active, along with the above-mentioned plugins:

.. image:: images/v2_code_execute.png
   :width: 400