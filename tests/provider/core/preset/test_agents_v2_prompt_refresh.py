import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.provider.core.preset.patches import patch_agents_v2_prompts as module


@pytest.fixture
def refresh(tmp_path, monkeypatch):
    user_dir = tmp_path / 'user'
    bundled_dir = tmp_path / 'app/data/config/presets'
    user_dir.mkdir()
    bundled_dir.mkdir(parents=True)
    old_prompt = 'previous stock prompt'
    filename = 'agent_v2_coder.json'
    monkeypatch.setattr(module, 'PREVIOUS_PROMPT_HASHES', {
        filename: tuple(hashlib.sha256(value.encode()).hexdigest()
                        for value in (old_prompt, "previous execution prompt")),
    })
    source = {'prompt': 'new execution instructions'}
    (bundled_dir / filename).write_text(json.dumps(source))
    window = SimpleNamespace(core=SimpleNamespace(
        config=SimpleNamespace(get_user_dir=lambda name: str(user_dir),
                               get_app_path=lambda: str(tmp_path / 'app')),
        debug=SimpleNamespace(log=MagicMock()),
    ))
    return module.Patch(window), user_dir / filename, old_prompt


@pytest.mark.parametrize("revision", ["previous stock prompt", "previous execution prompt"])
def test_refresh_changes_only_recognized_stock_prompt_and_is_idempotent(refresh, revision):
    patch, target, old = refresh
    original = {'prompt': revision, 'agent_v2': True, 'model': 'my-model', 'uuid': 'my-id',
                'tools': {'function': ['my-tool']}, 'extra': {'custom': True},
                'unknown_field': [1, 2], '__meta__': {'version': 'old'}}
    target.write_text(json.dumps(original))
    assert patch.execute() is True
    updated = json.loads(target.read_text())
    assert updated.pop('prompt') == 'new execution instructions'
    assert updated == {key: value for key, value in original.items() if key != 'prompt'}
    assert patch.execute() is False
    assert not list(target.parent.glob('.agents-v2-prompts-*'))


@pytest.mark.parametrize('prompt, enabled', [('my own instructions', True), ('previous stock prompt', False)])
def test_refresh_preserves_custom_or_non_agents_v2_presets(refresh, prompt, enabled):
    patch, target, _ = refresh
    target.write_text(json.dumps({'prompt': prompt, 'agent_v2': enabled}))
    before = target.read_bytes()
    assert patch.execute() is False
    assert target.read_bytes() == before


def test_refresh_preserves_invalid_file_and_continues(refresh):
    patch, target, _ = refresh
    target.write_text('{broken')
    assert patch.execute() is False
    assert target.read_text() == '{broken'
    patch.window.core.debug.log.assert_called_once()


def test_refresh_write_failure_preserves_original_and_removes_temporary_file(refresh, monkeypatch):
    patch, target, old = refresh
    target.write_text(json.dumps({'prompt': old, 'agent_v2': True}))
    before = target.read_bytes()
    monkeypatch.setattr(module.os, 'replace', MagicMock(side_effect=OSError('cannot replace')))
    assert patch.execute() is False
    assert target.read_bytes() == before
    assert not list(target.parent.glob('.agents-v2-prompts-*'))


def test_stock_prompt_registry_covers_all_bundled_agents_v2_presets():
    root = Path(__file__).resolve().parents[4] / 'src/pygpt_net/data/config/presets'
    files = {path.name for path in root.glob('*agent_v2*.json')}
    assert set(module.PREVIOUS_PROMPT_HASHES) == files
    for filename, digests in module.PREVIOUS_PROMPT_HASHES.items():
        current = json.loads((root / filename).read_text())['prompt']
        assert hashlib.sha256(current.strip().encode()).hexdigest() not in digests
