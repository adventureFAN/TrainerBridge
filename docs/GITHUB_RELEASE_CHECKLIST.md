# GitHub Release Checklist for TrainerBridge 1.0.0

## 1. Prepare and test the source

```bash
cd ~/TrainerBridge

python -m py_compile \
  main.py \
  about_dialog.py \
  options_dialog.py \
  components_dialog.py \
  core/*.py

QT_QPA_PLATFORM=offscreen python main.py --self-test
```

## 2. Build release artifacts

```bash
./scripts/build_appimage.sh
```

Expected files:

```text
release/TrainerBridge-1.0.0-x86_64.AppImage
release/TrainerBridge-1.0.0-x86_64.AppImage.sha256
release/TrainerBridge-1.0.0-x86_64.tar.xz
release/TrainerBridge-1.0.0-x86_64.tar.xz.sha256
```

Verify checksums:

```bash
cd release
sha256sum -c TrainerBridge-1.0.0-x86_64.AppImage.sha256
sha256sum -c TrainerBridge-1.0.0-x86_64.tar.xz.sha256
cd ..
```

## 3. Commit the stable release

```bash
git add -A
git commit -m "Release TrainerBridge 1.0.0"
git status
```

The working tree must be clean.

## 4. Create the GitHub repository

On GitHub, create a public repository named `TrainerBridge` under `adventureFAN`.

Do not initialize it with a README, `.gitignore`, or license because the local repository already contains them.

Then connect and push:

```bash
git branch -M main
git remote add origin https://github.com/adventureFAN/TrainerBridge.git
git push -u origin main
```

When `origin` already exists, inspect it first:

```bash
git remote -v
```

## 5. Create and push the tag

```bash
git tag -a v1.0.0 -m "TrainerBridge 1.0.0"
git push origin v1.0.0
```

## 6. Create the GitHub release

Open **Releases**, choose **Draft a new release**, and select tag `v1.0.0`.

Release title:

```text
TrainerBridge 1.0.0
```

Paste the contents of `docs/RELEASE_NOTES_1.0.0.md` into the description.

Upload these four release assets:

```text
TrainerBridge-1.0.0-x86_64.AppImage
TrainerBridge-1.0.0-x86_64.AppImage.sha256
TrainerBridge-1.0.0-x86_64.tar.xz
TrainerBridge-1.0.0-x86_64.tar.xz.sha256
```

Publish it as the latest release. GitHub automatically provides source-code archives, so no manual source ZIP is required.

## 7. Repository settings

Suggested repository description:

```text
Launch standalone Windows trainers alongside Steam games running through Proton on Linux.
```

Suggested topics:

```text
linux steam proton wine trainer gaming pyside6 appimage protontricks flatpak snap
```

Enable Issues and private vulnerability reporting. Add the repository link to the About section and select the `MIT` license topic when GitHub detects it.
