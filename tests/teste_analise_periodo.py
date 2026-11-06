"""Spec: .agents/docs/specs/analise-periodo.md (PE1-PE9, PE11 e casos-limite).

Revisado para historico-aquecimento.md: os fakes trazem ~100 pregões de
aquecimento e o resumo considera só o período.

PE10 (tela) está em teste_interface.py. PE7 aqui cobre o modelo (coluna e
índice); a migração 0004 em SQLite e PostgreSQL é exercida por
teste_persistencia.py (DB1, DB2 e DB6 migram até a última revisão).

SQLite temporário; Yahoo e os três provedores de IA simulados.
"""
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

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
os.environ["DATABASE_URL"] = f"sqlite:///{PASTA}/periodo.db"
os.environ["ANTHROPIC_API_KEY"] = "chave-de-teste"
os.environ["GEMINI_API_KEY"] = "chave-de-teste"
os.environ["OPENROUTER_API_KEY"] = "chave-de-teste"
os.environ["IA_PROVEDOR"] = "claude"
for variavel in ("OPENROUTER_MODEL", "OPENROUTER_BASE_URL", "GEMINI_MODEL"):
    os.environ.pop(variavel, None)

import numpy as np
import pandas as pd
import anthropic
import httpx
import src.models.base as base

base.criarTabelas()

from src.models import Parametros
from src.models.base import Session
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity
from src.models.entities.StockEntity import StockEntity, IndicatorsEntity
from src.models.services.YfinanceService import YfinanceService
from src.models.services.IndicatorsService import IndicatorsService
from src.models.services.AnaliseService import AnaliseService
from src.models.services.ItensB3Service import ItensB3Service
from src.models.services.ClaudeService import ClaudeService
from src.models.services import GeminiService as moduloGemini
from src.models.services import OpenRouterService as moduloOpenRouter
from src.controllers.AnaliseController import AnaliseController
from src.public.views import AnaliseView, BacktestView

# período + ~100 pregões de aquecimento (historico-aquecimento.md)
TAMANHOS = {"3mo": 170, "6mo": 230, "1y": 360, "2y": 610}


def historicoFake(item, periodo="1y"):
    rng = np.random.default_rng(sum(ord(c) for c in item))
    n = TAMANHOS[periodo]
    datas = pd.bdate_range(end="2026-10-02", periods=n, tz="America/Sao_Paulo")
    t = np.arange(n)
    preco = 30 + 0.02 * t + 4 * np.sin(t / 9) + rng.normal(0, 0.35, n)
    return pd.DataFrame({"Open": preco, "High": preco + 0.4, "Low": preco - 0.4, "Close": preco,
                         "Volume": 1000}, index=datas)


YfinanceService.buscarHistorico = (
    lambda self, item, periodo="1y", intervalo="1d": historicoFake(self.normalizarItem(item), periodo))
YfinanceService.buscarHistoricoIndice = lambda self, simbolo="^BVSP", periodo="1y": None
YfinanceService.buscarInfo = lambda self, item: StockEntity(
    item=self.normalizarItem(item), nome=f"Empresa {self.normalizarItem(item)} S.A.", setor="Energia",
    segmento="Petroleo", descricao="Oil and gas company.")
YfinanceService.buscarInfoAtivo = lambda self, item: {
    "item": self.normalizarItem(item), "nome": f"Empresa {self.normalizarItem(item)} S.A.", "setor": "Energia"}

from tests.respostas_ia import respostaJson
TEXTO = respostaJson("COMPRA", "A empresa atua no setor de energia.", "O RSI esta neutro.", ["Volatilidade"])
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


def perto(a, b, tol=0.01):
    return a is not None and abs(a - b) <= tol


CHAVES = {"retornoPct", "maxima", "minima", "distanciaMaximaPct", "distanciaMinimaPct",
          "volatilidadeAnualPct", "drawdownMaximoPct"}
indicadores = IndicatorsService()


def serie(fechamentos, inicio="2026-01-05"):
    datas = pd.bdate_range(inicio, periods=len(fechamentos))
    return pd.DataFrame({"Close": [float(f) for f in fechamentos]}, index=datas)


