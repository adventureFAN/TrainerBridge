#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/workspace"
APP_NAME="$(
    cd "$PROJECT_ROOT"
    python3 -c 'from core.version import APP_NAME; print(APP_NAME)'
)"
VERSION="$(
    cd "$PROJECT_ROOT"
    python3 -c 'from core.version import APP_VERSION; print(APP_VERSION)'
)"
ARCHITECTURE="x86_64"

BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"
APPDIR="$PROJECT_ROOT/${APP_NAME}.AppDir"
PORTABLE_STAGE="$PROJECT_ROOT/.portable-stage"
RELEASE_DIR="$PROJECT_ROOT/release"
TOOLS_DIR="$PROJECT_ROOT/tools"

APPIMAGETOOL="$TOOLS_DIR/appimagetool-${ARCHITECTURE}.AppImage"
APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCHITECTURE}.AppImage"

APPIMAGE_NAME="${APP_NAME}-${VERSION}-${ARCHITECTURE}.AppImage"
ARCHIVE_NAME="${APP_NAME}-${VERSION}-${ARCHITECTURE}.tar.xz"
APPIMAGE_OUTPUT="$RELEASE_DIR/$APPIMAGE_NAME"
ARCHIVE_OUTPUT="$RELEASE_DIR/$ARCHIVE_NAME"

export HOME="${HOME:-/tmp/trainerbridge-build-home}"
mkdir -p "$HOME" "$RELEASE_DIR" "$TOOLS_DIR"

required_files=(
    "$PROJECT_ROOT/main.py"
    "$PROJECT_ROOT/components_dialog.py"
    "$PROJECT_ROOT/about_dialog.py"
    "$PROJECT_ROOT/options_dialog.py"
    "$PROJECT_ROOT/assets/trainerbridge.png"
    "$PROJECT_ROOT/packaging/TrainerBridge.spec"
    "$PROJECT_ROOT/packaging/trainerbridge.desktop"
    "$PROJECT_ROOT/packaging/AppRun"
)

for required_file in "${required_files[@]}"; do
    if [[ ! -f "$required_file" ]]; then
        echo "Missing required file: $required_file" >&2
        exit 1
    fi
done

echo "Build environment:"
python3 --version
ldd --version | head -n 1
python3 -m PyInstaller --version

echo "Cleaning previous build output..."
rm -rf \
    "$BUILD_DIR" \
    "$DIST_DIR" \
    "$APPDIR" \
    "$PORTABLE_STAGE"

rm -f \
    "$APPIMAGE_OUTPUT" \
    "$APPIMAGE_OUTPUT.sha256" \
    "$ARCHIVE_OUTPUT" \
    "$ARCHIVE_OUTPUT.sha256"

echo "Freezing TrainerBridge with PyInstaller..."
cd "$PROJECT_ROOT"
python3 -m PyInstaller \
    --noconfirm \
    --clean \
    "$PROJECT_ROOT/packaging/TrainerBridge.spec"

FROZEN_EXECUTABLE="$DIST_DIR/TrainerBridge/TrainerBridge"

if [[ ! -x "$FROZEN_EXECUTABLE" ]]; then
    echo "PyInstaller did not create the expected executable." >&2
    exit 1
fi

echo "Running frozen application self-test..."
QT_QPA_PLATFORM=offscreen \
"$FROZEN_EXECUTABLE" --self-test

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

cp -a "$DIST_DIR/TrainerBridge/." "$APPDIR/usr/bin/"
cp "$PROJECT_ROOT/packaging/AppRun" "$APPDIR/AppRun"
cp "$PROJECT_ROOT/packaging/trainerbridge.desktop" "$APPDIR/trainerbridge.desktop"
cp "$PROJECT_ROOT/packaging/trainerbridge.desktop" "$APPDIR/usr/share/applications/trainerbridge.desktop"
cp "$PROJECT_ROOT/assets/trainerbridge.png" "$APPDIR/trainerbridge.png"
cp "$PROJECT_ROOT/assets/trainerbridge-32.png" "$APPDIR/usr/share/icons/hicolor/32x32/apps/trainerbridge.png"
cp "$PROJECT_ROOT/assets/trainerbridge-64.png" "$APPDIR/usr/share/icons/hicolor/64x64/apps/trainerbridge.png"
cp "$PROJECT_ROOT/assets/trainerbridge-128.png" "$APPDIR/usr/share/icons/hicolor/128x128/apps/trainerbridge.png"
cp "$PROJECT_ROOT/assets/trainerbridge-256.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/trainerbridge.png"
cp "$PROJECT_ROOT/assets/trainerbridge.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/trainerbridge.png"
cp "$PROJECT_ROOT/assets/THIRD_PARTY_NOTICES.txt" "$APPDIR/usr/share/doc/trainerbridge/THIRD_PARTY_NOTICES.txt"

