#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

PROJECT_ROOT="$(
    cd "$SCRIPT_DIR/.."
    pwd
)"

APP_NAME="TrainerBridge"
VERSION="0.9.0-beta.2"
ARCHITECTURE="x86_64"

BUILD_VENV="$PROJECT_ROOT/.build-venv"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"
APPDIR="$PROJECT_ROOT/${APP_NAME}.AppDir"
RELEASE_DIR="$PROJECT_ROOT/release"
TOOLS_DIR="$PROJECT_ROOT/tools"

APPIMAGETOOL="$TOOLS_DIR/appimagetool-${ARCHITECTURE}.AppImage"
APPIMAGE_OUTPUT="$RELEASE_DIR/${APP_NAME}-${VERSION}-${ARCHITECTURE}.AppImage"

APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCHITECTURE}.AppImage"

required_files=(
    "$PROJECT_ROOT/main.py"
    "$PROJECT_ROOT/components_dialog.py"
    "$PROJECT_ROOT/about_dialog.py"
    "$PROJECT_ROOT/assets/trainerbridge.png"
    "$PROJECT_ROOT/packaging/TrainerBridge.spec"
    "$PROJECT_ROOT/packaging/trainerbridge.desktop"
    "$PROJECT_ROOT/packaging/AppRun"
    "$PROJECT_ROOT/requirements-build.txt"
)

for required_file in "${required_files[@]}"; do

    if [[ ! -f "$required_file" ]]; then

        echo "Missing required file: $required_file" >&2
        exit 1

    fi

done

if ! command -v python3 >/dev/null 2>&1; then

    echo "python3 was not found." >&2
    exit 1

fi

if ! command -v curl >/dev/null 2>&1; then

    echo "curl was not found." >&2
    exit 1

fi

if [[ ! -d "$BUILD_VENV" ]]; then

    echo "Creating isolated build environment..."

    python3 -m venv "$BUILD_VENV"

fi

# shellcheck disable=SC1091
source "$BUILD_VENV/bin/activate"

echo "Installing or updating build dependencies..."

python -m pip install --upgrade pip wheel
python -m pip install --upgrade -r "$PROJECT_ROOT/requirements-build.txt"

echo "Cleaning previous build output..."

rm -rf \
    "$BUILD_DIR" \
    "$DIST_DIR" \
    "$APPDIR"

mkdir -p \
    "$RELEASE_DIR" \
    "$TOOLS_DIR"

echo "Freezing TrainerBridge with PyInstaller..."

cd "$PROJECT_ROOT"

python -m PyInstaller \
    --noconfirm \
    --clean \
    "$PROJECT_ROOT/packaging/TrainerBridge.spec"

if [[ ! -x "$DIST_DIR/TrainerBridge/TrainerBridge" ]]; then

    echo "PyInstaller did not create the expected executable." >&2
    exit 1

fi

echo "Creating AppDir..."

mkdir -p \
    "$APPDIR/usr/bin" \
    "$APPDIR/usr/share/applications" \
    "$APPDIR/usr/share/icons/hicolor/32x32/apps" \
    "$APPDIR/usr/share/icons/hicolor/64x64/apps" \
    "$APPDIR/usr/share/icons/hicolor/128x128/apps" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
    "$APPDIR/usr/share/icons/hicolor/512x512/apps" \
    "$APPDIR/usr/share/doc/trainerbridge"

cp -a \
    "$DIST_DIR/TrainerBridge/." \
    "$APPDIR/usr/bin/"

cp \
    "$PROJECT_ROOT/packaging/AppRun" \
    "$APPDIR/AppRun"

cp \
    "$PROJECT_ROOT/packaging/trainerbridge.desktop" \
    "$APPDIR/trainerbridge.desktop"

cp \
    "$PROJECT_ROOT/packaging/trainerbridge.desktop" \
    "$APPDIR/usr/share/applications/trainerbridge.desktop"

cp \
    "$PROJECT_ROOT/assets/trainerbridge.png" \
    "$APPDIR/trainerbridge.png"

cp \
    "$PROJECT_ROOT/assets/trainerbridge-32.png" \
    "$APPDIR/usr/share/icons/hicolor/32x32/apps/trainerbridge.png"

cp \
    "$PROJECT_ROOT/assets/trainerbridge-64.png" \
    "$APPDIR/usr/share/icons/hicolor/64x64/apps/trainerbridge.png"

cp \
    "$PROJECT_ROOT/assets/trainerbridge-128.png" \
    "$APPDIR/usr/share/icons/hicolor/128x128/apps/trainerbridge.png"

cp \
    "$PROJECT_ROOT/assets/trainerbridge-256.png" \
    "$APPDIR/usr/share/icons/hicolor/256x256/apps/trainerbridge.png"

cp \
    "$PROJECT_ROOT/assets/trainerbridge.png" \
    "$APPDIR/usr/share/icons/hicolor/512x512/apps/trainerbridge.png"

cp \
    "$PROJECT_ROOT/assets/THIRD_PARTY_NOTICES.txt" \
    "$APPDIR/usr/share/doc/trainerbridge/THIRD_PARTY_NOTICES.txt"

chmod +x \
    "$APPDIR/AppRun" \
    "$APPDIR/usr/bin/TrainerBridge"

ln -sfn \
    trainerbridge.png \
    "$APPDIR/.DirIcon"

if [[ ! -x "$APPIMAGETOOL" ]]; then

    echo "Downloading appimagetool..."

    curl \
        --fail \
        --location \
        --output "$APPIMAGETOOL" \
        "$APPIMAGETOOL_URL"

    chmod +x "$APPIMAGETOOL"

fi

echo "Building AppImage..."

rm -f "$APPIMAGE_OUTPUT"

ARCH="$ARCHITECTURE" \
APPIMAGE_EXTRACT_AND_RUN=1 \
"$APPIMAGETOOL" \
    "$APPDIR" \
    "$APPIMAGE_OUTPUT"

chmod +x "$APPIMAGE_OUTPUT"

sha256sum \
    "$APPIMAGE_OUTPUT" \
    > "$APPIMAGE_OUTPUT.sha256"

echo
echo "Build complete:"
echo "$APPIMAGE_OUTPUT"
echo
echo "Run it with:"
echo "\"$APPIMAGE_OUTPUT\""
