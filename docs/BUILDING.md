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

## Output

The `release/` directory contains:

```text
TrainerBridge-1.0.0-x86_64.AppImage
TrainerBridge-1.0.0-x86_64.AppImage.sha256
TrainerBridge-1.0.0-x86_64.tar.xz
TrainerBridge-1.0.0-x86_64.tar.xz.sha256
```

The AppImage is the normal release. The `.tar.xz` archive is a FUSE-free fallback.

## Test the AppImage

```bash
./release/TrainerBridge-1.0.0-x86_64.AppImage --self-test

APPIMAGE_EXTRACT_AND_RUN=1 \
  ./release/TrainerBridge-1.0.0-x86_64.AppImage --self-test
```

## Use the portable archive

```bash
tar -xf release/TrainerBridge-1.0.0-x86_64.tar.xz
./TrainerBridge/TrainerBridge
```

## Automatic build checks

The build fails when:

- the frozen application self-test fails;
- the AppDir self-test fails;
- the AppImage self-test fails;
- developer-specific `/home/alex` paths are embedded;
- the old project name `ProtonTrainerManager` is embedded;
- the desktop entry is invalid.

The build reports the highest bundled `GLIBC_*` symbol requirement and generates SHA-256 checksum files with relative filenames.

The build also collects project and Python-package license files into the AppImage and portable archive.
