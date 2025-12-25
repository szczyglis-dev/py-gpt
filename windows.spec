# -*- mode: python ; coding: utf-8 -*-
import sys

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
)

block_cipher = None

hiddenimports = [
    'chromadb.api.segment',
    'chromadb.db.impl',
    'chromadb.db.impl.sqlite',
    'chromadb.utils.embedding_functions',
    'chromadb.migrations',
    'chromadb.migrations.sysdb',
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
    'transformers',
    'tiktoken_ext',
    'tiktoken_ext.openai_public',
    'pydub',
    'pywin32',
    'pywin32_ctypes',
    'tweepy',
    'ipykernel',
    'IPython.core.display',
    'IPython.core.interactiveshell',
    'jupyter_client',
]
for pkg in [
    'chromadb', 'chromadb.migrations', 'chromadb.telemetry',
    'chromadb.api', 'chromadb.db',
    'httpx', 'httpx_socks', 'nbconvert',
    'onnxruntime', 'win32com',
]:
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

datas = []
datas += collect_data_files('opentelemetry.sdk')
datas += collect_data_files('opentelemetry')
datas += collect_data_files('pinecone')
datas += collect_data_files('chromadb', include_py_files=True, includes=['**/*.py', '**/*.sql'])
datas += [
    (r'src\pygpt_net\data\config\presets\*', r'data\config\presets'),
    (r'src\pygpt_net\data\config\config.json', r'data\config'),
    (r'src\pygpt_net\data\config\models.json', r'data\config'),
    (r'src\pygpt_net\data\config\modes.json', r'data\config'),
    (r'src\pygpt_net\data\config\settings.json', r'data\config'),
    (r'src\pygpt_net\data\config\settings_section.json', r'data\config'),
    (r'src\pygpt_net\data\icons\*', r'data\icons'),
    (r'src\pygpt_net\data\icons\chat\*', r'data\icons\chat'),
    (r'src\pygpt_net\data\locale\*', r'data\locale'),
    (r'src\pygpt_net\data\audio\*', r'data\audio'),
    (r'src\pygpt_net\data\css\*', r'data\css'),
    (r'src\pygpt_net\data\fixtures\*', r'data\fixtures'),
    (r'src\pygpt_net\data\themes\*', r'data\themes'),
    (r'src\pygpt_net\data\fonts\Lato\*', r'data\fonts\Lato'),
    (r'src\pygpt_net\data\fonts\SpaceMono\*', r'data\fonts\SpaceMono'),
    (r'src\pygpt_net\data\fonts\MonaspaceArgon\*', r'data\fonts\MonaspaceArgon'),
    (r'src\pygpt_net\data\fonts\MonaspaceKrypton\*', r'data\fonts\MonaspaceKrypton'),
    (r'src\pygpt_net\data\fonts\MonaspaceNeon\*', r'data\fonts\MonaspaceNeon'),
    (r'src\pygpt_net\data\fonts\MonaspaceRadon\*', r'data\fonts\MonaspaceRadon'),
    (r'src\pygpt_net\data\fonts\MonaspaceXenon\*', r'data\fonts\MonaspaceXenon'),
    (r'src\pygpt_net\data\js\highlight\styles\*', r'data\js\highlight\styles'),
    (r'src\pygpt_net\data\prompts.csv', r'data'),
    (r'src\pygpt_net\data\languages.csv', r'data'),
    (r'src\pygpt_net\data\logo.png', r'data'),
    (r'src\pygpt_net\data\icon.ico', r'data'),
    (r'src\pygpt_net\data\icon_web.ico', r'data'),
    (r'src\pygpt_net\data\icon_tray_idle.ico', r'data'),
    (r'src\pygpt_net\data\icon_tray_busy.ico', r'data'),
    (r'src\pygpt_net\data\icon_tray_error.ico', r'data'),
    (r'src\pygpt_net\CHANGELOG.txt', r'.'),
    (r'src\pygpt_net\LICENSE', r'.'),
    (r'src\pygpt_net\data\icon.png', r'.'),
    (r'src\pygpt_net\data\icon.ico', r'.'),
    (r'src\pygpt_net\data\icon_web.png', r'.'),
    (r'src\pygpt_net\data\icon_web.ico', r'.'),
    (r'src\pygpt_net\data\win32\USER-LICENSE.rtf', r'.'),
    (r'src\pygpt_net\data\win32\README.rtf', r'.'),
    (r'src\pygpt_net\data\win32\banner.bmp', r'.'),
    (r'src\pygpt_net\data\win32\banner_welcome.bmp', r'.'),
    (r'README.md', r'.'),
    (r'src\pygpt_net\__init__.py', r'.'),
    (r'venv\Lib\site-packages\llama_index\legacy\VERSION', r'llama_index\legacy'),
    (r'venv\Lib\site-packages\llama_index\legacy\_static\nltk_cache\corpora\stopwords\*', r'llama_index\legacy\_static\nltk_cache\corpora\stopwords'),
    (r'venv\Lib\site-packages\llama_index\legacy\_static\nltk_cache\tokenizers\punkt\*', r'llama_index\legacy\_static\nltk_cache\tokenizers\punkt'),
    (r'venv\Lib\site-packages\llama_index\legacy\_static\nltk_cache\tokenizers\punkt\PY3\*', r'llama_index\legacy\_static\nltk_cache\tokenizers\punkt\PY3'),
    (r'venv\Lib\site-packages\llama_index\core\_static\nltk_cache\corpora\stopwords\*', r'llama_index\core\_static\nltk_cache\corpora\stopwords'),
    (r'venv\Lib\site-packages\llama_index\core\agent\react\templates\*', r'llama_index\core\agent\react\templates'),
    (r'venv\Lib\site-packages\opentelemetry_sdk-1.39.1.dist-info\*', r'opentelemetry_sdk-1.39.1.dist-info'),
    (r'venv\Lib\site-packages\pinecone\__version__', r'pinecone'),
]

a = Analysis(
    [r'src\pygpt_net\app.py'],
    pathex=[r'src', r'src\pygpt_net'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    a.binaries + [
              ('pywintypes310.dll', 'venv\\Lib\\site-packages\\pywin32_system32\\pywintypes310.dll', 'BINARY'),
              ('pythoncom310.dll', 'venv\\Lib\\site-packages\\pywin32_system32\\pythoncom310.dll', 'BINARY'),
              ('msvcp100.dll', 'C:\\Windows\\System32\\msvcp100.dll', 'BINARY'),
              ('msvcr100.dll', 'C:\\Windows\\System32\\msvcr100.dll', 'BINARY')]
    if sys.platform == 'win32' else a.binaries,
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
    icon=r'src\pygpt_net\data\icon.ico',
    version='version.rc'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Windows',
)
