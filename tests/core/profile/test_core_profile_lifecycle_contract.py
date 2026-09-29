import json
from pathlib import Path
from unittest.mock import MagicMock

from pygpt_net.core.profile.profile import Profile


def make_profile(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    profile = Profile()
    profile.set_base_workdir(str(base))
    return profile, base


def test_init_installs_loads_and_updates_path_once(tmp_path):
    profile, base = make_profile(tmp_path)
    profile.install = MagicMock()
    profile.load = MagicMock()
    profile.update_path = MagicMock()
    profile.init(str(base))
    profile.install.assert_called_once_with()
    profile.load.assert_called_once_with()
    profile.update_path.assert_called_once_with()
    assert profile.base_workdir == str(base)

    profile.initialized = True
    profile.init(str(base))
    assert profile.load.call_count == 1
    assert profile.update_path.call_count == 1


def test_has_file_and_load_valid_profile_json(tmp_path):
    profile, base = make_profile(tmp_path)
    assert profile.has_file() is False
    payload = {
        "_version": "1.0.0",
        "current": "p1",
        "profiles": {"p1": {"name": "One", "workdir": "%HOME%/one"}},
    }
    (base / Profile.PROFILE_FILE).write_text(json.dumps(payload), encoding="utf-8")
    assert profile.has_file() is True
    profile.load()
    assert profile.current == "p1"
    assert profile.profiles == payload["profiles"]
    assert profile.initialized is True


def test_save_writes_version_current_profiles_and_removes_lock(tmp_path):
    profile, base = make_profile(tmp_path)
    profile.current = "p1"
    profile.profiles = {"p1": {"name": "One", "workdir": "/tmp/one"}}
    profile.save()
    data = json.loads((base / Profile.PROFILE_FILE).read_text(encoding="utf-8"))
    assert data == {
        "_version": "1.0.0",
        "current": "p1",
        "profiles": profile.profiles,
    }
    assert not (base / f"{Profile.PROFILE_FILE}.lock").exists()


def test_save_aborts_when_lock_exists(tmp_path, capsys):
    profile, base = make_profile(tmp_path)
    lock = base / f"{Profile.PROFILE_FILE}.lock"
    lock.write_text("lock", encoding="utf-8")
    profile.save()
    assert not (base / Profile.PROFILE_FILE).exists()
    assert "save aborted" in capsys.readouterr().out


def test_add_update_remove_append_and_sorted_get_all(tmp_path, monkeypatch):
    profile, _ = make_profile(tmp_path)
    profile.save = MagicMock()
    ids = iter(["uuid-a", "uuid-b"])
    monkeypatch.setattr("pygpt_net.core.profile.profile.uuid4", lambda: next(ids))

    first = profile.add("Zulu", str(Path.home() / "z"))
    second = profile.add("Alpha", "/tmp/a")
    assert (first, second) == ("uuid-a", "uuid-b")
    assert profile.profiles[first]["workdir"] == "%HOME%/z"
    assert list(profile.get_all()) == [second, first]

    assert profile.update_profile(first, "Beta", str(Path.home() / "b")) is True
    assert profile.profiles[first] == {"name": "Beta", "workdir": "%HOME%/b"}
    assert profile.update_profile("missing", "X", "/x") is False

    profile.append("manual", {"name": "Manual", "workdir": "/m"})
    assert profile.get("manual")["name"] == "Manual"
    assert profile.get("missing") is None
    assert profile.remove("manual") is True
    assert profile.remove("manual") is False
    assert profile.save.call_count >= 4


def test_set_current_updates_path_and_getters(tmp_path):
    profile, _ = make_profile(tmp_path)
    profile.profiles = {"p": {"name": "Profile", "workdir": "/missing"}}
    profile.save = MagicMock()
    profile.update_path = MagicMock()
    assert profile.set_current("missing") is False
    assert profile.set_current("p") is True
    assert profile.get_current() == "p"
    assert profile.get_current_name() == "Profile"
    profile.save.assert_called_once_with()
    profile.update_path.assert_called_once_with()


def test_get_current_workdir_prefers_existing_profile_directory(tmp_path):
    profile, base = make_profile(tmp_path)
    active = tmp_path / "active"
    active.mkdir()
    profile.current = "p"
    profile.profiles = {"p": {"name": "P", "workdir": str(active)}}
    assert profile.get_current_workdir() == str(active)
    profile.profiles["p"]["workdir"] = str(tmp_path / "missing")
    assert profile.get_current_workdir() == str(base)


def test_update_current_workdir_replaces_home_and_saves(tmp_path):
    profile, _ = make_profile(tmp_path)
    profile.current = "p"
    profile.profiles = {"p": {"name": "P", "workdir": "old"}}
    profile.save = MagicMock()
    profile.update_current_workdir(str(Path.home() / "new-workdir"))
    assert profile.profiles["p"]["workdir"] == "%HOME%/new-workdir"
    profile.save.assert_called_once_with()


def test_update_path_writes_empty_for_base_and_profile_path_otherwise(tmp_path):
    profile, base = make_profile(tmp_path)
    profile.update_path()
    assert (base / "path.cfg").read_text(encoding="utf-8") == ""

    active = tmp_path / "active"
    active.mkdir()
    profile.current = "p"
    profile.profiles = {"p": {"name": "P", "workdir": str(active)}}
    profile.update_path()
    assert (base / "path.cfg").read_text(encoding="utf-8") == str(active).replace(str(Path.home()), "%HOME%")


def test_update_path_ignores_missing_directory(tmp_path):
    profile, base = make_profile(tmp_path)
    profile.current = "p"
    profile.profiles = {"p": {"name": "P", "workdir": str(tmp_path / "missing")}}
    profile.update_path()
    assert (base / "path.cfg").read_text(encoding="utf-8") == ""
