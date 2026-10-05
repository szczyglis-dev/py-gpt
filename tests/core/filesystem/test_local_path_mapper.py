from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.filesystem import Filesystem
from pygpt_net.core.filesystem.local_mapper import LocalPathMapper


@pytest.mark.parametrize('project_location', ['separate', 'base', 'parent', 'shared'])
def test_snapshot_matches_profile_and_project_path_rules(tmp_path, project_location):
    base = tmp_path / 'profile'
    shared = base / 'data'
    data = {'separate': tmp_path / 'project', 'base': base, 'parent': tmp_path,
            'shared': shared}[project_location]
    globals = (base / 'tmp', base / 'img')
    mapper = LocalPathMapper(str(base), str(data), str(shared), tuple(map(str, globals)))
    assert mapper(str(data / 'docs/note.txt')) == '%workdir%/data/docs/note.txt'
    if project_location == 'shared':
        assert mapper(str(base / 'tmp/a.txt')) == '%workdir%/tmp/a.txt'
        assert mapper(str(shared / 'a.txt')) == '%workdir%/data/a.txt'
    else:
        assert mapper(str(base / 'tmp/a.txt')) == '%workdir%/tmp/a.txt'
        assert mapper(str(shared / 'a.txt')) == str(shared / 'a.txt')
    assert mapper(str(tmp_path.parent / 'outside.txt')) == str(tmp_path.parent / 'outside.txt')
    assert mapper(str(data) + '-other/file.txt') != '%workdir%/data/-other/file.txt'
    assert mapper('') == ''


def test_snapshot_resolves_roots_once_and_survives_runtime_project_change(tmp_path):
    config = SimpleNamespace(get_user_path=lambda: str(tmp_path / 'profile'))
    fs = Filesystem(SimpleNamespace(core=SimpleNamespace(config=config)))
    fs.get_data_dir = MagicMock(return_value=str(tmp_path / 'project'))
    fs.get_shared_data_dir = MagicMock(return_value=str(tmp_path / 'profile/data'))
    fs._global_profile_roots = MagicMock(return_value=[str(tmp_path / 'profile/tmp')])
    meta = object()
    mapper = fs.local_path_mapper(ctx=meta)
    fs.get_data_dir.assert_called_once_with(ctx=meta, meta_id=None, group_id=None, create=False)
    fs.get_data_dir.return_value = str(tmp_path / 'other-project')
    for i in range(100):
        assert mapper(str(tmp_path / 'project' / f'{i}.txt')) == f'%workdir%/data/{i}.txt'
    assert fs.get_data_dir.call_count == 1
