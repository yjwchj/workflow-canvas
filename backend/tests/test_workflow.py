import asyncio
import io
from copy import deepcopy
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db import SessionLocal
from app.models import Template, Run, Asset
from app.worker import process_run


def png(color='green'):
    stream = io.BytesIO()
    Image.new('RGB', (32, 32), color).save(stream, 'PNG')
    return stream.getvalue()


def template_body(kind='text-to-image'):
    return {'name': '生成' if kind == 'text-to-image' else '编辑', 'kind': kind, 'provider': 'comfyui',
            'config': {'workflow': {'6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'original'}},
                                    '3': {'class_type': 'KSampler', 'inputs': {'steps': 20}},
                                    '10': {'class_type': 'LoadImage', 'inputs': {'image': 'original.png'}}},
                       'prompt_binding': {'node_id': '6', 'field': 'text'},
                       'image_binding': {'node_id': '10', 'field': 'image'} if kind == 'image-edit' else None,
                       'parameters': [{'key': 'steps', 'label': '步数', 'type': 'integer', 'default': 20,
                                       'min': 1, 'max': 50, 'node_id': '3', 'field': 'steps'}]}}


def canvas_chain(admin, mode='manual'):
    t1 = admin.post('/api/admin/templates', json=template_body()).json()['id']
    t2 = admin.post('/api/admin/templates', json=template_body('image-edit')).json()['id']
    canvas = admin.post('/api/canvases', json={'name': 'test'}).json()
    nodes = [{'id': 'text', 'type': 'text', 'position': {'x': 0, 'y': 0}, 'data': {'text': 'a forest'}},
             {'id': 'generate', 'type': 'workflow', 'position': {'x': 300, 'y': 0}, 'data': {'templateId': t1, 'params': {'count': 2, 'steps': 25}}},
             {'id': 'result1', 'type': 'result', 'position': {'x': 600, 'y': 0}, 'data': {}},
             {'id': 'edit', 'type': 'workflow', 'position': {'x': 900, 'y': 0}, 'data': {'templateId': t2, 'params': {}}},
             {'id': 'result2', 'type': 'result', 'position': {'x': 1200, 'y': 0}, 'data': {}}]
    edges = [{'id': str(i), 'source': source, 'target': target, 'targetHandle': handle}
             for i, (source, target, handle) in enumerate([('text', 'generate', 'text'), ('generate', 'result1', 'image'),
                                                         ('result1', 'edit', 'image'), ('text', 'edit', 'text'), ('edit', 'result2', 'image')])]
    graph = {'nodes': nodes, 'edges': edges, 'selectionMode': mode}
    saved = admin.put(f"/api/canvases/{canvas['id']}", json={'name': 'test', 'revision': 1, 'graph': graph})
    assert saved.status_code == 200, saved.text
    return canvas['id'], graph


def test_user_isolation_and_authorization(admin):
    canvas_id, _ = canvas_chain(admin)
    second = TestClient(app)
    assert second.post('/api/auth/register', json={'username': 'friend', 'password': 'Friend123!'}).status_code == 201
    assert second.get('/api/canvases').json() == []
    assert second.get(f'/api/canvases/{canvas_id}').status_code == 404
    assert second.get(f'/api/canvases/{canvas_id}/runs').status_code == 404
    assert second.get('/api/admin/templates').status_code == 403
    assert 'workflow' not in second.get('/api/templates').json()[0]
    second.post('/api/auth/logout')
    assert second.get('/api/canvases').status_code == 401


def test_revisions_and_graph_validation(admin):
    canvas_id, graph = canvas_chain(admin)
    assert admin.put(f'/api/canvases/{canvas_id}', json={'name': 'test', 'revision': 1, 'graph': graph}).status_code == 409
    bad = deepcopy(graph)
    bad['edges'].append({'id': 'cycle', 'source': 'result2', 'target': 'generate', 'targetHandle': 'image'})
    assert admin.put(f'/api/canvases/{canvas_id}', json={'name': 'test', 'revision': 2, 'graph': bad}).status_code == 422
    graph['nodes'][1]['data']['params']['steps'] = 500
    assert admin.put(f'/api/canvases/{canvas_id}', json={'name': 'test', 'revision': 2, 'graph': graph}).status_code == 200
    assert admin.post(f'/api/canvases/{canvas_id}/runs', json={}).status_code == 422


