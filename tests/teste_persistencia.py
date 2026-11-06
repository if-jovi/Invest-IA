"""Spec: .agents/docs/specs/persistencia.md (DB1-DB6 e casos-limite).

Contrato: as migrações Alembic ficam em `migracoes/` e `base.migrar(engine)`
aplica as pendentes (`base.criarTabelas()` passa a chamar `migrar()`).

SQLite em arquivos temporários; DB6 usa o PostgreSQL do docker compose
(bancos temporários criados e apagados pelo teste).
"""
import os
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
PASTA = tempfile.mkdtemp()
try:
    import pandas_ta
except ImportError:
    from tests import pandas_ta_simulado
    sys.modules["pandas_ta"] = pandas_ta_simulado
import dotenv
dotenv.load_dotenv = lambda *a, **k: False
os.environ["DATABASE_URL"] = f"sqlite:///{PASTA}/app.db"
os.environ["ANTHROPIC_API_KEY"] = "chave-de-teste"
os.environ["IA_PROVEDOR"] = "claude"

import numpy as np
import pandas as pd
import anthropic
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, Table, create_engine, event, inspect, select, text
from sqlalchemy import types as tipos

import src.models.base as base

ok = []


def passo(nome):
    ok.append(nome)
    print("OK ", nome)


CABECA = ScriptDirectory(str(RAIZ / "migracoes")).get_current_head()
assert CABECA, "nenhuma migração encontrada em migracoes/"
TABELAS = {"usuarios", "carteiras", "itens_b3", "itens_carteiras", "operacoes", "recomendacoes",
           "avaliacoes_ia"}  # avaliacoes_ia: desempenho-ia.md (DI7, migração 0005)

# Schema gerado pelo create_all antes do Alembic (extraído do código anterior)
DDL_ANTIGO = """
CREATE TABLE itens_b3 (item VARCHAR(10) NOT NULL, nome VARCHAR(150) NOT NULL, setor VARCHAR(100),
    ativo BOOLEAN, PRIMARY KEY (item));
CREATE TABLE usuarios (id INTEGER NOT NULL, nome VARCHAR(100) NOT NULL, email VARCHAR(150) NOT NULL,
    senha_hash VARCHAR(255) NOT NULL, criado_em DATETIME, PRIMARY KEY (id), UNIQUE (email));
CREATE TABLE carteiras (id INTEGER NOT NULL, usuario_id INTEGER NOT NULL, nome VARCHAR(100) NOT NULL,
    criado_em DATETIME, PRIMARY KEY (id), UNIQUE (usuario_id), FOREIGN KEY(usuario_id) REFERENCES usuarios (id));
CREATE TABLE operacoes (id INTEGER NOT NULL, usuario_id INTEGER, item VARCHAR(20) NOT NULL, data_entrada DATE,
    preco_entrada NUMERIC(10, 2), data_saida DATE, preco_saida NUMERIC(10, 2), resultado_pct NUMERIC(6, 2),
    PRIMARY KEY (id), FOREIGN KEY(usuario_id) REFERENCES usuarios (id));
CREATE TABLE recomendacoes (id INTEGER NOT NULL, item VARCHAR(20) NOT NULL, data_referencia VARCHAR(10) NOT NULL,
    preco_atual NUMERIC(10, 2), rsi NUMERIC(6, 2), sinal_rsi VARCHAR(20), macd NUMERIC(10, 4),
    macd_signal NUMERIC(10, 4), macd_cruzamento VARCHAR(10), sma20 NUMERIC(10, 2), sma50 NUMERIC(10, 2),
    tendencia_sma VARCHAR(10), recomendacao VARCHAR(10) NOT NULL, justificativa TEXT, riscos TEXT,
    resposta_completa TEXT, gerado_em DATETIME, PRIMARY KEY (id), FOREIGN KEY(item) REFERENCES itens_b3 (item));
CREATE INDEX ix_recomendacoes_item_data ON recomendacoes (item, data_referencia);
CREATE TABLE itens_carteiras (id INTEGER NOT NULL, carteira_id INTEGER NOT NULL, item VARCHAR(20) NOT NULL,
    quantidade NUMERIC(14, 4) NOT NULL, preco_medio NUMERIC(10, 2) NOT NULL, atualizado_em DATETIME,
    PRIMARY KEY (id), CONSTRAINT uq_carteira_item UNIQUE (carteira_id, item),
    FOREIGN KEY(carteira_id) REFERENCES carteiras (id), FOREIGN KEY(item) REFERENCES itens_b3 (item));
"""

