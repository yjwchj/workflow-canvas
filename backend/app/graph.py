from copy import deepcopy
from fastapi import HTTPException
from .models import Template, Asset


def invalid(message):
    raise HTTPException(422, message)


def validate_graph(graph):
    nodes = {node['id']: node for node in graph['nodes']}
    if len(nodes) != len(graph['nodes']):
        invalid('节点 ID 不可重复')
    seen, incoming, adjacency = set(), {}, {key: [] for key in nodes}
    for edge in graph['edges']:
        source, target = nodes.get(edge['source']), nodes.get(edge['target'])
        if not source or not target or source == target:
            invalid('连线引用了不存在或相同的节点')
        pair = (edge['source'], edge['target'], edge.get('targetHandle'))
        if pair in seen:
            invalid('不可重复连线')
        seen.add(pair)
        st, tt, handle = source['type'], target['type'], edge.get('targetHandle')
        valid = (st == 'text' and tt == 'workflow' and handle == 'text') or \
                (st in ('image', 'result') and tt == 'workflow' and handle == 'image') or \
                (st == 'workflow' and tt == 'result' and handle == 'image')
        if not valid:
            invalid('仅允许文字→工作流文字输入、图片/结果→工作流图片输入、工作流→结果')
        port = (edge['target'], handle)
        if port in incoming:
            invalid('每个输入端口只能连接一个来源')
        incoming[port] = edge['source']
        adjacency[edge['source']].append(edge['target'])
    degrees = {key: 0 for key in nodes}
    for targets in adjacency.values():
        for target in targets:
            degrees[target] += 1
    queue = [key for key, degree in degrees.items() if not degree]
    order = []
    while queue:
        key = queue.pop(0)
        order.append(key)
        for target in adjacency[key]:
            degrees[target] -= 1
            if degrees[target] == 0:
                queue.append(target)
    if len(order) != len(nodes):
        invalid('画布存在循环连线，请移除循环后运行')
    return nodes, incoming, adjacency, order


def checked_params(template, raw):
    params = {}
    allowed = {p['key'] for p in template['config']['parameters']} | {'count'}
    if set(raw) - allowed:
        invalid('包含未开放的工作流参数')
    count = raw.get('count', 1)
    if type(count) is not int or not 1 <= count <= 8:
        invalid('生成次数必须是 1–8 的整数')
    params['count'] = count
    for spec in template['config']['parameters']:
        value = raw.get(spec['key'], spec['default'])
        kind = spec['type']
        if kind == 'integer' and type(value) is not int:
            invalid(f"{spec['label']}必须是整数")
        if kind == 'number' and (type(value) not in (int, float) or not __import__('math').isfinite(value)):
            invalid(f"{spec['label']}必须是有效数字")
        if kind in ('text', 'select') and (not isinstance(value, str) or len(value) > 10000):
            invalid(f"{spec['label']}格式不正确")
        if kind == 'select' and value not in spec['options']:
            invalid(f"{spec['label']}不在允许选项中")
        if kind in ('integer', 'number'):
            if spec.get('min') is not None and value < spec['min'] or spec.get('max') is not None and value > spec['max']:
                invalid(f"{spec['label']}超出允许范围")
        params[spec['key']] = value
    return params


def template_snapshot(template):
    return {'id': template.id, 'name': template.name, 'kind': template.kind,
            'provider': template.provider, 'version': template.version, 'config': deepcopy(template.config)}


def build_snapshot(db, canvas, node_id=None):
    graph = deepcopy(canvas.graph)
    nodes, incoming, adjacency, order = validate_graph(graph)
    workflows = [key for key in order if nodes[key]['type'] == 'workflow']
    if node_id:
        if node_id not in workflows:
            invalid('请选择工作流节点运行')
        workflows = [node_id]
    if not workflows:
        invalid('请先添加工作流节点')
    steps = []
    planned_results = set()
    for key in workflows:
        node = nodes[key]
        template = db.get(Template, node['data'].get('templateId'))
        if not template or not template.enabled:
            invalid('工作流未配置或已停用，请联系维护者')
        snapshot = template_snapshot(template)
        params = checked_params(snapshot, node['data'].get('params', {}))
        text_source = incoming.get((key, 'text'))
        prompt = nodes[text_source]['data'].get('text', '') if text_source else ''
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 10000:
            invalid(f'{template.name}需要连接非空的文字节点（最多 10000 字）')
        image_source = incoming.get((key, 'image'))
        selected = None
        if template.kind == 'image-edit':
            if not image_source:
                invalid(f'{template.name}需要连接图片或结果节点')
            selected = nodes[image_source]['data'].get('selectedAssetId')
            if image_source not in planned_results:
                asset = db.get(Asset, selected) if selected else None
                if not asset or asset.user_id != canvas.user_id or asset.canvas_id != canvas.id or asset.node_id != image_source:
                    invalid('图片输入尚未选择有效图片')
        results = [target for target in adjacency[key] if nodes[target]['type'] == 'result']
        if len(results) != 1:
            invalid(f'{template.name}必须连接一个结果节点')
        result_id = results[0]
        steps.append({'node_id': key, 'result_id': result_id, 'template': snapshot,
                      'params': params, 'prompt': prompt, 'image_source': image_source,
                      'selected_asset_id': selected})
        planned_results.add(result_id)
    return {'graph': graph, 'steps': steps, 'selection_mode': graph.get('selectionMode', 'manual')}