# PE1 — valores calculados à mão
# Fechamentos 10, 12, 9, 11, 15, 12:
#   retorno = 12/10 - 1 = +20,00% | máxima 15, mínima 9
#   distância da máxima = 12/15 - 1 = -20,00% | da mínima = 12/9 - 1 = +33,33%
#   retornos diários: +20%, -25%, +22,22%, +36,36%, -20%
#   desvio amostral = 0,274570 -> x raiz(252) = 435,87%
#   máximo acumulado 10,12,12,12,15,15 -> quedas 0, 0, -25%, -8,33%, 0, -20% -> drawdown -25,00%
resumo = indicadores.resumirPeriodo(serie([10, 12, 9, 11, 15, 12]))
assert set(resumo) == CHAVES, set(resumo) ^ CHAVES
esperado = {"retornoPct": 20.0, "maxima": 15.0, "minima": 9.0, "distanciaMaximaPct": -20.0,
            "distanciaMinimaPct": 33.33, "volatilidadeAnualPct": 435.87, "drawdownMaximoPct": -25.0}
for chave, valor in esperado.items():
    assert perto(resumo[chave], valor), (chave, resumo[chave], valor)
assert all(v == round(v, 2) for v in resumo.values()), resumo
passo("PE1 resumo de série conhecida bate com o cálculo à mão (2 casas)")

# Casos-limite do resumo
constante = indicadores.resumirPeriodo(serie([20] * 10))
for chave in ("retornoPct", "distanciaMaximaPct", "distanciaMinimaPct", "volatilidadeAnualPct",
              "drawdownMaximoPct"):
    assert constante[chave] == 0.0, (chave, constante)
assert constante["maxima"] == constante["minima"] == 20.0
passo("PE limite: série constante -> retorno, volatilidade, drawdown e distâncias 0.0")

subindo = indicadores.resumirPeriodo(serie([10, 11, 12, 13, 14]))
assert subindo["drawdownMaximoPct"] == 0.0 and subindo["distanciaMaximaPct"] == 0.0, subindo
assert perto(subindo["retornoPct"], 40.0) and perto(subindo["distanciaMinimaPct"], 40.0), subindo
passo("PE limite: série só subindo -> drawdown 0.0 e distância da máxima 0.0")

comBuraco = serie([10, 12, 9, 11, 15, 12])
comBuraco.iloc[2, 0] = math.nan
semBuraco = serie([10, 12, 11, 15, 12])
assert indicadores.resumirPeriodo(comBuraco) == indicadores.resumirPeriodo(semBuraco)
passo("PE limite: fechamento NaN é ignorado no resumo")

# PE2 — período inteiro, inclusive os primeiros pregões (que o dropna descartava antes do aquecimento)
datas = pd.bdate_range(end="2026-10-02", periods=170, tz="America/Sao_Paulo")
inicioPeriodo = datas[datas >= datas[-1] - pd.DateOffset(months=3)][0]
nPeriodo = int((datas >= inicioPeriodo).sum())
fechamentos = np.r_[np.full(170 - nPeriodo, 45.0), np.full(10, 50.0), np.linspace(40.0, 30.0, nPeriodo - 10)]
completo = pd.DataFrame({"Open": fechamentos, "High": fechamentos, "Low": fechamentos, "Close": fechamentos,
                         "Volume": 1000}, index=datas)
ind = indicadores.calcular("PETR4", completo, "3mo")
assert ind.historico.index[0] == inicioPeriodo, "o período começa no 1º pregão, sem perder dias"
assert ind.periodo == "3mo", ind.periodo
assert set(ind.resumo_periodo) == CHAVES
assert ind.resumo_periodo["maxima"] == 50.0, ind.resumo_periodo
assert perto(ind.resumo_periodo["retornoPct"], -40.0), ind.resumo_periodo
assert perto(ind.resumo_periodo["distanciaMaximaPct"], -40.0), ind.resumo_periodo
passo("PE2 resumo usa o período inteiro: máxima nos 10 primeiros pregões e retorno desde o 1º fechamento")

# PE3 — prompt: rótulos num único lugar, horizonte e valores em pt-BR
assert Parametros.ROTULOS_PERIODO == {"3mo": "3 meses", "6mo": "6 meses", "1y": "1 ano", "2y": "2 anos"}
assert AnaliseView.ROTULOS_PERIODO is Parametros.ROTULOS_PERIODO
assert BacktestView.ROTULOS_PERIODO is Parametros.ROTULOS_PERIODO
assert AnaliseView.rotuloPeriodo("3mo") == "3 meses" and AnaliseView.rotuloPeriodo(None) == "—"

stock = StockEntity(item="PETR4", nome="Petrobras", setor="Energia", segmento="Petroleo", descricao="Oil and gas")


def indComResumo(periodo, resumoPeriodo):
    return IndicatorsEntity(
        item="PETR4", data_referencia="2026-10-02", preco_atual=40.0, rsi=55.0, sinal_rsi="neutro",
        macd=0.12, macd_signal=0.10, macd_cruzamento="alta", sma_short=39.0, sma_long=37.5,
        tendencia_sma="alta", periodo=periodo, resumo_periodo=resumoPeriodo)