DADOS_ANTIGOS = """
INSERT INTO itens_b3 (item, nome, setor, ativo) VALUES ('PETR4', 'Petrobras', 'Energia', TRUE);
INSERT INTO itens_b3 (item, nome, setor, ativo) VALUES ('VALE3', 'Vale', 'Mineração', TRUE);
INSERT INTO usuarios (id, nome, email, senha_hash, criado_em) VALUES (1, 'Maria', 'maria@email.com', 'x$y', '2026-09-01 10:00:00');
INSERT INTO carteiras (id, usuario_id, nome, criado_em) VALUES (1, 1, 'Minha carteira', '2026-09-01 10:00:00');
INSERT INTO itens_carteiras (id, carteira_id, item, quantidade, preco_medio, atualizado_em) VALUES (1, 1, 'PETR4', 100, 10.5, '2026-09-02 10:00:00');
INSERT INTO operacoes (id, usuario_id, item, data_entrada, preco_entrada, data_saida, preco_saida, resultado_pct) VALUES (1, 1, 'PETR4', '2026-05-04', 30, '2026-06-01', 33, 10);
INSERT INTO recomendacoes (id, item, data_referencia, recomendacao, justificativa, riscos, resposta_completa, gerado_em) VALUES (1, 'PETR4', '{data}', 'COMPRA', 'J', '- R', 'texto', '2026-10-02 18:00:00');
INSERT INTO recomendacoes (id, item, data_referencia, recomendacao, justificativa, riscos, resposta_completa, gerado_em) VALUES (2, 'VALE3', '2026-10-01', 'VENDA', 'J', '- R', 'texto', '2026-10-01 18:00:00');
"""


def executar(engine, script):
    with engine.begin() as conexao:
        for comando in (c.strip() for c in script.split(";")):
            if comando:
                conexao.execute(text(comando))


def ddlPara(engine):
    if engine.dialect.name != "postgresql":
        return DDL_ANTIGO
    return DDL_ANTIGO.replace("id INTEGER NOT NULL", "id SERIAL").replace("DATETIME", "TIMESTAMP")


def criarBancoAntigo(engine, dataReferencia="2026-10-02"):
    executar(engine, ddlPara(engine))
    executar(engine, DADOS_ANTIGOS.replace("{data}", dataReferencia))


def versao(engine):
    with engine.connect() as conexao:
        return conexao.execute(text("SELECT version_num FROM alembic_version")).scalar()


def contagens(engine):
    existentes = set(inspect(engine).get_table_names())
    with engine.connect() as conexao:
        return {t: conexao.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in sorted(TABELAS & existentes)
                if t != "avaliacoes_ia"}


def novoSqlite(nome):
    return create_engine(f"sqlite:///{PASTA}/{nome}.db")


def conferirBancoNovo(engine, rotulo):
    base.migrar(engine)
    nomes = set(inspect(engine).get_table_names())
    assert nomes == TABELAS | {"alembic_version"}, (rotulo, nomes)
    assert versao(engine) == CABECA, (rotulo, versao(engine), CABECA)
    colunas = {c["name"]: c for c in inspect(engine).get_columns("recomendacoes")}
    assert isinstance(colunas["data_referencia"]["type"], tipos.Date), (rotulo, colunas["data_referencia"])
    assert "sobre_empresa" in colunas, rotulo
    colunasAvaliacao = {c["name"] for c in inspect(engine).get_columns("avaliacoes_ia")}
    assert {"item", "data_referencia", "periodo", "recomendacao", "preco", "provedor", "modelo",
            "resposta_completa", "gerado_em"} <= colunasAvaliacao, (rotulo, colunasAvaliacao)
    unicas = [sorted(u["column_names"]) for u in inspect(engine).get_unique_constraints("avaliacoes_ia")]
    assert sorted(["item", "data_referencia", "periodo", "modelo"]) in unicas, (rotulo, unicas)
    with engine.begin() as conexao:
        conexao.execute(text("INSERT INTO usuarios (nome, email, senha_hash) VALUES ('Ana', 'ana@x.com', 'h')"))
        assert conexao.execute(text("SELECT id FROM usuarios WHERE email = 'ana@x.com'")).scalar() is not None


