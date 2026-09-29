"""Configuration and application-runtime migrations for 2.8.35."""
import copy
import os
import shutil


def _same_filesystem(source: str, destination_parent: str) -> bool:
    """Return True when source and destination live on the same filesystem."""
    try:
        return os.stat(source).st_dev == os.stat(destination_parent).st_dev
    except OSError:
        # st_dev is normally sufficient on all supported platforms. Keep a
        # conservative Windows fallback for unusual filesystems/providers.
        if os.name == "nt":
            source_drive = os.path.splitdrive(os.path.abspath(source))[0].lower()
            target_drive = os.path.splitdrive(os.path.abspath(destination_parent))[0].lower()
            return bool(source_drive) and source_drive == target_drive
        return False


def _directory_size(path: str) -> int:
    """Return the amount of file data that must be copied cross-filesystem."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        # Symlinked directories are moved as links; do not walk their targets.
        dirnames[:] = [
            name for name in dirnames
            if not os.path.islink(os.path.join(dirpath, name))
        ]
        for name in filenames:
            item = os.path.join(dirpath, name)
            try:
                total += os.lstat(item).st_size
            except OSError:
                continue
    return total


def _directory_has_payload(path: str) -> bool:
    """Return True if a directory contains files or symlinks, not only empty dirs."""
    if os.path.islink(path):
        return True
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        if filenames:
            return True
        for name in dirnames:
            if os.path.islink(os.path.join(dirpath, name)):
                return True
    return False


def _format_bytes(value: int) -> str:
    size = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{int(value)} B"


def _migrate_application_runtime_dir(window, name: str) -> bool:
    """Move a profile-local runtime directory into the application base workdir.

    Same-filesystem migrations use a direct move and intentionally skip free
    space accounting. Cross-filesystem moves first verify that the destination
    volume has enough free space for the complete source directory.
    """
    config = window.core.config
    workdir = os.path.realpath(config.get_user_path())
    base_workdir = os.path.realpath(config.get_base_workdir())
    # If the active workdir is already the application base workdir, the
    # runtime directory is already global and there is nothing to migrate.
    if os.path.normcase(workdir) == os.path.normcase(base_workdir):
        return False

    source = os.path.join(workdir, name)
    destination = os.path.join(base_workdir, name)
    # Do not follow a profile-controlled symlink and accidentally migrate its
    # external target into the application runtime directory.
    if not os.path.isdir(source) or os.path.islink(source):
        return False

    os.makedirs(base_workdir, exist_ok=True)

    # RuntimePackages.activate() may have pre-created an empty
    # extra_packages/<python-version> tree before config migration runs. Such
    # empty scaffolding is safe to replace. For sandbox we intentionally replace
    # an existing application-global sandbox with the profile-local one being
    # migrated. A sandbox is disposable runtime state and the old profile copy
    # is the one that belongs to the user configuration being upgraded.
    destination_exists = os.path.lexists(destination)
    destination_size = 0
    if destination_exists:
        if name == "sandbox":
            # On a cross-filesystem migration the existing destination will be
            # removed before copying, so its occupied bytes become available.
            # Account for them during the free-space check without deleting
            # anything until that check succeeds.
            if os.path.isdir(destination) and not os.path.islink(destination):
                destination_size = _directory_size(destination)
            else:
                try:
                    destination_size = os.lstat(destination).st_size
                except OSError:
                    destination_size = 0
        elif os.path.isdir(destination) and not _directory_has_payload(destination):
            try:
                shutil.rmtree(destination)
                destination_exists = False
            except OSError as exc:
                print(
                    f"WARNING: Unable to prepare {name} migration destination "
                    f"{destination}: {exc}. Migration skipped."
                )
                return False
        else:
            print(
                f"WARNING: {name} migration destination already contains data: "
                f"{destination}. Migration skipped to avoid overwriting it."
            )
            return False

    same_filesystem = _same_filesystem(source, base_workdir)
    if not same_filesystem:
        required = _directory_size(source)
        try:
            free = shutil.disk_usage(base_workdir).free
        except OSError as exc:
            print(
                f"WARNING: Unable to check free disk space for {name} migration "
                f"to {destination}: {exc}. Migration skipped."
            )
            return False
        available = free + destination_size
        if available < required:
            print(
                f"WARNING: Not enough free disk space to migrate {name} directory "
                f"to application base workdir: {destination}. "
                f"Required: {_format_bytes(required)}, free after replacing destination: "
                f"{_format_bytes(available)}. Migration skipped."
            )
            return False

    print(
        f"Migration {name} directory to application base workdir: "
        f"{destination}. Please wait..."
    )
    try:
        if destination_exists and name == "sandbox":
            if os.path.isdir(destination) and not os.path.islink(destination):
                shutil.rmtree(destination)
            else:
                os.remove(destination)

        # shutil.move resolves to a rename on the same filesystem and to a
        # copy+remove only when source and destination are on different volumes.
        shutil.move(source, destination)
    except Exception as exc:
        print(
            f"WARNING: Unable to migrate {name} directory to application base "
            f"workdir: {destination}: {exc}"
        )
        return False
    if name == "sandbox":
        # Python virtual environments contain absolute paths/shebangs and are
        # not safely relocatable. Keep the migrated uv runtime/cache, but make
        # the managed python/os venvs rebuild in their new absolute location on
        # first use.
        for env_name in ("python", "os"):
            marker = os.path.join(destination, env_name, ".pygpt-sandbox.json")
            try:
                if os.path.isfile(marker):
                    os.remove(marker)
            except OSError as exc:
                print(
                    f"WARNING: Unable to invalidate relocated sandbox marker "
                    f"{marker}: {exc}"
                )

    print(f"Migration {name} directory finished: {destination}")
    return True


def migrate_application_runtime_dirs(window) -> bool:
    """Move built-in sandbox and optional package runtimes out of the profile."""
    moved = False
    for name in ("sandbox", "extra_packages"):
        current_moved = _migrate_application_runtime_dir(window, name)
        moved = current_moved or moved
        if current_moved and name == "extra_packages":
            # RuntimePackages.activate() runs before the version patcher. Run it
            # once more after moving the old directory so newly arrived .pth
            # files and Windows DLL directories take effect in this session.
            try:
                window.core.packages.activate()
            except Exception as exc:
                print(
                    "WARNING: extra_packages directory was migrated, but its "
                    f"runtime activation failed: {exc}"
                )
    return moved


def metadata_providers():
    # Config migration runs before LLM registration. Instantiate only metadata
    # providers; no SDK clients or API calls are needed for their setup().
    from pygpt_net.provider.llms.openai.provider import OpenAILLM
    from pygpt_net.provider.llms.google.provider import GoogleLLM
    from pygpt_net.provider.llms.anthropic.provider import AnthropicLLM
    from pygpt_net.provider.llms.x_ai.provider import xAILLM

    return (OpenAILLM(), GoogleLLM(), AnthropicLLM(), xAILLM())


def legacy_defaults() -> dict:
    return {field["legacy_key"]: copy.deepcopy(field.get("default"))
            for provider in metadata_providers()
            for field in provider.get_remote_tools_schema().values()
            if "legacy_key" in field}


def migrate_remote_tools(data: dict) -> bool:
    changed = False
    providers = data.get("providers")
    if not isinstance(providers, dict):
        providers = {}
        data["providers"] = providers
        changed = True
    for provider in metadata_providers():
        config_id = provider.get_config_id()
        entry = providers.get(config_id)
        if not isinstance(entry, dict):
            entry = {}
            providers[config_id] = entry
            changed = True
        remote = entry.get("remote_tools")
        if not isinstance(remote, dict):
            remote = {}
            entry["remote_tools"] = remote
            changed = True
        for key, field in provider.get_remote_tools_schema().items():
            legacy = field.get("legacy_key")
            aliases = field.get("legacy_aliases", [])
            old_keys = [legacy, *aliases] if legacy else aliases
            if key not in remote:
                value = next((data[k] for k in old_keys if k in data), field.get("default"))
                remote[key] = copy.deepcopy(value)
                changed = True
            for old_key in old_keys:
                if old_key in data:
                    del data[old_key]
                    changed = True

    # Retain also retired/manual provider options not exposed by today's schema.
    for old_key in list(data):
        if not old_key.startswith("remote_tools.") or old_key.startswith("remote_tools.global."):
            continue
        if old_key in ("remote_tools.computer_use.env", "remote_tools.computer_use.sandbox"):
            continue
        local_key = old_key[len("remote_tools."):]
        config_id = "openai"
        for prefix, provider_id in (("google.", "google"), ("anthropic.", "anthropic"), ("xai.", "x_ai")):
            if local_key.startswith(prefix):
                config_id, local_key = provider_id, local_key[len(prefix):]
                break
        if local_key.startswith("tool_search."):
            config_id = "anthropic"
        providers[config_id]["remote_tools"].setdefault(local_key, data.pop(old_key))
        changed = True

    # These are shared computer-runtime settings, not OpenAI tool options.
    for key in ("env", "sandbox"):
        old_key = "remote_tools.computer_use." + key
        if old_key in data:
            data.setdefault("computer_use." + key, data.pop(old_key))
            changed = True
    return changed