def test_manual_resume_old_image_and_snapshot(admin):
    canvas_id, graph = canvas_chain(admin)
    response = admin.post(f'/api/canvases/{canvas_id}/runs', json={})
    assert response.status_code == 201, response.text
    run_id = response.json()['id']
    graph['nodes'][1]['data']['params']['steps'] = 12
    admin.put(f'/api/canvases/{canvas_id}', json={'name': 'test', 'revision': 2, 'graph': graph})
    calls = []

    async def executor(step, image_path, submitted):
        calls.append((step['params'], image_path))
        submitted('remote-test')
        return [png()]

    asyncio.run(process_run(run_id, executor))
    first = admin.get(f'/api/canvases/{canvas_id}/runs').json()[0]
    assert first['status'] == 'waiting_selection'
    assert first['step'] == 1 and len(calls) == 2
    assert calls[0][0]['steps'] == 25
    old_id = first['outputs']['result1']['assets'][0]
    assert admin.post(f'/api/runs/{run_id}/resume', json={'asset_id': old_id}).status_code == 200
    assert admin.post(f'/api/runs/{run_id}/resume', json={'asset_id': old_id}).status_code == 409
    asyncio.run(process_run(run_id, executor))
    final = admin.get(f'/api/canvases/{canvas_id}/runs').json()[0]
    assert final['status'] == 'completed' and len(calls) == 3
    assert old_id in str(calls[-1][1])
    images = admin.get(f'/api/canvases/{canvas_id}/assets').json()
    assert len(images) == 3
    assert len([image for image in images if image['node_id'] == 'result1']) == 2
    assert admin.get(images[0]['url']).status_code == 200
    friend = TestClient(app)
    friend.post('/api/auth/register', json={'username': 'friend', 'password': 'Friend123!'})
    assert friend.get(images[0]['url']).status_code == 404
    assert friend.post(f'/api/runs/{run_id}/resume', json={'asset_id': old_id}).status_code == 404
    with SessionLocal() as db:
        template = db.scalar(select(Template).where(Template.kind == 'text-to-image'))
        assert template.config['workflow']['6']['inputs']['text'] == 'original'
        assert template.config['workflow']['3']['inputs']['steps'] == 20


def test_auto_uses_latest_from_current_batch_and_groups_history(admin):
    canvas_id, _ = canvas_chain(admin, 'auto')
    paths = []

    async def executor(step, path, submitted):
        paths.append(path)
        return [png('red'), png('blue')]

    for _ in range(2):
        run_id = admin.post(f'/api/canvases/{canvas_id}/runs', json={}).json()['id']
        asyncio.run(process_run(run_id, executor))
        run = admin.get(f'/api/canvases/{canvas_id}/runs').json()[0]
        assert run['status'] == 'completed'
        last = run['outputs']['result1']['assets'][-1]
        assert last in str(paths[-1])
    assert len(admin.get(f'/api/canvases/{canvas_id}/assets').json()) == 12


def test_upload_save_restore_and_single_step(admin):
    canvas_id, graph = canvas_chain(admin)
    graph['nodes'].append({'id': 'upload', 'type': 'image', 'position': {'x': 5, 'y': 6}, 'data': {}})
    graph['edges'] = [e for e in graph['edges'] if e['source'] != 'result1']
    graph['edges'].append({'id': 'upload-edit', 'source': 'upload', 'target': 'edit', 'targetHandle': 'image'})
    assert admin.put(f'/api/canvases/{canvas_id}', json={'name': 'test', 'revision': 2, 'graph': graph}).status_code == 200
    uploaded = admin.post(f'/api/canvases/{canvas_id}/assets', data={'node_id': 'upload'}, files={'file': ('img.png', png(), 'image/png')})
    assert uploaded.status_code == 201, uploaded.text
    asset_id = uploaded.json()['id']
    graph['nodes'][-1]['data']['selectedAssetId'] = asset_id
    graph['viewport'] = {'x': -50, 'y': 90, 'zoom': 0.7}
    admin.put(f'/api/canvases/{canvas_id}', json={'name': 'test', 'revision': 3, 'graph': graph})
    admin.post('/api/auth/logout')
    admin.post('/api/auth/login', json={'username': 'testowner', 'password': 'TestOwner123!'})
    restored = admin.get(f'/api/canvases/{canvas_id}').json()['graph']
    assert restored['nodes'][-1]['data']['selectedAssetId'] == asset_id
    assert restored['viewport'] == graph['viewport']
    response = admin.post(f'/api/canvases/{canvas_id}/runs', json={'node_id': 'edit'})
    assert response.status_code == 201, response.text
    assert response.json()['total_steps'] == 1
    assert admin.post(f'/api/canvases/{canvas_id}/assets', data={'node_id': 'upload'}, files={'file': ('bad.png', b'not an image')}).status_code == 422


def test_cancel_and_failures_preserve_task_history(admin):
    canvas_id, _ = canvas_chain(admin)
    run_id = admin.post(f'/api/canvases/{canvas_id}/runs', json={}).json()['id']
    assert admin.post(f'/api/runs/{run_id}/cancel').status_code == 200
    assert admin.post(f'/api/runs/{run_id}/cancel').status_code == 409
    called = []

    async def executor(*args):
        called.append(True)
        raise RuntimeError('secret must not be exposed')

    asyncio.run(process_run(run_id, executor))
    assert not called
    run_id = admin.post(f'/api/canvases/{canvas_id}/runs', json={}).json()['id']
    asyncio.run(process_run(run_id, executor))
    failed = admin.get(f'/api/canvases/{canvas_id}/runs').json()[0]
    assert failed['status'] == 'failed' and 'secret' not in failed['error']


def test_csrf_and_template_mapping(admin):
    assert admin.post('/api/canvases', json={}, headers={'Origin': 'https://evil.example'}).status_code == 403
    body = template_body()
    body['config']['prompt_binding']['node_id'] = 'missing'
    assert admin.post('/api/admin/templates', json=body).status_code == 422
    body = template_body()
    body['config']['parameters'][0]['field'] = 'text'
    body['config']['parameters'][0]['node_id'] = '6'
    assert admin.post('/api/admin/templates', json=body).status_code == 422
