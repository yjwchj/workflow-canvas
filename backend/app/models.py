from datetime import datetime, timezone
from sqlalchemy import String, Integer, JSON, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True)
    password: Mapped[str] = mapped_column(String(256))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)


class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class Canvas(Base):
    __tablename__ = 'canvases'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    graph: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Template(Base):
    __tablename__ = 'templates'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    provider: Mapped[str] = mapped_column(String(20))
    version: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict] = mapped_column(JSON)


class Run(Base):
    __tablename__ = 'runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    canvas_id: Mapped[str] = mapped_column(ForeignKey('canvases.id'), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    step: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    remote_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Asset(Base):
    __tablename__ = 'assets'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    canvas_id: Mapped[str] = mapped_column(ForeignKey('canvases.id'), index=True)
    node_id: Mapped[str] = mapped_column(String(80), index=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey('runs.id'), nullable=True)
    path: Mapped[str] = mapped_column(String(300))
    mime: Mapped[str] = mapped_column(String(30))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
