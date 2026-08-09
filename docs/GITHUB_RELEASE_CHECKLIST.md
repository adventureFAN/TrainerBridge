# GitHub Release Checklist for TrainerBridge 1.0.1

## 1. Final source and runtime checks

The release version must come from `core/version.py` and read `1.0.1`.

Before publishing, the full 1.0.1 regression suite, the source self-test, the real Bazzite smoke tests, the final AppImage build, both SHA-256 checks, and the final AppImage self-test must all have passed.

## 2. Expected release artifacts

The final build must provide:

```text
release/TrainerBridge-1.0.1-x86_64.AppImage
release/TrainerBridge-1.0.1-x86_64.AppImage.sha256
release/TrainerBridge-1.0.1-x86_64.tar.xz
release/TrainerBridge-1.0.1-x86_64.tar.xz.sha256
```

Verify checksums:

```bash
cd ~/TrainerBridge/release
sha256sum -c TrainerBridge-1.0.1-x86_64.AppImage.sha256
sha256sum -c TrainerBridge-1.0.1-x86_64.tar.xz.sha256
```

Run the final AppImage self-test:

```bash
./TrainerBridge-1.0.1-x86_64.AppImage --self-test
```

## 3. Publish helper

The repository contains `scripts/publish_github_release.sh` to perform the final Git/GitHub handoff safely.

It:

1. verifies version, repository, GitHub CLI authentication, checksums, AppImage self-test, and source hygiene;
2. stages the complete public source while rejecting generated/build paths;
3. shows the staged file list and diff summary before asking for confirmation;
4. creates the release commit if required;
5. pushes `main`;
6. creates and pushes annotated tag `v1.0.1`;
7. creates a **draft** GitHub Release with `docs/RELEASE_NOTES_1.0.1.md` and the four release assets.

Run from the project directory:

```bash
cd ~/TrainerBridge
./scripts/publish_github_release.sh
```

The script deliberately creates a draft rather than immediately publishing it. Review the GitHub draft once, then click **Publish release**.

## 4. What belongs in GitHub

The Git repository contains the actual source, tests, documentation, packaging files, and build scripts.

Generated/local content must not be committed, including:

```text
venv/
.build-venv/
build/
dist/
release/
TrainerBridge.AppDir/
tools/
__pycache__/
```

The four files under `release/` are uploaded as GitHub Release assets rather than tracked in Git.

GitHub automatically exposes source-code `.zip` and `.tar.gz` downloads for the tagged repository state, so no manually prepared source archive is required.

## 5. Release metadata

Tag:

```text
v1.0.1
```

Release title:

```text
TrainerBridge 1.0.1
```

Release notes:

```text
docs/RELEASE_NOTES_1.0.1.md
```

Release assets:

```text
TrainerBridge-1.0.1-x86_64.AppImage
TrainerBridge-1.0.1-x86_64.AppImage.sha256
TrainerBridge-1.0.1-x86_64.tar.xz
TrainerBridge-1.0.1-x86_64.tar.xz.sha256
```
