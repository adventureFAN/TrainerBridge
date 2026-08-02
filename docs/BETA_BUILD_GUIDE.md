# TrainerBridge RC Build Guide

TrainerBridge release builds are created inside an Ubuntu 22.04 container. This keeps the bundled Linux binaries compatible with Ubuntu 22.04 and newer distributions instead of inheriting Bazzite/Fedora's newer glibc requirement.

## Requirements

One container engine is required:

- Podman (recommended on Bazzite/Fedora)
- Docker

No local Python build environment is used for the release build.

## Build

From the project directory:

```bash
./scripts/build_appimage.sh
```

The first build downloads the Ubuntu image, installs the pinned build dependencies and may take several minutes. Later builds reuse the container cache.

## Output

The `release/` directory will contain:

```text
TrainerBridge-1.0.0-rc.1-x86_64.AppImage
TrainerBridge-1.0.0-rc.1-x86_64.AppImage.sha256
TrainerBridge-1.0.0-rc.1-x86_64.tar.xz
TrainerBridge-1.0.0-rc.1-x86_64.tar.xz.sha256
```

The AppImage is the normal release. The `.tar.xz` archive is a FUSE-free fallback.

## Test the AppImage without FUSE

```bash
APPIMAGE_EXTRACT_AND_RUN=1 \
./release/TrainerBridge-1.0.0-rc.1-x86_64.AppImage
```

## Use the portable archive

```bash
tar -xf release/TrainerBridge-1.0.0-rc.1-x86_64.tar.xz
./TrainerBridge/TrainerBridge
```

## Automatic build checks

The build fails if:

- the frozen application self-test fails;
- the AppDir self-test fails;
- the AppImage self-test fails;
- developer-specific `/home/alex` paths are embedded;
- the old project name `ProtonTrainerManager` is embedded;
- the desktop entry is invalid.

The build also reports the highest `GLIBC_*` symbol found in bundled ELF files and creates checksums with relative filenames.
