from setuptools import setup, find_packages

VERSION = '2.0.84'
DESCRIPTION = 'Desktop AI Assistant powered by GPT-4, GPT-4V, GPT-3, Whisper, TTS and DALL-E 3 with chatbot, assistant, text completion, ' \
              'vision and image generation, real-time internet access, commands and code execution, files upload and download and more'
LONG_DESCRIPTION = 'Package contains a GPT-4, GPT-4V, GPT-3, Whisper, TTS and DALL-E 3 Desktop AI Assistant with chatbot, ' \
                   'text completion, vision and image generation, internet access and more - using OpenAI API and your own API ' \
                   'Key. Includes context memory and history, editable presets, customizable UI and more. '

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
    package_data={'': ['CHANGELOG.txt', 'data/*', 'data/css/*', 'data/fonts/*', 'data/fonts/Lato/*', 'data/locale/*', 'data/config/*', 'data/config/presets/*']},
    url='https://github.com/szczyglis-dev/py-gpt',
    keywords='py_gpt, py-gpt, pygpt, PyGPT, desktop, app, gpt, gpt-4, gpt-4v, gpt-3, gpt-4, gpt-3, tts, whisper, vision, chatgpt, dall-e, '
             'chat, chatbot, assistant, text completion, image generation, ai, api, openai, api key, memory, '
             'history, presets, ui, qt, pyside',
    install_requires=[
        'azure-cognitiveservices-speech>=1.27.0',
        'beautifulsoup4>=4.12.2',
        'docker>=7.0.0',
        'langchain>=0.0.345',
        'langchain-experimental>=0.0.44',
        'Markdown>=3.5.1',
        'openai>=1.3.7',
        'opencv-python>=4.8.1.78',
        'packaging>=23.0',
        'PyAudio>=0.2.14',
        'pygame>=2.5.2',
        'pyinstaller>=5.9.0',
        'PySide6>=6.4.2',
        'PySide6-Addons>=6.4.2',
        'PySide6-Essentials>=6.4.2',
        'qt-material>=2.14',
        'SpeechRecognition>=3.10.0',
        'SQLAlchemy>=2.0.23',
        'show-in-file-manager>=1.1.4',
        'tiktoken>=0.3.3',
        'wikipedia>=1.4.0',
    ],
)
