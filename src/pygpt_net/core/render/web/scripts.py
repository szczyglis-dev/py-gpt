"""Ordered frontend resources shared by development and production builds."""
import json
from pathlib import Path

from pygpt_net.config import Config

APP_SCRIPT_FILES = tuple(json.loads(
    (Path(Config().get_app_path()) / "data/js/app/manifest.json").read_text(encoding="utf-8")
))


def script_alias(filename: str) -> str:
    return "app-" + filename.replace("/", "-")


def development_script_tags() -> str:
    return "\n".join(
        f'                <script type="text/javascript" src="qrc:///js/{script_alias(name)}"></script>'
        for name in APP_SCRIPT_FILES
    )
