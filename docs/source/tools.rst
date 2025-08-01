Tools
=====

PyGPT features several useful tools, including:

* Notepad
* Calendar
* Painter
* Indexer
* Media Player
* Image Viewer
* Text Eeditor
* Transcribe Audio/Video Files
* Python Code Interpreter
* HTML/JS Canvas (built-in HTML renderer)

.. image:: images/v2_tool_menu.png
   :width: 400

Notepad
-------

The application has a built-in notepad, divided into several tabs. This can be useful for storing information in a convenient way, without the need to open an external text editor. The content of the notepad is automatically saved whenever the content changes.

.. image:: images/v2_notepad.png
   :width: 600

Painter
-------

Using the ``Painter`` tool, you can create quick sketches and submit them to the model for analysis. You can also edit open or camera-captured images, for example, by adding elements like arrows or outlines to objects. Additionally, you can capture screenshots from the system - the captured image is placed in the drawing tool and attached to the query being sent.

.. image:: images/v2_draw.png
   :width: 800

To quick capture the screenshot click on the option ``Ask with screenshot`` in tray-icon dropdown:

.. image:: images/v2_screenshot.png
   :width: 300


Calendar
--------

Using the calendar, you can go back to selected conversations from a specific day and add daily notes. After adding a note, it will be marked on the list, and you can change the color of its label by right-clicking and selecting ``Set label color`` option. By clicking on a particular day of the week, conversations from that day will be displayed.

.. image:: images/v2_calendar.png
   :width: 800


Indexer
-------

This tool allows indexing of local files or directories and external web content to a vector database, which can then be used with the ``Chat with Files`` mode. Using this tool, you can manage local indexes and add new data with built-in ``LlamaIndex`` integration.

.. image:: images/v2_tool_indexer.png
   :width: 800


Media Player
------------

A simple video/audio player that allows you to play video files directly from within the app.


Image Viewer
------------

A simple image browser that lets you preview images directly within the app.


Text Editor
-----------

A simple text editor that enables you to edit text files directly within the app.


Transcribe Audio/Video Files
-----------------------------

An audio transcription tool with which you can prepare a transcript from a video or audio file. It will use a speech recognition plugin to generate the text from the file.


Python Code Interpreter
-----------------------

This tool allows you to run Python code directly from within the app. It is integrated with the ``Code Interpreter`` plugin, ensuring that code generated by the model is automatically available from the interpreter. In the plugin settings, you can enable the execution of code in a Docker environment.

**INFO:** Executing Python code using IPython in compiled versions requires an enabled sandbox (Docker container). You can connect the Docker container via ``Plugins -> Settings``.

HTML/JS Canvas
---------------

Allows to render HTML/JS code in HTML Canvas (built-in renderer based on Chromium). To use it, just ask the model to render the HTML/JS code in built-in browser (HTML Canvas). Tool is integrated with the ``Code Interpreter`` plugin.