def conferirBancoAntigo(engine, rotulo):
    criarBancoAntigo(engine)
    antes = contagens(engine)
    base.migrar(engine)
    assert versao(engine) == CABECA, (rotulo, versao(engine))
    assert contagens(engine) == antes, (rotulo, antes, contagens(engine))
    recomendacoes = Table("recomendacoes", MetaData(), autoload_with=engine)
    with engine.connect() as conexao:
        linhas = {r.id: r for r in conexao.execute(select(recomendacoes))}
    assert linhas[1].data_referencia == date(2026, 10, 2), (rotulo, linhas[1].data_referencia)
    assert linhas[2].data_referencia == date(2026, 10, 1), (rotulo, linhas[2].data_referencia)
    assert linhas[1].recomendacao == "COMPRA" and linhas[1].sobre_empresa is None
    with engine.connect() as conexao:
        assert conexao.execute(text("SELECT preco_medio FROM itens_carteiras")).scalar() == 10.5
        assert conexao.execute(text("SELECT email FROM usuarios WHERE id = 1")).scalar() == "maria@email.com"
    return antes


# DB1 — banco vazio
conferirBancoNovo(novoSqlite("vazio"), "SQLite vazio")
passo("DB1 banco vazio: cria todas as tabelas, data_referencia DATE, sobre_empresa e alembic_version na última revisão")

# DB2 — banco antigo (create_all) com dados
antigo = novoSqlite("antigo")
contagemAntiga = conferirBancoAntigo(antigo, "SQLite antigo")
passo("DB2 banco antigo é reconhecido e migrado sem perder linhas; data_referencia vira data")

# DB3 — idempotência
base.migrar(antigo)
assert versao(antigo) == CABECA and contagens(antigo) == contagemAntiga
vazio = novoSqlite("vazio")
base.migrar(vazio)
assert versao(vazio) == CABECA and contagens(vazio)["usuarios"] == 1
passo("DB3 rodar a migração de novo não falha nem duplica dados")

# Caso-limite — data fora do formato no banco antigo
invalido = novoSqlite("invalido")
criarBancoAntigo(invalido, dataReferencia="02/10/2026")
try:
    base.migrar(invalido)
except RuntimeError as erro:
    mensagem = str(erro)
    assert "data_referencia" in mensagem and "AAAA-MM-DD" in mensagem and "02/10/2026" in mensagem, mensagem
else:
    raise AssertionError("migração com data fora do formato deveria falhar")
with invalido.connect() as conexao:
    valor = conexao.execute(text("SELECT data_referencia FROM recomendacoes WHERE id = 1")).scalar()
assert str(valor) == "02/10/2026", valor
assert versao(invalido) != CABECA
passo("DB limite: data fora do formato faz a migração falhar com mensagem clara, sem gravar data errada")

# Banco do app (DATABASE_URL) para DB4 e DB5
base.criarTabelas()
assert versao(base.engine) == CABECA, "criarTabelas() deve aplicar as migrações"

from src.models.base import Session
from src.models.entities.ItensB3Entity import ItensB3Entity
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity
from src.models.entities.StockEntity import StockEntity
from src.models.services.RecomendacoesService import RecomendacoesService
from src.models.services.YfinanceService import YfinanceService
from src.models.services.AnaliseService import AnaliseService

# DB4 — últimas recomendações em uma única consulta
with Session() as session:
    for codigo in ("AAAA3", "BBBB3", "CCCC3", "DDDD3"):
        session.add(ItensB3Entity(item=codigo, nome=f"Empresa {codigo}", setor="Energia"))
    for codigo, dia, rec in (("AAAA3", 1, "VENDA"), ("AAAA3", 3, "COMPRA"), ("AAAA3", 2, "MANTER"),
                             ("BBBB3", 5, "MANTER"), ("BBBB3", 4, "COMPRA"), ("CCCC3", 1, "VENDA")):
        session.add(RecomendacoesEntity(item=codigo, data_referencia=f"2026-10-0{dia}", recomendacao=rec,
                                        gerado_em=datetime(2026, 10, dia, 18)))
    session.commit()

consultas = []


def contar(conn, cursor, statement, parameters, context, executemany):
    if statement.lstrip().upper().startswith(("SELECT", "WITH")):
        consultas.append(statement)


