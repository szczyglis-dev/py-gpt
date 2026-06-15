from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class LicenseDocument:
    title: str
    path: Path
    text: str


@dataclass(frozen=True)
class LicenseBundle:
    documents: tuple[LicenseDocument, ...]
    combined_text: str
    digest: str


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return here.parents[2]


def _state_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "PyHuey"
    return Path.home() / ".config" / "pyhuey"


def state_path() -> Path:
    return _state_dir() / "license-acceptance.json"


def reset_license_acceptance() -> None:
    try:
        state_path().unlink()
    except FileNotFoundError:
        pass


def _pygpt_workdir_from_argv() -> Path | None:
    """Return the PyGPT/PyHuey workdir requested on the command line, if any."""
    argv = sys.argv[1:]
    for index, arg in enumerate(argv):
        if arg in {"-w", "--workdir"} and index + 1 < len(argv):
            return Path(argv[index + 1])
        if arg.startswith("--workdir="):
            return Path(arg.split("=", 1)[1])

    env_workdir = os.environ.get("PYGPT_WORKDIR")
    if env_workdir:
        return Path(env_workdir)

    return None


def _sync_pygpt_license_acceptance() -> None:
    """Disable PyGPT's legacy first-run license popup in the active workdir."""
    workdir = _pygpt_workdir_from_argv()
    if workdir is None:
        return

    config_path = workdir / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    if data.get("license.accepted") is True:
        return

    data["license.accepted"] = True
    config_path.write_text(json.dumps(data, indent=4), encoding="utf-8")


