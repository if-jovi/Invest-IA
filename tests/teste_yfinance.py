import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
PASTA = tempfile.mkdtemp()
try:
    import pandas_ta
except ImportError:
    from tests import pandas_ta_simulado
    sys.modules["pandas_ta"] = pandas_ta_simulado
import sys, time
import yfinance as yf
from tests import yahoo_simulado as fake_yahoo
from src.models.services.YfinanceService import YfinanceService

def novo(modo):
    return fake_yahoo.instalar(modo), YfinanceService()

print("yfinance", yf.__version__)
sessao, s = novo("ok")
df = s.buscarHistorico("b3sa3", "1y")
assert len(df) == 252 and any("B3SA3.SA" in u for u, _ in sessao.chamadas)
assert s.buscarInfoAtivo("PETR4")["setor"] == "Energia"
print("OK  caminho feliz (historico, info, setor traduzido; B3SA3 vira B3SA3.SA)")

sessao, s = novo("429")
try:
    s.buscarHistorico("PETR4", "1y")
    raise SystemExit("deveria falhar")
except RuntimeError as e:
    assert "limitou as requisições" in str(e) and "429" in str(e), e
try:
    s.buscarInfoAtivo("PETR4")
    raise SystemExit("deveria falhar")
except RuntimeError as e:
    assert "limitou as requisições" in str(e)
print("OK  HTTP 429 do Yahoo -> RuntimeError claro (e NAO 'ativo nao encontrado')")

sessao, s = novo("queda")
try:
    s.buscarInfoAtivo("PETR4")
    raise SystemExit("deveria falhar")
except RuntimeError as e:
    assert "Verifique a conexão" in str(e) and "não foi encontrado" not in str(e), e
print("OK  rede fora do ar -> RuntimeError de conexao (e NAO 'ativo nao encontrado')")

sessao, s = novo("ok")
try:
    s.buscarInfoAtivo("ZZZZ9")
    raise SystemExit("deveria falhar")
except ValueError as e:
    assert "ZZZZ9 não foi encontrado na B3" in str(e), e
print("OK  ticker que realmente nao existe -> ValueError 'nao foi encontrado na B3'")

# ---- Cotações em lote (spec .agents/docs/specs/carteira.md, CT1-CT6) ----
from datetime import datetime
from types import SimpleNamespace
import numpy as np
import pandas as pd
import src.models.services.YfinanceService as modulo

FECHAMENTOS = {
    "PETR4.SA": [30.0, 31.0, 32.0, 33.0, 34.65],
    "VALE3.SA": [60.0, 61.0, 62.0, 64.0, 62.40],
    "ITUB4.SA": [np.nan, np.nan, np.nan, 35.0, 35.70],
    "NOVO3.SA": [np.nan, np.nan, np.nan, np.nan, 12.0],
    "VAZI3.SA": [np.nan] * 5,
}
downloads = []
estado = {"falhar": False}


def downloadFalso(tickers, *args, **kwargs):
    lista = tickers.split() if isinstance(tickers, str) else list(tickers)
    downloads.append({"tickers": lista, "kwargs": kwargs})
    if estado["falhar"]:
        raise ConnectionError("Failed to connect: rede indisponivel")
    datas = pd.bdate_range(end="2026-11-04", periods=5, name="Date")
    colunas, dados = [], []
    for t in lista:
        fecha = FECHAMENTOS.get(t, [np.nan] * 5)
        for campo in ("Open", "High", "Low", "Close", "Adj Close", "Volume"):
            colunas.append((t, campo) if kwargs.get("group_by") == "ticker" else (campo, t))
            dados.append(fecha if campo != "Volume" else [1000.0] * 5)
    nomes = ["Ticker", "Price"] if kwargs.get("group_by") == "ticker" else ["Price", "Ticker"]
    return pd.DataFrame(np.array(dados, dtype=float).T, index=datas,
                        columns=pd.MultiIndex.from_tuples(colunas, names=nomes))


