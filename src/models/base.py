import os
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config.settings import DB_CONFIG

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
)

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)


FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def agora() -> datetime:
    return datetime.now(FUSO_BRASILIA).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


def criarTabelas() -> None:
    import src.models.entities
    Base.metadata.create_all(engine)
