#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

REPO="adventureFAN/TrainerBridge"
EXPECTED_BRANCH="main"

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

step() {
    printf '\n============================================================\n'
    printf '%s\n' "$*"
    printf '============================================================\n'
}

confirm() {
    local answer
    printf '\n%s [y/N] ' "$1"
    read -r answer
    [[ "$answer" =~ ^[Yy]$ ]]
}

command -v git >/dev/null 2>&1 || fail "git is not installed."
command -v python3 >/dev/null 2>&1 || fail "python3 is not installed."
command -v gh >/dev/null 2>&1 || fail "GitHub CLI (gh) is not installed. Install/login to gh first, then run this script again."

[[ -d .git ]] || fail "This is not the TrainerBridge Git working tree: $PROJECT_ROOT"

VERSION="$(python3 -c 'from core.version import APP_VERSION; print(APP_VERSION)')"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "Unexpected APP_VERSION: $VERSION"

TAG="v$VERSION"
TITLE="TrainerBridge $VERSION"
NOTES="docs/RELEASE_NOTES_${VERSION}.md"
APPIMAGE="release/TrainerBridge-${VERSION}-x86_64.AppImage"
APPIMAGE_SHA="${APPIMAGE}.sha256"
ARCHIVE="release/TrainerBridge-${VERSION}-x86_64.tar.xz"
ARCHIVE_SHA="${ARCHIVE}.sha256"
ASSETS=("$APPIMAGE" "$APPIMAGE_SHA" "$ARCHIVE" "$ARCHIVE_SHA")

step "TrainerBridge $VERSION release preflight"

BRANCH="$(git branch --show-current)"
[[ "$BRANCH" == "$EXPECTED_BRANCH" ]] || fail "Expected branch '$EXPECTED_BRANCH', but current branch is '$BRANCH'."

ORIGIN_URL="$(git remote get-url origin 2>/dev/null || true)"
case "$ORIGIN_URL" in
    https://github.com/adventureFAN/TrainerBridge|https://github.com/adventureFAN/TrainerBridge.git|git@github.com:adventureFAN/TrainerBridge.git|ssh://git@github.com/adventureFAN/TrainerBridge.git)
        ;;
    *)
        fail "Unexpected origin remote: ${ORIGIN_URL:-<missing>}"
        ;;
esac

[[ -f "$NOTES" ]] || fail "Missing release notes: $NOTES"
for asset in "${ASSETS[@]}"; do
    [[ -f "$asset" ]] || fail "Missing release asset: $asset"
done

printf 'Repository: %s\n' "$REPO"
printf 'Branch:     %s\n' "$BRANCH"
printf 'Version:    %s\n' "$VERSION"
printf 'Tag:        %s\n' "$TAG"
printf 'Origin:     %s\n' "$ORIGIN_URL"

step "GitHub authentication"
gh auth status -h github.com

step "Final release artifact verification"
(
    cd release
    sha256sum -c "TrainerBridge-${VERSION}-x86_64.AppImage.sha256"
    sha256sum -c "TrainerBridge-${VERSION}-x86_64.tar.xz.sha256"
)

QT_QPA_PLATFORM=offscreen APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGE" --self-test

step "Final source hygiene checks"
python3 tests/test_source_hygiene.py
python3 tests/test_version_metadata.py
git diff --check

step "Stage complete public source"
git add -A

git diff --cached --check

FORBIDDEN_TRACKED="$({
    git diff --cached --name-only
    git ls-files
} | sort -u | grep -E '(^|/)(venv|\.build-venv|build|dist|release|TrainerBridge\.AppDir|tools|__pycache__)(/|$)|(^|/)\.git(/|$)|\.AppImage$|\.zip$|\.before-step' || true)"

if [[ -n "$FORBIDDEN_TRACKED" ]]; then
    printf '%s\n' "$FORBIDDEN_TRACKED" >&2
    fail "Generated/local files would be committed. Remove them from Git staging/tracking before release."
fi

printf '\nFiles staged for the release commit:\n'
git diff --cached --name-status || true
printf '\nDiff summary:\n'
git diff --cached --stat || true

if ! git diff --cached --quiet; then
    confirm "Commit these source changes as '$TITLE'?" || fail "Cancelled before commit. Nothing was pushed."
    git commit -m "Release TrainerBridge $VERSION"
else
    printf '\nNo uncommitted source changes; existing HEAD will be released.\n'
fi

[[ -z "$(git status --porcelain)" ]] || {
    git status --short
    fail "Working tree is not clean after the release commit."
}

step "Check remote state"
git fetch origin --tags

if git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
    fail "Remote tag $TAG already exists. Refusing to overwrite an existing release tag."
fi

if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
    fail "GitHub Release $TAG already exists. Refusing to overwrite it."
fi

printf 'Commit to publish: %s\n' "$(git rev-parse --short HEAD)"
printf 'Commit subject:    %s\n' "$(git log -1 --pretty=%s)"

confirm "Push main, create/push $TAG, and upload the four assets to a GitHub DRAFT release?" || fail "Cancelled before GitHub changes."

step "Push source"
git push origin "$BRANCH"

step "Create and push annotated tag"
git tag -a "$TAG" -m "$TITLE"
git push origin "$TAG"

step "Create GitHub draft release and upload assets"
gh release create "$TAG" \
    "${ASSETS[@]}" \
    --repo "$REPO" \
    --verify-tag \
    --title "$TITLE" \
    --notes-file "$NOTES" \
    --draft

printf '\nSUCCESS: Source, tag, release notes, and release assets are on GitHub.\n'
printf 'The release is intentionally still a DRAFT. Review it on GitHub and click Publish release.\n'
printf 'GitHub will provide Source code (zip) and Source code (tar.gz) automatically from tag %s.\n' "$TAG"
