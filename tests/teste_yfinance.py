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
    YfinanceService.cotacoes.clear()
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

sessao, s = novo("queda")
antes = len(sessao.chamadas)
t0 = time.time()
assert [s.buscarPrecoAtual("PETR4") for _ in range(4)] == [None] * 4
tentativas = len([c for c in sessao.chamadas[antes:] if "/v8/finance/chart" in c[0]])
assert tentativas == 1, tentativas
print(f"OK  cotacao com Yahoo fora: 4 consultas geram {tentativas} tentativa de rede (cache negativo de 60s)")

sessao, s = novo("ok")
preco = s.buscarPrecoAtual("PETR4")
fake_yahoo.instalar("queda")
YfinanceService.cotacoes["PETR4"] = (time.time() - 400, preco, False)
assert s.buscarPrecoAtual("PETR4") == preco
print("OK  cotacao vencida + Yahoo fora -> mantem a ultima cotacao conhecida")
print("\nyfinance real validado nos 3 cenarios")
