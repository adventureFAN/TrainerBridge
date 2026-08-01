# TrainerBridge pre-build update

This update adds:

- a warning for trainers that exit with a non-zero code within 15 seconds;
- a direct button to Prefix Components from that warning;
- Game and AppID inside the hidden technical-details section;
- saved About dialog position (Main and Prefix Components already use saved geometry);
- an Ubuntu 22.04 Podman/Docker release build;
- pinned Python build dependencies;
- AppImage plus FUSE-free portable `.tar.xz` output;
- frozen/AppDir/AppImage self-tests;
- relative SHA256 files;
- checks for developer-specific absolute paths.
