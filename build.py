from pathlib import Path
import shutil
import subprocess

from version import APP_NAME, __version__

# -------------------------
# Пути
# -------------------------

PROJECT_DIR = Path(__file__).parent.resolve()

DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"
SPEC_FILE = PROJECT_DIR / f"{APP_NAME}.spec"

RELEASE_DIR = (
    PROJECT_DIR.parent /
    "Releases" /
    f"{APP_NAME} v{__version__}"
)

ICON = PROJECT_DIR / "assets" / "icon.png"

print("Cleaning old build...")

shutil.rmtree(DIST_DIR, ignore_errors=True)
shutil.rmtree(BUILD_DIR, ignore_errors=True)

if SPEC_FILE.exists():
    SPEC_FILE.unlink()

command = [
    "pyinstaller",
    "--onefile",
    "--windowed",
    "--clean",
    "--name", APP_NAME,
    "main.py",
]

if ICON.exists():
    command.extend([
        "--icon",
        str(ICON)
    ])

print("Building...")

subprocess.run(command, check=True)

RELEASE_DIR.mkdir(parents=True, exist_ok=True)

exe = DIST_DIR / f"{APP_NAME}.exe"

shutil.copy2(
    exe,
    RELEASE_DIR / exe.name
)

print()
print("=" * 40)
print(f"Build complete!")
print(f"Version : {__version__}")
print(f"Output  : {RELEASE_DIR}")
print("=" * 40)