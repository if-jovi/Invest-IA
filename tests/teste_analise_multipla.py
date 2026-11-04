"""Spec: .agents/docs/specs/analise-multipla.md (AM1-AM6).

SQLite temporário; Yahoo e IA simulados.
"""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
PASTA = tempfile.mkdtemp()
try:
    import pandas_ta
except ImportError:
    from tests import pandas_ta_simulado
    sys.modules["pandas_ta"] = pandas_ta_simulado
os.environ["DATABASE_URL"] = f"sqlite:///{PASTA}/multipla.db"
os.environ["ANTHROPIC_API_KEY"] = "chave-de-teste"
os.environ["IA_PROVEDOR"] = "claude"

import numpy as np
import pandas as pd
import anthropic
import src.models.base as base

base.criarTabelas()

from src.models.entities.StockEntity import StockEntity
from src.models.services.YfinanceService import YfinanceService
from src.models.services.AnaliseService import AnaliseService
from src.controllers import AnaliseController as moduloController
from src.controllers.AnaliseController import AnaliseController


def historicoFake(self, item, periodo="1y", intervalo="1d"):
    if self.normalizarItem(item) == "ZZZZ9":
        raise ValueError("Nenhum dado encontrado para ZZZZ9.SA.")
    rng = np.random.default_rng(7)
    n = {"5d": 5, "1mo": 22, "3mo": 90, "6mo": 180, "1y": 320, "2y": 600}[periodo]
    datas = pd.bdate_range(end="2026-10-02", periods=n, tz="America/Sao_Paulo")
    t = np.arange(n)
    preco = 30 + 0.02 * t + 4 * np.sin(t / 9) + rng.normal(0, 0.35, n)
    return pd.DataFrame({"Open": preco, "High": preco + 0.4, "Low": preco - 0.4, "Close": preco,
                         "Volume": 1000}, index=datas)


YfinanceService.buscarHistorico = historicoFake
YfinanceService.buscarInfo = lambda self, item: StockEntity(
    item=self.normalizarItem(item), nome=f"Empresa {self.normalizarItem(item)} S.A.", setor="Energia",
    segmento="Petroleo", descricao="Oil and gas company.")
YfinanceService.buscarInfoAtivo = lambda self, item: (
    (_ for _ in ()).throw(ValueError(f"O ativo {self.normalizarItem(item)} não foi encontrado na B3."))
    if self.normalizarItem(item) == "ZZZZ9"
    else {"item": self.normalizarItem(item), "nome": f"Empresa {self.normalizarItem(item)} S.A.", "setor": "Energia"})

TEXTO = """RECOMENDAÇÃO: COMPRA

SOBRE A EMPRESA:
A empresa atua no setor de energia.

JUSTIFICATIVA:
O RSI esta neutro.

RISCOS:
- Volatilidade
"""
chamadasIA = []


class FakeMsg:
    def __init__(self, t):
        self.content = [type("B", (), {"text": t})()]


class FakeClient:
    def __init__(self, api_key=None, **kw):
        pass

    class messages:
        @staticmethod
        def create(**kw):
            chamadasIA.append(kw["messages"][0]["content"])
            return FakeMsg(TEXTO)


anthropic.Anthropic = FakeClient

ok = []


def passo(nome):
    ok.append(nome)
    print("OK ", nome)


def esperaErro(fn, trecho):
    try:
        fn()
    except ValueError as e:
        assert trecho in str(e), f"mensagem inesperada: {e}"
        return
    raise AssertionError(f"era esperado ValueError contendo '{trecho}'")


controller = AnaliseController()
assert moduloController.LIMITE_ATIVOS_ANALISE == 5

# AM1 — dois ativos, ordem de entrada
r = controller.analisarVarios(["VALE3", "PETR4"], "1y")
assert set(r) == {"resultados", "erros"}, r.keys()
assert [x["ativo"]["item"] for x in r["resultados"]] == ["VALE3", "PETR4"]
assert r["erros"] == []
for x in r["resultados"]:
    assert set(x) >= {"ativo", "indicadores", "recomendacao", "doCache"}
    assert x["recomendacao"]["recomendacao"] == "COMPRA"
passo("AM1 dois ativos analisados na ordem de entrada, sem erros")

