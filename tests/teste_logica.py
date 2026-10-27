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
os.environ["DATABASE_URL"] = f"sqlite:///{PASTA}/logica.db"
os.environ["ANTHROPIC_API_KEY"] = "chave-de-teste"

import numpy as np
import pandas as pd
from sqlalchemy import event

import src.models.base as base

@event.listens_for(base.engine, "connect")
def fk(conn, _):
    conn.execute("PRAGMA foreign_keys=ON")

base.criarTabelas()

from src.models.entities.StockEntity import StockEntity
from src.models.services.YfinanceService import YfinanceService
import anthropic

def historicoFake(item, periodo="1y", intervalo="1d"):
    rng = np.random.default_rng(7)
    n = {"5d": 5, "1mo": 22, "3mo": 90, "6mo": 180, "1y": 320, "2y": 600}[periodo]
    datas = pd.bdate_range(end="2026-10-02", periods=n, tz="America/Sao_Paulo")
    t = np.arange(n)
    preco = 30 + 0.02 * t + 4 * np.sin(t / 9) + rng.normal(0, 0.35, n)
    df = pd.DataFrame({"Open": preco, "High": preco + 0.4, "Low": preco - 0.4, "Close": preco, "Volume": 1000}, index=datas)
    return df

chamadasHistorico = []
def buscarHistorico(self, item, periodo="1y", intervalo="1d"):
    chamadasHistorico.append(item)
    if self.normalizarItem(item) in ("ZZZZ9",):
        raise ValueError("Nenhum dado encontrado")
    return historicoFake(item, periodo)

YfinanceService.buscarHistorico = buscarHistorico
YfinanceService.buscarInfo = lambda self, item: StockEntity(
    item=self.normalizarItem(item), nome=f"Empresa {self.normalizarItem(item)} S.A.", setor="Energia",
    segmento="Petroleo", descricao="Oil and gas company.")
YfinanceService.buscarPrecoAtual = lambda self, item: 40.0

TEXTO = """RECOMENDAÇÃO: COMPRA

SOBRE A EMPRESA:
A empresa atua no setor de energia.

JUSTIFICATIVA:
O RSI esta neutro.

O MACD cruzou para cima.

RISCOS:
- Volatilidade do petroleo
- Risco regulatorio
"""
chamadasIA = []
class FakeMsg:
    def __init__(self, t): self.content = [type("B", (), {"text": t})()]
class FakeClient:
    def __init__(self, api_key=None, **kw): pass
    class messages:
        @staticmethod
        def create(**kw):
            chamadasIA.append(kw)
            return FakeMsg(TEXTO)
anthropic.Anthropic = FakeClient

from src.controllers.AuthController import AuthController
from src.controllers.CarteiraController import CarteiraController
from src.controllers.ItensCarteiraController import ItensCarteiraController
from src.controllers.AnaliseController import AnaliseController
from src.controllers.BacktestController import BacktestController
from src.models.base import Session
from src.models.entities.UsuariosEntity import UsuariosEntity
from src.models.entities.CarteirasEntity import CarteirasEntity
from src.models.entities.ItensB3Entity import ItensB3Entity
from src.models.entities.ItensCarteirasEntity import ItensCarteirasEntity
from src.models.entities.OperacoesEntity import OperacoesEntity
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity

def espera_erro(fn, trecho):
    try:
        fn()
    except (ValueError, RuntimeError) as e:
        assert trecho in str(e), f"mensagem inesperada: {e}"
        return
    raise AssertionError(f"era esperado erro contendo '{trecho}'")

ok = []
def passo(nome): ok.append(nome); print("OK ", nome)

auth = AuthController()
u = auth.cadastrar("Joao", "Joao@Email.com", "segredo1", "segredo1")
assert u["email"] == "joao@email.com" and u["carteiraId"]
passo("cadastro cria usuario e carteira (1:1)")
espera_erro(lambda: auth.cadastrar("Joao", "joao@email.com", "segredo1", "segredo1"), "já está cadastrado")
espera_erro(lambda: auth.cadastrar("A", "x@y.com", "123", "123"), "mínimo 6")
espera_erro(lambda: auth.cadastrar("A", "x@y.com", "123456", "654321"), "não coincidem")
espera_erro(lambda: auth.cadastrar("A", "invalido", "123456", "123456"), "email válido")
passo("validacoes de cadastro")
assert auth.login("JOAO@email.com", "segredo1")["id"] == u["id"]
espera_erro(lambda: auth.login("joao@email.com", "errada"), "inválidos")
espera_erro(lambda: auth.login("naoexiste@email.com", "segredo1"), "inválidos")
passo("login correto e rejeicao de senha/usuario errados")
with Session() as s:
    assert s.query(UsuariosEntity).first().senha_hash != "segredo1"
    assert s.query(CarteirasEntity).count() == 1