def _read_text(path: Path, fallback: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return fallback


def load_license_bundle() -> LicenseBundle:
    root = _project_root()

    candidates = (
        (
            "Original PyGPT / PyGPT-net License",
            root / "LICENSES" / "UPSTREAM-PYGPT-LICENSE.txt",
            "Original PyGPT / PyGPT-net license text is missing.",
        ),
        (
            "PyHuey / Monkey-Head-Project License Notice",
            root / "LICENSES" / "PYHUEY-MONKEYHEAD-NOTICE.md",
            "PyHuey / Monkey-Head-Project license notice is missing.",
        ),
    )

    documents: list[LicenseDocument] = []
    sections: list[str] = []

    for title, path, fallback in candidates:
        text = _read_text(path, fallback).strip()
        documents.append(LicenseDocument(title=title, path=path, text=text))
        sections.append(
            f"{'=' * 80}\n"
            f"{title}\n"
            f"{path}\n"
            f"{'=' * 80}\n\n"
            f"{text}\n"
        )

    combined = "\n\n".join(sections).strip() + "\n"
    digest = sha256(combined.encode("utf-8")).hexdigest()
    return LicenseBundle(
        documents=tuple(documents),
        combined_text=combined,
        digest=digest,
    )


def is_license_accepted(bundle: LicenseBundle | None = None) -> bool:
    if bundle is None:
        bundle = load_license_bundle()

    try:
        data = json.loads(state_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    return bool(data.get("accepted")) and data.get("license_hash") == bundle.digest


def accept_license(bundle: LicenseBundle | None = None) -> None:
    if bundle is None:
        bundle = load_license_bundle()

    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "accepted": True,
        "accepted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "license_hash": bundle.digest,
        "documents": [
            {
                "title": document.title,
                "path": str(document.path),
            }
            for document in bundle.documents
        ],
    }

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _sync_pygpt_license_acceptance()


def show_license_cli(bundle: LicenseBundle | None = None) -> int:
    if bundle is None:
        bundle = load_license_bundle()

    print(bundle.combined_text)
    print()
    upstream = input(
        "Do you accept the original upstream PyGPT/PyGPT-net license terms? [y/n]: "
    )
    project = input(
        "Do you accept the PyHuey / Monkey-Head-Project license notice? [y/n]: "
    )

    if upstream.strip().lower() not in {"y", "yes"}:
        print("Original upstream license was not accepted.")
        return 3
    if project.strip().lower() not in {"y", "yes"}:
        print("PyHuey / Monkey-Head-Project license notice was not accepted.")
        return 3

    accept_license(bundle)
    print("License acceptance recorded.")
    return 0


def _dialog_stylesheet() -> str:
    return """
    QDialog {
        background-color: #170023;
        color: #f7f1ff;
        font-family: "Segoe UI", "Arial";
        font-size: 10pt;
    }

    QLabel#HeroTitle {
        color: #ffffff;
        font-size: 22pt;
        font-weight: 700;
    }

    QLabel#HeroSubtitle {
        color: #d8c6ff;
        font-size: 10pt;
    }

    QLabel#SectionTitle {
        color: #ffffff;
        font-size: 12pt;
        font-weight: 700;
    }

    QLabel#FinePrint {
        color: #bba6d9;
        font-size: 8pt;
    }

    QFrame#Hero {
        background-color: #250038;
        border: 1px solid #6f2dbd;
        border-radius: 16px;
    }

    QFrame#Card {
        background-color: #21102f;
        border: 1px solid #4c1d73;
        border-radius: 12px;
    }

    QTextEdit {
        background-color: #100019;
        color: #f4edff;
        border: 1px solid #4c1d73;
        border-radius: 10px;
        padding: 10px;
        selection-background-color: #00c853;
        selection-color: #07120a;
        font-family: "Cascadia Mono", "Consolas", monospace;
        font-size: 9pt;
    }

    QCheckBox {
        color: #f7f1ff;
        spacing: 8px;
        padding: 4px;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }

    QPushButton {
        border-radius: 9px;
        padding: 9px 16px;
        font-weight: 700;
    }

    QPushButton#AcceptButton {
        background-color: #00c853;
        color: #07120a;
        border: 1px solid #6dff9a;
    }

    QPushButton#AcceptButton:disabled {
        background-color: #385040;
        color: #94aa99;
        border: 1px solid #4f6656;
    }

    QPushButton#DeclineButton {
        background-color: #3a164f;
        color: #f7f1ff;
        border: 1px solid #7b2cbf;
    }

    QPushButton#DeclineButton:hover {
        background-color: #51206d;
    }
    """


def show_license_dialog(bundle: LicenseBundle | None = None) -> int:
    if bundle is None:
        bundle = load_license_bundle()

    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QApplication,
            QCheckBox,
            QDialog,
            QFrame,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QTextEdit,
            QVBoxLayout,
        )
    except Exception:
        return show_license_cli(bundle)

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    dialog = QDialog()
    dialog.setWindowTitle("PyHuey License Agreement")
    dialog.setModal(True)
    dialog.setSizeGripEnabled(True)
    dialog.setStyleSheet(_dialog_stylesheet())

    screen = app.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        width = min(780, max(520, int(available.width() * 0.82)))
        height = min(620, max(430, int(available.height() * 0.80)))
        dialog.resize(width, height)
    else:
        dialog.resize(720, 540)

    dialog.setMinimumSize(420, 320)

    outer = QVBoxLayout(dialog)
    outer.setContentsMargins(14, 14, 14, 14)
    outer.setSpacing(12)

    hero = QFrame()
    hero.setObjectName("Hero")
    hero_layout = QVBoxLayout(hero)
    hero_layout.setContentsMargins(18, 16, 18, 16)
    hero_layout.setSpacing(4)

    title = QLabel("PyHuey License Agreement")
    title.setObjectName("HeroTitle")
    title.setTextInteractionFlags(Qt.TextSelectableByMouse)

    subtitle = QLabel(
        "Before PyHuey starts, confirm the upstream PyGPT/PyGPT-net terms "
        "and the PyHuey / Monkey-Head-Project notice."
    )
    subtitle.setObjectName("HeroSubtitle")
    subtitle.setWordWrap(True)
    subtitle.setTextInteractionFlags(Qt.TextSelectableByMouse)

    hero_layout.addWidget(title)
    hero_layout.addWidget(subtitle)
    outer.addWidget(hero)

    card = QFrame()
    card.setObjectName("Card")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(14, 14, 14, 14)
    card_layout.setSpacing(10)

    section_title = QLabel("Agreement Text")
    section_title.setObjectName("SectionTitle")
    card_layout.addWidget(section_title)

    text = QTextEdit()
    text.setReadOnly(True)
    text.setPlainText(bundle.combined_text)
    text.setMinimumHeight(190)
    card_layout.addWidget(text, stretch=1)

    digest_label = QLabel(f"Agreement hash: {bundle.digest[:16]}…")
    digest_label.setObjectName("FinePrint")
    digest_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    card_layout.addWidget(digest_label)

    outer.addWidget(card, stretch=1)

    checks = QFrame()
    checks.setObjectName("Card")
    checks_layout = QVBoxLayout(checks)
    checks_layout.setContentsMargins(14, 12, 14, 12)
    checks_layout.setSpacing(6)

    upstream_box = QCheckBox(
        "I accept the original upstream PyGPT / PyGPT-net license terms."
    )
    project_box = QCheckBox(
        "I accept the PyHuey / Monkey-Head-Project license notice."
    )

    checks_layout.addWidget(upstream_box)
    checks_layout.addWidget(project_box)
    outer.addWidget(checks)

    buttons = QHBoxLayout()
    buttons.setSpacing(10)

    accept_button = QPushButton("Accept and Continue")
    accept_button.setObjectName("AcceptButton")
    accept_button.setEnabled(False)

    decline_button = QPushButton("Decline and Exit")
    decline_button.setObjectName("DeclineButton")

    def update_accept_button() -> None:
        accept_button.setEnabled(upstream_box.isChecked() and project_box.isChecked())

    upstream_box.stateChanged.connect(update_accept_button)
    project_box.stateChanged.connect(update_accept_button)

    result = {"accepted": False}

    def on_accept() -> None:
        accept_license(bundle)
        result["accepted"] = True
        dialog.accept()

    def on_decline() -> None:
        result["accepted"] = False
        dialog.reject()

    accept_button.clicked.connect(on_accept)
    decline_button.clicked.connect(on_decline)

    buttons.addWidget(accept_button)
    buttons.addWidget(decline_button)
    buttons.addStretch(1)

    outer.addLayout(buttons)

    dialog.exec()

    if owns_app:
        app.quit()

    return 0 if result["accepted"] else 3


