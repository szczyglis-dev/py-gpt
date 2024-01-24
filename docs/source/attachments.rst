Files and attachments
=====================

Input (upload)
-------
**PyGPT** makes it simple for users to upload files to the server and send them to the model for tasks like analysis, similar to attaching files in ````ChatGPT````. There's a separate ```Files`` tab next to the text input area specifically for managing file uploads. Users can opt to have files automatically deleted after each upload or keep them on the list for repeated use.

The attachment feature is available in both the ``Assistant`` and ``Vision`` modes at default.
In ``Assistant`` mode, you can send documents and files to analyze, while in ``Vision`` mode, you can send images.
In other modes, you can enable attachments by activating the ``Vision (inline)`` plugin (for providing images only).

.. image:: images/v2_file_input.png
   :width: 800



Output (download, generation)
-----------------------------
**PyGPT** enables the automatic download and saving of files created by the model. This is carried out in the background, with the files being saved to an ``data`` folder located within the user's working directory. To view or manage these files, users can navigate to the ``Files`` tab which features a file browser for this specific directory. Here, users have the interface to handle all files sent by the AI.

This ``data`` directory is also where the application stores files that are generated locally by the AI, such as code files or any other outputs requested from the model. Users have the option to execute code directly from the stored files and read their contents, with the results fed back to the AI. This hands-off process is managed by the built-in plugin system and model-triggered commands. You can also indexing files from this directory (using integrated Llama-index) and use it's contents as additional context provided to discussion.

The ``Command: Files I/O`` plugin takes care of file operations in the ``data`` directory, while the ``Command: Code Interpreter`` plugin allows for the execution of code from these files.

.. image:: images/v2_file_output.png
   :width: 800

To allow the model to manage files or python code execution, the ``Execute commands`` option must be active, along with the above-mentioned plugins:

.. image:: images/v2_code_execute.png
   :width: 400


Draw (paint)
=============

Using the ``Draw`` tool, you can create quick sketches and submit them to the model for analysis. You can also edit open or camera-captured images, for example, by adding elements like arrows or outlines to objects. Additionally, you can capture screenshots from the system - the captured image is placed in the drawing tool and attached to the query being sent.

.. image:: images/v2_draw.png
   :width: 800

To quick capture the screenshot click on the option ``Ask with screeshot`` in tray-menu dropdown:

.. image:: images/v2_screenshot.png
   :width: 400


Calendar
=========

Using the calendar, you can go back to selected conversations from a specific day and add daily notes. After adding a note, it will be marked on the list, and you can change the color of its label by right-clicking and selecting Set label color. By clicking on a particular day of the week, conversations from that day will be displayed.

.. image:: images/v2_calendar.png
   :width: 800