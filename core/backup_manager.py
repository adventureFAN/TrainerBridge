import errno
import fcntl
import json
import os
import shutil
import tarfile
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.paths import BACKUP_DIR


FICLONE = 0x40049409
CHUNK_SIZE = 1024 * 1024


class BackupError(RuntimeError):
    pass


class BackupCancelled(BackupError):
    pass


@dataclass(frozen=True)
class BackupInfo:
    appid: str
    game_name: str
    created_at: str
    method: str
    source_size: int
    stored_size: int
    file_count: int
    proton_name: str | None
    proton_version: str | None
    windows_version: str | None
    components: tuple
    backup_path: Path


class _ProgressReader:
    def __init__(self, file_object, size, on_progress, cancel_event):
        self.file_object = file_object
        self.size = size
        self.on_progress = on_progress
        self.cancel_event = cancel_event

    def read(self, amount=-1):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise BackupCancelled("Backup creation was cancelled.")

        data = self.file_object.read(amount)
        if data:
            self.on_progress(len(data))
        return data


class BackupManager:
    def __init__(self, game):
        self.game = game
        self.appid = str(game.appid)
        self.source_path = (
            Path(game.prefix)
            if game.prefix
            else (
                Path(game.library)
                / "steamapps"
                / "compatdata"
                / self.appid
            )
        )
        self.backup_path = BACKUP_DIR / self.appid
        self.metadata_path = self.backup_path / "backup.json"

        self._recover_interrupted_operations()

    def _recover_interrupted_operations(self):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        previous_backups = sorted(
            BACKUP_DIR.glob(f".{self.appid}.previous-*")
        )
        protected_previous_backup = None

        if not self.backup_path.exists() and previous_backups:
            protected_previous_backup = previous_backups[-1]
            try:
                protected_previous_backup.rename(self.backup_path)
                protected_previous_backup = None
            except OSError:
                pass

        for previous_backup in previous_backups:
            if (
                previous_backup != protected_previous_backup
                and previous_backup.exists()
            ):
                shutil.rmtree(previous_backup, ignore_errors=True)

        for temporary_backup in BACKUP_DIR.glob(
            f".{self.appid}.creating-*"
        ):
            shutil.rmtree(temporary_backup, ignore_errors=True)

        source_parent = self.source_path.parent

        if source_parent.is_dir():
            previous_sources = sorted(
                source_parent.glob(
                    f".{self.appid}.trainerbridge-current-*"
                )
            )
            protected_previous_source = None

            if not self.source_path.exists() and previous_sources:
                protected_previous_source = previous_sources[-1]
                try:
                    protected_previous_source.rename(self.source_path)
                    protected_previous_source = None
                except OSError:
                    pass

            for previous_source in previous_sources:
                if (
                    previous_source != protected_previous_source
                    and previous_source.exists()
                ):
                    shutil.rmtree(previous_source, ignore_errors=True)

            for restore_directory in source_parent.glob(
                f".{self.appid}.trainerbridge-restore-*"
            ):
                shutil.rmtree(restore_directory, ignore_errors=True)

    @staticmethod
    def format_size(size):
        value = float(max(0, int(size or 0)))
        units = ("B", "KiB", "MiB", "GiB", "TiB")

        for unit in units:
            if value < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(value)} {unit}"
                return f"{value:.1f} {unit}"
            value /= 1024

        return f"{value:.1f} TiB"

    def _ensure_source(self):
        if self.source_path is None:
            raise BackupError("No Proton compatdata directory was found for this game.")

        if not self.source_path.is_dir():
            raise BackupError(
                "The Proton compatdata directory does not exist: "
                f"{self.source_path}"
            )

        if not (self.source_path / "pfx").is_dir():
            raise BackupError(
                "The selected compatdata directory does not contain a Proton prefix."
            )

    def _iter_entries(self, root):
        root = Path(root)
        yield root

        for current_root, directory_names, file_names in os.walk(
            root,
            topdown=True,
            followlinks=False
        ):
            current_root = Path(current_root)
            directory_names.sort()
            file_names.sort()

            for directory_name in directory_names:
                yield current_root / directory_name

            for file_name in file_names:
                yield current_root / file_name

    def source_summary(self):
        self._ensure_source()

        total_size = 0
        file_count = 0

        for entry in self._iter_entries(self.source_path):
            if entry == self.source_path:
                continue

            try:
                if entry.is_file() and not entry.is_symlink():
                    total_size += entry.stat().st_size
                file_count += 1
            except OSError:
                file_count += 1

        return total_size, file_count

    def _stored_size(self, path):
        path = Path(path)
        if not path.exists():
            return 0

        if path.is_file():
            return path.stat().st_size

        total = 0
        for entry in self._iter_entries(path):
            try:
                if entry.is_file() and not entry.is_symlink():
                    stat_result = entry.stat()
                    allocated_blocks = getattr(stat_result, "st_blocks", 0)
                    total += (
                        allocated_blocks * 512
                        if allocated_blocks
                        else stat_result.st_size
                    )
            except OSError:
                continue
        return total

    def has_backup(self):
        return self.metadata_path.is_file()

    def load_info(self):
        if not self.metadata_path.is_file():
            return None

        try:
            data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None

        method = str(data.get("method") or "")
        payload_name = "compatdata.tar.zst" if method == "compressed" else "compatdata"
        payload_path = self.backup_path / payload_name

        if not payload_path.exists():
            return None

        return BackupInfo(
            appid=str(data.get("appid") or self.appid),
            game_name=str(data.get("game_name") or self.game.name),
            created_at=str(data.get("created_at") or ""),
            method=method,
            source_size=int(data.get("source_size") or 0),
            stored_size=int(data.get("stored_size") or self._stored_size(payload_path)),
            file_count=int(data.get("file_count") or 0),
            proton_name=data.get("proton_name"),
            proton_version=data.get("proton_version"),
            windows_version=data.get("windows_version"),
            components=tuple(data.get("components") or ()),
            backup_path=payload_path
        )

    def _first_regular_file(self):
        for entry in self._iter_entries(self.source_path):
            try:
                if entry.is_file() and not entry.is_symlink():
                    return entry
            except OSError:
                continue
        return None

    def _supports_reflink(self, destination_parent):
        source_file = self._first_regular_file()
        if source_file is None:
            return False

        destination_parent = Path(destination_parent)
        destination_parent.mkdir(parents=True, exist_ok=True)

        handle, test_name = tempfile.mkstemp(
            prefix=".trainerbridge-reflink-test-",
            dir=destination_parent
        )
        os.close(handle)
        test_path = Path(test_name)

        try:
            with source_file.open("rb") as source, test_path.open("wb") as target:
                fcntl.ioctl(target.fileno(), FICLONE, source.fileno())
            return True
        except OSError:
            return False
        finally:
            try:
                test_path.unlink()
            except OSError:
                pass

    def resolve_method(self, requested_method):
        requested_method = str(requested_method or "auto")

        if requested_method == "compressed":
            return "compressed"

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        reflink_supported = self._supports_reflink(BACKUP_DIR)

        if requested_method == "folder":
            return "reflink" if reflink_supported else "folder"

        return "reflink" if reflink_supported else "compressed"

    def _check_cancelled(self, cancel_event):
        if cancel_event is not None and cancel_event.is_set():
            raise BackupCancelled("Backup creation was cancelled.")

    def _copy_file(self, source, target, use_reflink, progress, cancel_event):
        source = Path(source)
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)

        self._check_cancelled(cancel_event)

        if use_reflink:
            try:
                with source.open("rb") as source_file, target.open("wb") as target_file:
                    fcntl.ioctl(target_file.fileno(), FICLONE, source_file.fileno())
                shutil.copystat(source, target, follow_symlinks=False)
                progress(source.stat().st_size)
                return target
            except OSError as error:
                try:
                    target.unlink()
                except OSError:
                    pass

                if error.errno not in {
                    errno.EXDEV,
                    errno.EINVAL,
                    errno.ENOTTY,
                    errno.EOPNOTSUPP,
                    errno.ENOSYS
                }:
                    raise

        with source.open("rb") as source_file, target.open("wb") as target_file:
            while True:
                self._check_cancelled(cancel_event)
                chunk = source_file.read(CHUNK_SIZE)
                if not chunk:
                    break
                target_file.write(chunk)
                progress(len(chunk))

        shutil.copystat(source, target, follow_symlinks=False)
        return target

    def _copy_tree(self, source, target, use_reflink, progress, cancel_event=None):
        source = Path(source)
        target = Path(target)

        def copy_function(source_file, target_file):
            return str(
                self._copy_file(
                    source_file,
                    target_file,
                    use_reflink=use_reflink,
                    progress=progress,
                    cancel_event=cancel_event
                )
            )

        shutil.copytree(
            source,
            target,
            symlinks=True,
            copy_function=copy_function
        )

    def _require_zstandard(self):
        try:
            import zstandard
        except ImportError as error:
            raise BackupError(
                "Compressed backups require the Python package 'zstandard'. "
                "Install it in the development environment or rebuild the AppImage."
            ) from error
        return zstandard

    def _create_archive(self, target_archive, progress, cancel_event):
        zstandard = self._require_zstandard()

        target_archive = Path(target_archive)
        target_archive.parent.mkdir(parents=True, exist_ok=True)

        with target_archive.open("wb") as raw_file:
            compressor = zstandard.ZstdCompressor(level=6, threads=-1)

            with compressor.stream_writer(raw_file, closefd=False) as compressed_file:
                with tarfile.open(fileobj=compressed_file, mode="w|") as archive:
                    for entry in self._iter_entries(self.source_path):
                        self._check_cancelled(cancel_event)

                        relative = entry.relative_to(self.source_path)
                        archive_name = Path("compatdata") / relative
                        if entry == self.source_path:
                            archive_name = Path("compatdata")

                        tar_info = archive.gettarinfo(
                            str(entry),
                            arcname=str(archive_name)
                        )

                        if tar_info.isreg():
                            with entry.open("rb") as source_file:
                                reader = _ProgressReader(
                                    source_file,
                                    tar_info.size,
                                    progress,
                                    cancel_event
                                )
                                archive.addfile(tar_info, reader)
                        else:
                            archive.addfile(tar_info)

    def _validate_archive(self, archive_path):
        """Read a compressed backup to the end before publishing it.

        This verifies both the Zstandard stream and the TAR structure and
        confirms that the archive contains a Proton prefix. A backup is only
        published after this validation succeeds.
        """
        zstandard = self._require_zstandard()
        archive_path = Path(archive_path)

        found_compatdata = False
        found_prefix = False
        member_count = 0

        try:
            with archive_path.open("rb") as raw_file:
                with zstandard.ZstdDecompressor().stream_reader(raw_file) as reader:
                    with tarfile.open(fileobj=reader, mode="r|") as archive:
                        for member in archive:
                            member_count += 1
                            parts = Path(member.name).parts

                            if parts and parts[0] == "compatdata":
                                found_compatdata = True

                            if (
                                len(parts) >= 2
                                and parts[0] == "compatdata"
                                and parts[1] == "pfx"
                            ):
                                found_prefix = True

        except (OSError, EOFError, tarfile.TarError, zstandard.ZstdError) as error:
            raise BackupError(
                "The compressed safety backup could not be verified and was "
                "not saved.\n\n"
                f"{type(error).__name__}: {error}"
            ) from error

        if member_count == 0 or not found_compatdata or not found_prefix:
            raise BackupError(
                "The compressed safety backup did not contain a complete "
                "Proton compatdata directory and was not saved."
            )


    def _safe_member_destination(self, target_root, member_name):
        target_root = Path(target_root).resolve()
        destination = (target_root / member_name).resolve(strict=False)

        try:
            destination.relative_to(target_root)
        except ValueError as error:
            raise BackupError(
                "The backup archive contains an unsafe path and was not restored."
            ) from error

        return destination

    def _extract_archive_member(self, archive, member, target_root):
        """Extract one member while preserving Wine's absolute symlinks.

        Proton prefixes normally contain entries such as pfx/dosdevices/s:
        that point to absolute host paths. Python 3.14's default TAR safety
        filter rejects those links with AbsoluteLinkError. The archive is
        created by TrainerBridge itself, so we validate every member path
        before explicitly opting into trusted extraction.
        """
        self._safe_member_destination(target_root, member.name)

        if member.islnk():
            raise BackupError(
                "The backup archive contains an unsupported hard link and "
                "was not restored."
            )

        try:
            archive.extract(
                member,
                path=target_root,
                set_attrs=True,
                filter="fully_trusted"
            )
        except TypeError:
            # Python versions before extraction filters were introduced.
            archive.extract(
                member,
                path=target_root,
                set_attrs=True
            )

    def _extract_archive(self, archive_path, target_root, progress):
        zstandard = self._require_zstandard()
        archive_path = Path(archive_path)
        target_root = Path(target_root)
        target_root.mkdir(parents=True, exist_ok=True)

        with archive_path.open("rb") as raw_file:
            with zstandard.ZstdDecompressor().stream_reader(raw_file) as reader:
                with tarfile.open(fileobj=reader, mode="r|") as archive:
                    for member in archive:
                        self._extract_archive_member(
                            archive,
                            member,
                            target_root
                        )
                        if member.isfile():
                            progress(member.size)

    def _write_metadata(
        self,
        temporary_backup,
        method,
        source_size,
        stored_size,
        file_count,
        components,
        windows_version
    ):
        data = {
            "format_version": 1,
            "appid": self.appid,
            "game_name": self.game.name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "source_path": str(self.source_path),
            "source_size": int(source_size),
            "stored_size": int(stored_size),
            "file_count": int(file_count),
            "proton_name": self.game.proton_name,
            "proton_version": self.game.proton_version,
            "windows_version": windows_version,
            "components": list(components or ())
        }

        metadata_path = Path(temporary_backup) / "backup.json"
        metadata_path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

    def _publish_backup(self, temporary_backup):
        temporary_backup = Path(temporary_backup)
        previous_backup = BACKUP_DIR / f".{self.appid}.previous-{int(time.time())}"

        if previous_backup.exists():
            shutil.rmtree(previous_backup, ignore_errors=True)

        try:
            if self.backup_path.exists():
                self.backup_path.rename(previous_backup)

            temporary_backup.rename(self.backup_path)

        except Exception:
            if self.backup_path.exists() and not self.metadata_path.exists():
                shutil.rmtree(self.backup_path, ignore_errors=True)

            if previous_backup.exists() and not self.backup_path.exists():
                previous_backup.rename(self.backup_path)
            raise

        shutil.rmtree(previous_backup, ignore_errors=True)

    def create_backup(
        self,
        requested_method="auto",
        components=(),
        windows_version=None,
        progress_callback=None,
        cancel_event=None
    ):
        self._ensure_source()
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        source_size, file_count = self.source_summary()
        actual_method = self.resolve_method(requested_method)

        free_space = shutil.disk_usage(BACKUP_DIR).free
        if actual_method == "folder":
            required_space = source_size
        elif actual_method == "reflink":
            required_space = min(source_size, 128 * 1024 * 1024)
        else:
            required_space = min(
                source_size,
                max(256 * 1024 * 1024, source_size // 4)
            )

        if free_space < required_space:
            raise BackupError(
                "There may not be enough free space for the safety backup.\n\n"
                f"Estimated minimum: {self.format_size(required_space)}\n"
                f"Available: {self.format_size(free_space)}"
            )

        temporary_backup = BACKUP_DIR / f".{self.appid}.creating-{os.getpid()}-{int(time.time())}"
        shutil.rmtree(temporary_backup, ignore_errors=True)
        temporary_backup.mkdir(parents=True, exist_ok=False)

        processed = 0

        def report_increment(amount, message="Creating safety backup..."):
            nonlocal processed
            processed += int(amount or 0)
            if progress_callback:
                progress_callback(processed, source_size, message)

        if progress_callback:
            progress_callback(0, source_size, "Scanning and preparing the safety backup...")

        try:
            if actual_method in {"folder", "reflink"}:
                payload = temporary_backup / "compatdata"
                self._copy_tree(
                    self.source_path,
                    payload,
                    use_reflink=(actual_method == "reflink"),
                    progress=report_increment,
                    cancel_event=cancel_event
                )
            else:
                payload = temporary_backup / "compatdata.tar.zst"
                self._create_archive(
                    payload,
                    report_increment,
                    cancel_event
                )

                self._check_cancelled(cancel_event)

                if progress_callback:
                    progress_callback(
                        None,
                        None,
                        "Verifying compressed safety backup..."
                    )

                self._validate_archive(payload)

            self._check_cancelled(cancel_event)
            stored_size = self._stored_size(payload)

            self._write_metadata(
                temporary_backup=temporary_backup,
                method=("compressed" if actual_method == "compressed" else actual_method),
                source_size=source_size,
                stored_size=stored_size,
                file_count=file_count,
                components=components,
                windows_version=windows_version
            )

            self._publish_backup(temporary_backup)

        except Exception:
            shutil.rmtree(temporary_backup, ignore_errors=True)
            raise

        if progress_callback:
            progress_callback(source_size, source_size, "Safety backup completed.")

        return self.load_info()

    def restore_backup(self, progress_callback=None):
        info = self.load_info()

        if info is None:
            raise BackupError("No valid safety backup exists for this game.")

        parent = self.source_path.parent
        restore_root = parent / f".{self.appid}.trainerbridge-restore-{os.getpid()}-{int(time.time())}"
        previous_root = parent / f".{self.appid}.trainerbridge-current-{os.getpid()}-{int(time.time())}"

        shutil.rmtree(restore_root, ignore_errors=True)
        shutil.rmtree(previous_root, ignore_errors=True)
        restore_root.mkdir(parents=True, exist_ok=False)

        processed = 0
        total = max(1, info.source_size)

        def report_increment(amount, message="Restoring safety backup..."):
            nonlocal processed
            processed += int(amount or 0)
            if progress_callback:
                progress_callback(processed, total, message)

        try:
            if info.method == "compressed":
                self._extract_archive(
                    info.backup_path,
                    restore_root,
                    report_increment
                )
                restored_compatdata = restore_root / "compatdata"
            else:
                restored_compatdata = restore_root / "compatdata"
                self._copy_tree(
                    info.backup_path,
                    restored_compatdata,
                    use_reflink=self._supports_reflink(parent),
                    progress=report_increment,
                    cancel_event=None
                )

            if not (restored_compatdata / "pfx").is_dir():
                raise BackupError(
                    "The restored backup did not contain a valid Proton prefix."
                )

            source_existed = self.source_path.exists()

            if source_existed:
                self.source_path.rename(previous_root)

            try:
                restored_compatdata.rename(self.source_path)
            except Exception:
                if previous_root.exists() and not self.source_path.exists():
                    previous_root.rename(self.source_path)
                raise

            shutil.rmtree(previous_root, ignore_errors=True)

        except Exception:
            if self.source_path.exists() and not (self.source_path / "pfx").is_dir():
                shutil.rmtree(self.source_path, ignore_errors=True)

            if previous_root.exists() and not self.source_path.exists():
                previous_root.rename(self.source_path)
            raise
        finally:
            shutil.rmtree(restore_root, ignore_errors=True)

        if progress_callback:
            progress_callback(total, total, "Safety backup restored.")

        return info

    def delete_backup(self):
        if not self.backup_path.exists():
            return False

        shutil.rmtree(self.backup_path)
        return True