def require_license_acceptance() -> None:
    bundle = load_license_bundle()
    if is_license_accepted(bundle):
        _sync_pygpt_license_acceptance()
        return

    env = os.environ.copy()
    env["PYHUEY_LICENSE_CHILD"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "pygpt_net.huey_license", "--dialog"],
        env=env,
        check=False,
    )

    if result.returncode != 0 or not is_license_accepted(bundle):
        raise SystemExit("PyHuey license was not accepted.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dialog", action="store_true", help="show the GUI dialog")
    parser.add_argument("--cli", action="store_true", help="show the CLI prompt")
    parser.add_argument("--check", action="store_true", help="check acceptance state")
    parser.add_argument("--reset", action="store_true", help="reset PyHuey license acceptance")
    args = parser.parse_args(argv)

    bundle = load_license_bundle()

    if args.reset:
        reset_license_acceptance()
        print(f"reset: {state_path()}")
        return 0

    if args.check:
        print("accepted" if is_license_accepted(bundle) else "not accepted")
        print(f"state: {state_path()}")
        print(f"hash: {bundle.digest}")
        return 0 if is_license_accepted(bundle) else 1

    if args.cli:
        return show_license_cli(bundle)

    return show_license_dialog(bundle)


if __name__ == "__main__":
    raise SystemExit(main())
