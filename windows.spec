# -*- mode: python ; coding: utf-8 -*-
import sys

block_cipher = None


a = Analysis(
    ['src\\pygpt_net\\app.py'],
    pathex=[
        'src\\pygpt_net\\'
    ],
    binaries=[],
    datas=[
        ('src\\pygpt_net\\data\\config\\presets\\*', 'data\\config\\presets'),
        ('src\\pygpt_net\\data\\config\\config.json', 'data\\config'),
        ('src\\pygpt_net\\data\\config\\models.json', 'data\\config'),
        ('src\\pygpt_net\\data\\locale\\*', 'data\\locale'),
        ('src\\pygpt_net\\data\\logo.png', 'data'),
        ('src\\pygpt_net\\CHANGELOG.txt', '.'),
        ('README.md', '.'),
        ('src\\pygpt_net\\__init__.py', '.')
    ],
    hiddenimports=[
    'tiktoken_ext', 
    'tiktoken_ext.openai_public', 
    'wikipedia', 
    'pydub'],
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
    a.binaries + [('msvcp100.dll', 'C:\\Windows\\System32\\msvcp100.dll', 'BINARY'),
              ('msvcr100.dll', 'C:\\Windows\\System32\\msvcr100.dll', 'BINARY')]
    if sys.platform == 'win32' else a.binaries,
    exclude_binaries=True,
    name='Py-GPT',
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
    icon='src\\pygpt_net\\data\\icon.ico',
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
