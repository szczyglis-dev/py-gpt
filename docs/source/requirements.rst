How to Install
===============

Prebuilt binaries
-----------------

**Download PyGPT:** https://pygpt.net/#download

Prebuilt 64-bit packages are the simplest installation option:

* **Windows 10/11** - MSI installer.
* **Linux** - prebuilt archive; requires ``GLIBC >= 2.35``.
* **macOS** - install from PyPI or run from source.

Microsoft Store
---------------

Windows users can also install PyGPT from Microsoft Store:

https://apps.microsoft.com/detail/XP99R4MX3X65VQ

AppImage
--------

Download the latest AppImage from GitHub Releases:

https://github.com/szczyglis-dev/py-gpt/releases

Make it executable before the first run:

.. code-block:: console

    chmod +x ./PyGPT-X.X.X-x86_64.AppImage

Optional incremental updates are available through AppImageUpdate: https://github.com/AppImage/AppImageUpdate

.. code-block:: console

    appimageupdatetool ./PyGPT-X.X.X-x86_64.AppImage

Snap Store
----------

Install PyGPT:

.. code-block:: console

    sudo snap install pygpt

Update an existing installation:

.. code-block:: console

    sudo snap refresh pygpt

Optional Snap interfaces are required only for the corresponding features.

Camera:

.. code-block:: console

    sudo snap connect pygpt:camera

Microphone:

.. code-block:: console

    sudo snap connect pygpt:audio-record :audio-record
    sudo snap connect pygpt:alsa

Audio output:

.. code-block:: console

    sudo snap connect pygpt:audio-playback
    sudo snap connect pygpt:alsa

Docker sandbox:

.. code-block:: console

    sudo snap connect pygpt:docker-executables docker:docker-executables
    sudo snap connect pygpt:docker docker:docker-daemon

Snap Store: https://snapcraft.io/pygpt

PyPI (pip)
-----------

Requires Python ``>=3.10, <3.14``. A virtual environment is recommended:

.. code-block:: console

    python3 -m venv venv
    source venv/bin/activate

Install and run PyGPT:

.. code-block:: console

    pip install pygpt-net
    pygpt

Running from source
-------------------

Clone the repository and install the requirements in a virtual environment:

.. code-block:: console

    git clone https://github.com/szczyglis-dev/py-gpt.git
    cd py-gpt
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python3 run.py

Poetry
``````

Poetry can be used instead of ``pip``:

.. code-block:: console

    git clone https://github.com/szczyglis-dev/py-gpt.git
    cd py-gpt
    pip install poetry
    poetry env use python3.10
    poetry shell
    poetry install
    poetry run python3 run.py

For Poetry >= 2.0, activate the environment with:

.. code-block:: console

    poetry env use python3.10
    poetry env activate

.. tip::
   You can use ``PyInstaller`` to create a compiled version of the application (required version ``6.4.0``).

Troubleshooting
---------------
If you have problems with ``xcb`` plugin with newer versions of PySide on Linux, e.g. like this:

.. code-block:: console

    qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
    This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

...then install libxcb on linux:

.. code-block:: console

    $ sudo apt install libxcb-cursor0

If you have problems with audio on Linux, then try to install ``portaudio19-dev`` and/or ``libasound2``:

.. code-block:: console

    $ sudo apt install portaudio19-dev

.. code-block:: console

    $ sudo apt install libasound2
    $ sudo apt install libasound2-data 
    $ sudo apt install libasound2-plugins


**Snap and AppArmor permission denied**

Snap installs AppArmor profiles for each application by default. The profile for PyGPT is created at:

``/var/lib/snapd/apparmor/profiles/snap.pygpt.pygpt``

The application should work with the default profile; however, if you encounter errors like:

.. code-block:: console

    PermissionError: [Errno 13] Permission denied: '/etc/httpd/conf/mime.types'

add the appropriate access rules to the profile file, for example:

.. code-block:: console

    # /var/lib/snapd/apparmor/profiles/snap.pygpt.pygpt

    ...

    /etc/httpd/conf/mime.types r

and reload the profiles.

Alternatively, you can try removing snap and reinstalling it:

.. code-block:: console

    $ sudo snap remove --purge pygpt

.. code-block:: console

    $ sudo snap install pygpt


**Problems with GLIBC on Linux**

If you encounter error: 

.. code-block:: console

    Error loading Python lib libpython3.10.so.1.0: dlopen: /lib/x86_64-linux-gnu/libm.so.6: version GLIBC_2.35 not found (required by libpython3.10.so.1.0)

when trying to run the compiled version for Linux, try updating GLIBC to version ``2.35``, or use a newer operating system that has at least version ``2.35`` of GLIBC.

**Access to microphone and audio in Windows version:**

If you have problems with audio or microphone in the non-binary PIP/Python version on Windows, check to see if FFmpeg is installed. If it's not, install it and add it to the PATH. You can find a tutorial on how to do this here: https://phoenixnap.com/kb/ffmpeg-windows. The binary version already includes FFmpeg.

**Windows and VC++ Redistributable**

On Windows, the proper functioning requires the installation of the ``VC++ Redistributable``, which can be found on the Microsoft website:

https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist

The libraries from this environment are used by ``PySide6`` - one of the base packages used by PyGPT.
The absence of the installed libraries may cause display errors or completely prevent the application from running.

It may also be necessary to add the path ``C:\path\to\venv\Lib\python3.x\site-packages\PySide6`` to the ``PATH`` variable.

**WebEngine/Chromium renderer and OpenGL problems**

If you have problems with ``WebEngine / Chromium`` renderer you can try to disable OpenGL hardware acceleration by launching the app with command line arguments:

.. code-block:: console

    $ python3 run.py --disable-gpu=1


You can also manually disable hardware acceleration by editing config file - open the ``%WORKDIR%/config.json`` config file in editor and set the following options:

.. code-block:: json

    "render.open_gl": false,

Other requirements
------------------
For API-based models, an internet connection and the appropriate provider API key are required. Models from OpenAI, Google, Anthropic, and xAI require API keys for their respective providers. Local models, such as those served through Ollama, do not require external API keys.

Debugging and logging
---------------------

Please go to ``Debugging and Logging`` section for instructions on how to log and diagnose issues in a more detailed manner.
