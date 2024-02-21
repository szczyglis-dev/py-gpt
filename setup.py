from setuptools import setup, find_packages

VERSION = '2.0.160'
DESCRIPTION = 'Desktop AI Assistant powered by GPT-4, GPT-4V, GPT-3.5, DALL-E 3, Langchain LLMs, Llama-index, ' \
              'Whisper and more with chatbot, assistant, text completion, vision and image generation, ' \
              'internet access, chat with files, commands and code execution, file upload and download and more'
LONG_DESCRIPTION = 'Package contains a GPT-4, GPT-4V, GPT-3.5, DALL-E 3, Langchain LLMs and Llama-index powered ' \
                   'Desktop AI Assistant with chatbot, text completion, vision and image generation, internet ' \
                   'access, chat with files and more - using OpenAI API and your own API Key. Includes context ' \
                   'memory and history, editable presets, customizable UI and more.'

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
    package_data={'': [
        'CHANGELOG.txt',
        'LICENSE',
        'data/*',
        'data/css/*',
        'data/fonts/*',
        'data/fonts/Lato/*',
        'data/locale/*',
        'data/config/*',
        'data/config/presets/*'
    ]},
    url='https://github.com/szczyglis-dev/py-gpt',
    keywords='py_gpt, py-gpt, pygpt, PyGPT, desktop, app, gpt, gpt-4, gpt-4v, gpt-4, gpt-3.5, tts, whisper, vision, '
             'chatgpt, dall-e, chat, chatbot, assistant, text completion, image generation, ai, api, openai, api key, '
             'langchain, llama-index, presets, ui, qt, pyside',
    install_requires=[
        'beautifulsoup4>=4.12.2, <5.0.0',
        'chromadb>=0.4.22, <1.0.0',
        'croniter>=2.0.1, <3.0.0',
        'docker>=7.0.0, <8.0.0',
        'docx2txt>=0.8, <1.0',
        'EbookLib>=0.18, <1.0',
        'langchain>=0.1.0, <0.2.0',
        'langchain-community>=0.0.11, <0.0.20',
        'langchain-experimental>=0.0.49, <0.1.0',
        'langchain-openai>=0.0.2.post1, <0.1.0',
        'llama-hub>=0.0.69, <0.1.0',
        'llama-index==0.9.38',
        'Markdown>=3.5.1, <4.0.0',
        'openai>=1.12.0, <2.0.0',
        'opencv-python>=4.8.1.78',
        'packaging>=23.2',
        'pandas>=2.1.4, <3.0.0',
        'pillow>=10.2.0, <11.0.0',
        'pinecone-client>=3.0.1, <4.0.0',
        'PyAudio>=0.2.14, <0.3.0',
        'pygame>=2.5.2, <3.0.0',
        'pyinstaller>=5.9.0',
        'pypdf>=3.17.4, <4.0.0',
        'pyserial>=3.5, <4.0.0',
        'PySide6>=6.4.2, <7.0.0',
        'PySide6-Addons>=6.4.2, <7.0.0',
        'PySide6-Essentials>=6.4.2, <7.0.0',
        'qt-material>=2.14, <3.0.0',
        'SpeechRecognition>=3.10.0, <4.0.0',
        'SQLAlchemy>=2.0.23, <3.0.0',
        'show-in-file-manager>=1.1.4',
        'tiktoken>=0.5.2, <1.0.0',
    ],
)
