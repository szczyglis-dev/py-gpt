from setuptools import setup, find_packages

VERSION = '0.9.6'
DESCRIPTION = 'GPT4, GPT3, ChatGPT and DALL-E 2 Desktop App with chatbot, text completion and image generation'
LONG_DESCRIPTION = 'A package containing a GPT4, GPT3, ChatGPT and DALL-E 2 desktop chatbot, ' \
                   'text completion and image generation app, using OpenAI API and your own API Key. ' \
                   'It includes context memory and history, editable presets, customizable UI and more.'

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
    keywords='py_gpt, py-gpt, pygpt, desktop, app, gpt, gpt4, gpt3, chatgpt, dall-e, chat, chatbot, text completion,'
             'image generation, ai, api, openai, api key, context memory, history, presets, ui, qt, pyside',
    install_requires=[
        'beautifulsoup4>=4.12.2',
        'openai>=0.27.4',
        'packaging>=23.0',
        'pydub>=0.25.1',
        'pyinstaller>=5.9.0',
        'PySide6-Essentials>=6.4.2',
        'qt-material>=2.14',
        'show-in-file-manager>=1.1.4',
        'tiktoken>=0.3.3',
        'wikipedia>=1.4.0',
    ],
)