resumoExemplo = {"retornoPct": 8.4, "maxima": 41.2, "minima": 35.0, "distanciaMaximaPct": -3.1,
                 "distanciaMinimaPct": 14.0, "volatilidadeAnualPct": 27.5, "drawdownMaximoPct": -9.8}
TRECHOS = ["horizonte: 3 meses", "Retorno no período: +8,40%", "Máxima: R$ 41,20", "3,10% abaixo",
           "Mínima: R$ 35,00", "14,00% acima", "Volatilidade anualizada: 27,50%",
           "(drawdown máximo): -9,80%", "Considere o horizonte informado"]
prompt = ClaudeService().montarPrompt(stock, indComResumo("3mo", resumoExemplo))
for trecho in TRECHOS:
    assert trecho in prompt, f"'{trecho}' ausente do prompt:\n{prompt}"

negativo = dict(resumoExemplo, retornoPct=-5.0, maxima=1234.5)
prompt = ClaudeService().montarPrompt(stock, indComResumo("2y", negativo))
assert "horizonte: 2 anos" in prompt and "Retorno no período: -5,00%" in prompt, prompt
assert "Máxima: R$ 1.234,50" in prompt, prompt
for codigo, rotulo in Parametros.ROTULOS_PERIODO.items():
    assert f"horizonte: {rotulo}" in ClaudeService().montarPrompt(stock, indComResumo(codigo, resumoExemplo))
passo("PE3 prompt com horizonte, os seis valores do resumo em pt-BR e a regra do horizonte")

# PE3 — o mesmo conteúdo chega na requisição de cada provedor
indExemplo = indComResumo("3mo", resumoExemplo)

chamadasIA.clear()
ClaudeService().gerarRecomendacao(stock, indExemplo)
enviadoClaude = chamadasIA[-1]

chamadasGemini = []


class FakeModels:
    def generate_content(self, model, contents, config):
        chamadasGemini.append(contents)
        return SimpleNamespace(text=TEXTO, prompt_feedback=SimpleNamespace(block_reason=None))


class FakeClienteGemini:
    models = FakeModels()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


moduloGemini.GeminiService.cliente = lambda self: FakeClienteGemini()
moduloGemini.GeminiService().gerarRecomendacao(stock, indExemplo)
enviadoGemini = str(chamadasGemini[-1])

requisicoesOpenRouter = []


def handlerOpenRouter(request):
    requisicoesOpenRouter.append(json.loads(request.content))
    return httpx.Response(200, json={"id": "gen-1", "model": moduloOpenRouter.MODELO_PADRAO, "choices": [
        {"index": 0, "message": {"role": "assistant", "content": TEXTO}}]})


moduloOpenRouter.OpenRouterService.cliente = (
    lambda self: httpx.Client(transport=httpx.MockTransport(handlerOpenRouter)))
moduloOpenRouter.OpenRouterService().gerarRecomendacao(stock, indExemplo)
enviadoOpenRouter = requisicoesOpenRouter[-1]["messages"][0]["content"]

for nome, enviado in (("Claude", enviadoClaude), ("Gemini", enviadoGemini), ("OpenRouter", enviadoOpenRouter)):
    for trecho in TRECHOS:
        assert trecho in enviado, f"{nome}: '{trecho}' ausente da requisição"
passo("PE3 Claude, Gemini e OpenRouter enviam o horizonte e o resumo na requisição")

# PE4 — cache por ativo + data + período
servico = AnaliseService()
chamadasIA.clear()
r1y = servico.analisar("PETR4", "1y")
r3m = servico.analisar("PETR4", "3mo")
assert r1y["indicadores"].data_referencia == r3m["indicadores"].data_referencia, "mesma data de referência"
assert not r1y["doCache"] and not r3m["doCache"]
assert len(chamadasIA) == 2, "período diferente chama a IA de novo"
assert "horizonte: 1 ano" in chamadasIA[0] and "horizonte: 3 meses" in chamadasIA[1]
r3mDeNovo = servico.analisar("PETR4", "3mo")
r1yDeNovo = servico.analisar("PETR4", "1y")
assert r3mDeNovo["doCache"] and r1yDeNovo["doCache"]
assert len(chamadasIA) == 2, "mesmo período reaproveita sem chamar a IA"
assert r3mDeNovo["recomendacao"]["id"] == r3m["recomendacao"]["id"]
assert r1yDeNovo["recomendacao"]["id"] == r1y["recomendacao"]["id"]
passo("PE4 mesmo ativo e data: período diferente chama a IA; mesmo período usa o cache")

