# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.hooks import collect_all

datas = [('assets\\app-logo.png', 'assets'), ('assets\\app-logo.ico', 'assets'),
         ('LICENSE', '.'), ('THIRD-PARTY-NOTICES.txt', '.')]
binaries = []
hiddenimports = []
hiddenimports += collect_submodules('windows_toasts')
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['assets/runtime_hook_mp.py'],
    excludes=['numpy', 'scipy', 'pandas', 'matplotlib', 'tkinter.test', 'unittest', 'xmlrpc', 'pydoc', 'doctest', 'ftplib', 'imaplib', 'smtplib', 'nntplib', 'poplib', 'telnetlib', 'turtle', 'turtledemo', 'curses', 'lib2to3', 'ensurepip', 'venv', 'distutils', 'setuptools', 'pkg_resources', 'pip', 'PIL.ImageQt'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AIUsageTracker',
    version='assets/windows-version.txt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\app-logo.ico'],
)
