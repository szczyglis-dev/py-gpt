"""Preserve metadata for distributions actually included by Analysis.

The optional package resolver needs the frozen runtime's installed versions;
metadata must not claim that excluded packages are present.
"""
from importlib import metadata
import os
from pathlib import Path


def add_runtime_metadata(analysis):
    sources = {os.path.normcase(os.path.realpath(source))
               for _, source, _ in [*analysis.pure, *analysis.binaries] if source}
    destinations = {name for name, _, _ in analysis.datas}
    for dist in metadata.distributions():
        files = list(dist.files or [])
        if not any(os.path.normcase(os.path.realpath(dist.locate_file(file))) in sources
                   for file in files):
            continue
        for file in files:
            parts = Path(file).parts
            if not parts or not parts[0].endswith(('.dist-info', '.egg-info')):
                continue
            source = Path(dist.locate_file(file))
            destination = str(file)
            if source.is_file() and destination not in destinations:
                analysis.datas.append((destination, str(source), 'DATA'))
                destinations.add(destination)
