"""Spec: .agents/docs/specs/historico-aquecimento.md (AQ1-AQ5).

Yahoo simulado; sem banco (o backtesting roda sem usuário, sem gravar).
"""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/aq.db"

import numpy as np
import pandas as pd
import yfinance as yf
from src.models import Parametros
from src.models.services import YfinanceService as moduloYf
from src.models.services.YfinanceService import YfinanceService
from src.models.services.IndicatorsService import IndicatorsService
from src.models.services.BacktestService import BacktestService

ok = []


def passo(nome):
    ok.append(nome)
    print("OK ", nome)


assert Parametros.MESES_PERIODO == {"3mo": 3, "6mo": 6, "1y": 12, "2y": 24}
assert Parametros.DIAS_AQUECIMENTO == 150


def historico(n=170, fim="2026-10-02", fechamentos=None):
    datas = pd.bdate_range(end=fim, periods=n)
    t = np.arange(n)
    preco = fechamentos if fechamentos is not None else 30 + 0.02 * t + 4 * np.sin(t / 7)
    return pd.DataFrame({"Open": preco, "High": preco, "Low": preco, "Close": preco, "Volume": 1000}, index=datas)


# AQ1 — pede ao Yahoo desde hoje - período - 150 dias
pedidos = []


class FakeTicker:
    def __init__(self, simbolo, *a, **k):
        self.simbolo = simbolo

    def history(self, **kwargs):
        pedidos.append((self.simbolo, kwargs))
        return historico()


moduloYf.yf.Ticker = FakeTicker
yf.Ticker = FakeTicker
for periodo, meses in Parametros.MESES_PERIODO.items():
    pedidos.clear()
    YfinanceService().buscarHistorico("PETR4", periodo)
    simbolo, kwargs = pedidos[-1]
    assert simbolo == "PETR4.SA" and "period" not in kwargs and kwargs.get("interval", "1d") == "1d", kwargs
    esperado = (pd.Timestamp.today().normalize() - pd.DateOffset(months=meses) - pd.Timedelta(days=150)).date()
    obtido = pd.Timestamp(kwargs["start"]).date()
    assert abs((obtido - esperado).days) <= 1, (periodo, obtido, esperado)
passo("AQ1 o Yahoo é consultado a partir de hoje - período - 150 dias (3mo, 6mo, 1y, 2y)")

servico = IndicatorsService()
dados = historico()
inicio = dados.index[dados.index >= dados.index[-1] - pd.DateOffset(months=3)][0]
noPeriodo = dados[dados.index >= inicio]
assert servico.inicioPeriodo(dados, "3mo") == inicio
assert servico.recortarPeriodo(dados, "3mo").index.equals(noPeriodo.index)

# AQ2 — o período inteiro, com indicadores completos
ind = servico.calcular("PETR4", dados, "3mo")
assert ind.historico.index[0] == inicio and ind.historico.index.equals(noPeriodo.index), ind.historico.index[:3]
assert 60 <= len(ind.historico) <= 70, len(ind.historico)
colunas = ["RSI", "MACD", "MACD_Sig", "SMA20", "SMA50"]
assert not ind.historico[colunas].isna().any().any()
passo(f"AQ2 3 meses = {len(ind.historico)} pregões no gráfico, do 1º dia do período, sem valores faltando")

# AQ3 — a máxima do aquecimento não entra no resumo
precos = dados["Close"].to_numpy().copy()
precos[5] = 99.0
comPico = historico(fechamentos=precos)
ind = servico.calcular("PETR4", comPico, "3mo")
assert ind.resumo_periodo["maxima"] < 99.0, ind.resumo_periodo
assert ind.resumo_periodo == servico.resumirPeriodo(comPico[comPico.index >= inicio])
passo("AQ3 resumo do período ignora o aquecimento (pico de R$ 99 fora do período não aparece)")

# AQ4 — indicadores do último dia usam o aquecimento
ind = servico.calcular("PETR4", dados, "3mo")
rsiCompleto = round(float(servico.rsi(dados["Close"], Parametros.RSI_PERIOD).iloc[-1]), 2)
rsiSoPeriodo = round(float(servico.rsi(noPeriodo["Close"], Parametros.RSI_PERIOD).iloc[-1]), 2)
assert ind.rsi == rsiCompleto, (ind.rsi, rsiCompleto)
assert rsiCompleto != rsiSoPeriodo, "a série de teste precisa distinguir os dois cálculos"
passo(f"AQ4 RSI do último dia com aquecimento ({rsiCompleto}) e não só com o período ({rsiSoPeriodo})")

# AQ5 — backtesting de 3 meses simula sobre o período inteiro
YfinanceService.buscarHistorico = lambda self, item, periodo="1y", intervalo="1d": dados
YfinanceService.buscarHistoricoIndice = lambda self, simbolo="^BVSP", periodo="1y": None
resultado = BacktestService().executar("PETR4", "3mo")
assert resultado["pregoesSimulados"] == len(noPeriodo), (resultado["pregoesSimulados"], len(noPeriodo))
assert all(pd.Timestamp(o["dataEntrada"]) >= inicio for o in resultado["operacoes"])
assert resultado["operacoes"], "a série senoidal de teste gera operações em 3 meses"
passo(f"AQ5 backtesting de 3 meses simula {resultado['pregoesSimulados']} pregões, "
      f"{len(resultado['operacoes'])} operação(ões), nenhuma antes do período")

print(f"\n{len(ok)} critérios do aquecimento passaram")
