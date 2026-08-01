import hashlib
import json
import os
import re
import shutil
import subprocess

from dataclasses import dataclass

from core.paths import CACHE_DIR
from core.host_process import host_environment
from core.process_monitor import ProcessMonitor


FLATPAK_APP_ID = (
    "com.github.Matoking.protontricks"
)


SUPPORTED_CATEGORIES = {
    "dlls": "DLLs & Runtimes",
    "fonts": "Fonts",
    "settings": "Settings",
    "apps": "Windows Applications"
}


WINDOWS_VERSION_VERBS = {
    "nt351",
    "nt40",
    "vista",
    "win10",
    "win11",
    "win20",
    "win2k",
    "win2k3",
    "win2k8",
    "win2k8r2",
    "win30",
    "win31",
    "win7",
    "win8",
    "win81",
    "win95",
    "win98",
    "winme",
    "winxp",
    "winver="
}


WINDOWS_VERSION_LABELS = {
    "nt351": "Windows NT 3.51",
    "nt40": "Windows NT 4.0",
    "vista": "Windows Vista",
    "win10": "Windows 10",
    "win11": "Windows 11",
    "win20": "Windows 2.0",
    "win2k": "Windows 2000",
    "win2k3": "Windows Server 2003",
    "win2k8": "Windows Server 2008",
    "win2k8r2": "Windows Server 2008 R2",
    "win30": "Windows 3.0",
    "win31": "Windows 3.1",
    "win7": "Windows 7",
    "win8": "Windows 8",
    "win81": "Windows 8.1",
    "win95": "Windows 95",
    "win98": "Windows 98",
    "winme": "Windows Me",
    "winxp": "Windows XP",
    "winver=": "Windows 7 (legacy default)"
}


WINECFG_VERSION_TO_VERB = {
    "win2003": "win2k3",
    "win2008": "win2k8",
    "win2008r2": "win2k8r2",
    "winxp64": "winxp"
}


VERB_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9_.+=-]*$"
)


IGNORED_OUTPUT_NAMES = {
    "bwrap",
    "error",
    "executing",
    "flatpak",
    "info",
    "note",
    "protontricks",
    "using",
    "warning",
    "wine",
    "wineserver"
}


class ProtontricksError(
    RuntimeError
):

    pass


class ProtontricksCommandError(
    ProtontricksError
):

    def __init__(
        self,
        command,
        return_code,
        output
    ):

        self.command = command
        self.return_code = return_code
        self.output = output

        command_text = " ".join(
            str(part)
            for part in command
        )

        message = (
            "The Protontricks command failed.\n"
            f"Command: {command_text}\n"
            f"Exit code: {return_code}"
        )

        if output.strip():

            message += (
                "\n\nOutput:\n"
                f"{output.strip()}"
            )

        super().__init__(
            message
        )


@dataclass(
    frozen=True
)
class ProtontricksInstallation:

    kind: str
    command_prefix: tuple
    display_name: str


@dataclass(
    frozen=True
)
class ProtontricksComponent:

    name: str
    description: str
    category: str
    installed: bool = False


@dataclass(
    frozen=True
)
class ProtontricksCatalog:

    version: str
    components: tuple
    from_cache: bool
    windows_version: str | None