passo("senha armazenada como hash")

cid = u["carteiraId"]
r = CarteiraController().obterResumo(cid)
assert r["itens"] == [] and r["valorInvestido"] == 0 and r["valorAtual"] is None
passo("carteira vazia")

itens = ItensCarteiraController()
espera_erro(lambda: itens.adicionarCompra(cid, "XYZ", 10, 10), "Código inválido")
espera_erro(lambda: itens.adicionarCompra(cid, "PETR4", 0, 10), "maior que zero")
espera_erro(lambda: itens.adicionarCompra(cid, "ZZZZ9", 10, 10), "não foi encontrado")
passo("validacoes de ticker/quantidade/preco")

class Falha(Exception): pass
YfinanceService.validarItem = lambda self, item: self.normalizarItem(item) != "ZZZZ9"
espera_erro(lambda: itens.adicionarCompra(cid, "ZZZZ9", 10, 10), "não foi encontrado")
itens.adicionarCompra(cid, "petr4.sa", 100, 30.0)
itens.adicionarCompra(cid, "PETR4", 100, 40.0)
r = CarteiraController().obterResumo(cid)
p = r["itens"][0]
assert p["item"] == "PETR4" and p["quantidade"] == 200 and abs(p["precoMedio"] - 35.0) < 1e-6
assert p["nome"] == "Empresa PETR4 S.A." and p["setor"] == "Energia"
assert abs(r["valorInvestido"] - 7000) < 1e-6 and abs(r["valorAtual"] - 8000) < 1e-6
assert abs(r["resultado"] - 1000) < 1e-6 and abs(r["resultadoPct"] - 14.2857) < 1e-3
passo("compra cadastra ativo via API, normaliza .SA e recalcula preco medio")
with Session() as s:
    assert s.query(ItensB3Entity).count() == 1
    assert s.query(ItensCarteirasEntity).count() == 1
passo("catalogo cadastrado automaticamente e sem duplicar item na carteira")

espera_erro(lambda: itens.registrarVenda(cid, "PETR4", 500), "apenas 200")
espera_erro(lambda: itens.registrarVenda(cid, "VALE3", 1), "não está na sua carteira")
assert itens.registrarVenda(cid, "PETR4", 50)["quantidade"] == 150
assert itens.definirPosicao(cid, "PETR4", 120, 33.5)["precoMedio"] == 33.5
assert itens.registrarVenda(cid, "PETR4", 120)["removido"] is True
assert CarteiraController().obterResumo(cid)["itens"] == []
passo("venda parcial, venda excedente, correcao e venda total remove a posicao")

itens.adicionarCompra(cid, "PETR4", 10, 30.0)
itens.remover(cid, "PETR4")
assert itens.listarItens(cid) == []
passo("remocao de ativo")

itens.adicionarCompra(cid, "PETR4", 100, 30.0)
analise = AnaliseController()
a1 = analise.analisar("petr4", "1y")
assert a1["doCache"] is False and a1["recomendacao"]["recomendacao"] == "COMPRA"
assert a1["recomendacao"]["sobreEmpresa"].startswith("A empresa atua")
assert "RSI" in a1["recomendacao"]["justificativa"] and "regulatorio" in a1["recomendacao"]["riscos"]
assert a1["indicadores"].historico is not None and len(chamadasIA) == 1
a2 = analise.analisar("PETR4", "1y")
assert a2["doCache"] is True and len(chamadasIA) == 1
a3 = analise.analisar("PETR4", "1y", forcar=True)
assert a3["doCache"] is False and len(chamadasIA) == 2
assert len(analise.buscarHistorico("PETR4")) == 2
passo("analise: gera, reaproveita cache (sem nova chamada a IA) e forca nova analise")
prompt = chamadasIA[0]["messages"][0]["content"]
assert "PETR4" in prompt and "RSI" in prompt and "iniciantes" in prompt
passo("prompt contem ativo, indicadores e publico iniciante")

r = CarteiraController().obterResumo(cid)
assert r["itens"][0]["recomendacao"] == "COMPRA" and r["itens"][0]["dataRecomendacao"]
passo("carteira exibe a ultima recomendacao de cada ativo (RF17)")

