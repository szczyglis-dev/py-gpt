# PyGPT custom launcher example.

from pygpt_net.app import run  # <-- import the "run" function from the app

from example_plugin import Plugin as ExamplePlugin
from example_llm import ExampleLlm
from example_vector_store import ExampleVectorStore
from example_data_loader import ExampleDataLoader

"""
Extending PyGPT with custom plugins, LLM wrappers, vector stores, and data loaders:

- You can pass custom plugin, LLM wrappers, vector store providers, and data loader instances to the launcher.
- This is useful if you want to extend PyGPT with your own plugins, vectors storage, data loaders, or LLMs.

First, create a custom launcher file, for example, "my_launcher.py," and register your extensions in it.

To register custom plugin:

- Pass a list with the plugin instances as the "plugins" keyword argument.

To register custom LLM wrapper:

- Pass a list with the LLM wrapper instances as the "llms" keyword argument.

To register custom vector store provider:

- Pass a list with the vector store provider instances as the "vector_stores" keyword argument.

To register custom data loader:

- Pass a list with the data loader instances as the "loaders" keyword argument.

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

# 1. Prepare instances of your custom plugins, LLMs, vector stores, and data loaders:

plugins = [
    ExamplePlugin(),  # add your custom plugin instances here
]
llms = [
    ExampleLlm(),  # add your custom LLM wrappers instances here
]
vector_stores = [
    ExampleVectorStore(),  # add your custom vector store instances here
]
loaders = [
    ExampleDataLoader(),  # add your custom data loader instances here
]

# 2. Register example plugins, LLM wrappers, vector stores, and data loaders using the run function:

run(
    plugins=plugins,  # pass the list with the plugin instances
    llms=llms,  # pass the list with the LLM provider instances
    vector_stores=vector_stores,  # pass the list with the vector store instances
    loaders=loaders,  # pass the list with the data loader instances
)

if __name__ == '__main__':
    run()

# 3. Run the app using this custom launcher instead of the default one:

"""
    $ source venv/bin/activate
    $ python3 custom_launcher.py
"""
