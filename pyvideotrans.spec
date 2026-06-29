# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for pyVideoTrans
Build a single portable .exe that bundles all dependencies
"""
import sys
from pathlib import Path

ROOT = Path(r'c:\Users\CMD\Downloads\pyvideotrans-main\pyvideotrans-main')

a = Analysis(
    [str(ROOT / 'sp.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Core config & language
        (str(ROOT / 'videotrans' / 'cfg.json'), 'videotrans'),
        (str(ROOT / 'videotrans' / 'params.json'), 'videotrans'),
        (str(ROOT / 'videotrans' / 'codec.json'), 'videotrans'),
        (str(ROOT / 'videotrans' / 'ass.json'), 'videotrans'),
        (str(ROOT / 'videotrans' / 'glossary.txt'), 'videotrans'),
        (str(ROOT / 'videotrans' / 'language'), 'videotrans/language'),
        # Prompts
        (str(ROOT / 'videotrans' / 'prompts'), 'videotrans/prompts'),
        # Styles (QDarkStyle)
        (str(ROOT / 'videotrans' / 'styles'), 'videotrans/styles'),
        # Voice JSON configs
        (str(ROOT / 'videotrans' / 'voicejson'), 'videotrans/voicejson'),
        # FFmpeg binaries (bundled)
        (str(ROOT / 'ffmpeg'), 'ffmpeg'),
        # Models (ONNX + faster-whisper)
        (str(ROOT / 'models'), 'models'),
        # Docs (optional, for help/about)
        (str(ROOT / 'docs'), 'docs'),
        # Law/license
        (str(ROOT / 'law.txt'), '.'),
        (str(ROOT / 'LICENSE'), '.'),
    ],
    hiddenimports=[
        # PySide6
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'PySide6.QtNetwork', 'PySide6.QtPrintSupport',
        # Common hidden imports
        'pkgutil', 'importlib', 'importlib.metadata',
        'ctranslate2', 'faster_whisper',
        'google.genai', 'google.api_core',
        'google.cloud.texttospeech',
        'edge_tts',
        'azure.cognitiveservices.speech',
        'dashscope',
        'deepgram',
        'deepl',
        'anthropic',
        'openai',
        'qdarkstyle',
        'librosa',
        'soundfile',
        'pydub',
        'av',
        'PIL',
        'cv2',
        'torch', 'torchaudio',
        'transformers',
        'diffusers',
        'peft',
        'accelerate',
        'onnxruntime',
        'numba',
        'scipy',
        'sklearn',
        'pandas',
        'jieba',
        'sentencepiece',
        'py7zr',
        'pytorch_wpe',
        'kaldiio',
        'resampy',
        'pooch',
        'norbert',
        'huggingface_hub',
        'datasets',
        'httpx', 'httpcore',
        'websockets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'pytest',
        'setuptools', 'distutils', 'pip',
        'IPython', 'jupyter', 'notebook',
        'matplotlib', 'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='pyVideoTrans',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False = GUI app (no console window)
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