# PE5 — período gravado
with Session() as session:
    periodos = sorted(r.periodo for r in session.query(RecomendacoesEntity).filter_by(item="PETR4"))
assert periodos == ["1y", "3mo"], periodos
assert r3m["recomendacao"]["periodo"] == "3mo" and r3mDeNovo["recomendacao"]["periodo"] == "3mo"
assert r1y["recomendacao"]["periodo"] == "1y"
passo("PE5 recomendações gravadas e devolvidas com o código do período")

# PE6 — recomendação antiga (periodo nulo) não é reaproveitada, mas segue no histórico
ItensB3Service().obterOuCadastrar("VALE3")
dataVale = str(historicoFake("VALE3", "1y").index[-1].date())
with Session() as session:
    session.add(RecomendacoesEntity(item="VALE3", data_referencia=dataVale, recomendacao="MANTER",
                                    justificativa="Antiga", riscos="- Antigo", resposta_completa="antiga"))
    session.commit()
antes = len(chamadasIA)
rVale = servico.analisar("VALE3", "1y")
assert rVale["indicadores"].data_referencia == dataVale
assert not rVale["doCache"] and len(chamadasIA) == antes + 1, "registro sem período não pode ser cache"
historico = servico.buscarHistorico("VALE3")
assert sorted((h["periodo"] or "") for h in historico) == ["", "1y"], historico
assert AnaliseView.rotuloPeriodo(next(h["periodo"] for h in historico if h["periodo"] is None)) == "—"
passo("PE6 registro antigo sem período ignorado pelo cache e exibido como '—' no histórico")

# PE7 (modelo) — coluna anulável e período no índice do cache
coluna = RecomendacoesEntity.__table__.c.periodo
assert coluna.nullable, "registros antigos não têm período"
indices = [[c.name for c in i.columns] for i in RecomendacoesEntity.__table__.indexes]
assert ["item", "data_referencia", "periodo"] in indices, indices
passo("PE7 coluna 'periodo' anulável e índice ativo + data + período (migração: ver persistencia.md)")

# PE8 — forcar ignora o cache e grava com o período
antes = len(chamadasIA)
rForcado = servico.analisar("PETR4", "3mo", forcar=True)
assert not rForcado["doCache"] and len(chamadasIA) == antes + 1
assert rForcado["recomendacao"]["periodo"] == "3mo"
assert rForcado["recomendacao"]["id"] != r3m["recomendacao"]["id"]
with Session() as session:
    assert session.query(RecomendacoesEntity).filter_by(item="PETR4", periodo="3mo").count() == 2
passo("PE8 'forcar' chama a IA e grava nova recomendação com o período")

# PE9 — "Variação no período" usa o retorno do resumo
ind3m = r3m["indicadores"]
fechamentosCortados = ind3m.historico["Close"]
variacaoAntiga = (float(fechamentosCortados.iloc[-1]) / float(fechamentosCortados.iloc[0]) - 1) * 100
assert perto(variacaoAntiga, ind3m.resumo_periodo["retornoPct"]), "com aquecimento, o gráfico cobre o período inteiro"
assert perto(AnaliseView.variacaoPeriodo(ind3m), ind3m.resumo_periodo["retornoPct"])
esperado3m = indicadores.resumirPeriodo(indicadores.recortarPeriodo(historicoFake("PETR4", "3mo"), "3mo"))
assert ind3m.resumo_periodo == esperado3m, (ind3m.resumo_periodo, esperado3m)
passo("PE9 'Variação no período' = retorno do período inteiro (sem o aquecimento)")

# PE11 — análise múltipla: resumo de cada ativo, mesmo período
r = AnaliseController().analisarVarios(["ITUB4", "BBDC4"], "6mo")
assert r["erros"] == [], r["erros"]
resumos = {}
for resultado in r["resultados"]:
    item = resultado["ativo"]["item"]
    assert resultado["indicadores"].periodo == "6mo"
    assert resultado["recomendacao"]["periodo"] == "6mo"
    assert resultado["indicadores"].resumo_periodo == indicadores.resumirPeriodo(
        indicadores.recortarPeriodo(historicoFake(item, "6mo"), "6mo"))
    resumos[item] = resultado["indicadores"].resumo_periodo
assert resumos["ITUB4"] != resumos["BBDC4"]
passo("PE11 análise múltipla: cada ativo com o próprio resumo, todos no período escolhido")

print(f"\n{len(ok)} critérios da análise por período passaram")