event.listen(base.engine, "before_cursor_execute", contar)
ultimas = RecomendacoesService().buscarUltimasPorItens(["AAAA3", "BBBB3", "CCCC3", "DDDD3"])
event.remove(base.engine, "before_cursor_execute", contar)
assert len(consultas) == 1, f"{len(consultas)} consultas: {consultas}"
assert set(ultimas) == {"AAAA3", "BBBB3", "CCCC3"}, ultimas.keys()
assert ultimas["AAAA3"]["recomendacao"] == "COMPRA" and ultimas["AAAA3"]["dataReferencia"] == "2026-10-03"
assert ultimas["BBBB3"]["recomendacao"] == "MANTER" and ultimas["CCCC3"]["recomendacao"] == "VENDA"
passo("DB4 buscarUltimasPorItens com 4 ativos: 1 consulta SQL e a mais recente de cada um")

# DB5 — cache por ativo + data com a data em DATE


def historicoFake(self, item, periodo="1y", intervalo="1d"):
    rng = np.random.default_rng(7)
    n = {"3mo": 90, "6mo": 180, "1y": 320, "2y": 600}[periodo]
    datas = pd.bdate_range(end="2026-10-02", periods=n, tz="America/Sao_Paulo")
    t = np.arange(n)
    preco = 30 + 0.02 * t + 4 * np.sin(t / 9) + rng.normal(0, 0.35, n)
    return pd.DataFrame({"Open": preco, "High": preco, "Low": preco, "Close": preco, "Volume": 1000}, index=datas)


YfinanceService.buscarHistorico = historicoFake
YfinanceService.buscarHistoricoIndice = lambda self, simbolo="^BVSP", periodo="1y": None  # comparacao-ibovespa.md
YfinanceService.buscarInfo = lambda self, item: StockEntity(item=item, nome="Petrobras", setor="Energia",
                                                           segmento="Petroleo", descricao="Oil and gas company.")
YfinanceService.buscarInfoAtivo = lambda self, item: {"item": item, "nome": "Petrobras", "setor": "Energia"}
chamadasIA = []


class FakeClient:
    def __init__(self, api_key=None, **kw):
        pass

    class messages:
        @staticmethod
        def create(**kw):
            chamadasIA.append(kw)
            from tests.respostas_ia import respostaJson
            texto = respostaJson()
            return type("M", (), {"content": [type("B", (), {"text": texto})()]})()


anthropic.Anthropic = FakeClient
servico = AnaliseService()
primeira = servico.analisar("PETR4", "1y")
segunda = servico.analisar("PETR4", "1y")
assert not primeira["doCache"] and segunda["doCache"] and len(chamadasIA) == 1
assert segunda["recomendacao"]["id"] == primeira["recomendacao"]["id"]
assert segunda["recomendacao"]["dataReferencia"] == "2026-10-02", segunda["recomendacao"]["dataReferencia"]
with Session() as session:
    gravada = session.get(RecomendacoesEntity, primeira["recomendacao"]["id"])
    assert gravada.data_referencia == date(2026, 10, 2), repr(gravada.data_referencia)
passo("DB5 cache por ativo + data funciona com data_referencia gravada como DATE")

# DB6 — PostgreSQL


def urlPostgres(banco):
    from config.settings import DB_CONFIG
    return (f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{banco}")


try:
    admin = create_engine(urlPostgres("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conexao:
        conexao.execute(text("SELECT 1"))
except Exception as erro:
    print(f"PULADO DB6: PostgreSQL indisponível ({erro.__class__.__name__}); rode no container do app")
else:
    for sufixo, conferir in (("vazio", conferirBancoNovo), ("antigo", conferirBancoAntigo)):
        nome = f"invest_ia_teste_migracao_{sufixo}_{os.getpid()}"
        with admin.connect() as conexao:
            conexao.execute(text(f"DROP DATABASE IF EXISTS {nome}"))
            conexao.execute(text(f"CREATE DATABASE {nome}"))
        engine = create_engine(urlPostgres(nome))
        try:
            conferir(engine, f"PostgreSQL {sufixo}")
            base.migrar(engine)
            assert versao(engine) == CABECA
        finally:
            engine.dispose()
            with admin.connect() as conexao:
                conexao.execute(text(f"DROP DATABASE IF EXISTS {nome}"))
    passo("DB6 migrações em PostgreSQL: banco vazio, banco antigo com dados e reexecução")

print(f"\n{len(ok)} critérios de persistência passaram")
