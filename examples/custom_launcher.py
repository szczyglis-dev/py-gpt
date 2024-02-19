# PyGPT custom launcher example.

from pygpt_net.app import run  # <-- import the run function from the app

from example_plugin import Plugin as ExamplePlugin
from example_llm import ExampleLlm
from example_vector_store import ExampleVectorStore
from example_data_loader import ExampleDataLoader

"""
Extending PyGPT with custom plugins, LLMs wrappers, vector stores and data loaders

- You can pass custom plugin instances, LLMs wrappers and vector store providers to the launcher.
- This is useful if you want to extend PyGPT with your own plugins, vectors storage and LLMs.

To register custom plugins create custom launcher, e.g. "my_launcher.py" and:

- Pass a list with the plugin instances as 'plugins' keyword argument.

To register custom LLMs wrappers:

- Pass a list with the LLMs wrappers instances as 'llms' keyword argument.

To register custom vector store providers:

- Pass a list with the vector store provider instances as 'vector_stores' keyword argument.

To register custom data loaders:

- Pass a list with the data loader instances as 'loaders' keyword argument.

Example:
--------
::

    # my_launcher.py

    from pygpt_net.app import run
    from my_plugins import MyCustomPlugin, MyOtherCustomPlugin
    from my_llms import MyCustomLLM
    from my_vector_stores import MyCustomVectorStore
    from my_loaders import MyCustomLoader

    plugins = [
        MyCustomPlugin(),
        MyOtherCustomPlugin(),
    ]
    llms = [
        MyCustomLLM(),
    ]
    vector_stores = [
        MyCustomVectorStore(),
    ]
    loaders = [
        MyCustomLoader(),
    ]

    run(
        plugins=plugins,
        llms=llms,
        vector_stores=vector_stores,
        loaders=loaders
    )

"""

# Working example:

# 1. Prepare instances of your custom plugins, LLMs, vector stores and data loaders:

plugins = [
    ExamplePlugin(),  # add your custom plugin instances here
]
llms = [
    ExampleLlm(),  # add your custom LLM instances here
]
vector_stores = [
    ExampleVectorStore(),  # add your custom vector store instances here
]
loaders = [
    ExampleDataLoader(),
]

# 2. Register example plugins, LLMs, vector stores and data loaders to the PyGPT launcher using the run function:

run(
    plugins=plugins,  # pass the list with the plugin instances
    llms=llms,  # pass the list with the LLM provider instances
    vector_stores=vector_stores,  # pass the list with the vector store instances
    loaders=loaders  # pass the list with the data loader instances
)

if __name__ == '__main__':
    run()

# 3. Run the app using this custom launcher instead of the default one:

"""
    $ source venv/bin/activate
    $ python3 custom_launcher.py
"""
