"""Spec: .agents/docs/specs/comparacao-ibovespa.md (IB1-IB3, IB5, IB6).

IB4 (cards na tela) está em teste_interface.py. Yahoo e IA simulados.
"""
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import dotenv
dotenv.load_dotenv = lambda *a, **k: False
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/ibov.db"
os.environ["ANTHROPIC_API_KEY"] = "chave-de-teste"
os.environ["IA_PROVEDOR"] = "claude"

import numpy as np
import pandas as pd
import anthropic
import src.models.base as base

base.criarTabelas()

from tests.respostas_ia import respostaJson
from src.models.entities.StockEntity import StockEntity, IndicatorsEntity
from src.models.services import YfinanceService as moduloYf
from src.models.services.YfinanceService import YfinanceService
from src.models.services.IndicatorsService import IndicatorsService
from src.models.services.ClaudeService import ClaudeService
from src.models.services.GeminiService import GeminiService
from src.models.services.OpenRouterService import OpenRouterService
from src.models.services.AnaliseService import AnaliseService
from src.models.services.BacktestService import BacktestService

ok = []


def passo(nome):
    ok.append(nome)
    print("OK ", nome)


def perto(a, b, tol=0.01):
    return a is not None and abs(a - b) <= tol


def fechamentos(valores, inicio):
    return pd.DataFrame({"Close": [float(v) for v in valores]}, index=pd.bdate_range(inicio, periods=len(valores)))


servico = IndicatorsService()
ORIGINAL_INDICE = YfinanceService.__dict__.get("buscarHistoricoIndice")

# IB1 — retorno do índice e diferença em p.p.
ativo = fechamentos([10, 10.5, 11, 11.3], "2026-09-01")
indice = fechamentos([100000, 103000, 104000, 108000], "2026-09-01")
comparacao = servico.compararIndice(ativo, indice)
assert set(comparacao) == {"retornoPct", "diferencaPct"}, comparacao
assert perto(comparacao["retornoPct"], 8.0) and perto(comparacao["diferencaPct"], 5.0), comparacao
passo("IB1 ativo +13% e Ibovespa +8% -> diferença de +5,00 p.p.")

# IB2 — alinhamento às datas do período do ativo
indiceLargo = fechamentos([1, 1, 100000, 103000, 104000, 108000, 999999], "2026-08-28")
assert indiceLargo.index[2] == ativo.index[0] and indiceLargo.index[5] == ativo.index[-1]
assert servico.compararIndice(ativo, indiceLargo) == comparacao
semDiaInicial = indice.drop(indice.index[0])
semDiaInicial = pd.concat([fechamentos([95000], "2026-08-31"), semDiaInicial])
c2 = servico.compararIndice(ativo, semDiaInicial)
assert perto(c2["retornoPct"], (108000 / 103000 - 1) * 100), c2
passo("IB2 Ibovespa recortado ao período do ativo (1º fechamento >= início, último <= fim)")

# IB3 — prompt nos três provedores
stock = StockEntity(item="PETR4", nome="Petrobras", setor="Energia", segmento="Petroleo", descricao="Oil and gas")


def indCom(ibovespa):
    return IndicatorsEntity(
        item="PETR4", data_referencia="2026-10-02", preco_atual=40.0, rsi=55.0, periodo="3mo",
        resumo_periodo={"retornoPct": 8.4, "maxima": 41.2, "minima": 35.0, "distanciaMaximaPct": -3.1,
                        "distanciaMinimaPct": 14.0, "volatilidadeAnualPct": 27.5, "drawdownMaximoPct": -9.8},
        ibovespa=ibovespa)


prompt = ClaudeService().montarPrompt(stock, indCom({"retornoPct": 5.1, "diferencaPct": 3.3}))
assert "- Ibovespa no mesmo período: +5,10% (a ação ficou 3,30 p.p. acima do índice)" in prompt, prompt
assert "Compare o desempenho da ação com o do Ibovespa" in prompt
prompt = ClaudeService().montarPrompt(stock, indCom({"retornoPct": -2.0, "diferencaPct": -1.25}))
assert "- Ibovespa no mesmo período: -2,00% (a ação ficou 1,25 p.p. abaixo do índice)" in prompt, prompt
for provedor in (GeminiService, OpenRouterService):
    assert "montarPrompt" not in provedor.__dict__, f"{provedor.__name__} deve herdar o prompt"