# AM2 — normalização e repetidos
antes = len(chamadasIA)
r = controller.analisarVarios(["petr4", "PETR4.SA", " PETR4 "], "1y", forcar=True)
assert [x["ativo"]["item"] for x in r["resultados"]] == ["PETR4"]
assert len(chamadasIA) - antes == 1
passo("AM2 'petr4', 'PETR4.SA', ' PETR4 ' viram uma única análise")

# AM3 — validações
esperaErro(lambda: controller.analisarVarios([], "1y"), "Informe ao menos um ativo.")
esperaErro(lambda: controller.analisarVarios(["", "  "], "1y"), "Informe ao menos um ativo.")
esperaErro(lambda: controller.analisarVarios(["PETR4", "VALE3", "ITUB4", "BBDC4", "WEGE3", "ABEV3"], "1y"),
           "Selecione no máximo 5 ativos por análise.")
cincoComRepetido = ["PETR4", "VALE3", "ITUB4", "BBDC4", "WEGE3", "petr4"]
assert len(controller.analisarVarios(cincoComRepetido, "1y")["resultados"]) == 5
esperaErro(lambda: controller.analisarVarios(["PETR4"], "10y"), "Período inválido")
passo("AM3 vazio, 6 distintos e período inválido recusados; 5 + repetido aceito")

# AM4 — falha isolada por ativo
r = controller.analisarVarios(["PETR4", "ZZZZ9", "XX", "VALE3"], "1y")
assert [x["ativo"]["item"] for x in r["resultados"]] == ["PETR4", "VALE3"]
erros = {e["item"]: e["mensagem"] for e in r["erros"]}
assert list(erros) == ["ZZZZ9", "XX"], r["erros"]
assert "não foi encontrado" in erros["ZZZZ9"], erros
assert "Código inválido" in erros["XX"], erros
passo("AM4 ativos inválidos vão para 'erros' sem derrubar os válidos")

original = AnaliseService.analisar


def explode(self, item, periodo="1y", forcar=False):
    if item.strip().upper() == "BBAS3":
        raise KeyError("falha interna")
    return original(self, item, periodo, forcar)


AnaliseService.analisar = explode
r = controller.analisarVarios(["BBAS3", "PETR4"], "1y")
assert [x["ativo"]["item"] for x in r["resultados"]] == ["PETR4"]
assert r["erros"][0]["item"] == "BBAS3"
assert r["erros"][0]["mensagem"].startswith("Não foi possível concluir a análise:"), r["erros"]
AnaliseService.analisar = original
passo("AM4 exceção inesperada vira 'Não foi possível concluir a análise: ...'")

# AM5 — no máximo 2 em paralelo (e de fato paralelo)
ativos = {"agora": 0, "pico": 0}
trava = threading.Lock()


def lento(self, item, periodo="1y", forcar=False):
    with trava:
        ativos["agora"] += 1
        ativos["pico"] = max(ativos["pico"], ativos["agora"])
    time.sleep(0.3)
    with trava:
        ativos["agora"] -= 1
    return {"ativo": {"item": item.strip().upper()}, "indicadores": None, "recomendacao": None, "doCache": True}


AnaliseService.analisar = lento
t0 = time.time()
r = controller.analisarVarios(["PETR4", "VALE3", "ITUB4", "BBDC4", "WEGE3"], "1y")
duracao = time.time() - t0
AnaliseService.analisar = original
assert ativos["pico"] == 2, f"pico de concorrência {ativos['pico']}"
assert [x["ativo"]["item"] for x in r["resultados"]] == ["PETR4", "VALE3", "ITUB4", "BBDC4", "WEGE3"]
assert duracao < 1.3, duracao
passo(f"AM5 pico de 2 análises simultâneas; 5 ativos x 0,3s em {duracao:.1f}s, ordem preservada")

# AM6 — cache por ativo + data
controller.analisarVarios(["ITUB4"], "1y")
antes = len(chamadasIA)
r = controller.analisarVarios(["ITUB4", "B3SA3"], "1y")
assert len(chamadasIA) - antes == 1, "só o ativo sem cache chama a IA"
assert [x["doCache"] for x in r["resultados"]] == [True, False]
antes = len(chamadasIA)
controller.analisarVarios(["ITUB4", "B3SA3"], "1y", forcar=True)
assert len(chamadasIA) - antes == 2
passo("AM6 cache por ativo + data; 'forcar' gera de novo para todos")

print(f"\n{len(ok)} critérios da análise múltipla passaram")
