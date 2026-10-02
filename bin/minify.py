#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minifies and concatenates JS files from:
  src/pygpt_net/data/js/app
into a single file:
  src/pygpt_net/data/js/app.min.js

Intended to be run from the 'bin' directory (but works from anywhere).
All paths are resolved relative to this script location (../src/pygpt_net/...).

The source order is shared with the development loader in app/manifest.json.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

# Try to use rjsmin. If it's missing, the script will still run (concat only).
try:
    from rjsmin import jsmin as _jsmin  # type: ignore
    HAVE_RJSMIN = True
except Exception:
    HAVE_RJSMIN = False

    def _jsmin(s: str) -> str:
        # Fallback: no minification (concatenation only).
        return s


def sync_resource_manifest(path: Path, files: list[str]) -> None:
    """Keep Qt aliases in the same order as the shared source manifest."""
    tree = ET.parse(path)
    resources = tree.getroot().find("qresource[@prefix='/js']")
    if resources is None:
        raise ValueError("Missing /js resource group")
    for entry in list(resources):
        if (entry.text or "").startswith("data/js/app/"):
            resources.remove(entry)
    for index, filename in enumerate(files):
        entry = ET.Element("file", alias="app-" + filename.replace("/", "-"))
        entry.text = "data/js/app/" + filename
        resources.insert(index, entry)
    ET.indent(tree, space="    ")
    content = ET.tostring(tree.getroot(), encoding="unicode") + "\n"
    if path.read_text(encoding="utf-8") != content:
        path.write_text(content, encoding="utf-8")


def main() -> int:
    # bin/minify.py -> repo_root
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent

    src_pkg_root = repo_root / "src" / "pygpt_net"
    app_dir = src_pkg_root / "data" / "js" / "app"
    out_file = src_pkg_root / "data" / "js" / "app.min.js"

    # Order of files to minify/concatenate (relative to src/pygpt_net)
    file_order = json.loads((app_dir / "manifest.json").read_text(encoding="utf-8"))
    FILE_ORDER = [f"data/js/app/{name}" for name in file_order]


    if len(set(file_order)) != len(file_order):
        print("ERROR: Duplicate source in app/manifest.json", file=sys.stderr)
        return 2

    # Validate file existence
    abs_paths = [(rel, (src_pkg_root / rel)) for rel in FILE_ORDER]
    missing = [str(p) for _, p in abs_paths if not p.is_file()]
    if missing:
        print("ERROR: Missing JS files:", file=sys.stderr)
        for m in missing:
            print(f" - {m}", file=sys.stderr)
        print(
            "\nMake sure paths match this structure:\n"
            "  src/pygpt_net/data/js/app/<files>.js",
            file=sys.stderr,
        )
        return 2

    sync_resource_manifest(src_pkg_root / "js.qrc", file_order)

    # Minify and concatenate
    out_file.parent.mkdir(parents=True, exist_ok=True)

    banner_engine = "rjsmin" if HAVE_RJSMIN else "concat-only (no minify)"
    banner = (
        f"/* app.min.js — generated on {datetime.now():%Y-%m-%d %H:%M:%S} "
        f"by bin/minify.py using {banner_engine} */\n"
    )
    chunks: list[str] = [banner]

    for rel, path in abs_paths:
        src = path.read_text(encoding="utf-8")
        minified = _jsmin(src)

        # Safe concatenation: insert a comment with the file name + guard semicolon
        chunks.append(f"\n/* {rel} */\n")
        chunks.append(minified)
        if not minified.rstrip().endswith(";"):
            chunks.append(";\n")
        else:
            chunks.append("\n")

    final_js = "".join(chunks)
    out_file.write_text(final_js, encoding="utf-8", newline="\n")

    size = out_file.stat().st_size
    # Print paths relative to src/pygpt_net for readability
    print(f"OK: wrote {out_file.relative_to(src_pkg_root)} ({size} bytes)")
    print(f"Sources: {app_dir.relative_to(src_pkg_root)}")
    if not HAVE_RJSMIN:
        print(
            "WARNING: rjsmin was not available — files were not minified (concatenation only).",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())