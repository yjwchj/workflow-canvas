import os
import tempfile
from pathlib import Path
import pytest

test_root = Path(tempfile.mkdtemp(prefix='canvas-tests-'))
os.environ['DATABASE_URL'] = f'sqlite:///{(test_root / "test.db").as_posix()}'
os.environ['MEDIA_DIR'] = str(test_root / 'media')
os.environ['ADMIN_USERNAME'] = 'testowner'
os.environ['ADMIN_PASSWORD'] = 'TestOwner123!'

from app.main import app
from app.db import Base, engine, SessionLocal
from app.models import User
from app.security import hash_password
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def fresh_database(monkeypatch):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(User(username='testowner', password=hash_password('TestOwner123!'), is_admin=True))
        db.commit()
    monkeypatch.setattr('app.main.wake_worker', lambda: None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin(client):
    assert client.post('/api/auth/login', json={'username': 'testowner', 'password': 'TestOwner123!'}).status_code == 200
    return client
