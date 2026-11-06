"""Spec: .agents/docs/specs/desempenho-ia.md (DI1-DI6, DI9, DI10).

DI7 (migração) está em teste_persistencia.py; DI8 (tela) em teste_interface.py.
SQLite temporário; Yahoo e IA simulados.
"""
import io
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import dotenv
dotenv.load_dotenv = lambda *a, **k: False
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/desempenho.db"
os.environ["IA_PROVEDOR"] = "openrouter"

import numpy as np
import pandas as pd
import src.models.base as base

base.criarTabelas()

from src.models import Parametros
from src.models.base import Session
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity
from src.models.entities.AvaliacoesIaEntity import AvaliacoesIaEntity
from src.models.entities.StockEntity import StockEntity
from src.models.services import DesempenhoIaService as moduloDesempenho
from src.models.services.DesempenhoIaService import DesempenhoIaService, intervaloWilson, pValorBinomial
from src.models.services.IndicatorsService import IndicatorsService
from src.models.services.ItensB3Service import ItensB3Service
from src.models.services.YfinanceService import YfinanceService
from src.scripts import AvaliarIA

ok = []


def passo(nome):
    ok.append(nome)
    print("OK ", nome)


def perto(a, b, tol=0.01):
    return a is not None and abs(a - b) <= tol


assert Parametros.HORIZONTE_AVALIACAO == 20 and Parametros.FAIXA_MANTER_PCT == 3.0
servico = DesempenhoIaService()

# DI1 — retorno futuro e acerto
assert servico.retornoFuturo(100, 103) == 3.0 and servico.retornoFuturo(100, 97) == -3.0
casos = [
    ("COMPRA", 0.5, None, True, None), ("COMPRA", 0.0, None, False, None), ("COMPRA", -1.0, None, False, None),
    ("VENDA", -0.5, None, True, None), ("VENDA", 0.0, None, False, None), ("VENDA", 2.0, None, False, None),
    ("MANTER", 3.0, None, True, None), ("MANTER", -3.0, None, True, None), ("MANTER", 3.01, None, False, None),
    ("MANTER", -3.01, None, False, None), ("MANTER", 0.0, 5.0, True, None),
    ("COMPRA", 0.5, 0.6, True, False), ("COMPRA", -2.0, -3.0, False, True),
    ("VENDA", -1.0, 0.5, True, True), ("VENDA", 1.0, 0.5, False, False),
]
for rec, retorno, ibov, acerto, acertoIbov in casos:
    r = servico.avaliarCaso(rec, retorno, ibov)
    assert r == {"acerto": acerto, "acertoIbovespa": acertoIbov}, (rec, retorno, ibov, r)
passo("DI1 acerto de COMPRA/VENDA/MANTER nos limites (0% e ±3%) e contra o Ibovespa")

# DI9 — intervalo de Wilson e teste binomial (valores calculados à mão)
inf, sup = intervaloWilson(6, 10)
assert perto(inf, 0.31267, 0.001) and perto(sup, 0.83182, 0.001), (inf, sup)
inf, sup = intervaloWilson(0, 5)
assert perto(inf, 0.0, 0.001) and perto(sup, 0.43449, 0.001)
assert intervaloWilson(0, 0) is None
assert perto(pValorBinomial(6, 10, 0.5), 0.376953, 0.001)
assert perto(pValorBinomial(2, 3, 4 / 7), 208 / 343, 0.001)
assert pValorBinomial(0, 0, 0.5) is None
passo("DI9 Wilson(6,10) = 31,3% a 83,2%; P(X>=6 | n=10, p=0,5) = 0,377; n=0 -> None")

