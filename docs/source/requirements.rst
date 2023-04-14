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
extract it. Then run the application by running the "pygpt" binary file in the
root directory.

Python version
---------------
The second way to run is to download the source code from GitHub and run
the application using the Python interpreter (at least version 3.9).
You can also install application from PyPi (using "pip install").

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

Other requirements
------------------
To operate, you need an Internet connection (for API connection), registered OpenAI account and an active API key, which must be entered in the program.

