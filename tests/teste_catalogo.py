"""Spec: .agents/docs/specs/catalogo-ativos.md (CA1-CA9, CA13).

SQLite temporário; Yahoo e rede substituídos por dublês que falham se chamados.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
PASTA = Path(tempfile.mkdtemp())
try:
    import pandas_ta
except ImportError:
    from tests import pandas_ta_simulado
    sys.modules["pandas_ta"] = pandas_ta_simulado
os.environ["DATABASE_URL"] = f"sqlite:///{PASTA}/catalogo.db"

import httpx
import src.models.base as base
from src.models.base import Session
from src.models.entities.ItensB3Entity import ItensB3Entity
from src.models.services.YfinanceService import YfinanceService
from src.models.services.ItensB3Service import ItensB3Service

base.criarTabelas()

CATALOGO_REAL = RAIZ / "src" / "data" / "ativos_b3.json"
ok = []


def passo(nome):
    ok.append(nome)
    print("OK ", nome)


class RedeProibida(AssertionError):
    pass


def proibido(*a, **k):
    raise RedeProibida("acesso à rede/Yahoo durante operação que deveria ser offline")


originais = {
    nome: getattr(YfinanceService, nome)
    for nome in ("buscarHistorico", "buscarInfo", "buscarInfoAtivo", "buscarPrecoAtual")
    if hasattr(YfinanceService, nome)
}
originalSend = httpx.Client.send


def bloquearRede():
    for nome in originais:
        setattr(YfinanceService, nome, proibido)
    httpx.Client.send = proibido


def liberarRede():
    for nome, funcao in originais.items():
        setattr(YfinanceService, nome, funcao)
    httpx.Client.send = originalSend


def gravarJson(nome, conteudo):
    caminho = PASTA / nome
    caminho.write_text(conteudo if isinstance(conteudo, str) else json.dumps(conteudo, ensure_ascii=False),
                       encoding="utf-8")
    return caminho


def linhas():
    with Session() as s:
        return {i.item: (i.nome, i.setor, bool(i.ativo)) for i in s.query(ItensB3Entity).all()}


# CA6 — JSON versionado
assert CATALOGO_REAL.exists(), f"{CATALOGO_REAL} não existe"
catalogo = json.loads(CATALOGO_REAL.read_text(encoding="utf-8"))
codigos = [a["item"] for a in catalogo]
assert len(catalogo) >= 300, len(catalogo)
assert len(codigos) == len(set(codigos)), "códigos repetidos"
assert codigos == sorted(codigos), "JSON fora de ordem"
servico = ItensB3Service()
for ativo in catalogo:
    assert set(ativo) == {"item", "nome", "setor"}, ativo
    assert ativo["nome"] and ativo["setor"], ativo
    servico.validarFormato(ativo["item"])
    assert not ativo["item"].endswith(".SA")
assert {"PETR4", "VALE3", "ITUB4", "KLBN11"} <= set(codigos)
passo(f"CA6 JSON com {len(catalogo)} ações, ordenado, sem repetidos, códigos válidos")

# CA1, CA4 — seed em banco vazio, offline
pequeno = [
    {"item": "PETR4", "nome": "PETROBRAS PN", "setor": "Energia"},
    {"item": "VALE3", "nome": "VALE ON", "setor": "Materiais Básicos"},
    {"item": "WEGE3", "nome": "WEG ON", "setor": "Industrial"},
]
caminhoPequeno = gravarJson("pequeno.json", pequeno)
bloquearRede()
inseridos = ItensB3Service().semearCatalogo(caminhoPequeno)
assert inseridos == 3, inseridos
assert linhas() == {
    "PETR4": ("PETROBRAS PN", "Energia", True),
    "VALE3": ("VALE ON", "Materiais Básicos", True),
    "WEGE3": ("WEG ON", "Industrial", True),
}, linhas()
passo("CA1 seed grava item, nome, setor e ativo=TRUE")
passo("CA4 seed não chama o Yahoo nem faz requisição HTTP")

# CA2 — idempotente
assert ItensB3Service().semearCatalogo(caminhoPequeno) == 0
with Session() as s:
    assert s.query(ItensB3Entity).count() == 3
passo("CA2 seed duas vezes não duplica nem falha")

# CA3 — preserva existentes
with Session() as s:
    petr = s.query(ItensB3Entity).filter_by(item="PETR4").first()
    petr.nome = "Petroleo Brasileiro S.A. - Petrobras"
    s.query(ItensB3Entity).filter_by(item="VALE3").first().ativo = False
    s.commit()
pequeno.append({"item": "ITUB4", "nome": "ITAUUNIBANCO PN", "setor": "Serviços Financeiros"})
caminhoPequeno = gravarJson("pequeno.json", pequeno)
assert ItensB3Service().semearCatalogo(caminhoPequeno) == 1
atual = linhas()
assert atual["PETR4"][0] == "Petroleo Brasileiro S.A. - Petrobras"
assert atual["VALE3"][2] is False and "ITUB4" in atual
passo("CA3 ativo existente mantém nome e ativo=FALSE; só o novo é inserido")

# CA5 — listagem ordenada só com ativos
lista = ItensB3Service().listarAtivos()
assert [a["item"] for a in lista] == ["ITUB4", "PETR4", "WEGE3"], lista
assert lista[1]["nome"] == "Petroleo Brasileiro S.A. - Petrobras" and lista[1]["setor"] == "Energia"
passo("CA5 listarAtivos ordena por código e omite ativo=FALSE")

# CA9 — JSON ausente ou corrompido não derruba
assert ItensB3Service().semearCatalogo(PASTA / "nao_existe.json") == 0
assert ItensB3Service().semearCatalogo(gravarJson("quebrado.json", "{isto não é json")) == 0
assert ItensB3Service().semearCatalogo(gravarJson("formato.json", {"stocks": []})) == 0
passo("CA9 JSON ausente/corrompido/formato errado: seed devolve 0 sem exceção")

# Seed com o JSON real do repositório (padrão sem argumento)
total = ItensB3Service().semearCatalogo()
with Session() as s:
    assert s.query(ItensB3Entity).count() >= len(catalogo)
passo(f"seed padrão lê src/data/ativos_b3.json ({total} novos)")
liberarRede()

# CA13 — SeedItensB3
from src.scripts import SeedItensB3

with Session() as s:
    s.query(ItensB3Entity).delete()
    s.commit()
bloquearRede()
SeedItensB3.main([])
assert len(linhas()) == len(catalogo)
liberarRede()
consultados = []
YfinanceService.buscarInfoAtivo = lambda self, item: (
    consultados.append(item) or {"item": item, "nome": "Nova Empresa", "setor": "Energia"})
SeedItensB3.main(["ABCD3"])
assert consultados == ["ABCD3"] and "ABCD3" in linhas()
liberarRede()
passo("CA13 SeedItensB3 sem argumentos é offline; com argumentos valida no Yahoo")

# CA7, CA8 — script de atualização a partir da brapi
from src.scripts import AtualizarCatalogoB3 as atualizador


def acao(i, tipo="stock", setor="Finance", nome=None):
    return {"stock": i, "name": nome or f"EMPRESA {i}", "close": 10.0, "sector": setor, "type": tipo}


def payloadBrapi(qtdAcoes=320):
    stocks = [acao("Q" + "".join(chr(65 + (n // 26 ** k) % 26) for k in range(3)) + "3")
              for n in range(qtdAcoes)]
    stocks += [
        acao("PETR4", setor="Energy Minerals", nome="PETROBRAS PN"),
        acao("KLBN11", setor="Process Industries", nome="KLABIN UNT"),
        acao("SEMS3", setor=None, nome="SEM SETOR"),
        acao("XPTO3", setor="Setor Desconhecido"),
        acao("MXRF11", tipo="fund"),
        acao("AAPL34", tipo="bdr"),
        acao("PETR4F", nome="FRACIONARIO"),
        acao("^BVSP", nome="IBOVESPA"),
        acao("PETR4", setor="Energy Minerals", nome="PETROBRAS PN"),
    ]
    return {"indexes": [{"stock": "^BVSP", "name": "IBOVESPA"}], "stocks": stocks}


def clienteSimulado(resposta):
    def handler(request):
        if isinstance(resposta, Exception):
            raise resposta
        return resposta
    return httpx.Client(transport=httpx.MockTransport(handler))


destino = PASTA / "ativos_b3.json"
codigo = atualizador.main([], cliente=clienteSimulado(httpx.Response(200, json=payloadBrapi())), caminho=destino)
assert codigo == 0, codigo
gerado = json.loads(destino.read_text(encoding="utf-8"))
porItem = {a["item"]: a for a in gerado}
assert "MXRF11" not in porItem and "AAPL34" not in porItem, "fundos/BDRs não entram"
assert "PETR4F" not in porItem and "^BVSP" not in porItem, "códigos fora do formato são descartados"
assert porItem["PETR4"] == {"item": "PETR4", "nome": "PETROBRAS PN", "setor": "Energia"}, porItem["PETR4"]
assert porItem["KLBN11"]["setor"] == "Materiais Básicos", porItem["KLBN11"]
assert porItem["SEMS3"]["setor"] == "Não disponível" and porItem["XPTO3"]["setor"] == "Não disponível"
assert [a["item"] for a in gerado] == sorted(porItem), "ordenado e sem repetidos"
assert atualizador.SETORES_BRAPI["Finance"] == "Serviços Financeiros"
passo("CA7 script grava só ações, traduz setor, descarta códigos inválidos, ordena e deduplica")

conteudoAnterior = destino.read_text(encoding="utf-8")
falhas = {
    "rede": httpx.ConnectError("sem rede"),
    "http 500": httpx.Response(500, text="erro"),
    "sem stocks": httpx.Response(200, json={"indexes": []}),
    "truncada": httpx.Response(200, json=payloadBrapi(qtdAcoes=10)),
    "json inválido": httpx.Response(200, text="<html>"),
}
for nome, resposta in falhas.items():
    codigo = atualizador.main([], cliente=clienteSimulado(resposta), caminho=destino)
    assert codigo != 0, f"{nome}: deveria sair com código != 0"
    assert destino.read_text(encoding="utf-8") == conteudoAnterior, f"{nome}: JSON foi sobrescrito"
passo("CA8 falha de rede/HTTP/payload/truncada: código != 0 e JSON anterior intacto")

print(f"\n{len(ok)} critérios do catálogo passaram")
