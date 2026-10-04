"""Run PyGPT with the tutorial Python extensions registered directly.

This is the development alternative to packaging/installing an external Add-on.
Run it from the repository root after installing PyGPT's dependencies::

    python examples/custom_launcher.py

Static theme/locale packages are not registered through ``run()``; install those
with Config -> Install Add-on... so the normal theme/locale loaders can see them.
"""

from pygpt_net.app import run

from examples.addons.agents.example_agent.agent import ExampleAgent
from examples.addons.audio_input.example_audio_input.provider import ExampleAudioInput
from examples.addons.audio_output.example_audio_output.provider import ExampleAudioOutput
from examples.addons.llms.example_llm.provider import ExampleLLM
from examples.addons.loaders.example_loader.loader import ExampleLoader
from examples.addons.file_previews.example_file_preview.preview import ExampleFilePreview
from examples.addons.plugins.example_plugin.plugin import ExamplePlugin
from examples.addons.tools.example_tool.tool import ExampleTool
from examples.addons.vector_stores.example_vector_store.provider import ExampleVectorStore
from examples.addons.web.example_web.provider import ExampleWeb


if __name__ == "__main__":
    run(
        plugins=[ExamplePlugin()],
        llms=[ExampleLLM()],
        vector_stores=[ExampleVectorStore()],
        loaders=[ExampleLoader()],
        file_previews=[ExampleFilePreview()],
        audio_input=[ExampleAudioInput()],
        audio_output=[ExampleAudioOutput()],
        web=[ExampleWeb()],
        agents=[ExampleAgent()],
        tools=[ExampleTool()],
    )
