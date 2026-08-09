# Building TrainerBridge

TrainerBridge release builds are created inside an Ubuntu 22.04 container. This keeps bundled Linux binaries compatible with Ubuntu 22.04 and newer distributions instead of inheriting a newer host glibc requirement.

## Requirements

One container engine is required:

- Podman, recommended on Bazzite and Fedora
- Docker

No local Python build environment is required for the release build.

## Build

```bash
./scripts/build_appimage.sh
```

The first build downloads the Ubuntu image and build tooling and may take several minutes. Later builds reuse the container cache.

The release build uses the fixed upstream `appimagetool` release **1.9.1** from the maintained `AppImage/appimagetool` repository. The cached tool filename includes that version, so changing the pinned release cannot silently reuse an older cached `continuous` binary.

## Output

The `release/` directory contains:

```text
TrainerBridge-<version>-x86_64.AppImage
TrainerBridge-<version>-x86_64.AppImage.sha256
TrainerBridge-<version>-x86_64.tar.xz
TrainerBridge-<version>-x86_64.tar.xz.sha256
```

The AppImage is the normal release. The `.tar.xz` archive is a FUSE-free fallback.

## Test the AppImage

```bash
./release/TrainerBridge-<version>-x86_64.AppImage --self-test

APPIMAGE_EXTRACT_AND_RUN=1 \
  ./release/TrainerBridge-<version>-x86_64.AppImage --self-test
```

## Use the portable archive

```bash
tar -xf release/TrainerBridge-<version>-x86_64.tar.xz
./TrainerBridge/TrainerBridge
```

## Automatic build checks

The build fails when:

- the frozen application self-test fails;
- the AppDir self-test fails;
- the AppImage self-test fails;
- developer-specific absolute home paths such as `/home/<user>/...` or `/var/home/<user>/...` are embedded in staged text content;
- the old project name `ProtonTrainerManager` is embedded;
- the desktop entry is invalid;
- the pinned `appimagetool` download cannot be obtained.

The staged home-path check intentionally treats binary dependencies as vendor artifacts rather than text. Third-party ELF libraries can contain harmless upstream build paths (for example Qt's `/home/<vendor-user>/work/...`); TrainerBridge-owned source text is covered separately by `tests/test_source_hygiene.py`.

The build reports the highest bundled `GLIBC_*` symbol requirement and generates SHA-256 checksum files with relative filenames.

The build also collects project and Python-package license files into the AppImage and portable archive.
