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
    width = 88
    title = " PyHuey "
    rule_left = "═" * 28
    rule_right = "═" * max(0, width - len(rule_left) - len(title))

    print("")
    print(f"╔{rule_left}{title}{rule_right}╗")
    print("║ Monkey-Head-Project".ljust(width + 1) + "║")
    print("║ PyHuey Build v0.4.0  [Windows 11 Pro Insiders Edition]".ljust(width + 1) + "║")
    print("║ https://github.com/DylanLRPollock/Monkey-Head-Project".ljust(width + 1) + "║")
    print("╚" + "═" * width + "╝")
