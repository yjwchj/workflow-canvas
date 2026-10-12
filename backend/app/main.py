import re
from contextlib import asynccontextmanager
from copy import deepcopy
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select, update, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from redis import Redis
from redis.exceptions import RedisError
from .config import settings
from .db import Base, engine, get_db, SessionLocal
from .models import User, LoginSession, Canvas, Template, Asset, Run, now
from .schemas import Credentials, CanvasCreate, CanvasSave, TemplateBody, RunBody, ResumeBody, Graph
from .security import current_user, admin_user, hash_password, check_password, create_session, token_hash
from .graph import validate_graph, build_snapshot, checked_params
from .media import store_image, asset_payload

queue = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    if settings.admin_username and settings.admin_password:
        Credentials(username=settings.admin_username, password=settings.admin_password)
        with SessionLocal() as db:
            admin_name = settings.admin_username.lower()
            admin = db.scalar(select(User).where(User.username == admin_name))
            if not admin:
                db.add(User(username=admin_name, password=hash_password(settings.admin_password), is_admin=True))
                db.commit()
    yield


app = FastAPI(title='局域网 AI 工作流画布', lifespan=lifespan)


@app.middleware('http')
async def same_origin_mutations(request: Request, call_next):
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        origin = request.headers.get('origin')
        if origin and origin != f"{request.url.scheme}://{request.headers.get('host')}":
            return Response('跨站请求已拒绝', status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    return response


def own(db, model, key, user):
    item = db.get(model, key)
    if not item or item.user_id != user.id:
        raise HTTPException(404, '内容不存在')
    return item


def user_payload(user):
    return {'id': user.id, 'username': user.username, 'is_admin': user.is_admin}


def canvas_payload(canvas, full=False):
    payload = {'id': canvas.id, 'name': canvas.name, 'revision': canvas.revision,
               'updated_at': canvas.updated_at.isoformat() + 'Z'}
    if full:
        payload['graph'] = canvas.graph
    return payload


def set_login(response, token):
    response.set_cookie('canvas_session', token, httponly=True, samesite='strict',
                        secure=settings.secure_cookies, max_age=7 * 86400)


@app.post('/api/auth/register', status_code=201)
def register(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = User(username=body.username.lower(), password=hash_password(body.password), is_admin=False)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '用户名已存在')
    set_login(response, create_session(db, user))
    return user_payload(user)


@app.post('/api/auth/login')
def login(body: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username.lower()))
    if not user or not check_password(body.password, user.password):
        raise HTTPException(401, '用户名或密码不正确')
    set_login(response, create_session(db, user))
    return user_payload(user)


@app.get('/api/auth/me')
def me(user: User = Depends(current_user)):
    return user_payload(user)


@app.post('/api/auth/logout')
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session = db.get(LoginSession, token_hash(request.cookies.get('canvas_session', '')))
    if session:
        db.delete(session)
        db.commit()
    response.delete_cookie('canvas_session')
    return {'ok': True}


@app.get('/api/health')
def health(db: Session = Depends(get_db)):
    db.execute(text('SELECT 1'))
    try:
        queue.ping()
        worker = bool(queue.exists('canvas:worker:alive'))
        redis_ready = True
    except RedisError:
        redis_ready, worker = False, False
    return {'database': True, 'redis': redis_ready, 'worker': worker,
            'runninghub_configured': bool(settings.runninghub_api_key)}


