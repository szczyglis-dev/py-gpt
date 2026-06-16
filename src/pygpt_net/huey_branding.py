from __future__ import annotations

APP_NAME = "PyHuey"
PROJECT_NAME = "Monkey-Head-Project"
BUILD = "v0.4.0"
OS_LABEL = "Windows 11 Pro Insiders Edition"
PROJECT_URL = "https://github.com/DylanLRPollock/Monkey-Head-Project"
UPSTREAM_PROJECT = "PyGPT"
UPSTREAM_AUTHOR = "Marcin Szczygliński"
UPSTREAM_URL = "https://github.com/szczyglis-dev/py-gpt"

DISPLAY_BANNER = (
    "Monkey-Head-Project  PyHuey Build v0.4.0 "
    "[Windows 11 Pro Insiders Edition]  "
    "https://github.com/DylanLRPollock/Monkey-Head-Project"
)

SPLASH_TITLE = "Monkey-Head-Project"
SPLASH_MESSAGE = (
    "PyHuey Build v0.4.0\n"
    "[Windows 11 Pro Insiders Edition]\n"
    "https://github.com/DylanLRPollock/Monkey-Head-Project"
)


def print_startup_banner() -> None:
    print(DISPLAY_BANNER)
