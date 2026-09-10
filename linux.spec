# -*- mode: python ; coding: utf-8 -*-

import os, glob
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
    copy_metadata,
)
import PySide6

RT_HOOK_PATH = os.path.abspath('rt_wayland.py')
if not os.path.exists(RT_HOOK_PATH):
    with open(RT_HOOK_PATH, 'w', encoding='utf-8') as f:
        f.write(
            "import os\n"
            "os.environ.setdefault('QT_QPA_PLATFORM', 'wayland;xcb')\n"
            "# os.environ.setdefault('QT_DEBUG_PLUGINS', '1')\n"
        )

pkg_dir = os.path.dirname(PySide6.__file__)
plugins_root = os.path.join(pkg_dir, 'plugins')
platforms_dir = os.path.join(plugins_root, 'platforms')
qtlib_dir = os.path.join(pkg_dir, 'Qt', 'lib')

qt_binaries = []
for p in glob.glob(os.path.join(platforms_dir, 'libqwayland*.so*')) + glob.glob(os.path.join(platforms_dir, 'libqxcb.so*')):
    qt_binaries.append((p, os.path.join('PySide6', 'plugins', 'platforms')))
for p in glob.glob(os.path.join(qtlib_dir, 'libQt6WaylandClient*.so*')):
    qt_binaries.append((p, os.path.join('PySide6', 'Qt', 'lib')))

for subdir in ('wayland-graphics-integration-client', 'wayland-shell-integration'):
    src_dir = os.path.join(plugins_root, subdir)
    if os.path.isdir(src_dir):
        for p in glob.glob(os.path.join(src_dir, '*.so*')):
            qt_binaries.append((p, os.path.join('PySide6', 'plugins', subdir)))

dyn_bins = []
for pkg in ('onnxruntime', 'tokenizers', 'tiktoken'):
    try:
        dyn_bins += collect_dynamic_libs(pkg)
    except Exception:
        pass

# ipykernel imports debugpy during kernel initialization. debugpy's vendored
# pydevd runtime contains native extensions with names such as
# ``*_cython*.so`` (not only ``lib*.so``), so collect them explicitly.
try:
    dyn_bins += collect_dynamic_libs(
        'debugpy',
        search_patterns=['*.so', '*.dylib', '*.dll', '*.pyd'],
    )
except Exception:
    pass

datas = []
datas += collect_data_files('opentelemetry.sdk')
datas += collect_data_files('opentelemetry')
datas += collect_data_files('pinecone')
datas += collect_data_files('chromadb', include_py_files=True, includes=['**/*.py', '**/*.sql'])
# Local IPython kernel runtime for PyInstaller builds.  In particular,
# ipykernel/resources is used by jupyter_client's native python3 kernelspec.
# jupyter_client discovers the built-in local provisioner through package
# entry-point metadata, so its dist-info must be present in the bundle.
datas += copy_metadata('jupyter_client')
for pkg in ('ipykernel', 'IPython', 'jupyter_client', 'jupyter_core'):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

# debugpy._vendored uses os.listdir() and temporarily prepends the physical
# ``debugpy/_vendored/pydevd`` directory to sys.path. The vendored Python
# sources therefore must exist as real files in the frozen distribution;
# keeping them only in PyInstaller's PYZ archive is not sufficient.
try:
    datas += collect_data_files(
        'debugpy',
        include_py_files=True,
        excludes=['**/__pycache__/**', '**/*.pyc'],
    )
except Exception:
    pass