passo("IB3 linha do Ibovespa (acima/abaixo) e regra de comparação no prompt; Gemini e OpenRouter herdam o prompt")


def historicoFake(self, item, periodo="1y", intervalo="1d"):
    datas = pd.bdate_range(end="2026-10-02", periods=360)
    preco = 30 + 4 * np.sin(np.arange(360) / 9)
    return pd.DataFrame({"Open": preco, "High": preco, "Low": preco, "Close": preco, "Volume": 1000}, index=datas)


chamadasIA = []


class FakeClaude:
    def __init__(self, api_key=None, **kw):
        pass

    class messages:
        @staticmethod
        def create(**kw):
            chamadasIA.append(kw["messages"][0]["content"])
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=respostaJson())], stop_reason="end_turn")


anthropic.Anthropic = FakeClaude
YfinanceService.buscarHistorico = historicoFake
YfinanceService.buscarInfo = lambda self, item: stock
YfinanceService.buscarInfoAtivo = lambda self, item: {"item": item, "nome": "Petrobras", "setor": "Energia"}

# IB3 (fim a fim) + análise com Ibovespa disponível
indiceAno = pd.DataFrame({"Close": np.linspace(120000.0, 132000.0, 360)},
                         index=pd.bdate_range(end="2026-10-02", periods=360))
YfinanceService.buscarHistoricoIndice = lambda self, simbolo="^BVSP", periodo="1y": indiceAno
r = AnaliseService().analisar("PETR4", "1y", forcar=True)
assert r["indicadores"].ibovespa is not None and r["indicadores"].ibovespa["retornoPct"] > 0, r["indicadores"].ibovespa
assert "Ibovespa no mesmo período" in chamadasIA[-1]
bt = BacktestService().executar("PETR4", "1y")
assert bt["metricas"]["retornoIbovespa"] is not None and bt["metricas"]["retornoIbovespa"] > 0
passo("IB3 análise fim a fim envia o Ibovespa à IA; backtesting traz o retorno do Ibovespa")


# IB5 — sem Ibovespa, tudo funciona
def falha(self, simbolo="^BVSP", periodo="1y"):
    raise RuntimeError("Yahoo fora do ar")


YfinanceService.buscarHistoricoIndice = falha
r = AnaliseService().analisar("PETR4", "1y", forcar=True)
assert r["indicadores"].ibovespa is None and r["recomendacao"]["recomendacao"] == "COMPRA"
assert "Ibovespa" not in chamadasIA[-1].split("Regras:")[0], "sem dados, a linha do Ibovespa é omitida"
bt = BacktestService().executar("PETR4", "1y")
assert bt["metricas"]["retornoIbovespa"] is None and bt["operacoes"] is not None
passo("IB5 Ibovespa indisponível: análise e backtesting seguem, sem a linha no prompt e com o card vazio")

# IB6 — cache: uma consulta ao Yahoo por período
assert ORIGINAL_INDICE is not None, "YfinanceService.buscarHistoricoIndice não existe"
YfinanceService.buscarHistoricoIndice = ORIGINAL_INDICE  # volta ao método real
consultas = []


class FakeTicker:
    def __init__(self, simbolo, *a, **k):
        self.simbolo = simbolo

    def history(self, **kwargs):
        consultas.append((self.simbolo, kwargs))
        return indiceAno


moduloYf.yf.Ticker = FakeTicker
YfinanceService.limparCacheIndice()
for _ in range(5):
    YfinanceService().buscarHistoricoIndice("^BVSP", "1y")
assert [s for s, _ in consultas] == ["^BVSP"], consultas
YfinanceService().buscarHistoricoIndice("^BVSP", "3mo")
assert len(consultas) == 2
passo("IB6 cinco análises no mesmo período consultam o Ibovespa uma vez (cache); outro período consulta de novo")

print(f"\n{len(ok)} critérios da comparação com o Ibovespa passaram")
