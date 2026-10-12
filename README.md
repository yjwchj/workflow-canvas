# 织图 · 局域网 AI 工作流无限画布

基于 `PRD-局域网工作流无限画布-v0.1.md` 的第一版实现。Vue 3、Element Plus、Vite、JavaScript；FastAPI、Python；MySQL、Redis。

## 已实现

- 自行注册和登录，账号独立的多画布、任务及图片访问权限。
- 无限画布平移、缩放、节点拖动、手动连线、缩略地图；连线类型、单输入和循环校验。
- 文字输入、图片上传/拖入、文字生成图片和图片编辑工作流、复用同一结果节点。
- 维护者导入 ComfyUI API 工作流、配置 RunningHub 工作流、设置开放参数与映射、发布模板新版本。
- 工作流单步运行、整条 DAG 按拓扑顺序运行，提交时固定图、模板版本、参数和已有输入图片。
- 手动选图暂停与继续、自动使用本次最后一张输出图；每次重复执行 1–8 次，历史图片累计保存。
- 图片节点内切换、右侧历史选择、最多四张图片并排比较，历史图片可以作为下游输入。
- MySQL 持久化、Redis 协调 FIFO 队列；等待选图释放执行资源；任务记录、排队位置、错误提示。
- 900 ms 防抖自动保存、手动保存、关闭页面前未保存提醒、画布 revision 冲突检测和 JSON 导出。

## 启动：Docker Desktop

需要安装并启动 Docker Desktop。当前交付机器未检测到 Docker、MySQL 和 Redis，因此该部署路径尚未在这台机器运行验证。

在项目根目录执行：

```powershell
Copy-Item .env.example .env
# 编辑 .env：填写 MYSQL_PASSWORD、MYSQL_ROOT_PASSWORD、ADMIN_USERNAME、ADMIN_PASSWORD
docker compose up --build -d
docker compose logs -f api worker
```

打开 `http://localhost:8080`。朋友使用 `http://维护者电脑的局域网IP:8080`，需允许 Windows 防火墙的 8080 端口入站。本产品只面向局域网。

维护者账号在首次启动时由 `.env` 创建；密码至少 8 位，用户名为 3–40 位英文、数字、下划线或短横线。不要使用示例密码。以后修改 `.env` 的管理员密码不会自动覆盖已有账号。朋友通过页面自行注册。

MySQL 与 Redis 仅在容器网络内部开放。图片保存在项目 `data/media`，API 和 worker 共用同一目录。MySQL 与 Redis 使用命名卷。

### 接入本地 ComfyUI

1. 在维护者电脑启动 ComfyUI。使用 Docker Desktop 时，`.env` 的 `COMFYUI_URL=http://host.docker.internal:8188`。ComfyUI 需要在容器可访问的地址监听（例如启动参数 `--listen 0.0.0.0`），并通过局域网防火墙控制访问。
2. 从 ComfyUI 导出 **API 格式**工作流 JSON；通常包含以节点 ID 为键的对象，以及 `class_type`、`inputs`，不能使用 `nodes/links` 画布格式。
3. 以维护者账号登录，打开“工作流管理”，创建模板、导入 JSON。
4. 配置文字输入节点 ID 和字段（例如 `6.text`）；图片编辑额外配置 LoadImage 输入（例如 `10.image`）。
5. 添加开放参数（例如 `3.steps`），指定类型、默认值和范围。参数不能覆盖文字或图片映射。可指定输出节点 ID；留空时保存所有图片输出。
6. 确认模型、插件节点和 SaveImage/PreviewImage 输出在原 ComfyUI 工作流中可运行。

### 接入 RunningHub

1. 在根目录 `.env` 配置 `RUNNINGHUB_API_KEY`、`RUNNINGHUB_URL`；重新创建服务使配置生效：`docker compose up -d --force-recreate api worker`。
2. 在“工作流管理”选择 RunningHub，填写工作流数字 ID，以及与该工作流一致的 nodeId/fieldName 映射。
3. 当前接入的是 **ComfyUI 工作流 API** `/task/openapi/create`，不是 AI 应用 webapp API。工作流必须支持 API 调用，维护者账号需有可用余额。
4. 后端自动上传选中的输入图片、提交任务、轮询状态、下载图片并保存；API Key 不进入画布、浏览器或文件 CDN 请求。

