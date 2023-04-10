# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['app.py'],
    pathex=[
        '.'
    ],
    binaries=[],
    datas=[
        ('data/config/presets/*', 'data/config/presets'),
        ('data/config/config.json', 'data/config'),
        ('data/config/models.json', 'data/config'),
        ('data/locale/*', 'data/locale'),
        ('data/logo.png', 'data'),
        ('CHANGELOG.txt', '.'),
        ('README.md', '.'),
        ('__init__.py', '.')
    ],
    hiddenimports=['core', 'tiktoken_ext', 'tiktoken_ext.openai_public'],
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
    icon='./data/icon.ico'
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
