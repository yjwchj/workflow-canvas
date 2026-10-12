import asyncio
import json
from copy import deepcopy
import httpx
from app import providers
from app.config import settings
from test_workflow import template_body, png


def step(provider='comfyui'):
    template = template_body('image-edit')
    template['provider'] = provider
    template['config']['workflow_id'] = '123456'
    return {'template': template, 'params': {'steps': 33, 'count': 1}, 'prompt': 'fresh prompt'}


def test_comfy_adapter_upload_mapping_poll_and_download(monkeypatch, tmp_path):
    image = tmp_path / 'input.png'
    image.write_bytes(png())
    original = step()
    before = deepcopy(original)
    seen = []

    def handle(request):
        seen.append(request.url.path)
        if request.url.path == '/upload/image':
            assert b'input.png' in request.content
            return httpx.Response(200, json={'name': 'uploaded.png', 'subfolder': 'api'})
        if request.url.path == '/prompt':
            workflow = json.loads(request.content)['prompt']
            assert workflow['6']['inputs']['text'] == 'fresh prompt'
            assert workflow['3']['inputs']['steps'] == 33
            assert workflow['10']['inputs']['image'] == 'api/uploaded.png'
            return httpx.Response(200, json={'prompt_id': 'abc'})
        if request.url.path == '/history/abc':
            return httpx.Response(200, json={'abc': {'status': {'status_str': 'success'}, 'outputs': {'9': {'images': [{'filename': 'out.png', 'type': 'output', 'subfolder': ''}]}}}})
        if request.url.path == '/view':
            return httpx.Response(200, content=png('blue'))
        raise AssertionError(request.url)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(providers.httpx, 'AsyncClient', lambda **kw: original_client(transport=httpx.MockTransport(handle), **kw))
    remote = []
    result = asyncio.run(providers.execute_comfy(original, image, remote.append))
    assert len(result) == 1 and remote == ['abc']
    assert seen == ['/upload/image', '/prompt', '/history/abc', '/view']
    assert original == before


def test_runninghub_upload_mapping_status_download_and_key_isolation(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'runninghub_api_key', 'test-private-key')
    image = tmp_path / 'input.png'
    image.write_bytes(png())
    remote = []

    def handle(request):
        path = request.url.path
        if request.url.host == 'files.example':
            assert 'authorization' not in request.headers
            assert 'test-private-key' not in str(request.url)
            return httpx.Response(200, content=png())
        assert request.headers['authorization'] == 'Bearer test-private-key'
        if path == '/task/openapi/upload':
            assert b'test-private-key' in request.content
            assert b'input' in request.content
            return httpx.Response(200, json={'code': 0, 'data': {'fileName': 'api/uploaded.png'}})
        data = json.loads(request.content)
        assert data['apiKey'] == 'test-private-key'
        if path == '/task/openapi/create':
            assert data['workflowId'] == '123456'
            assert {'nodeId': '10', 'fieldName': 'image', 'fieldValue': 'api/uploaded.png'} in data['nodeInfoList']
            return httpx.Response(200, json={'code': 0, 'data': {'taskId': 'rh123'}})
        if path == '/task/openapi/status':
            return httpx.Response(200, json={'code': 0, 'data': 'SUCCESS'})
        if path == '/task/openapi/outputs':
            return httpx.Response(200, json={'code': 0, 'data': [{'fileType': 'png', 'fileUrl': 'https://files.example/output.png'}]})
        raise AssertionError(request.url)

    original_client = httpx.AsyncClient
    monkeypatch.setattr(providers.httpx, 'AsyncClient', lambda **kw: original_client(transport=httpx.MockTransport(handle), **kw))
    result = asyncio.run(providers.execute_runninghub(step('runninghub'), image, remote.append))
    assert remote == ['rh123'] and len(result) == 1


def test_provider_errors_do_not_include_credentials():
    try:
        providers.rh_data({'code': 401, 'msg': 'secret-key'} )
    except providers.ProviderError as error:
        assert '401' in str(error) and 'secret-key' not in str(error)
