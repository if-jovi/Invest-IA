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
os.environ["DATABASE_URL"] = f"sqlite:///{PASTA}/teste.db"
os.environ["ANTHROPIC_API_KEY"] = "chave-de-teste"
import numpy as np, pandas as pd, anthropic
from sqlalchemy import event
import src.models.base as base

@event.listens_for(base.engine, "connect")
def fk(conn, _):
    conn.execute("PRAGMA foreign_keys=ON")

from src.models.entities.StockEntity import StockEntity
from src.models.services.YfinanceService import YfinanceService

def historicoFake(periodo="1y"):
    rng = np.random.default_rng(7)
    n = {"5d": 5, "1mo": 22, "3mo": 90, "6mo": 180, "1y": 320, "2y": 600}[periodo]
    datas = pd.bdate_range(end="2026-10-02", periods=n, tz="America/Sao_Paulo")
    t = np.arange(n)
    p = 30 + 0.02 * t + 4 * np.sin(t / 9) + rng.normal(0, 0.35, n)
    return pd.DataFrame({"Open": p, "High": p + 0.4, "Low": p - 0.4, "Close": p, "Volume": 1000}, index=datas)

YfinanceService.buscarHistorico = lambda self, item, periodo="1y", intervalo="1d": historicoFake(periodo)
YfinanceService.validarItem = lambda self, item: self.normalizarItem(item) != "ZZZZ9"
YfinanceService.buscarInfo = lambda self, item: StockEntity(
    item=self.normalizarItem(item), nome=f"Empresa {self.normalizarItem(item)} S.A.", setor="Energia",
    segmento="Petroleo", descricao="Oil and gas company.")
YfinanceService.buscarPrecoAtual = lambda self, item: 40.0

TEXTO = """RECOMENDAÇÃO: COMPRA

SOBRE A EMPRESA:
A empresa atua no setor de energia.

JUSTIFICATIVA:
O RSI esta neutro e o MACD cruzou para cima.

RISCOS:
- Volatilidade do petroleo
"""
class FakeMsg:
    def __init__(self, t): self.content = [type("B", (), {"text": t})()]
class FakeClient:
    def __init__(self, api_key=None, **kw): pass
    class messages:
        @staticmethod
        def create(**kw): return FakeMsg(TEXTO)
anthropic.Anthropic = FakeClient
