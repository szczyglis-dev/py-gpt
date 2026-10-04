"""Generated artifacts stay private until finalization and inputs are not re-exported."""
import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pygpt_net.core.agents_v2.artifacts import RuntimeArtifacts
from pygpt_net.core.agents.runners.session_components import SessionArtifacts
from pygpt_net.item.ctx import CtxItem


def runtime():
    main, source = CtxItem('agent_v2'), CtxItem('agent_v2')
    return SimpleNamespace(context=SimpleNamespace(ctx=main), window=MagicMock(), run_id='run',
                           primary_actor=SimpleNamespace(id='orchestrator', tool_ctx=source),
                           workers=SimpleNamespace(states={}), verbose=MagicMock(), model=SimpleNamespace(provider='openai'))


@pytest.fixture(params=['v2', 'legacy'])
def artifacts(request):
    rt = runtime()
    if request.param == 'legacy':
        rt.provider_ctx = rt.primary_actor.tool_ctx
        rt.llm = None
        return rt, SessionArtifacts(rt)
    return rt, RuntimeArtifacts(rt)


def test_actor_context_is_private_and_copies_user_inputs(artifacts):
    rt, component = artifacts
    main = rt.context.ctx
    main.images, main.attachments, main.doc_ids = ['input.png'], ['input.txt'], ['doc']
    main.hidden_input = 'hidden'
    ctx = component.tool_context('worker')
    assert ctx is not main
    assert ctx.images == ['input.png'] and ctx.images is not main.images
    assert ctx.attachments == ['input.txt'] and ctx.attachments is not main.attachments
    assert ctx.doc_ids == ['doc'] and ctx.hidden_input == 'hidden'
    assert ctx.hidden and ctx.internal and ctx.agent_call and not ctx.current
    assert ctx.extra['run_id'] == 'run'
    ctx.images.append('generated')
    assert main.images == ['input.png']
    if isinstance(component, RuntimeArtifacts):
        worker_ctx = component.worker_context('w')
        assert worker_ctx.extra['agents_v2_worker'] == 'w'


def test_collect_excludes_read_files_and_deduplicates_other_outputs(artifacts):
    rt, component = artifacts
    source = rt.primary_actor.tool_ctx
    source.files, source.images, source.urls = ['read.py'], ['image.png'], ['https://source']
    component.collect(None)
    component.collect(source)
    component.collect(source)
    values = component.pending()
    assert values.get('files', []) == []
    assert values['images'] == ['image.png'] and values['urls'] == ['https://source']
    assert rt.context.ctx.images == []
    assert component.register_files([None, '', {'path': ' delivered.txt '}, 'delivered.txt']) == ['delivered.txt']
    assert component.pending()['files'] == ['delivered.txt']


def test_native_images_materialize_and_failures_are_logged(artifacts, tmp_path):
    rt, component = artifacts
    output = tmp_path / 'images' / 'generated.png'
    rt.window.core.image.gen_unique_path.return_value = str(output)
    rt.window.core.filesystem.make_local.return_value = 'generated.png'
    rt.window.core.filesystem.materialize_runtime_artifact.return_value = {'path': 'runtime.png'}
    assert component.register_image('') is None
    assert component.register_image(base64.b64encode(b'png').decode()) == {'path': 'runtime.png'}
    assert output.read_bytes() == b'png'
    assert component.pending()['images'] == ['generated.png']
    rt.window.core.image.gen_unique_path.side_effect = RuntimeError('write failed')
    assert component.register_image('YQ==') is None
    rt.window.core.debug.log.assert_called_once()


def test_container_download_and_failure(artifacts):
    rt, component = artifacts
    downloader = rt.window.core.api.openai.container.download_files
    downloader.return_value = ['downloaded.txt']
    assert component.register_container_files([]) == []
    assert component.register_container_files(['remote']) == ['downloaded.txt']
    downloader.side_effect = RuntimeError('download failed')
    assert component.register_container_files(['remote']) == []
    rt.window.core.debug.log.assert_called_once()


def test_v2_seed_suppresses_inputs_across_artifact_channels():
    rt = runtime()
    rt.context.ctx.images = [{'path': 'input.png', 'type': 'user'}]
    artifacts = RuntimeArtifacts(rt)
    artifacts.seed()
    assert artifacts.register_files(['input.png']) == []
    assert artifacts._append_artifact('images', 'new.png') is True
    assert artifacts.register_files(['new.png']) == []
    snapshot = artifacts.pending()
    snapshot['images'].append('mutated')
    assert artifacts.pending()['images'] == ['new.png']
    assert artifacts.provider_id() == 'openai'
    rt.model = MagicMock(provider='fallback')
    rt.model.get_provider.side_effect = RuntimeError('unsupported')
    assert artifacts.provider_id() == 'fallback'
