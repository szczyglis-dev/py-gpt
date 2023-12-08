from setuptools import setup, find_packages

VERSION = '2.0.6'
DESCRIPTION = 'AI Desktop Assistant powered by GPT-4, GPT-4V, GPT-3, Whisper, TTS and DALL-E 3 with chat, assistant, text completion, ' \
              'vision and image generation'
LONG_DESCRIPTION = 'A package containing a GPT-4, GPT-4V, GPT-3, Whisper, TTS and DALL-E 3 AI desktop assistant, chatbot, ' \
                   'text completion, vision and image generation app, using OpenAI API and your own API ' \
                   'Key. It includes context memory and history, editable presets, customizable UI and more. '

setup(
    name='pygpt-net',
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    license='MIT',
    author="Marcin Szczygliński",
    author_email='info@pygpt.net',
    maintainer="Marcin Szczygliński",
    maintainer_email='info@pygpt.net',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'': ['CHANGELOG.txt', 'data/*', 'data/locale/*', 'data/config/*', 'data/config/presets/*']},
    url='https://github.com/szczyglis-dev/py-gpt',
    keywords='py_gpt, py-gpt, pygpt, desktop, app, gpt, gpt4, gpt4-v, gpt3, gpt-4, gpt-3, tts, whisper, vision, chatgpt, dall-e, '
             'chat, chatbot, assistant, text completion, image generation, ai, api, openai, api key, context memory, '
             'history, presets, ui, qt, pyside',
    install_requires=[
        'azure-cognitiveservices-speech>=1.27.0',
        'beautifulsoup4>=4.12.2',
        'langchain>=0.0.345',
        'langchain-experimental>=0.0.44',
        'openai>=1.3.7',
        'packaging>=23.0',
        'PyAudio>=0.2.14',
        'pydub>=0.25.1',
        'pyinstaller>=5.9.0',
        'PySide6>=6.4.2',
        'PySide6-Addons>=6.4.2',
        'PySide6-Essentials>=6.4.2',
        'qt-material>=2.14',
        'SpeechRecognition>=3.10.0',
        'show-in-file-manager>=1.1.4',
        'tiktoken>=0.3.3',
        'wikipedia>=1.4.0',
    ],
)
