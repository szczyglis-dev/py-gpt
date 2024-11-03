# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None


a = Analysis(
    ['src/pygpt_net/app.py'],
    pathex=[
        'src',
        'src/pygpt_net'
    ],
    binaries=[],
    datas=collect_data_files('opentelemetry.sdk', 'pinecode') + collect_data_files('chromadb', include_py_files=True, includes=['**/*.py', '**/*.sql']) +  [  # chromadb, pinecode hack
        ('src/pygpt_net/data/config/presets/*', 'data/config/presets'),
        ('src/pygpt_net/data/config/config.json', 'data/config'),
        ('src/pygpt_net/data/config/models.json', 'data/config'),
        ('src/pygpt_net/data/config/modes.json', 'data/config'),
        ('src/pygpt_net/data/config/settings.json', 'data/config'),
        ('src/pygpt_net/data/config/settings_section.json', 'data/config'),
        ('src/pygpt_net/data/icons/chat/*', 'data/icons/chat'),
        ('src/pygpt_net/data/locale/*', 'data/locale'),
        ('src/pygpt_net/data/audio/*', 'data/audio'),
        ('src/pygpt_net/data/css/*', 'data/css'),
        ('src/pygpt_net/data/fonts/Lato/*', 'data/fonts/Lato'),
        ('src/pygpt_net/data/fonts/SpaceMono/*', 'data/fonts/SpaceMono'),
        ('src/pygpt_net/data/fonts/MonaspaceArgon/*', 'data/fonts/MonaspaceArgon'),
        ('src/pygpt_net/data/fonts/MonaspaceKrypton/*', 'data/fonts/MonaspaceKrypton'),
        ('src/pygpt_net/data/fonts/MonaspaceNeon/*', 'data/fonts/MonaspaceNeon'),
        ('src/pygpt_net/data/fonts/MonaspaceRadon/*', 'data/fonts/MonaspaceRadon'),
        ('src/pygpt_net/data/fonts/MonaspaceXenon/*', 'data/fonts/MonaspaceXenon'),
        ('src/pygpt_net/data/js/highlight/styles/*', 'data/js/highlight/styles'),
        ('src/pygpt_net/data/prompts.csv', 'data'),
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
        ('venv/lib/python3.10/site-packages/onnxruntime/capi/*', 'onnxruntime/capi/'),  # onnxruntime
        ('venv/lib/python3.10/site-packages/llama_index/legacy/VERSION', 'llama_index/legacy/'),  # llama-index hack
        ('venv/lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/corpora/stopwords/*', 'llama_index/legacy/_static/nltk_cache/corpora/stopwords/'),  # llama-index hack
        ('venv/lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/tokenizers/punkt/*', 'llama_index/legacy/_static/nltk_cache/tokenizers/punkt/'),  # llama-index hack
        ('venv/lib/python3.10/site-packages/llama_index/legacy/_static/nltk_cache/tokenizers/punkt/PY3/*', 'llama_index/legacy/_static/nltk_cache/tokenizers/punkt/PY3/'),  # llama-index hack
        ('venv/lib/python3.10/site-packages/llama_index/core/_static/nltk_cache/corpora/stopwords/*', 'llama_index/core/_static/nltk_cache/corpora/stopwords/'),  # llama-index hack
        ('venv/lib/python3.10/site-packages/llama_index/core/_static/nltk_cache/tokenizers/punkt/*', 'llama_index/core/_static/nltk_cache/tokenizers/punkt/'),  # llama-index hack
        ('venv/lib/python3.10/site-packages/llama_index/core/_static/nltk_cache/tokenizers/punkt/PY3/*', 'llama_index/core/_static/nltk_cache/tokenizers/punkt/PY3/'),  # llama-index hack
        ('venv/lib/python3.10/site-packages/langchain/chains', 'langchain/chains'),  # langchain/llama hack
        ('venv/lib/python3.10/site-packages/opentelemetry_sdk-1.27.0.dist-info/*', 'opentelemetry_sdk-1.27.0.dist-info'), # chromadb hack
        ('venv/lib/python3.10/site-packages/pinecone/__version__', 'pinecone'),  # pinecode hack
    ],
    hiddenimports=[
    'chromadb.api.segment', 
    'chromadb.db.impl', 
    'chromadb.db.impl.sqlite', 
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
    'pinecode',
    'opentelemetry',
    'opentelemetry.sdk',
    'onnxruntime',
    'tokenizers',
    'tiktoken_ext', 
    'tiktoken_ext.openai_public',
    'pydub',
    'tweepy'],
    collectsubmodules=['chromadb', 'chromadb.migrations', 'chromadb.telemetry', 'chromadb.api','chromadb.db', 'nbconvert'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    icon='src/pygpt_net/data/icon.ico'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Linux',
)
