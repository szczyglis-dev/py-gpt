Requirements and installation
==============================

Compiled binary version
-----------------
PYGPT requires a PC with Windows 10, 11 or Linux. Just download the installer or
archive with the appropriate version from the download page and then extract it
or install it and run the application.

Windows 10, 11 (64-bit)
```````
The application is available for 64-bit Windows 10, 11 in the form of an MSI installer.
The installer will automatically install all required dependencies and create
a shortcut on the desktop. Just download the installer from the download page and
run it

Linux (64-bit)
`````
The application is available for 64-bit Linux in the form of an archive with
all required dependencies. Just download the archive from the download page and
extract it. Then run the application by running the ``pygpt`` binary file in the
root directory.

Python version
---------------
The second way to run is to download the source code from GitHub and run
the application using the Python interpreter (at least version 3.9).
You can also install application from PyPi (using ``pip install``) and we recommend this type of installation.

PyPi (pip)
```````````

1. Create virtual environment:

.. code-block:: console

    python -m venv venv
    source venv/bin/activate

2. Install from PyPi:

.. code-block:: console

    pip install pygpt-net

3. Once installed run the command to start the application:

.. code-block:: console

    pygpt


Troubleshooting
---------------

If you have problems with xcb plugin with newer versions of PySide on Linux, e.g. like this:

.. code-block:: console

    qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
    This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

...then install libxcb on linux:

.. code-block:: console

    sudo apt install libxcb-cursor0

If this not help then try to downgrade PySide to ``PySide6-Essentials==6.4.2``:


.. code-block:: console

    pip install PySide6-Essentials==6.4.2

Running from GitHub source code
````````````````````````````````
1. Clone git repository or download .zip file:

.. code-block:: console

    git clone https://github.com/szczyglis-dev/py-gpt.git
    cd py-gpt

2. Create virtual environment:

.. code-block:: console

    python -m venv venv
    source venv/bin/activate

3. Install requirements:

.. code-block:: console

    pip install -r requirements.txt

4. Run the application:

.. code-block:: console

    cd src/pygpt_net
    python app.py

**Tip**: you can use ``PyInstaller`` to create a compiled version of
the application for your system.

Other requirements
------------------
For operation, an internet connection is needed (for API connectivity), a registered OpenAI account, 
and an active API key that must be input into the program.

