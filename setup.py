from setuptools import setup, find_packages

VERSION = '2.5.9'
DESCRIPTION = 'Desktop AI Assistant powered by models: OpenAI o1, GPT-4o, GPT-4, GPT-4 Vision, GPT-3.5, DALL-E 3, Llama 3, Mistral, Gemini, Claude, Bielik, and other models supported by Langchain, Llama Index, and Ollama. Features include chatbot, text completion, image generation, vision analysis, speech-to-text, internet access, file handling, command execution and more.'
LONG_DESCRIPTION = 'Package contains a gpt-4, gpt-4V, gpt-3.5, DALL-E 3, Langchain LLMs and Llama-index powered ' \
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
        'data/audio/*',
        'data/css/*',
        'data/fonts/*',
        'data/fonts/Lato/*',
        'data/fonts/SpaceMono/*',
        'data/fonts/MonaspaceArgon/*',
        'data/fonts/MonaspaceKrypton/*',
        'data/fonts/MonaspaceNeon/*',
        'data/fonts/MonaspaceRadon/*',
        'data/fonts/MonaspaceXenon/*',
        'data/icons/chat/*',
        'data/locale/*',
        'data/config/*',
        'data/config/presets/*',
        'data/js/*',
        'data/js/highlight/*',
        'data/js/highlight/styles/*',
        'data/js/highlight/languages/*',
        'data/js/highlight/es/*',
        'data/js/highlight/es/languages/*'
    ]},
    url='https://github.com/szczyglis-dev/py-gpt',
    keywords='py_gpt, py-gpt, pygpt, Pygpt, desktop, app, gpt, o1, gpt-4, gpt-4o, gpt-4v, gpt-3.5, tts, whisper, vision, '
             'chatgpt, dall-e, chat, chatbot, assistant, text completion, image generation, ai, api, openai, api key, '
             'langchain, llama-index, presets, ui, qt, pyside',
    install_requires=[
        'beautifulsoup4>=4.12.3,<5.0.0',
        'chromadb>=0.5.17,<0.6.0',
        'croniter>=2.0.1,<3.0.0',
        'docker>=7.0.0,<8.0.0',
        'docx2txt>=0.8,<0.9',
        'google-generativeai>=0.8.3,<0.9.0',
        'EbookLib>=0.18,<0.19',
        'httpx>=0.27.2,<0.28.0',
        'httpx-socks>=0.9.2,<0.10.0',
        'ipykernel>=6.29.5,<7.0.0',
        'jupyter_client>=8.6.3,<9.0.0',
        'langchain>=0.2.14,<0.3.0',
        'langchain-community>=0.2.12,<0.3.0',
        'langchain-experimental>=0.0.64,<0.1.0',
        'langchain-openai>=0.1.22,<0.2.0',
        'llama-index>=0.12.11,<0.13.0',
        'llama-index-agent-openai>=0.4.2,<0.5.0',
        'llama-index-core==0.12.11',
        'llama-index-embeddings-azure-openai>=0.3.0,<0.4.0',
        'llama-index-embeddings-huggingface-api>=0.3.0,<0.4.0',
        'llama-index-embeddings-gemini>=0.3.1,<0.4.0',
        'llama-index-embeddings-openai>=0.3.1,<0.4.0',
        'llama-index-embeddings-ollama>=0.5.0,<0.6.0',
        'llama-index-llms-anthropic>=0.6.3,<0.7.0',
        'llama-index-llms-deepseek>=0.1.0,<0.2.0',
        'llama-index-llms-huggingface-api>=0.3.1,<0.4.0',
        'llama-index-llms-openai>=0.3.13,<0.4.0',
        'llama-index-llms-openai-like>=0.3.3,<0.4.0',
        'llama-index-llms-azure-openai>=0.3.0,<0.4.0',
        'llama-index-llms-gemini>=0.4.3,<0.5.0',
        'llama-index-llms-ollama>=0.5.0,<0.6.0',
        'llama-index-multi-modal-llms-openai>=0.4.2,<0.5.0',
        'llama-index-vector-stores-chroma>=0.4.1,<0.5.0',
        'llama-index-vector-stores-elasticsearch>=0.4.0,<0.5.0',
        'llama-index-vector-stores-pinecone>=0.4.2,<0.5.0',
        'llama-index-vector-stores-redis>=0.4.0,<0.5.0',
        'llama-index-readers-chatgpt-plugin>=0.3.0,<0.4.0',
        'llama-index-readers-database>=0.3.0,<0.4.0',
        'llama-index-readers-file>=0.4.3,<0.5.0',
        'llama-index-readers-github>=0.5.0,<0.6.0',
        'llama-index-readers-google>=0.5.0,<0.6.0',
        'llama-index-readers-microsoft-onedrive>=0.3.0,<0.4.0',
        'llama-index-readers-twitter>=0.3.0,<0.4.0',
        'llama-index-readers-web>=0.3.3,<0.4.0',
        'Markdown>=3.7,<4.0',
        'mss>=9.0.2,<10.0.0',
        'nbconvert>=7.16.1,<8.0.0',
        'openai>=1.55.1,<1.60.0',
        'opencv-python>=4.9.0.80,<5.0.0',
        'packaging>=23.2,<24.0',
        'pandas>=2.2.0,<3.0.0',
        'pillow>=10.2.0,<11.0.0',
        'pinecone-client>=3.1.0,<4.0.0',
        'PyAudio>=0.2.14,<0.3.0',
        'PyAutoGUI>=0.9.54,<0.10.0',
        'Pygments>=2.18.0,<3.0.0',
        'pydub>=0.25.1,<0.26.0',
        'pygame>=2.5.2,<3.0.0',
        'pypdf>=5.1.0,<6.0.0',
        'pynput>=1.7.7,<2.0.0',
        'pyserial>=3.5,<4.0',
        'PySide6==6.6.2',
        'python-markdown-math>=0.8,<0.9',
        'redis>=5.0.1,<6.0.0',
        'qt-material>=2.14,<3.0',
        'SpeechRecognition>=3.10.1,<4.0.0',
        'show-in-file-manager>=1.1.4,<2.0.0',
        'SQLAlchemy>=2.0.27,<3.0.0',
        'tiktoken>=0.7.0,<0.8.0',
        'wikipedia>=1.4.0,<2.0.0',
        'youtube-transcript-api>=0.6.2,<0.7.0',
    ],
)