class ProtontricksManager:

    def __init__(
        self,
        installation
    ):

        self.installation = installation
        self.process_monitor = ProcessMonitor()


    @classmethod
    def detect(cls):

        native_command = shutil.which(
            "protontricks"
        )

        if native_command:

            return cls(
                ProtontricksInstallation(
                    kind="native",
                    command_prefix=(
                        native_command,
                    ),
                    display_name="System installation"
                )
            )

        flatpak_command = shutil.which(
            "flatpak"
        )

        if flatpak_command:

            result = subprocess.run(
                [
                    flatpak_command,
                    "info",
                    FLATPAK_APP_ID
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                env=host_environment()
            )

            if result.returncode == 0:

                return cls(
                    ProtontricksInstallation(
                        kind="flatpak",
                        command_prefix=(
                            flatpak_command,
                            "run",
                            FLATPAK_APP_ID
                        ),
                        display_name="Flatpak"
                    )
                )

        return None


    def build_command(
        self,
        *arguments
    ):

        command = list(
            self.installation.command_prefix
        )

        command.extend(
            str(argument)
            for argument in arguments
        )

        return command


    def _build_environment(
        self,
        force_english=False
    ):

        environment = host_environment()

        if force_english:

            environment["LANG"] = "C"
            environment["LC_ALL"] = "C"

        return environment


    def _combine_output(
        self,
        stdout,
        stderr
    ):

        output_parts = []

        if stdout:
            output_parts.append(stdout)

        if stderr:
            output_parts.append(stderr)

        return "\n".join(
            output_parts
        ).strip()


    def _run_capture(
        self,
        *arguments,
        force_english=True
    ):

        command = self.build_command(
            *arguments
        )

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=self._build_environment(
                force_english=force_english
            ),
            check=False
        )

        output = self._combine_output(
            result.stdout,
            result.stderr
        )

        if result.returncode != 0:

            raise ProtontricksCommandError(
                command=command,
                return_code=result.returncode,
                output=output
            )

        return output


    def _run_capture_allow_failure(
        self,
        *arguments,
        force_english=True
    ):

        command = self.build_command(
            *arguments
        )

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=self._build_environment(
                force_english=force_english
            ),
            check=False
        )

        output = self._combine_output(
            result.stdout,
            result.stderr
        )

        return (
            result.returncode,
            output
        )


    def get_version(self):

        output = self._run_capture(
            "--version"
        )

        fallback = None

        for line in output.splitlines():

            stripped = line.strip()

            if not stripped:
                continue

            if fallback is None:
                fallback = stripped

            if "protontricks" in stripped.lower():
                return stripped

        return fallback or "Unknown version"


    def _is_valid_verb(
        self,
        value
    ):

        if not VERB_PATTERN.fullmatch(
            value
        ):
            return False

        if value.lower() in IGNORED_OUTPUT_NAMES:
            return False

        return True


    def _parse_component_output(
        self,
        output,
        category
    ):

        components = []

        for raw_line in output.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("-"):
                continue

            parts = line.split(
                maxsplit=1
            )

            if len(parts) != 2:
                continue

            name = parts[0].strip()
            description = parts[1].strip()

            if not self._is_valid_verb(name):
                continue

            if not description:
                continue

            components.append(
                ProtontricksComponent(
                    name=name,
                    description=description,
                    category=category
                )
            )

        unique_components = {
            component.name: component
            for component in components
        }

        return sorted(
            unique_components.values(),
            key=lambda component: component.name
        )


    def _parse_installed_output(
        self,
        output
    ):

        installed = set()

        for raw_line in output.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("-"):
                continue

            first_part = line.split(
                maxsplit=1
            )[0]

            if not self._is_valid_verb(first_part):
                continue

            installed.add(
                first_part
            )

        return installed


    def list_installed(
        self,
        appid
    ):

        output = self._run_capture(
            str(appid),
            "list-installed"
        )

        return self._parse_installed_output(
            output
        )


    def list_category(
        self,
        appid,
        category
    ):

        if category not in SUPPORTED_CATEGORIES:

            raise ValueError(
                f"Unknown category: {category}"
            )

        output = self._run_capture(
            str(appid),
            category,
            "list"
        )

        return self._parse_component_output(
            output,
            category
        )


    def _parse_windows_version(
        self,
        output
    ):

        for raw_line in reversed(
            output.splitlines()
        ):

            candidate = raw_line.strip().lower()

            if not candidate:
                continue

            candidate = WINECFG_VERSION_TO_VERB.get(
                candidate,
                candidate
            )

            if candidate in WINDOWS_VERSION_VERBS:
                return candidate

        return None


    def _parse_registry_windows_version(
        self,
        output
    ):

        pattern = re.compile(
            r"\bVersion\s+REG_SZ\s+([a-zA-Z0-9]+)\b",
            re.IGNORECASE
        )

        for raw_line in output.splitlines():

            match = pattern.search(
                raw_line
            )

            if not match:
                continue

            candidate = match.group(1).lower()

            candidate = WINECFG_VERSION_TO_VERB.get(
                candidate,
                candidate
            )

            if candidate in WINDOWS_VERSION_VERBS:
                return candidate

        return None


    def get_windows_version(
        self,
        appid
    ):

        winecfg_return_code, winecfg_output = (
            self._run_capture_allow_failure(
                "-c",
                "winecfg /v",
                str(appid),
                force_english=True
            )
        )

        if winecfg_return_code == 0:

            version = self._parse_windows_version(
                winecfg_output
            )

            if version:
                return version

        registry_return_code, registry_output = (
            self._run_capture_allow_failure(
                "-c",
                (
                    'reg query "HKCU\\Software\\Wine" '
                    '/v Version'
                ),
                str(appid),
                force_english=True
            )
        )

        if registry_return_code == 0:

            version = self._parse_registry_windows_version(
                registry_output
            )

            if version:
                return version

        registry_output_lower = registry_output.lower()

        missing_value_markers = (
            "unable to find",
            "cannot find",
            "not found",
            "specified registry key",
            "specified registry value"
        )

        registry_value_is_missing = any(
            marker in registry_output_lower
            for marker in missing_value_markers
        )

        if (
            registry_value_is_missing
            or
            not registry_output.strip()
        ):

            # Modern Wine and Proton prefixes use Windows 10
            # when no explicit global Version override exists.
            return "win10"

        raise ProtontricksError(
            "TrainerBridge could not detect the current "
            "Windows compatibility version of the prefix. "
            "The prefix was not modified.\n\n"
            f"winecfg output:\n{winecfg_output}\n\n"
            f"Registry output:\n{registry_output}"
        )


    def set_windows_version(
        self,
        appid,
        version
    ):

        version = WINECFG_VERSION_TO_VERB.get(
            version,
            version
        )

        if version not in WINDOWS_VERSION_VERBS:

            raise ValueError(
                "Unsupported Windows compatibility version: "
                f"{version}"
            )

        return self._run_capture(
            str(appid),
            version,
            force_english=False
        )


    def _cache_key(
        self,
        version
    ):

        return hashlib.sha256(
            version.encode("utf-8")
        ).hexdigest()[:16]


    def _cache_file(
        self,
        version
    ):

        return (
            CACHE_DIR
            / (
                "protontricks-components-"
                f"{self._cache_key(version)}.json"
            )
        )


    def _load_catalog_cache(
        self,
        version
    ):

        cache_file = self._cache_file(
            version
        )

        if not cache_file.exists():
            return None

        try:

            with open(
                cache_file,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

        except (
            OSError,
            json.JSONDecodeError
        ):

            return None

        if data.get("version") != version:
            return None

        raw_components = data.get(
            "components"
        )

        if not isinstance(raw_components, list):
            return None

        components = []

        for raw_component in raw_components:

            try:

                name = raw_component["name"]
                description = raw_component["description"]
                category = raw_component["category"]

            except (
                KeyError,
                TypeError
            ):

                return None

            if category not in SUPPORTED_CATEGORIES:
                continue

            components.append(
                ProtontricksComponent(
                    name=str(name),
                    description=str(description),
                    category=str(category)
                )
            )

        return sorted(
            components,
            key=lambda component: (
                component.category,
                component.name
            )
        )


    def _save_catalog_cache(
        self,
        version,
        components
    ):

        CACHE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        cache_file = self._cache_file(
            version
        )

        temporary_file = cache_file.with_suffix(
            ".tmp"
        )

        data = {
            "version": version,
            "components": [
                {
                    "name": component.name,
                    "description": component.description,
                    "category": component.category
                }
                for component in components
            ]
        }

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )

        temporary_file.replace(
            cache_file
        )


    def clear_catalog_cache(self):

        if not CACHE_DIR.exists():
            return

        for cache_file in CACHE_DIR.glob(
            "protontricks-components-*.json"
        ):

            try:
                cache_file.unlink()
            except OSError:
                pass


    def _load_or_create_catalog(
        self,
        appid,
        version,
        force_refresh=False
    ):

        if not force_refresh:

            cached_components = self._load_catalog_cache(
                version
            )

            if cached_components is not None:

                return (
                    cached_components,
                    True
                )

        components = []

        for category in SUPPORTED_CATEGORIES:

            components.extend(
                self.list_category(
                    appid,
                    category
                )
            )

        components = sorted(
            components,
            key=lambda component: (
                component.category,
                component.name
            )
        )

        self._save_catalog_cache(
            version,
            components
        )

        return (
            components,
            False
        )


    def load_components(
        self,
        appid,
        force_refresh=False
    ):

        version = self.get_version()

        catalog_components, from_cache = (
            self._load_or_create_catalog(
                appid=appid,
                version=version,
                force_refresh=force_refresh
            )
        )

        installed_components = self.list_installed(
            appid
        )

        try:

            windows_version = self.get_windows_version(
                appid
            )

        except ProtontricksError:

            windows_version = None

        components = []

        for component in catalog_components:

            if component.name in WINDOWS_VERSION_VERBS:

                installed = (
                    windows_version is not None
                    and
                    component.name == windows_version
                )

            else:

                installed = (
                    component.name
                    in installed_components
                )

            components.append(
                ProtontricksComponent(
                    name=component.name,
                    description=component.description,
                    category=component.category,
                    installed=installed
                )
            )

        return ProtontricksCatalog(
            version=version,
            components=tuple(components),
            from_cache=from_cache,
            windows_version=windows_version
        )


    def list_components(
        self,
        appid,
        force_refresh=False
    ):

        return list(
            self.load_components(
                appid,
                force_refresh=force_refresh
            ).components
        )


    def validate_component_name(
        self,
        component_name
    ):

        component_name = component_name.strip()

        if not self._is_valid_verb(
            component_name
        ):

            raise ValueError(
                "Invalid component name: "
                f"{component_name}"
            )

        return component_name


    def validate_component_names(
        self,
        component_names
    ):

        validated_names = []
        seen_names = set()

        for component_name in component_names:

            validated_name = self.validate_component_name(
                component_name
            )

            if validated_name in seen_names:
                continue

            seen_names.add(
                validated_name
            )

            validated_names.append(
                validated_name
            )

        if not validated_names:

            raise ValueError(
                "No components were selected."
            )

        return validated_names


    def game_is_running(
        self,
        appid
    ):

        return (
            self.process_monitor.get_runtime(
                str(appid)
            )
            is not None
        )


    def build_install_command(
        self,
        appid,
        component_names
    ):

        validated_names = self.validate_component_names(
            component_names
        )

        return self.build_command(
            str(appid),
            *validated_names
        )


    def install_components_capture(
        self,
        appid,
        component_names
    ):

        if self.game_is_running(appid):

            raise ProtontricksError(
                "The selected game is still running. "
                "Close the game and its trainer before "
                "modifying the Proton prefix."
            )

        validated_names = self.validate_component_names(
            component_names
        )

        selected_windows_versions = [
            name
            for name in validated_names
            if name in WINDOWS_VERSION_VERBS
        ]

        if len(selected_windows_versions) > 1:

            raise ProtontricksError(
                "Select only one Windows compatibility version "
                "per installation. The prefix was not modified."
            )

        requested_windows_version = (
            selected_windows_versions[0]
            if selected_windows_versions
            else None
        )

        install_names = [
            name
            for name in validated_names
            if name not in WINDOWS_VERSION_VERBS
        ]

        try:

            original_windows_version = self.get_windows_version(
                appid
            )

        except ProtontricksError:

            if requested_windows_version is None:
                raise

            original_windows_version = None

        final_windows_version = (
            requested_windows_version
            or
            original_windows_version
        )

        output_sections = []

        if original_windows_version:

            original_label = WINDOWS_VERSION_LABELS.get(
                original_windows_version,
                original_windows_version
            )

            output_sections.append(
                "Windows compatibility version before "
                f"installation: {original_label}"
            )

        installation_error = None
        restoration_error = None

        try:

            if install_names:

                command = self.build_install_command(
                    appid,
                    install_names
                )

                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    env=self._build_environment(),
                    check=False
                )

                output = self._combine_output(
                    result.stdout,
                    result.stderr
                )

                if output:
                    output_sections.append(output)

                if result.returncode != 0:

                    installation_error = ProtontricksCommandError(
                        command=command,
                        return_code=result.returncode,
                        output=output
                    )

        finally:

            if final_windows_version:

                try:

                    restore_output = self.set_windows_version(
                        appid,
                        final_windows_version
                    )

                    final_label = WINDOWS_VERSION_LABELS.get(
                        final_windows_version,
                        final_windows_version
                    )

                    output_sections.append(
                        "Windows compatibility version after "
                        f"installation: {final_label}"
                    )

                    if restore_output:
                        output_sections.append(restore_output)

                except Exception as error:

                    restoration_error = error

        if installation_error:

            if restoration_error:

                raise ProtontricksError(
                    f"{installation_error}\n\n"
                    "TrainerBridge also failed to restore the "
                    "Windows compatibility version:\n"
                    f"{restoration_error}"
                )

            raise installation_error

        if restoration_error:

            raise ProtontricksError(
                "The selected components were installed, but "
                "TrainerBridge could not restore the Windows "
                "compatibility version. Open Prefix Components "
                "and apply the correct Windows version manually.\n\n"
                f"Details: {restoration_error}"
            )

        return "\n\n".join(
            section
            for section in output_sections
            if section
        )


    def install_component_capture(
        self,
        appid,
        component_name
    ):

        return self.install_components_capture(
            appid,
            [component_name]
        )