from src.models.services.ClaudeService import ClaudeService
c = ClaudeService()
variantes = {
    "**RECOMENDACAO:** VENDA\n\n**SOBRE A EMPRESA:**\nTexto A\n\n**JUSTIFICATIVA:**\nTexto J\n\n**RISCOS:**\n- r1": ("VENDA", "Texto A", "Texto J", "- r1"),
    "Recomendação: manter\nSobre a empresa:\nB\nJustificativa:\nJ2\nRiscos:\nR2": ("MANTER", "B", "J2", "R2"),
    "resposta fora do formato": (None, "", "", ""),
}
for texto, (tipo, sobre, just, risc) in variantes.items():
    assert c.identificarTipo(texto) == tipo, texto
    assert c.extrairSecao(texto, "SOBRE_EMPRESA") == sobre, texto
    assert c.extrairSecao(texto, "JUSTIFICATIVA") == just, texto
    assert c.extrairSecao(texto, "RISCOS") == risc, texto
passo("parser da resposta da IA (com/sem acento, negrito, formato quebrado)")

bt = BacktestController()
b = bt.executar("PETR4", "1y", u["id"])
m = b["metricas"]
assert m["totalOperacoes"] == len(b["operacoes"]) > 0 and len(b["curvaAcumulada"]) == len(b["operacoes"])
assert set(m) == {"totalOperacoes", "taxaAcerto", "retornoAcumulado", "retornoBuyHold", "drawdownMaximo", "sharpe"}
assert b["persistido"] is True
with Session() as s:
    qtd1 = s.query(OperacoesEntity).filter_by(usuario_id=u["id"]).count()
assert qtd1 == len(b["operacoes"])
b2 = bt.executar("PETR4", "1y", u["id"])
with Session() as s:
    assert s.query(OperacoesEntity).filter_by(usuario_id=u["id"]).count() == qtd1
passo(f"backtest: {m['totalOperacoes']} operacoes, metricas completas, persistencia sem duplicar ao reexecutar")
print("    metricas:", m)
espera_erro(lambda: bt.executar("", "1y", 1), "Informe")
espera_erro(lambda: analise.analisar("PETR4", "10y"), "Período inválido")
passo("validacoes de entrada dos controllers")


from src.models.services.ItensB3Service import ItensB3Service
b3 = ItensB3Service()
for valido in ("PETR4", "B3SA3", "BOVA11", "KLBN11", "AAPL34", "petr4.sa"):
    b3.validarFormato(b3.normalizar(valido))
for invalido in ("PETR", "1ETR4", "PETR444", "PE TR4", "", "PETR4;DROP"):
    espera_erro(lambda i=invalido: b3.validarFormato(b3.normalizar(i)), "Código inválido")
passo("formato de ticker aceita B3SA3/BOVA11/BDR e rejeita lixo")

itens.adicionarCompra(cid, "B3SA3", 10, 12.0)
assert "B3SA3" in itens.listarItens(cid)
passo("compra de B3SA3 (ticker com digito no nome) funciona de ponta a ponta")

from src.models.base import agora
from datetime import datetime, timedelta
with Session() as s:
    criado = s.query(UsuariosEntity).first().criado_em
    assert abs((criado - agora()).total_seconds()) < 120 and criado.tzinfo is None
utc = datetime.utcnow()
assert abs((agora() - (utc - timedelta(hours=3))).total_seconds()) < 5
passo("carimbo de data/hora em horario de Brasilia (UTC-3)")

espera_erro(lambda: auth.login("nao.existe@email.com", "qualquer1"), "inválidos")
passo("login de usuario inexistente nao vaza informacao")

from src.models.services.IndicatorsService import IndicatorsService
curto = historicoFake("X", "3mo").iloc[:40]
espera_erro(lambda: IndicatorsService().calcular("PETR4", curto), "Histórico insuficiente")
passo("historico curto gera mensagem clara em vez de erro interno")

for cod in ("VALE3", "ITUB4", "BBDC4", "WEGE3"):
    itens.adicionarCompra(cid, cod, 10, 20.0)
import time as _t
YfinanceService.buscarPrecoAtual = lambda self, item: (_t.sleep(0.5), 40.0)[1]
t0 = _t.time()
resumo = CarteiraController().obterResumo(cid)
dur = _t.time() - t0
assert len(resumo["itens"]) == 6 and dur < 1.6, dur
passo(f"cotacoes em paralelo: 6 ativos x 0,5s de latencia carregaram em {dur:.1f}s (sequencial seria 3,0s)")

print(f"\n{len(ok)} grupos de teste passaram")
