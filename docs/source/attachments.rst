Files and Attachments
=====================

Uploading attachments
---------------------

**Using Your Own Files as Additional Context in Conversations**

You can use your own files (for example, to analyze them) during any conversation. You can do this in two ways: by indexing (embedding) your files in a vector database, which makes them available all the time during a "Chat with Files" session, or by adding a file attachment (the attachment file will only be available during the conversation in which it was uploaded).

**Attachments**

.. warning::

   **Important**: When using ``Full context`` mode, the entire content of the file is included in the prompt, which can result in high token usage each time. If you want to reduce the number of tokens used, instead use the ``RAG`` option, which will only query the indexed attachment in the vector database to provide additional context.

**PyGPT** makes it simple for users to upload files and send them to the model for tasks like analysis, similar to attaching files in ``ChatGPT``. There's a separate ``Attachments`` tab next to the text input area specifically for managing file uploads. 

.. image:: images/v2_file_input.png
   :width: 800

You can use attachments to provide additional context to the conversation. Uploaded files will be converted into text using loaders from LlamaIndex. You can upload any file format supported by the application through LlamaIndex. Supported formats include:

Text-based types:

* CSV files (csv)
* Epub files (epub)
* Excel .xlsx spreadsheets (xlsx)
* HTML files (html, htm)
* IPYNB Notebook files (ipynb)
* JSON files (json)
* Markdown files (md)
* PDF documents (pdf)
* Plain-text files (txt and etc.)
* Word .docx documents (docx)
* XML files (xml)

Media-types:

* Image (using vision) (jpg, jpeg, png, gif, bmp, tiff, webp)
* Video/audio (mp4, avi, mov, mkv, webm, mp3, mpeg, mpga, m4a, wav)

Archives:

* zip
* tar, tar.gz, tar.bz2

The content from the uploaded attachments will be used in the current conversation and will be available throughout (per context). There are 3 modes available for working with additional context from attachments:

- ``Full context``: Provides best results. This mode attaches the entire content of the read file to the user's prompt. This process happens in the background and may require a large number of tokens if you uploaded extensive content.

- ``RAG``: The indexed attachment will only be queried in real-time using LlamaIndex. This operation does not require any additional tokens, but it may not provide access to the full content of the file 1:1.

- ``Summary``: When queried, an additional query will be generated in the background and executed by a separate model to summarize the content of the attachment and return the required information to the main model. You can change the model used for summarization in the settings under the ``Files and attachments`` section.

In the ``RAG`` and ``Summary`` mode, you can enable an additional setting by going to ``Settings -> Files and attachments -> Whole conversation for RAG query``. This allows for better preparation of queries for RAG. When this option is turned on, the entire conversation context is considered, rather than just the user's last query. This allows for better searching of the index for additional context. In the ``RAG limit`` option, you can set a limit on how many recent entries in a discussion should be considered (``0 = no limit, default: 5``).

**Images as Additional Context**

Files such as jpg, png, and similar images are a special case. By default, images are not used as additional context; they are analyzed in real-time using a vision model. If you want to use them as additional context instead, you must enable the "Allow images as additional context" option in the settings: ``Files and attachments -> Allow images as additional context``.

**Uploading larger files and auto-index**

To use the ``RAG`` mode, the file must be indexed in the vector database. This occurs automatically at the time of upload if the ``Auto-index on upload`` option in the ``Attachments`` tab is enabled. When uploading large files, such indexing might take a while - therefore, if you are using the ``Full context`` option, which does not use the index, you can disable the ``Auto-index`` option to speed up the upload of the attachment. In this case, it will only be indexed when the ``RAG`` option is called for the first time, and until then, attachment will be available in the form of ``Full context`` and ``Summary``.

Downloading files
-----------------

**PyGPT** enables the automatic download and saving of files created by the model. This is carried out in the background, with the files being saved to an ``data`` folder located within the user's working directory. To view or manage these files, users can navigate to the ``Files`` tab which features a file browser for this specific directory. Here, users have the interface to handle all files sent by the AI.

This ``data`` directory is also where the application stores files that are generated locally by the AI, such as code files or any other outputs requested from the model. Users have the option to execute code directly from the stored files and read their contents, with the results fed back to the AI. This hands-off process is managed by the built-in plugin system and model-triggered commands. You can also indexing files from this directory (using integrated ``LlamaIndex``) and use it's contents as additional context provided to discussion.

The ``Files I/O`` plugin takes care of file operations in the ``data`` directory, while the ``Code Interpreter`` plugin allows for the execution of code from these files.

.. image:: images/v2_file_output.png
   :width: 800

To allow the model to manage files or python code execution, the ``+ Tools`` option must be active, along with the above-mentioned plugins:

.. image:: images/v2_code_execute.png
   :width: 400