官方接口依据：[ComfyUI 服务路由](https://docs.comfy.org/development/comfyui-server/comms_routes)、[RunningHub 工作流 API](https://www.runninghub.cn/runninghub-api-doc-en/api-425761093)、[RunningHub 状态查询](https://www.runninghub.cn/runninghub-api-doc-en/api-425761033)、[RunningHub 输出查询](https://www.runninghub.cn/runninghub-api-doc-en/api-425761034)。适配器已做模拟 HTTP 契约测试；真实服务需由你的模型和工作流完成联调。

## 本机开发

需先准备 MySQL 8 和 Redis，创建 `canvas` 数据库及数据库账号。安装 Python 3.12+、Node.js 20.19+。

后端终端（`backend` 目录）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
# 编辑 backend/.env 中的数据库、Redis、管理员和生成服务配置
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

另开终端，在 `backend` 运行执行器：

```powershell
.\.venv\Scripts\python.exe -m app.worker
```

前端终端（`frontend` 目录）：

```powershell
npm ci
npm run dev
```

打开 `http://localhost:5174`。5173 已有其他项目，因此本项目使用 5174。浏览器统一通过前端 `/api` 代理访问后端；不要分别跨域连接。

## 本次本地预览

为了在没有 MySQL/Redis 的机器上检查页面，本次启动了 **SQLite 隔离预览**：`http://localhost:5174`。预览支持注册、画布编辑、上传和保存，任务不会执行；它不代表 MySQL/Redis 或真实图片生成已验收。预览数据位于 `backend/data/preview.db` 和 `backend/data/preview-media`，与正式部署隔离。

预览测试账号：`preview_owner`（维护者）、`preview_user`（普通用户），测试密码均为 `PreviewOnly123!`。这两个账号只用于隔离预览，正式部署不要使用这些测试凭据；也可自行注册新账号。预览中的“接入示例（待配模型）”用于检验管理表单和连线，需要替换 `YOUR_MODEL.safetensors` 或导入自己的完整工作流，尚未生成任何图片。

## 验证

```powershell
# backend
.\.venv\Scripts\python.exe -m pytest -q
# frontend
npm test
npm run build
```

后端测试使用临时 SQLite 数据库和模拟执行服务，覆盖权限、保存冲突、连线校验、参数快照、上传恢复、手动选图续跑、自动选图、历史累计及两种服务的 HTTP 适配。前端测试覆盖连线与保存序列化。实际 MySQL/Redis、真实模型和 RunningHub 余额/API Key 尚未联调；两个真人账号的完整验收需在这些资源配置后完成。

## 实现边界与默认规则

- 每个输入端口仅允许一个来源；工作流必须连接一个结果节点，图中不允许循环。图片编辑同时需要文字说明和图片输入。每次只传一张选中图片。
- 默认手动模式，只在某结果有未运行的图片下游时暂停；末尾步骤直接完成。自动模式使用当前步骤本批最后保存的图片，不使用上一次运行的图片。
- 第一版使用单执行器，所有来源共用 FIFO 队列，RunningHub 也按顺序提交；等待选图时释放执行器，继续时重新进入队尾。MySQL 是队列的持久化来源，Redis 提供唤醒与租约，Redis 重连后扫描未执行任务，避免只写入数据库时丢任务。
- 循环生成使用相同固定参数执行多次；若 seed 固定，可能生成相同图片。需在模板中开放 seed 或配置工作流随机节点。
- 模板更新后旧画布下次运行使用新版本；已提交任务仍使用旧副本。参数不兼容时明确报错，建议为不兼容变更新建模板。
- 可以取消排队及等待选图任务；运行中不提供远端全局中断，避免影响他人。失败后修改节点再运行；不自动重试付费或远端任务。进程中断/超时可能留下远端运行任务，需要核对远端记录后重新提交。
- 原始图片最多 20 MB、4000 万像素，支持 PNG/JPEG/WebP。图像通过带账号校验的接口访问，不公开媒体目录。
- 第一版暂不提供账号找回、画布删除、多人协作、朋友导入工作流、自动清理历史。数据库初次自动建表；后续改表结构需要独立迁移。
- 桌面浏览器为主要使用环境，建议 1280px 及以上；窄窗口可横向滚动工作台。

## 备份

停止提交任务，等待执行结束，保存画布，再停掉 `api` 和 `worker`；导出 MySQL `canvas` 数据库，同时备份 `data/media`。数据库与图片需要成对恢复。不要用 `docker compose down -v` 清空命名卷。

## 目录

```text
frontend/src/components/    登录、工作台、节点、参数、历史、管理界面
frontend/src/composables/   画布状态、自动保存、任务轮询
frontend/src/lib/           连线校验、图序列化和测试
backend/app/main.py        API、权限、画布、模板、图片、任务
backend/app/graph.py       DAG 校验、参数校验与执行快照
backend/app/worker.py      队列、任务执行、选图暂停和续跑
backend/app/providers.py   ComfyUI / RunningHub 接入
backend/tests/             隔离数据库及模拟执行测试
compose.yaml               MySQL / Redis / API / worker / web 部署
```
