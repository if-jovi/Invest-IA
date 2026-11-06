import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from sqlalchemy import Date, create_engine, inspect
from sqlalchemy.types import TypeDecorator
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


class DataIso(TypeDecorator):
    """Coluna DATE que também aceita texto 'AAAA-MM-DD' ao gravar e filtrar."""

    impl = Date
    cache_ok = True

    def process_bind_param(self, valor, dialect):
        if isinstance(valor, str):
            return date.fromisoformat(valor)
        return valor


PASTA_MIGRACOES = Path(__file__).resolve().parents[2] / "migracoes"
REVISAO_INICIAL = "0001"


def configuracaoAlembic():
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(PASTA_MIGRACOES))
    return config


def migrar(alvo=None) -> None:
    """Aplica as migrações pendentes. Banco criado pelo antigo create_all (com
    tabelas e sem alembic_version) é marcado na revisão inicial antes."""
    from alembic import command

    alvo = alvo if alvo is not None else engine
    config = configuracaoAlembic()

    with alvo.begin() as conexao:
        tabelas = set(inspect(conexao).get_table_names())
        if "alembic_version" not in tabelas and "recomendacoes" in tabelas:
            config.attributes["connection"] = conexao
            command.stamp(config, REVISAO_INICIAL)

    with alvo.begin() as conexao:
        config.attributes["connection"] = conexao
        command.upgrade(config, "head")


def criarTabelas() -> None:
    migrar()
