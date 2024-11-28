Debugging and Logging
======================

In ``Settings -> Developer`` dialog, you can enable the ``Show debug menu`` option to turn on the debugging menu. The menu allows you to inspect the status of application elements. In the debugging menu, there is a ``Logger`` option that opens a log window. In the window, the program's operation is displayed in real-time.

**Logging levels**:

By default, all errors and exceptions are logged to the file:

.. code-block:: ini

	{HOME_DIR}/.config/pygpt-net/app.log

To increase the logging level (``ERROR`` level is default), run the application with ``--debug`` argument:

.. code-block:: ini

	python3 run.py --debug=1

or

.. code-block:: ini

	python3 run.py --debug=2

* The value ``1`` enables the ``INFO`` logging level.
* The value ``2`` enables the ``DEBUG`` logging level (most information).


**Compatibility (legacy) mode**

If you have a problems with `WebEngine / Chromium` renderer you can force the legacy mode by launching the app with command line arguments:

.. code-block:: console

    python3 run.py --legacy=1

and to force disable OpenGL hardware acceleration:

.. code-block:: console

    python3 run.py --disable-gpu=1

You can also manualy enable legacy mode by editing config file - open the ``%WORKDIR%/config.json`` config file in editor and set the following options:

.. code-block:: json

    "render.engine": "legacy",
    "render.open_gl": false,