@app.get('/api/canvases')
def canvases(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return [canvas_payload(c) for c in db.scalars(select(Canvas).where(Canvas.user_id == user.id).order_by(Canvas.updated_at.desc()))]


@app.post('/api/canvases', status_code=201)
def create_canvas(body: CanvasCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    canvas = Canvas(id=str(uuid4()), user_id=user.id, name=body.name, graph=Graph().model_dump())
    db.add(canvas)
    db.commit()
    return canvas_payload(canvas, True)


@app.get('/api/canvases/{canvas_id}')
def get_canvas(canvas_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return canvas_payload(own(db, Canvas, canvas_id, user), True)


@app.put('/api/canvases/{canvas_id}')
def save_canvas(canvas_id: str, body: CanvasSave, db: Session = Depends(get_db), user: User = Depends(current_user)):
    own(db, Canvas, canvas_id, user)
    graph = body.graph.model_dump()
    validate_graph(graph)
    for node in graph['nodes']:
        selected = node['data'].get('selectedAssetId')
        if selected:
            asset = own(db, Asset, selected, user)
            if asset.canvas_id != canvas_id or asset.node_id != node['id']:
                raise HTTPException(422, '选中图片与节点不匹配')
    result = db.execute(update(Canvas).where(Canvas.id == canvas_id, Canvas.user_id == user.id,
                       Canvas.revision == body.revision).values(name=body.name, graph=graph,
                       revision=body.revision + 1, updated_at=now()))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, '画布已在其他页面修改，请导出当前画布后重新加载')
    db.commit()
    db.expire_all()
    return canvas_payload(db.get(Canvas, canvas_id), True)


@app.get('/api/templates')
def templates(db: Session = Depends(get_db), user: User = Depends(current_user)):
    items = db.scalars(select(Template).where(Template.enabled == True).order_by(Template.name))
    return [{'id': t.id, 'name': t.name, 'kind': t.kind, 'provider': t.provider, 'version': t.version,
             'parameters': [{key: value for key, value in p.items() if key not in ('node_id', 'field')} for p in t.config['parameters']]}
            for t in items]


@app.get('/api/admin/templates')
def admin_templates(db: Session = Depends(get_db), user: User = Depends(admin_user)):
    return [{'id': t.id, 'name': t.name, 'kind': t.kind, 'provider': t.provider, 'version': t.version,
             'enabled': t.enabled, 'config': t.config} for t in db.scalars(select(Template).order_by(Template.name))]


def validate_template(body):
    config = body.config.model_dump()
    keys = [p['key'] for p in config['parameters']]
    if len(set(keys)) != len(keys) or 'count' in keys:
        raise HTTPException(422, '开放参数名称重复或使用了保留名称 count')
    if body.kind == 'image-edit' and not config['image_binding']:
        raise HTTPException(422, '图片编辑工作流必须配置图片映射')
    bindings = [config['prompt_binding']] + config['parameters']
    if config['image_binding']:
        bindings.append(config['image_binding'])
    ports = [(b['node_id'], b['field']) for b in bindings]
    if len(set(ports)) != len(ports):
        raise HTTPException(422, '参数映射不可覆盖文字或图片输入映射')
    if body.provider == 'comfyui':
        if not config['workflow'] or 'nodes' in config['workflow']:
            raise HTTPException(422, '请上传 ComfyUI API 格式工作流，而非画布格式')
        for binding in bindings:
            node = config['workflow'].get(binding['node_id'], {})
            if not isinstance(node, dict) or binding['field'] not in node.get('inputs', {}):
                raise HTTPException(422, f"映射 {binding['node_id']}.{binding['field']} 不存在于工作流")
    elif not re.fullmatch(r'\d{1,80}', config['workflow_id']):
        raise HTTPException(422, 'RunningHub 工作流 ID 必须填写有效数字 ID')
    checked_params({'config': config}, {})
    return config


@app.post('/api/admin/templates', status_code=201)
def create_template(body: TemplateBody, db: Session = Depends(get_db), user: User = Depends(admin_user)):
    config = validate_template(body)
    template = Template(id=str(uuid4()), name=body.name, kind=body.kind, provider=body.provider,
                        enabled=body.enabled, config=config)
    db.add(template)
    db.commit()
    return {'id': template.id}


@app.put('/api/admin/templates/{template_id}')
def update_template(template_id: str, body: TemplateBody, db: Session = Depends(get_db), user: User = Depends(admin_user)):
    config = validate_template(body)
    template = db.get(Template, template_id)
    if not template:
        raise HTTPException(404, '工作流不存在')
    if template.kind != body.kind:
        raise HTTPException(422, '已有模板不可变更工作流类型，请新建模板')
    template.name, template.provider, template.enabled, template.config = body.name, body.provider, body.enabled, config
    template.version += 1
    db.commit()
    return {'id': template.id, 'version': template.version}


@app.get('/api/canvases/{canvas_id}/assets')
def assets(canvas_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    own(db, Canvas, canvas_id, user)
    return [asset_payload(a) for a in db.scalars(select(Asset).where(Asset.canvas_id == canvas_id, Asset.user_id == user.id).order_by(Asset.created_at, Asset.id))]


@app.post('/api/canvases/{canvas_id}/assets', status_code=201)
async def upload_asset(canvas_id: str, node_id: str = Form(...), file: UploadFile = File(...),
                       db: Session = Depends(get_db), user: User = Depends(current_user)):
    canvas = own(db, Canvas, canvas_id, user)
    if not any(n['id'] == node_id and n['type'] == 'image' for n in canvas.graph['nodes']):
        raise HTTPException(422, '请先保存图片输入节点')
    content = await file.read(settings.max_image_bytes + 1)
    asset = store_image(db, content, user.id, canvas_id, node_id)
    db.commit()
    return asset_payload(asset)


@app.get('/api/assets/{asset_id}/file')
def asset_file(asset_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    asset = own(db, Asset, asset_id, user)
    path = settings.media_dir / asset.path
    if not path.is_file():
        raise HTTPException(404, '图片文件不存在，请联系维护者恢复备份')
    return FileResponse(path, media_type=asset.mime)


def run_payload(run, position=None):
    steps = run.snapshot['steps']
    current = steps[min(run.step, len(steps) - 1)]
    waiting = steps[run.step - 1] if run.status == 'waiting_selection' else None
    return {'id': run.id, 'status': run.status, 'step': run.step, 'total_steps': len(steps),
            'node_id': current['node_id'], 'step_name': current['template']['name'],
            'waiting_result_id': waiting['result_id'] if waiting else None,
            'protected_node_ids': list({node for step in steps for node in (step['node_id'], step['result_id'], step['image_source']) if node}),
            'outputs': run.outputs, 'error': run.error, 'remote_id': run.remote_id,
            'queue_position': position, 'created_at': run.created_at.isoformat() + 'Z'}


def wake_worker():
    try:
        queue.lpush('canvas:wakeup', '1')
        queue.ltrim('canvas:wakeup', 0, 99)
    except RedisError:
        pass  # Database remains the durable queue; worker periodically reconciles it.


@app.post('/api/canvases/{canvas_id}/runs', status_code=201)
def create_run(canvas_id: str, body: RunBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    canvas = own(db, Canvas, canvas_id, user)
    snapshot = build_snapshot(db, canvas, body.node_id)
    run = Run(id=str(uuid4()), user_id=user.id, canvas_id=canvas_id, status='queued', snapshot=snapshot)
    db.add(run)
    db.commit()
    wake_worker()
    return run_payload(run)


@app.get('/api/canvases/{canvas_id}/runs')
def runs(canvas_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    own(db, Canvas, canvas_id, user)
    queued = list(db.scalars(select(Run.id).where(Run.status == 'queued').order_by(Run.queued_at, Run.id)))
    positions = {run_id: index + 1 for index, run_id in enumerate(queued)}
    items = db.scalars(select(Run).where(Run.canvas_id == canvas_id, Run.user_id == user.id).order_by(Run.created_at.desc()).limit(100))
    return [run_payload(r, positions.get(r.id)) for r in items]


@app.post('/api/runs/{run_id}/resume')
def resume(run_id: str, body: ResumeBody, db: Session = Depends(get_db), user: User = Depends(current_user)):
    run = own(db, Run, run_id, user)
    if run.status != 'waiting_selection':
        raise HTTPException(409, '任务当前未等待选图')
    result_id = run.snapshot['steps'][run.step - 1]['result_id']
    asset = own(db, Asset, body.asset_id, user)
    if asset.canvas_id != run.canvas_id or asset.node_id != result_id:
        raise HTTPException(422, '请选择等待节点中的图片')
    outputs = deepcopy(run.outputs)
    outputs[result_id]['selected'] = asset.id
    result = db.execute(update(Run).where(Run.id == run_id, Run.status == 'waiting_selection').values(
        outputs=outputs, status='queued', queued_at=now()))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, '任务已继续，请刷新状态')
    db.commit()
    db.expire_all()
    wake_worker()
    return run_payload(db.get(Run, run_id))


@app.post('/api/runs/{run_id}/cancel')
def cancel(run_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    own(db, Run, run_id, user)
    result = db.execute(update(Run).where(Run.id == run_id, Run.status.in_(['queued', 'waiting_selection'])).values(status='cancelled'))
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(409, '运行中的任务暂不支持取消，请等待执行结束')
    db.commit()
    return {'ok': True}
