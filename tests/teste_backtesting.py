"""Spec: .agents/docs/specs/backtesting.md (BT1-BT3, BT5-BT7 e casos-limite).

BT4 (rótulos na tela) está em teste_interface.py. Séries montadas à mão com as
colunas que a simulação usa (Close, MACD, MACD_Sig, RSI).
"""
import math
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/bt.db"

import pandas as pd
from src.models import Parametros
from src.models.services.BacktestService import BacktestService

ok = []


def passo(nome):
    ok.append(nome)
    print("OK ", nome)


def perto(a, b, tol=0.01):
    return abs(a - b) <= tol


def serie(fechamentos, macdAcima=None, rsi=50.0, inicio="2026-03-02"):
    """macdAcima: lista de bool (MACD acima do sinal em cada dia)."""
    datas = pd.bdate_range(inicio, periods=len(fechamentos))
    macdAcima = macdAcima or [False] * len(fechamentos)
    return pd.DataFrame({
        "Close": [float(f) for f in fechamentos],
        "MACD": [1.0 if a else -1.0 for a in macdAcima],
        "MACD_Sig": [0.0] * len(fechamentos),
        "RSI": [rsi] * len(fechamentos),
    }, index=datas)


def operacao(dados, iEntrada, iSaida, resultadoPct, emAberto=False):
    return {"item": "TEST3", "dataEntrada": dados.index[iEntrada].date(),
            "precoEntrada": float(dados["Close"].iloc[iEntrada]), "dataSaida": dados.index[iSaida].date(),
            "precoSaida": float(dados["Close"].iloc[iSaida]), "resultadoPct": resultadoPct, "emAberto": emAberto}


assert Parametros.CUSTO_OPERACAO_PCT == 0.03
semCusto = BacktestService(custoPct=0)
comCusto = BacktestService()
assert comCusto.custoPct == 0.03

# BT1 — Sharpe anualizado calculado à mão
# Fechamentos 10, 10, 11, 12, 11, 11; compra no 2º dia (10), venda no 4º (12), sem custo.
# Retornos diários (do 2º pregão em diante): 0 (entrada), +10%, +9,0909%, 0, 0
# média 0,0381818 / desvio amostral 0,0523813 x raiz(252) = 11,5713
dados = serie([10, 10, 11, 12, 11, 11])
ops = [operacao(dados, 1, 3, 20.0)]
retornos = list(semCusto.retornosDiarios(ops, dados))
assert len(retornos) == 5, retornos
for obtido, esperado in zip(retornos, [0.0, 0.1, 12 / 11 - 1, 0.0, 0.0]):
    assert perto(obtido, esperado, 1e-9), (retornos)
assert perto(semCusto.calcularMetricas(ops, dados)["sharpe"], 11.57), semCusto.calcularMetricas(ops, dados)
passo("BT1 Sharpe anualizado (retornos diários x raiz(252)) bate com o cálculo à mão: 11,57")

c = 0.0003
retornos = list(comCusto.retornosDiarios(ops, dados))
fator = math.prod(1 + r for r in retornos)
assert perto(fator, (12 * (1 - c)) / (10 * (1 + c)), 1e-9), fator
assert perto(retornos[0], 1 / (1 + c) - 1, 1e-12) and perto(retornos[2], (12 / 11) * (1 - c) - 1, 1e-12)
passo("BT1 com custo: entrada 1/(1+c)-1, saída x(1-c); o produto dos retornos diários = resultado líquido")

# BT2 — sem operações ou desvio zero
assert semCusto.calcularMetricas([], dados)["sharpe"] == 0.0
plano = serie([10] * 6)
assert semCusto.calcularMetricas([operacao(plano, 1, 3, 0.0)], plano)["sharpe"] == 0.0
passo("BT2 Sharpe 0.0 sem operações e com desvio zero")

