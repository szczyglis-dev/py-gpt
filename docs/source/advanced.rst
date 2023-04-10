Advanced configuration
======================

Manual configuration
---------------------
You can manually edit configuration files in the directory:

.. code-block:: ini

   {HOME_DIR}/.config/pygpt-net/


| - **config.json** - contains the main configuration

| - **models.json** - contains models configuration

| - **context.json** - contains an index of contexts

| - **context** - directory with contexts, ``.json`` files

| - **history** - directory with history, ``.txt`` files

| - **img** - directory with images generated with DALL-E, ``.png`` files

| - **presets** - directory with presets, ``.json`` files


Translations / locale
-----------------------
``ini`` files with locales are placed in the directory:

.. code-block:: ini

   ./data/locale


Above directory is automatically read when the application starts - prepare your own new translation and save it under a name, e.g.:

.. code-block:: ini

   locale.es.ini  


will automatically add the language to the language selection menu in the application.