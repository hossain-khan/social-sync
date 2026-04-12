# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Social Sync CLI
# Build with: pyinstaller sync.spec

block_cipher = None

a = Analysis(
    ["sync.py"],
    pathex=[],
    binaries=[],
    datas=[
        # Bundle .env.example so users can reference it for setup
        (".env.example", "."),
        # Bundle the src package so all modules are available
        ("src", "src"),
    ],
    hiddenimports=[
        # Core src modules
        "src.config",
        "src.bluesky_client",
        "src.mastodon_client",
        "src.sync_orchestrator",
        "src.sync_state",
        "src.content_processor",
        "src.social_sync",
        # atproto hidden imports
        "atproto",
        "atproto_client",
        "atproto_core",
        "atproto_identity",
        "atproto_lexicon",
        "atproto_server",
        # mastodon.py hidden imports
        "mastodon",
        "mastodon.streaming",
        # pydantic/pydantic-settings
        "pydantic",
        "pydantic.v1",
        "pydantic_settings",
        # python-dotenv
        "dotenv",
        # requests and dependencies
        "requests",
        "urllib3",
        "charset_normalizer",
        "certifi",
        "idna",
        # click
        "click",
        # cryptography (used by atproto)
        "cryptography",
        "cryptography.hazmat.backends",
        "cryptography.hazmat.primitives",
    ],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="social-sync",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,  # Ad-hoc signing applied post-build in CI workflow via codesign --sign -
    entitlements_file=None,
)