# BT5 — custo de 0,03% por ponta na operação e no Buy and Hold
dados = serie([9, 10, 10.5, 11], [False, True, True, False])
ops = comCusto.simular("TEST3", dados)
assert len(ops) == 1 and ops[0]["precoEntrada"] == 10.0 and ops[0]["precoSaida"] == 11.0, ops
assert perto(ops[0]["resultadoPct"], ((11 * (1 - c)) / (10 * (1 + c)) - 1) * 100), ops[0]
assert ops[0]["emAberto"] is False
m = comCusto.calcularMetricas(ops, dados)
assert perto(m["retornoBuyHold"], ((11 * (1 - c)) / (9 * (1 + c)) - 1) * 100), m
assert m["custoOperacaoPct"] == 0.03
passo("BT5 operação R$ 10 -> R$ 11 rende 9,93% líquido; Buy and Hold também desconta as duas pontas")

# BT3 — sem custo e sem posição aberta, métricas iguais às do cálculo anterior
precos = [10, 10, 11, 12, 11, 10, 10, 9, 10, 12, 13, 12, 11]
acima = [False, True, True, True, False, False, True, False, True, True, True, False, False]
dados = serie(precos, acima)
ops = semCusto.simular("TEST3", dados)
assert len(ops) == 3 and not any(o["emAberto"] for o in ops), ops
resultados = pd.Series([round((o["precoSaida"] - o["precoEntrada"]) / o["precoEntrada"] * 100, 2) for o in ops])
assert list(resultados) == [o["resultadoPct"] for o in ops]
acumulado = (1 + resultados / 100).cumprod()
esperado = {
    "totalOperacoes": 3,
    "taxaAcerto": round(float((resultados > 0).mean() * 100), 2),
    "retornoAcumulado": round(float((acumulado.iloc[-1] - 1) * 100), 2),
    "retornoBuyHold": round((precos[-1] - precos[0]) / precos[0] * 100, 2),
    "drawdownMaximo": round(float(((acumulado - acumulado.cummax()) / acumulado.cummax() * 100).min()), 2),
}
m = semCusto.calcularMetricas(ops, dados)
for chave, valor in esperado.items():
    assert m[chave] == valor, (chave, m[chave], valor)
passo("BT3 com custo 0 e sem posição aberta, acerto, retorno, Buy and Hold e drawdown iguais ao cálculo anterior")

# BT6 — posição aberta no último pregão
dados = serie([9, 10, 10.8], [False, True, True])
ops = comCusto.simular("TEST3", dados)
assert len(ops) == 1 and ops[0]["emAberto"] is True, ops
assert ops[0]["dataSaida"] == dados.index[-1].date() and ops[0]["precoSaida"] == 10.8
assert perto(ops[0]["resultadoPct"], ((10.8 * (1 - c)) / (10 * (1 + c)) - 1) * 100)
assert comCusto.calcularMetricas(ops, dados)["totalOperacoes"] == 1
passo("BT6 estratégia comprada no fim: sai pelo último fechamento, marcada 'em aberto' e conta nas métricas")

dados = serie([9, 9.5, 10], [False, False, True])
ops = comCusto.simular("TEST3", dados)
assert len(ops) == 1 and ops[0]["emAberto"] and ops[0]["dataEntrada"] == ops[0]["dataSaida"]
assert perto(ops[0]["resultadoPct"], ((1 - c) / (1 + c) - 1) * 100), ops[0]
passo("BT limite: compra no último pregão vira operação em aberto com resultado = só os custos")

# BT7 — nada de entrada antes do início do período
aquecimento = [10, 10.5, 11]
periodo = [11, 11.5, 12, 11]
dados = serie(aquecimento + periodo, [False, True, False, True, True, True, False])
inicio = dados.index[3]
ops = semCusto.simular("TEST3", dados, inicio=inicio)
assert len(ops) == 1, ops
assert ops[0]["dataEntrada"] == inicio.date(), "cruzamento no 1º dia do período (comparado ao último do aquecimento)"
assert all(pd.Timestamp(o["dataEntrada"]) >= inicio for o in ops)
passo("BT7 cruzamento dentro do aquecimento é ignorado; o do 1º dia do período (vs. último do aquecimento) vale")

# Caso-limite — custo inválido
for invalido in (-0.01, 100, 150):
    try:
        BacktestService(custoPct=invalido)
    except ValueError:
        pass
    else:
        raise AssertionError(f"custo {invalido} deveria ser recusado")
passo("BT limite: custo negativo ou >= 100% é recusado com ValueError")

print(f"\n{len(ok)} critérios do backtesting passaram")
