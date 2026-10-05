from pygpt_net.ui.dialog.system_info import WorkdirSizeWorker


def test_custom_sandbox_inside_workdir_is_not_counted_twice(tmp_path):
    sandbox = tmp_path / 'custom' / 'environment'
    sandbox.mkdir(parents=True)
    (sandbox / 'python.bin').write_bytes(b'12345')
    (tmp_path / 'chat.txt').write_bytes(b'abc')
    assert WorkdirSizeWorker._tree_size(tmp_path, exclude_paths=(sandbox,)) == 3
    assert WorkdirSizeWorker._tree_size(sandbox) == 5
