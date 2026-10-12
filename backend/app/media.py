import io
from uuid import uuid4
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException
from .config import settings
from .models import Asset


def store_image(db, content, user_id, canvas_id, node_id, run_id=None):
    if not content or len(content) > settings.max_image_bytes:
        raise HTTPException(413, '图片为空或超过 20 MB')
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.format not in ('PNG', 'JPEG', 'WEBP'):
                raise ValueError('仅支持 PNG、JPEG、WebP')
            if image.width * image.height > 40_000_000:
                raise ValueError('图片超过 4000 万像素')
            image.verify()
            width, height, fmt = image.width, image.height, image.format
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, '无效图片：仅支持 PNG、JPEG、WebP，最多 4000 万像素') from exc
    asset_id = str(uuid4())
    suffix = {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp'}[fmt]
    relative = f'{user_id}/{asset_id}.{suffix}'
    path = settings.media_dir / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    asset = Asset(id=asset_id, user_id=user_id, canvas_id=canvas_id, node_id=node_id,
                  run_id=run_id, path=relative, mime=f'image/{"jpeg" if fmt == "JPEG" else suffix}', width=width, height=height)
    db.add(asset)
    db.flush()
    return asset


def asset_payload(asset):
    return {'id': asset.id, 'node_id': asset.node_id, 'run_id': asset.run_id,
            'width': asset.width, 'height': asset.height,
            'url': f'/api/assets/{asset.id}/file', 'created_at': asset.created_at.isoformat() + 'Z'}