# DI2 + DI10 — agregação (calculada à mão)
#   COMPRA +5 (ibov 6), -2 (ibov -3), +1 (ibov 0) | VENDA -3 (ibov -1), +2 (ibov 1) | MANTER +1, -4 | 2 pendentes
lista = [
    {"recomendacao": "COMPRA", "retornoPct": 5.0, "retornoIbovespaPct": 6.0},
    {"recomendacao": "COMPRA", "retornoPct": -2.0, "retornoIbovespaPct": -3.0},
    {"recomendacao": "COMPRA", "retornoPct": 1.0, "retornoIbovespaPct": 0.0},
    {"recomendacao": "VENDA", "retornoPct": -3.0, "retornoIbovespaPct": -1.0},
    {"recomendacao": "VENDA", "retornoPct": 2.0, "retornoIbovespaPct": 1.0},
    {"recomendacao": "MANTER", "retornoPct": 1.0, "retornoIbovespaPct": 0.5},
    {"recomendacao": "MANTER", "retornoPct": -4.0, "retornoIbovespaPct": -1.0},
    {"recomendacao": "COMPRA", "retornoPct": None, "retornoIbovespaPct": None},
    {"recomendacao": "VENDA", "retornoPct": None, "retornoIbovespaPct": None},
]
a = servico.agregar(lista)
assert a["total"] == 7 and a["pendentes"] == 2, a
assert a["geral"]["acertos"] == 4 and a["geral"]["n"] == 7 and perto(a["geral"]["taxa"], 57.14)
ic = intervaloWilson(4, 7)
assert perto(a["geral"]["ic"][0], ic[0] * 100) and perto(a["geral"]["ic"][1], ic[1] * 100)
tipos = a["porTipo"]
assert (tipos["COMPRA"]["acertos"], tipos["COMPRA"]["n"]) == (2, 3) and perto(tipos["COMPRA"]["taxa"], 66.67)
assert (tipos["VENDA"]["acertos"], tipos["VENDA"]["n"]) == (1, 2) and perto(tipos["VENDA"]["taxa"], 50.0)
assert (tipos["MANTER"]["acertos"], tipos["MANTER"]["n"]) == (1, 2) and perto(tipos["MANTER"]["taxa"], 50.0)
assert perto(a["taxaBase"], 57.14), a["taxaBase"]
assert perto(a["pValorCompra"], 208 / 343, 0.001), a["pValorCompra"]
assert (a["contraIbovespa"]["acertos"], a["contraIbovespa"]["n"]) == (3, 5) and perto(a["contraIbovespa"]["taxa"], 60.0)
passo("DI2 total 7, pendentes 2, acerto 57,14%, por tipo 66,67/50/50, taxa base 57,14%, contra Ibovespa 3/5")
assert perto(tipos["COMPRA"]["retornoMedio"], 4 / 3) and perto(tipos["VENDA"]["retornoMedio"], -0.5)
assert perto(tipos["MANTER"]["retornoMedio"], -1.5) and perto(a["retornoMedioGeral"], 0.0)
passo("DI10 retorno médio depois de COMPRA (+1,33%), VENDA (-0,50%), MANTER (-1,50%) e geral (0,00%)")

vazio = servico.agregar([])
assert vazio["total"] == 0 and vazio["geral"]["taxa"] is None and vazio["geral"]["ic"] is None
assert vazio["pValorCompra"] is None
passo("DI9 sem casos avaliados: taxas, intervalo e p-valor ficam vazios (None)")

# --- Yahoo e IA simulados para o script e para avaliar() ------------------------------
FIM = "2026-10-02"


def serieAtivo(item):
    rng = np.random.default_rng(sum(ord(c) for c in item))
    n = 700
    datas = pd.bdate_range(end=FIM, periods=n)
    t = np.arange(n)
    preco = 30 + 0.01 * t + 3 * np.sin(t / 11) + rng.normal(0, 0.3, n)
    return pd.DataFrame({"Open": preco, "High": preco, "Low": preco, "Close": preco, "Volume": 1000}, index=datas)


def buscarHistoricoDesde(self, item, inicio, indice=False):
    serie = serieAtivo("IBOV" if indice else self.normalizarItem(item))
    if indice:
        serie = serie * 4000
    return serie[serie.index >= pd.Timestamp(inicio)]


YfinanceService.buscarHistoricoDesde = buscarHistoricoDesde
YfinanceService.buscarInfo = lambda self, item: StockEntity(item=item, nome=f"Empresa {item}", setor="Energia",
                                                           descricao="Company.")
YfinanceService.buscarInfoAtivo = lambda self, item: {"item": item, "nome": f"Empresa {item}", "setor": "Energia"}

historicosVistos = []
calcularOriginal = IndicatorsService.calcular


def calcularEspiao(self, item, historico, periodo=None):
    historicosVistos.append(historico.index.max())
    return calcularOriginal(self, item, historico, periodo)


IndicatorsService.calcular = calcularEspiao


class FakeIa:
    def __init__(self, falharNa=None):
        self.chamadas = []
        self.falharNa = falharNa

    def modelo(self):
        return "nvidia/nemotron-3.5-super-vl:free"

    def gerarRecomendacao(self, stock, ind):
        self.chamadas.append(ind)
        if self.falharNa is not None and len(self.chamadas) == self.falharNa:
            raise RuntimeError("Limite de uso do modelo gratuito atingido no OpenRouter. Tente amanhã.")
        rec = ["COMPRA", "VENDA", "MANTER"][len(self.chamadas) % 3]
        return RecomendacoesEntity(item=ind.item, data_referencia=ind.data_referencia, preco_atual=ind.preco_atual,
                                   recomendacao=rec, justificativa="j", riscos="- r", resposta_completa="{}")


def rodar(argv, ia):
    saida = io.StringIO()
    with redirect_stdout(saida):
        codigo = AvaliarIA.main(argv, servicoIa=ia)
    return codigo, saida.getvalue()