chmod +x "$APPDIR/AppRun" "$APPDIR/usr/bin/TrainerBridge"
ln -sfn trainerbridge.png "$APPDIR/.DirIcon"

desktop-file-validate "$APPDIR/trainerbridge.desktop"

echo "Running AppDir self-test..."
QT_QPA_PLATFORM=offscreen \
"$APPDIR/AppRun" --self-test

echo "Checking for developer-specific absolute paths..."
for forbidden_text in "/home/alex" "ProtonTrainerManager"; do
    if grep -R -a -F -l "$forbidden_text" "$APPDIR" >/tmp/trainerbridge-path-hits.txt 2>/dev/null; then
        echo "Found forbidden build path text: $forbidden_text" >&2
        cat /tmp/trainerbridge-path-hits.txt >&2
        exit 1
    fi
done

echo "Determining maximum bundled GLIBC symbol requirement..."
MAX_GLIBC="$({
    while IFS= read -r -d '' file_path; do
        if file "$file_path" | grep -q 'ELF'; then
            strings "$file_path" 2>/dev/null \
                | grep -Eo 'GLIBC_[0-9]+(\.[0-9]+)*' \
                || true
        fi
    done < <(find "$APPDIR" -type f -print0)
} | sort -V | tail -n 1)"

echo "Maximum GLIBC symbol found: ${MAX_GLIBC:-none}"

if [[ ! -x "$APPIMAGETOOL" ]]; then
    echo "Downloading appimagetool..."
    curl \
        --fail \
        --location \
        --retry 3 \
        --output "$APPIMAGETOOL" \
        "$APPIMAGETOOL_URL"
    chmod +x "$APPIMAGETOOL"
fi

echo "Building AppImage..."
ARCH="$ARCHITECTURE" \
APPIMAGE_EXTRACT_AND_RUN=1 \
"$APPIMAGETOOL" \
    "$APPDIR" \
    "$APPIMAGE_OUTPUT"

chmod +x "$APPIMAGE_OUTPUT"

echo "Running AppImage self-test without FUSE..."
QT_QPA_PLATFORM=offscreen \
APPIMAGE_EXTRACT_AND_RUN=1 \
"$APPIMAGE_OUTPUT" --self-test

echo "Creating portable tar.xz fallback..."
mkdir -p "$PORTABLE_STAGE/$APP_NAME"
cp -a "$DIST_DIR/TrainerBridge/." "$PORTABLE_STAGE/$APP_NAME/"
cp "$PROJECT_ROOT/assets/THIRD_PARTY_NOTICES.txt" "$PORTABLE_STAGE/$APP_NAME/THIRD_PARTY_NOTICES.txt"

tar \
    --create \
    --xz \
    --file "$ARCHIVE_OUTPUT" \
    --directory "$PORTABLE_STAGE" \
    "$APP_NAME"

(
    cd "$RELEASE_DIR"
    sha256sum "$APPIMAGE_NAME" > "$APPIMAGE_NAME.sha256"
    sha256sum "$ARCHIVE_NAME" > "$ARCHIVE_NAME.sha256"
)

rm -rf "$PORTABLE_STAGE"

echo
echo "Build complete:"
echo "  $APPIMAGE_OUTPUT"
echo "  $ARCHIVE_OUTPUT"
echo
echo "AppImage test command:"
echo "  APPIMAGE_EXTRACT_AND_RUN=1 \"$APPIMAGE_OUTPUT\" --self-test"
echo
echo "Portable archive start command after extraction:"
echo "  ./TrainerBridge/TrainerBridge"