relogio = [1_000_000.0]
modulo.time = SimpleNamespace(time=lambda: relogio[0], sleep=lambda s: None)
yf.download = downloadFalso
modulo.yf.download = downloadFalso
YfinanceService.cotacoes.clear()
s = YfinanceService()

c = s.buscarCotacoes(["PETR4", "vale3.sa", "ITUB4"])
assert len(downloads) == 1, downloads
assert sorted(downloads[0]["tickers"]) == ["ITUB4.SA", "PETR4.SA", "VALE3.SA"], downloads[0]
assert downloads[0]["kwargs"].get("period") == "5d" and downloads[0]["kwargs"].get("interval", "1d") == "1d"
assert set(c) == {"PETR4", "VALE3", "ITUB4"}, c.keys()
print("OK  CT1 uma chamada a yf.download com os simbolos .SA de todos os ativos")

p = c["PETR4"]
assert set(p) == {"preco", "fechamentoAnterior", "variacaoDia", "atualizadoEm", "desatualizada"}, p
assert abs(p["preco"] - 34.65) < 0.01 and abs(p["fechamentoAnterior"] - 33.0) < 0.01
assert abs(p["variacaoDia"] - 5.0) < 0.01, p
assert abs(c["VALE3"]["variacaoDia"] - (-2.5)) < 0.01, c["VALE3"]
assert abs(c["ITUB4"]["variacaoDia"] - 2.0) < 0.01, c["ITUB4"]
assert isinstance(p["atualizadoEm"], datetime) and p["desatualizada"] is False
print("OK  CT2 preco, fechamento anterior e variacao do dia batem com o calculo a mao")

c = s.buscarCotacoes(["VAZI3", "NOVO3", "ZZZZ9", "PETR4"])
assert c["VAZI3"] is None and c["ZZZZ9"] is None, c
assert c["NOVO3"]["preco"] == 12.0 and c["NOVO3"]["fechamentoAnterior"] is None and c["NOVO3"]["variacaoDia"] is None
assert c["PETR4"] is not None
print("OK  CT3 ativo ausente/so NaN sem cotacao; uma unica barra sem variacao; demais intactos")

downloads.clear()
relogio[0] += 59
s.buscarCotacoes(["PETR4", "VALE3"])
assert downloads == [], "dentro de 60s deve usar o cache"
relogio[0] += 2
s.buscarCotacoes(["PETR4", "VALE3"])
assert len(downloads) == 1 and sorted(downloads[0]["tickers"]) == ["PETR4.SA", "VALE3.SA"]
downloads.clear()
relogio[0] += 10
s.buscarCotacoes(["PETR4", "WEGE3"])
assert len(downloads) == 1 and downloads[0]["tickers"] == ["WEGE3.SA"], "so busca o que nao esta em cache"
print("OK  CT4 cache de 60s por ativo; busca apenas os vencidos/ausentes")

downloads.clear()
s.buscarCotacoes(["PETR4"], forcar=True)
assert len(downloads) == 1
print("OK  CT6 forcar=True ignora o cache")

relogio[0] += 61
estado["falhar"] = True
downloads.clear()
c = s.buscarCotacoes(["PETR4", "BBAS3"])
assert abs(c["PETR4"]["preco"] - 34.65) < 0.01 and c["PETR4"]["desatualizada"] is True, c["PETR4"]
assert c["BBAS3"] is None
assert len(downloads) == 1
relogio[0] += 29
s.buscarCotacoes(["PETR4", "BBAS3"])
assert len(downloads) == 1, "falha recente: nova tentativa so apos 30s"
relogio[0] += 2
s.buscarCotacoes(["PETR4", "BBAS3"])
assert len(downloads) == 2
estado["falhar"] = False
print("OK  CT5 Yahoo fora: ultimo valor marcado como desatualizado; sem valor -> None; retentativa apos 30s")

assert s.buscarCotacoes([]) == {} and len(downloads) == 2
print("OK  lista vazia nao chama o Yahoo")
print("\nyfinance real validado nos 3 cenarios")
