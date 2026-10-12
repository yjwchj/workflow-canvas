"""Provider adapters. Templates are copied before mapping any task inputs."""
import asyncio
from copy import deepcopy
from pathlib import Path
from uuid import uuid4
import httpx
from .config import settings


class ProviderError(Exception):
    pass


async def json_request(client, method, path, **kwargs):
    response = await client.request(method, path, **kwargs)
    if response.status_code >= 400:
        raise ProviderError(f'执行服务返回 HTTP {response.status_code}，请检查服务和工作流配置')
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError('执行服务返回了无效数据') from exc


def mapped_inputs(step, remote_image=None):
    config = step['template']['config']
    bindings = [(config['prompt_binding'], step['prompt'])]
    if remote_image:
        bindings.append((config['image_binding'], remote_image))
    for parameter in config['parameters']:
        bindings.append((parameter, step['params'][parameter['key']]))
    return bindings


def comfy_prompt(step, remote_image=None):
    workflow = deepcopy(step['template']['config']['workflow'])
    for binding, value in mapped_inputs(step, remote_image):
        try:
            workflow[binding['node_id']]['inputs'][binding['field']] = value
        except (KeyError, TypeError) as exc:
            raise ProviderError('模板参数映射与 ComfyUI API 工作流不匹配') from exc
    return workflow


async def bounded_download(client, url, **kwargs):
    chunks, size = [], 0
    async with client.stream('GET', url, **kwargs) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > settings.max_image_bytes:
                raise ProviderError('生成图片超过 20 MB，无法保存')
            chunks.append(chunk)
    return b''.join(chunks)


async def execute_comfy(step, image_path, on_submitted):
    async with httpx.AsyncClient(base_url=settings.comfyui_url.rstrip('/'), timeout=60) as client:
        remote_image = None
        if image_path:
            with image_path.open('rb') as file:
                upload = await json_request(client, 'POST', '/upload/image',
                                            files={'image': (image_path.name, file)}, data={'overwrite': 'false'})
            remote_image = '/'.join(filter(None, [upload.get('subfolder'), upload['name']]))
        prompt = comfy_prompt(step, remote_image)
        submitted = await json_request(client, 'POST', '/prompt', json={'prompt': prompt, 'client_id': str(uuid4())})
        if submitted.get('node_errors') or not submitted.get('prompt_id'):
            raise ProviderError('ComfyUI 拒绝了工作流，请检查模型、节点和参数映射')
        prompt_id = submitted['prompt_id']
        on_submitted(prompt_id)
        deadline = asyncio.get_running_loop().time() + settings.provider_timeout
        while asyncio.get_running_loop().time() < deadline:
            history = await json_request(client, 'GET', f'/history/{prompt_id}')
            if prompt_id in history:
                result = history[prompt_id]
                if result.get('status', {}).get('status_str') == 'error':
                    raise ProviderError('ComfyUI 执行失败，请在 ComfyUI 中检查对应任务')
                contents = []
                allowed = step['template']['config'].get('output_nodes', [])
                for node_id, output in result.get('outputs', {}).items():
                    if allowed and node_id not in allowed:
                        continue
                    for image in output.get('images', []):
                        contents.append(await bounded_download(client, '/view', params=image))
                if not contents:
                    raise ProviderError('工作流没有图片输出，请设置 SaveImage/PreviewImage 输出节点')
                return contents
            await asyncio.sleep(2)
        raise ProviderError('ComfyUI 等待超时；远端任务可能仍在运行，请检查后再提交')


def rh_data(payload):
    if payload.get('code') != 0:
        # Do not echo raw provider responses: they may include account credentials.
        raise ProviderError(f"RunningHub 请求失败（代码 {payload.get('code', '未知')}），请检查余额、API Key 和工作流")
    return payload.get('data')


async def execute_runninghub(step, image_path, on_submitted):
    if not settings.runninghub_api_key:
        raise ProviderError('维护者尚未配置 RunningHub API Key')
    key = settings.runninghub_api_key
    async with httpx.AsyncClient(base_url=settings.runninghub_url.rstrip('/'), timeout=90,
                                headers={'Authorization': f'Bearer {key}'}) as client:
        remote_image = None
        if image_path:
            with image_path.open('rb') as file:
                uploaded = await json_request(client, 'POST', '/task/openapi/upload',
                                              data={'apiKey': key, 'fileType': 'input'}, files={'file': (image_path.name, file)})
            remote_image = rh_data(uploaded)['fileName']
        node_info = [{'nodeId': binding['node_id'], 'fieldName': binding['field'], 'fieldValue': str(value)}
                     for binding, value in mapped_inputs(step, remote_image)]
        submitted = await json_request(client, 'POST', '/task/openapi/create',
                                       json={'apiKey': key, 'workflowId': step['template']['config']['workflow_id'],
                                             'nodeInfoList': node_info})
        task_id = rh_data(submitted)['taskId']
        on_submitted(str(task_id))
        deadline = asyncio.get_running_loop().time() + settings.provider_timeout
        while asyncio.get_running_loop().time() < deadline:
            payload = {'apiKey': key, 'taskId': task_id}
            state = rh_data(await json_request(client, 'POST', '/task/openapi/status', json=payload))
            if state == 'FAILED':
                raise ProviderError('RunningHub 工作流执行失败，请在 RunningHub 中检查对应任务')
            if state == 'SUCCESS':
                outputs = rh_data(await json_request(client, 'POST', '/task/openapi/outputs', json=payload))
                contents = []
                # Use a separate client so the API key is never sent to a file CDN.
                async with httpx.AsyncClient(timeout=90, follow_redirects=True) as files_client:
                    for item in outputs or []:
                        if str(item.get('fileType', '')).lower() in ('png', 'jpg', 'jpeg', 'webp', 'image'):
                            contents.append(await bounded_download(files_client, item['fileUrl']))
                if not contents:
                    raise ProviderError('RunningHub 未返回支持的图片输出')
                return contents
            if state not in ('QUEUED', 'RUNNING'):
                raise ProviderError('RunningHub 返回未知任务状态')
            await asyncio.sleep(3)
        raise ProviderError('RunningHub 等待超时；远端任务可能仍在运行，请检查后再提交')


async def execute(step, image_path, on_submitted):
    try:
        if step['template']['provider'] == 'comfyui':
            return await execute_comfy(step, image_path, on_submitted)
        return await execute_runninghub(step, image_path, on_submitted)
    except httpx.ConnectError as exc:
        raise ProviderError('无法连接执行服务，请检查服务是否启动及网络地址') from exc
    except httpx.TimeoutException as exc:
        raise ProviderError('执行服务请求超时；请核对远端任务状态后再重试') from exc
    except (KeyError, TypeError, httpx.HTTPStatusError) as exc:
        raise ProviderError('执行服务响应格式不正确，请检查工作流及接口配置') from exc
