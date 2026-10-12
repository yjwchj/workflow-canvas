import asyncio
import contextlib
import logging
from copy import deepcopy
from sqlalchemy import select, update
from redis.asyncio import Redis
from .config import settings
from .db import SessionLocal
from .models import Run, Asset, now
from .media import store_image
from .providers import execute, ProviderError

logger = logging.getLogger(__name__)


async def process_run(run_id, executor=execute):
    """Each step commits its images before pausing. A pause never holds a GPU lease."""
    with SessionLocal() as db:
        run = db.get(Run, run_id)
        if not run or run.status != 'queued':
            return
        claimed = db.execute(update(Run).where(Run.id == run_id, Run.status == 'queued').values(status='running'))
        if claimed.rowcount != 1:
            db.rollback()
            return
        db.commit()
        db.expire_all()
        run = db.get(Run, run_id)
        try:
            steps = run.snapshot['steps']
            while run.step < len(steps):
                step = steps[run.step]
                run.remote_id = None
                db.commit()
                image_path = None
                if step['template']['kind'] == 'image-edit':
                    chosen = run.outputs.get(step['image_source'], {}).get('selected', step['selected_asset_id'])
                    asset = db.get(Asset, chosen) if chosen else None
                    if not asset or asset.user_id != run.user_id or asset.canvas_id != run.canvas_id:
                        raise ProviderError('下游步骤没有可用的输入图片')
                    image_path = settings.media_dir / asset.path
                batch = []

                def record_remote(remote_id):
                    run.remote_id = remote_id
                    db.commit()

                for _ in range(step['params']['count']):
                    contents = await executor(deepcopy(step), image_path, record_remote)
                    for content in contents:
                        asset = store_image(db, content, run.user_id, run.canvas_id, step['result_id'], run.id)
                        batch.append(asset.id)
                    db.commit()
                if not batch:
                    raise ProviderError('工作流没有生成图片')
                outputs = deepcopy(run.outputs)
                outputs[step['result_id']] = {'assets': batch, 'selected': batch[-1]}
                run.outputs = outputs
                run.step += 1
                remaining = steps[run.step:]
                has_downstream = any(item['image_source'] == step['result_id'] for item in remaining)
                if has_downstream and run.snapshot['selection_mode'] == 'manual':
                    run.status = 'waiting_selection'
                    db.commit()
                    return
                db.commit()
            run.status = 'completed'
            db.commit()
        except asyncio.CancelledError:
            run.status = 'failed'
            run.error = '执行进程中断；远端可能仍在运行，请核对后再提交'
            db.commit()
            raise
        except Exception as exc:
            db.rollback()
            run = db.get(Run, run_id)
            run.status = 'failed'
            if isinstance(exc, ProviderError):
                run.error = str(exc)
            elif hasattr(exc, 'detail'):
                run.error = str(exc.detail)
            else:
                run.error = '结果处理失败，请联系维护者检查服务日志'
                logger.exception('Task processing failed: %s', run_id)
            db.commit()


async def renew_lease(lock, redis):
    while True:
        await asyncio.sleep(8)
        await lock.extend(30, replace_ttl=True)
        await redis.set('canvas:worker:alive', '1', ex=20)


async def work():
    redis = Redis.from_url(settings.redis_url)
    lock = redis.lock('canvas:worker:lease', timeout=30, thread_local=False)
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            if not await lock.acquire(blocking=False):
                await asyncio.sleep(5)
                continue
            heartbeat = asyncio.create_task(renew_lease(lock, redis))
            try:
                with SessionLocal() as db:
                    # A crashed task is not blindly resubmitted to a paid/external provider.
                    db.execute(update(Run).where(Run.status == 'running').values(
                        status='failed', error='执行进程曾中断；请检查远端任务后重新提交'))
                    db.commit()
                await redis.set('canvas:worker:alive', '1', ex=20)
                while not heartbeat.done():
                    await redis.set('canvas:worker:alive', '1', ex=20)
                    with SessionLocal() as db:
                        run_id = db.scalar(select(Run.id).where(Run.status == 'queued').order_by(Run.queued_at, Run.id).limit(1))
                    if run_id:
                        task = asyncio.create_task(process_run(run_id))
                        done, _ = await asyncio.wait([task, heartbeat], return_when=asyncio.FIRST_COMPLETED)
                        if heartbeat in done:
                            task.cancel()
                            with contextlib.suppress(asyncio.CancelledError):
                                await task
                            heartbeat.result()
                        await task
                    else:
                        await redis.blpop('canvas:wakeup', timeout=3)
            finally:
                heartbeat.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat
                with contextlib.suppress(Exception):
                    await lock.release()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Worker unavailable; retrying')
            await asyncio.sleep(5)


if __name__ == '__main__':
    asyncio.run(work())