# DI3 — datas e uso só de dados até a data
indice = serieAtivo("PETR4").index
candidatos = indice[indice >= indice[-1] - pd.DateOffset(months=12)]
candidatos = candidatos[candidatos <= indice[-1 - 20]]
esperadas = list(candidatos[::10])
assert [d.date() for d in AvaliarIA.datasAvaliacao(indice, meses=12, intervalo=10, horizonte=20)] == \
    [d.date() for d in esperadas]
ia = FakeIa()
historicosVistos.clear()
codigo, saida = rodar(["--ativos", "PETR4", "--meses", "12", "--intervalo", "10", "--periodo", "1y",
                       "--limite", "500", "--pausa", "0"], ia)
assert codigo == 0, saida
assert [c.data_referencia for c in ia.chamadas] == [str(d.date()) for d in esperadas], ia.chamadas[:3]
assert [h.date() for h in historicosVistos] == [d.date() for d in esperadas], "histórico termina na data avaliada"
with Session() as s:
    assert s.query(AvaliacoesIaEntity).filter_by(item="PETR4", periodo="1y").count() == len(esperadas)
    linha = s.query(AvaliacoesIaEntity).first()
    assert linha.modelo == "nvidia/nemotron-3.5-super-vl:free" and linha.provedor == "openrouter"
passo(f"DI3 {len(esperadas)} datas (1 a cada 10 pregões, 12 meses, sem os últimos 20); IA só vê dados até cada data")

# DI4 — retomável
ia2 = FakeIa()
codigo, saida = rodar(["--ativos", "PETR4", "--meses", "12", "--intervalo", "10", "--periodo", "1y",
                       "--limite", "500", "--pausa", "0"], ia2)
assert codigo == 0 and ia2.chamadas == [], len(ia2.chamadas)
assert "puladas" in saida.lower(), saida
passo("DI4 rodar de novo não chama a IA para o que já foi gravado")

# DI5 — limite de chamadas e parada no limite de uso da IA
ia3 = FakeIa()
codigo, saida = rodar(["--ativos", "VALE3", "--limite", "3", "--pausa", "0"], ia3)
assert codigo == 0 and len(ia3.chamadas) == 3, (codigo, len(ia3.chamadas))
ia4 = FakeIa(falharNa=2)
codigo, saida = rodar(["--ativos", "ITUB4", "--limite", "50", "--pausa", "0"], ia4)
assert codigo == 2 and len(ia4.chamadas) == 2, (codigo, len(ia4.chamadas), saida)
assert "continuar" in saida.lower(), saida
with Session() as s:
    assert s.query(AvaliacoesIaEntity).filter_by(item="ITUB4").count() == 1
    assert s.query(AvaliacoesIaEntity).filter_by(item="VALE3").count() == 3
passo("DI5 --limite 3 faz 3 chamadas; limite de uso da IA para o script (código 2), guarda o feito e orienta continuar")

# DI6 — fontes: histórico (avaliacoes_ia) e app (recomendacoes)
ItensB3Service().obterOuCadastrar("BBAS3")
serieB = serieAtivo("BBAS3")
dataApp = serieB.index[-60]
precoApp = float(serieB["Close"].iloc[-60])
futuro = float(serieB["Close"].iloc[-40])
with Session() as s:
    s.add(RecomendacoesEntity(item="BBAS3", data_referencia=str(dataApp.date()), periodo="1y", preco_atual=precoApp,
                              recomendacao="COMPRA", justificativa="j", riscos="- r", resposta_completa="{}"))
    s.add(RecomendacoesEntity(item="BBAS3", data_referencia=str(serieB.index[-5].date()), periodo="1y",
                              preco_atual=float(serieB["Close"].iloc[-5]), recomendacao="VENDA",
                              justificativa="j", riscos="- r", resposta_completa="{}"))
    s.commit()
app = servico.avaliar("app")
assert {c["item"] for c in app["casos"]} == {"BBAS3"} and app["resumo"]["pendentes"] == 1, app["resumo"]
caso = next(c for c in app["casos"] if c["retornoPct"] is not None)
assert perto(caso["retornoPct"], (futuro / round(precoApp, 2) - 1) * 100, 0.02), (caso, futuro, precoApp)
historico = servico.avaliar("historico")
assert {c["item"] for c in historico["casos"]} == {"PETR4", "VALE3", "ITUB4"}
assert historico["resumo"]["total"] == len(esperadas) + 3 + 1, historico["resumo"]
passo("DI6 fonte 'app' lê recomendacoes (com retorno 20 pregões depois); fonte 'historico' lê avaliacoes_ia")

print(f"\n{len(ok)} critérios do desempenho da IA passaram")
