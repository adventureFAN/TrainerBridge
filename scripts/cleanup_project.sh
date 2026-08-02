#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -f "main.py" || ! -d "core" || ! -d "packaging" ]]; then
    echo "Error: This does not look like the TrainerBridge project root."
    exit 1
fi

echo "TrainerBridge project cleanup"
echo
echo "This will:"
echo "  - remove generated AppDir/build folders"
echo "  - remove obsolete prototypes and one-off test scripts"
echo "  - keep release documentation under docs/"
echo "  - keep the application source, assets, packaging and build script"
echo
echo "The removed files remain recoverable through Git history."
echo
read -r -p "Type CLEANUP to continue: " confirmation

if [[ "$confirmation" != "CLEANUP" ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

is_tracked() {
    git ls-files --error-unmatch -- "$1" >/dev/null 2>&1
}

remove_path() {
    local path="$1"

    if [[ ! -e "$path" && ! -L "$path" ]]; then
        return
    fi

    echo "Removing $path"

    if is_tracked "$path"; then
        git rm -r -f -- "$path"
    else
        rm -rf -- "$path"
    fi
}

move_path() {
    local source="$1"
    local destination="$2"

    if [[ ! -e "$source" ]]; then
        return
    fi

    mkdir -p -- "$(dirname -- "$destination")"
    echo "Moving $source -> $destination"

    if is_tracked "$source"; then
        git mv -f -- "$source" "$destination"
    else
        mv -f -- "$source" "$destination"
    fi
}

mkdir -p docs
move_path "BETA_BUILD_GUIDE.md" "docs/BETA_BUILD_GUIDE.md"
move_path "BETA_TEST_CHECKLIST.md" "docs/BETA_TEST_CHECKLIST.md"

obsolete_files=(
    "LAYOUT_UPDATE_NOTES.md"
    "packaging/gitignore-snippet.txt"

    "steam_scan.py"
    "steam_libraries.py"
    "game_scan.py"
    "proton_scan.py"
    "launcher.py"
    "steam_launcher.py"
    "diagnose_game_process.py"

    "test_core.py"
    "test_model.py"
    "test_scanner.py"
    "test_storage.py"
    "test_import.py"
    "test_prefixes.py"
    "test_execute.py"
    "test_process_detection.py"
    "test_runtime_monitor.py"
    "test_monitor.py"
    "test_launcher.py"
    "test_session.py"
    "test_game_detection.py"
    "test_runinprefix.py"
    "test_protontricks.py"
    "test_protontricks_bwrap.py"
    "test_steam.py"
    "test_windows_version.py"
)

for file in "${obsolete_files[@]}"; do
    remove_path "$file"
done

remove_path "TrainerBridge.AppDir"
remove_path "build"
remove_path "dist"
remove_path "ui"
remove_path "tools"

find . -type d -name "__pycache__" -prune -exec rm -rf {} +
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete

python_command="python3"

if [[ -x "venv/bin/python" ]]; then
    python_command="venv/bin/python"
fi

echo
echo "Checking the remaining Python source..."
"$python_command" -m py_compile \
    main.py \
    about_dialog.py \
    components_dialog.py \
    core/*.py

echo
echo "Cleanup completed successfully."
echo
echo "Remaining top-level structure:"
find . -maxdepth 2 \
    \( -path './.git' -o -path './venv' -o -path './.build-venv' \) -prune \
    -o -maxdepth 2 -print \
    | sort

echo
echo "Git status:"
git status --short
