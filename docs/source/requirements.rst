Requirements and installation
==============================

Compiled binary versions
------------------------
**PyGPT** requires a PC with Windows 10, 11 or Linux. Just download the installer or
archive with the appropriate version from the download page and then extract it
or install it and run the application.

Windows 10, 11 (64-bit)
```````````````````````
The application is available for 64-bit Windows 10, 11 in the form of an MSI installer.
The installer will automatically install all required dependencies and create
a shortcut on the desktop. Just download the installer from the download page and
run it

Linux (64-bit)
``````````````
The application is available for 64-bit Linux in the form of an archive with
all required dependencies. Just download the archive from the download page and
extract it. Then run the application by running the ``pygpt`` binary file in the
root directory.

Snap Store
-----------
You can install **PyGPT** directly from Snap Store:

.. code-block:: console

    sudo snap install pygpt


To manage future updates just use:

.. code-block:: console

    sudo snap refresh pygpt


**Using camera:** to use camera in Snap version you must connect the camera with interface:

.. code-block:: console

    snap connect pygpt:camera


**Using microphone:** to use microphone in Snap version you must connect the microphone with:

.. code-block:: console

    sudo snap connect pygpt:audio-record :audio-record


**Snap Store:** https://snapcraft.io/pygpt

Python version
---------------
The second way to run is to download the source code from GitHub and run
the application using the Python interpreter (>=3.10, <3.12).
You can also install application from PyPi (using ``pip install``) and we recommend this type of installation.

PyPi (pip)
```````````

1. Create a new virtual environment:

.. code-block:: console

    python3 -m venv venv
    source venv/bin/activate

2. Install from PyPi:

.. code-block:: console

    pip install pygpt-net

3. Once installed run the command to start the application:

.. code-block:: console

    pygpt


Running from GitHub source code
````````````````````````````````
1. Clone git repository or download .zip file:

.. code-block:: console

    git clone https://github.com/szczyglis-dev/py-gpt.git
    cd py-gpt

2. Create virtual environment:

.. code-block:: console

    python3 -m venv venv
    source venv/bin/activate

3. Install requirements:

.. code-block:: console

    pip install -r requirements.txt

4. Run the application:

.. code-block:: console

    python3 run.py

**Install with Poetry**

1. Clone git repository or download .zip file:

.. code-block:: console

    git clone https://github.com/szczyglis-dev/py-gpt.git
    cd py-gpt

2. Install Poetry (if not installed):

.. code-block:: console

    pip install poetry

3. Create a new virtual environment that uses Python 3.10:

.. code-block:: console
    
    poetry env use python3.10
    poetry shell

4. Install requirements:

.. code-block:: console

    poetry install

5. Run the application:

.. code-block:: console

    poetry run python3 run.py


**Tip**: you can use ``PyInstaller`` to create a compiled version of
the application for your system (required version >= ``6.0.0``).

Troubleshooting
---------------
If you have a problems with xcb plugin with newer versions of PySide on Linux, e.g. like this:

.. code-block:: console

    qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
    This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

...then install libxcb on linux:

.. code-block:: console

    sudo apt install libxcb-cursor0

If you have a problems with audio on Linux, then try to install ``portaudio19-dev`` and/or ``libasound2``:

.. code-block:: console

    sudo apt install portaudio19-dev

.. code-block:: console

    sudo apt install libasound2
    sudo apt install libasound2-data 
    sudo apt install libasound2-plugins


**Access to camera in Snap version:**

To use camera in Vision mode in Snap version you must connect the camera with:

.. code-block:: console

    sudo snap connect pygpt:camera

**Access to microphone in Snap version:**

To use microphone in Snap version you must connect the microphone with:

.. code-block:: console

    sudo snap connect pygpt:audio-record :audio-record


**Windows and VC++ Redistributable**

On Windows, the proper functioning requires the installation of the ``VC++ Redistributable``, which can be found on the Microsoft website:

https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist

The libraries from this environment are used by ``PySide6`` - one of the base packages used by PyGPT. 
The absence of the installed libraries may cause display errors or completely prevent the application from running.

It may also be necessary to add the path ``C:\path\to\venv\Lib\python3.x\site-packages\PySide6`` to the ``PATH`` variable.


**WebEngine/Chromium renderer and OpenGL problems**

If you have a problems with ``WebEngine / Chromium`` renderer you can force the legacy mode by launching the app with command line arguments:

.. code-block:: console

    python3 run.py --legacy=1

and to force disable OpenGL hardware acceleration:

.. code-block:: console

    python3 run.py --disable-gpu=1


You can also manualy enable legacy mode by editing config file - open the ``%WORKDIR%/config.json`` config file in editor and set the following options:

.. code-block:: json

    // config.json
    "render.engine": "legacy",
    "render.open_gl": false,

Other requirements
------------------
For operation, an internet connection is needed (for API connectivity), a registered OpenAI account, 
and an active API key that must be input into the program.

Debugging and logging
---------------------

**Tip:** Go to ``Debugging and Logging`` section for instructions on how to log and diagnose issues in a more detailed manner.