datas += [
    ('src/pygpt_net/data/config/presets/*', 'data/config/presets'),
    ('src/pygpt_net/data/config/config.json', 'data/config'),
    ('src/pygpt_net/data/config/models.json', 'data/config'),
    ('src/pygpt_net/data/config/modes.json', 'data/config'),
    ('src/pygpt_net/data/config/settings.json', 'data/config'),
    ('src/pygpt_net/data/config/settings_section.json', 'data/config'),
    ('src/pygpt_net/data/banners/*', 'data/banners'),
    ('src/pygpt_net/data/icons/*', 'data/icons'),
    ('src/pygpt_net/data/icons/chat/*', 'data/icons/chat'),
    ('src/pygpt_net/data/locale/*', 'data/locale'),
    ('src/pygpt_net/data/audio/*', 'data/audio'),
    ('src/pygpt_net/data/css/*', 'data/css'),
    ('src/pygpt_net/data/themes/*', 'data/themes'),
    ('src/pygpt_net/data/fixtures/*', 'data/fixtures'),
    ('src/pygpt_net/data/fonts/Lato/*', 'data/fonts/Lato'),
    ('src/pygpt_net/data/fonts/SpaceMono/*', 'data/fonts/SpaceMono'),
    ('src/pygpt_net/data/fonts/MonaspaceArgon/*', 'data/fonts/MonaspaceArgon'),
    ('src/pygpt_net/data/fonts/MonaspaceKrypton/*', 'data/fonts/MonaspaceKrypton'),
    ('src/pygpt_net/data/fonts/MonaspaceNeon/*', 'data/fonts/MonaspaceNeon'),
    ('src/pygpt_net/data/fonts/MonaspaceRadon/*', 'data/fonts/MonaspaceRadon'),
    ('src/pygpt_net/data/fonts/MonaspaceXenon/*', 'data/fonts/MonaspaceXenon'),
    ('src/pygpt_net/data/js/highlight/styles/*', 'data/js/highlight/styles'),
    ('src/pygpt_net/data/prompts.csv', 'data'),
    ('src/pygpt_net/data/languages.csv', 'data'),
    ('src/pygpt_net/data/banners.json', 'data'),
    ('src/pygpt_net/data/logo.png', 'data'),
    ('src/pygpt_net/data/icon.ico', 'data'),
    ('src/pygpt_net/data/icon_tray_idle.ico', 'data'),
    ('src/pygpt_net/data/icon_tray_busy.ico', 'data'),
    ('src/pygpt_net/data/icon_tray_error.ico', 'data'),
    ('src/pygpt_net/CHANGELOG.txt', '.'),
    ('src/pygpt_net/LICENSE', '.'),
    ('src/pygpt_net/data/icon.png', '.'),
    ('src/pygpt_net/data/icon.ico', '.'),
    ('README.md', '.'),
    ('src/pygpt_net/__init__.py', '.'),
    ('venv/lib/python3.10/site-packages/llama_index/legacy/VERSION', 'llama_index/legacy/'),
    ('venv/lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/corpora/stopwords/*', 'llama_index/legacy/_static/nltk_cache/corpora/stopwords/'),
    ('venv/lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/tokenizers/punkt/*', 'llama_index/legacy/_static/nltk_cache/tokenizers/punkt/'),
    ('venv/lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/tokenizers/punkt/PY3/*', 'llama_index/legacy/_static/nltk_cache/tokenizers/punkt/PY3/'),
    ('venv/lib/python3.10/site-packages/llama_index/core/_static/nltk_cache/corpora/stopwords/*', 'llama_index/core/_static/nltk_cache/corpora/stopwords/'),
    ('venv/lib/python3.10/site-packages/llama_index/core/agent/react/templates/*', 'llama_index/core/agent/react/templates/'),
    ('venv/lib/python3.10/site-packages/opentelemetry_sdk-1.44.0.dist-info/*', 'opentelemetry_sdk-1.44.0.dist-info'),
    ('venv/lib/python3.10/site-packages/pinecone/__version__', 'pinecone'),
]

hiddenimports = [
    'chromadb.api.segment',
    'chromadb.db.impl',
    'chromadb.db.impl.sqlite',
    'chromadb.utils.embedding_functions',
    'chromadb.migrations',
    'chromadb.migrations.embeddings_queue',
    'chromadb.segment.impl.manager',
    'chromadb.segment.impl.manager.local',
    'chromadb.segment.impl.metadata',
    'chromadb.segment.impl.metadata.sqlite',
    'chromadb.segment.impl.vector',
    'chromadb.segment.impl.vector.batch',
    'chromadb.segment.impl.vector.brute_force_index',
    'chromadb.segment.impl.vector.hnsw_params',
    'chromadb.segment.impl.vector.local_hnsw',
    'chromadb.segment.impl.vector.local_persistent_hnsw',
    'chromadb.telemetry.posthog',
    'chromadb.telemetry.product.posthog',
    'httpx',
    'httpx_socks',
    'pinecone',
    'opentelemetry',
    'opentelemetry.sdk',
    'opentelemetry.context.contextvars_context',
    'onnxruntime',
    'tokenizers',
    'tiktoken_ext',
    'tiktoken_ext.openai_public',
    'pydub',
    'tweepy',
    'ipykernel',
    'ipykernel_launcher',
    'ipykernel.kernelapp',
    'IPython.core.display',
    'IPython.core.interactiveshell',
    'jupyter_client',
    'aiosqlite',
    'sqlalchemy.dialects.sqlite.aiosqlite',
]
for pkg in [
    'chromadb', 'chromadb.migrations', 'chromadb.telemetry',
    'chromadb.api', 'chromadb.db',
    'httpx', 'httpx_socks', 'nbconvert', 'aiosqlite',
    # Kernel modules are partly imported lazily/dynamically at runtime.
    'ipykernel', 'jupyter_client', 'IPython.core.magics', 'IPython.extensions',
    'debugpy', 'zmq.backend',
]:
    hiddenimports += collect_submodules(pkg)

block_cipher = None

a = Analysis(
    ['src/pygpt_net/app.py'],
    pathex=['src', 'src/pygpt_net'],
    binaries=qt_binaries + dyn_bins,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[RT_HOOK_PATH],
    excludes=['pkg_resources', 'setuptools'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pygpt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/pygpt_net/data/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'PySide6/plugins/*',
        'PySide6/Qt/lib/libQt6WaylandClient*',
    ],
    name='Linux',
)