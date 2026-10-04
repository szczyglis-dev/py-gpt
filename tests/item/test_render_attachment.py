import copy
import json
from types import SimpleNamespace

from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.render_attachment import AttachmentPath, attachment_paths, attachment_records
from pygpt_net.provider.core.ctx.db_sqlite.storage import Storage


def test_typed_paths_are_compatible_with_existing_path_lists_and_deepcopy():
    path = AttachmentPath('/work/image.png', 'user')
    assert path == '/work/image.png'
    assert path.endswith('.png')
    assert path in ['/work/image.png']
    assert json.dumps([path]) == '["/work/image.png"]'
    assert copy.deepcopy(path).type == 'user'


def test_mixed_legacy_and_typed_records_default_legacy_to_output():
    values = ['legacy.txt', {'path': 'upload.txt', 'type': 'user'},
              {'path': 'generated.txt', 'type': 'output'}, {'path': 'unknown.txt'}]
    paths = attachment_paths(values)
    assert paths == ['legacy.txt', 'upload.txt', 'generated.txt', 'unknown.txt']
    assert attachment_records(paths) == [
        {'path': 'legacy.txt', 'type': 'output'},
        {'path': 'upload.txt', 'type': 'user'},
        {'path': 'generated.txt', 'type': 'output'},
        {'path': 'unknown.txt', 'type': 'output'},
    ]


def test_ctx_json_round_trip_preserves_provenance_without_changing_transport():
    ctx = CtxItem()
    ctx.images = [AttachmentPath('user.png', 'user'), 'output.png']
    ctx.files = [AttachmentPath('upload.txt', 'user'), 'generated.txt']
    data = json.loads(json.dumps(ctx.to_dict()))
    assert data['images'][0] == {'path': 'user.png', 'type': 'user'}
    assert data['files'][1] == {'path': 'generated.txt', 'type': 'output'}
    restored = CtxItem()
    restored.from_dict(data)
    assert restored.images == ['user.png', 'output.png']
    assert restored.files == ['upload.txt', 'generated.txt']
    assert restored.images[0].type == restored.files[0].type == 'user'
    assert restored.to_dict()['files'] == data['files']


def test_image_database_serialization_keeps_origin_and_excludes_transport():
    window = SimpleNamespace(core=SimpleNamespace(attachments=SimpleNamespace(
        is_ctx_excluded_path=lambda path: path.endswith('hidden.png'))))
    ctx = CtxItem()
    ctx.images = [AttachmentPath('upload.png', 'user'), 'output.png', 'hidden.png']
    stored = json.loads(Storage(window)._pack_ctx_images(ctx))
    assert stored == [{'path': 'upload.png', 'type': 'user'}, {'path': 'output.png', 'type': 'output'}]
    assert ctx.images == ['upload.png', 'output.png', 'hidden.png']


def test_database_read_accepts_mixed_records_and_resaves_without_losing_type():
    from collections import defaultdict
    from pygpt_net.provider.core.ctx.db_sqlite.utils import unpack_item
    row = defaultdict(lambda: None)
    row['images_json'] = json.dumps(['old.png', {'path': 'new.png', 'type': 'user'}])
    row['files_json'] = json.dumps([{'path': 'report.pdf', 'type': 'output'},
                                  {'path': 'upload.pdf', 'type': 'user'}, 'legacy.pdf'])
    ctx = unpack_item(CtxItem(), row)
    assert ctx.images == ['old.png', 'new.png']
    assert [path.type for path in ctx.images] == ['output', 'user']
    assert [path.type for path in ctx.files] == ['output', 'user', 'output']
    stored = json.loads(Storage()._pack_ctx_images(ctx))
    assert stored[1] == {'path': 'new.png', 'type': 'user'}
    assert ctx.to_dict()['files'][1] == {'path': 'upload.pdf', 'type': 'user'}
