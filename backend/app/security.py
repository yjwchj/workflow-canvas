import hashlib
import hmac
import secrets
from datetime import timedelta
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, LoginSession, now


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f'{salt}:{digest}'


def check_password(password, stored):
    salt, expected = stored.split(':')
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(expected, actual)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db, user):
    token = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires_at=now() + timedelta(days=7)))
    db.commit()
    return token


def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get('canvas_session', '')
    session = db.get(LoginSession, token_hash(token)) if token else None
    if not session or session.expires_at <= now():
        raise HTTPException(401, '请先登录')
    return db.get(User, session.user_id)


def admin_user(user: User = Depends(current_user)):
    if not user.is_admin:
        raise HTTPException(403, '仅维护者可以管理工作流')
    return user
