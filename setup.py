from setuptools import setup, find_packages

VERSION = '2.0.118'
DESCRIPTION = 'Desktop AI Assistant powered by GPT-4, GPT-4V, GPT-3, Whisper, DALL-E 3, Langchain and Llama-index with chatbot, assistant, text completion, ' \
              'vision and image generation, real-time internet access, commands and code execution, files upload and download and more'
LONG_DESCRIPTION = 'Package contains a GPT-4, GPT-4V, GPT-3, Whisper, DALL-E 3 Desktop AI Assistant with chatbot, ' \
                   'text completion, vision and image generation, internet access, llama-index and more - using OpenAI API and your own API ' \
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
             'chat, chatbot, assistant, text completion, image generation, ai, api, openai, api key, langchain, '
             'llama-index, presets, ui, qt, pyside',
    install_requires=[
        'azure-cognitiveservices-speech>=1.27.0',
        'beautifulsoup4>=4.12.2',
        'chromadb>=0.4.22',
        'croniter>=2.0.1',
        'docker>=7.0.0',
        'docx2txt>=0.8',
        'EbookLib>=0.18',
        'langchain>=0.1.0',
        'langchain-community>=0.0.11',
        'langchain-experimental>=0.0.49',
        'langchain-openai>=0.0.2.post1',
        'llama-hub>=0.0.69',
        'llama-index>=0.9.29',
        'Markdown>=3.5.1',
        'openai>=1.7.2',
        'opencv-python>=4.8.1.78',
        'packaging>=23.2',
        'pandas>=2.1.4',
        'pillow>=10.2.0',
        'pinecone-client>=3.0.1',
        'PyAudio>=0.2.14',
        'pygame>=2.5.2',
        'pyinstaller>=5.9.0',
        'pypdf>=3.17.4',
        'pyserial>=3.5',
        'PySide6>=6.4.2',
        'PySide6-Addons>=6.4.2',
        'PySide6-Essentials>=6.4.2',
        'qt-material>=2.14',
        'SpeechRecognition>=3.10.0',
        'SQLAlchemy>=2.0.23',
        'show-in-file-manager>=1.1.4',
        'tiktoken>=0.5.2',
        'wikipedia>=1.4.0',
    ],
)
