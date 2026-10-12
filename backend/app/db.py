from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings


class Base(DeclarativeBase):
    pass


database_url = settings.database_url or URL.create('mysql+pymysql', username=settings.mysql_user,
    password=settings.mysql_password, host=settings.mysql_host, port=settings.mysql_port,
    database=settings.mysql_database, query={'charset': 'utf8mb4'})
engine = create_engine(database_url, pool_pre_ping=True,
                       connect_args={'check_same_thread': False} if settings.database_url.startswith('sqlite') else {})
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as db:
        yield db
