"""Taxa de acerto das recomendações da IA (spec desempenho-ia.md).

Para cada recomendação, confere o fechamento HORIZONTE_AVALIACAO pregões depois
e calcula acerto, acerto contra o Ibovespa, taxa base, intervalo de confiança
(Wilson) e teste binomial contra a taxa base.
"""
import logging
import math
from datetime import date
from typing import Optional, Tuple

import pandas as pd

from src.models.base import Session
from src.models.entities.AvaliacoesIaEntity import AvaliacoesIaEntity
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity
from src.models.Parametros import FAIXA_MANTER_PCT, HORIZONTE_AVALIACAO, SIMBOLO_IBOVESPA
from src.models.services.YfinanceService import YfinanceService

logger = logging.getLogger(__name__)

TIPOS = ("COMPRA", "VENDA", "MANTER")
FONTES = {"historico": "Avaliação histórica", "app": "Uso no app"}
Z_95 = 1.96


def intervaloWilson(acertos: int, n: int, z: float = Z_95) -> Optional[Tuple[float, float]]:
    """Intervalo de confiança de Wilson para uma proporção (valores entre 0 e 1)."""
    if n <= 0:
        return None
    p = acertos / n
    denominador = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / denominador
    margem = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominador
    return max(0.0, centro - margem), min(1.0, centro + margem)


def pValorBinomial(acertos: int, n: int, p: float) -> Optional[float]:
    """P(X >= acertos) para X ~ Binomial(n, p): chance de acertar tanto por acaso."""
    if n <= 0 or p is None:
        return None
    return float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(acertos, n + 1)))


def percentual(acertos: int, n: int) -> Optional[float]:
    return round(acertos / n * 100, 2) if n else None


def media(valores: list) -> Optional[float]:
    return round(sum(valores) / len(valores), 2) + 0.0 if valores else None


def diaSemFuso(valor) -> date:
    ts = pd.Timestamp(valor)
    return (ts.tz_localize(None) if ts.tzinfo is not None else ts).date()


class DesempenhoIaService:

    def __init__(self, yfinance: YfinanceService = None):
        self.yfinanceService = yfinance or YfinanceService()

    # --- regras ------------------------------------------------------------------------
    @staticmethod
    def retornoFuturo(precoReferencia: float, precoFuturo: float) -> float:
        return round((float(precoFuturo) / float(precoReferencia) - 1) * 100, 2) + 0.0

    @staticmethod
    def avaliarCaso(recomendacao: str, retornoPct: float, retornoIbovespaPct: float = None) -> dict:
        if recomendacao == "COMPRA":
            acerto = retornoPct > 0
        elif recomendacao == "VENDA":
            acerto = retornoPct < 0
        else:
            acerto = abs(retornoPct) <= FAIXA_MANTER_PCT

        acertoIbovespa = None
        if retornoIbovespaPct is not None and recomendacao in ("COMPRA", "VENDA"):
            acertoIbovespa = retornoPct > retornoIbovespaPct if recomendacao == "COMPRA" \
                else retornoPct < retornoIbovespaPct
        return {"acerto": acerto, "acertoIbovespa": acertoIbovespa}

    @staticmethod
    def taxa(acertos: int, n: int) -> dict:
        ic = intervaloWilson(acertos, n)
        return {
            "acertos": acertos,
            "n": n,
            "taxa": percentual(acertos, n),
            "ic": (round(ic[0] * 100, 2), round(ic[1] * 100, 2)) if ic else None,
        }

    def agregar(self, casos: list) -> dict:
        avaliados = [c for c in casos if c.get("retornoPct") is not None]
        for c in avaliados:
            c.update(self.avaliarCaso(c["recomendacao"], c["retornoPct"], c.get("retornoIbovespaPct")))

        porTipo = {}
        for tipo in TIPOS:
            doTipo = [c for c in avaliados if c["recomendacao"] == tipo]
            porTipo[tipo] = self.taxa(sum(c["acerto"] for c in doTipo), len(doTipo))
            porTipo[tipo]["retornoMedio"] = media([c["retornoPct"] for c in doTipo])

        n = len(avaliados)
        subidas = sum(c["retornoPct"] > 0 for c in avaliados)
        taxaBase = subidas / n if n else None
        compra = porTipo["COMPRA"]
        comIbovespa = [c for c in avaliados if c.get("acertoIbovespa") is not None]

        return {
            "total": n,
            "pendentes": len(casos) - n,
            "geral": self.taxa(sum(c["acerto"] for c in avaliados), n),
            "porTipo": porTipo,
            "taxaBase": round(taxaBase * 100, 2) if taxaBase is not None else None,
            "pValorCompra": pValorBinomial(compra["acertos"], compra["n"], taxaBase) if taxaBase is not None else None,
            "contraIbovespa": self.taxa(sum(c["acertoIbovespa"] for c in comIbovespa), len(comIbovespa)),
            "retornoMedioGeral": media([c["retornoPct"] for c in avaliados]),
        }

    # --- dados -------------------------------------------------------------------------
    def carregar(self, fonte: str) -> list:
        if fonte not in FONTES:
            raise ValueError("Fonte inválida. Use 'historico' ou 'app'.")
        with Session() as session:
            if fonte == "app":
                linhas = session.query(RecomendacoesEntity).all()
                return [{"item": r.item, "dataReferencia": diaSemFuso(r.data_referencia), "periodo": r.periodo,
                         "recomendacao": r.recomendacao, "preco": float(r.preco_atual)}
                        for r in linhas if r.preco_atual is not None]
            linhas = session.query(AvaliacoesIaEntity).all()
            return [{"item": r.item, "dataReferencia": diaSemFuso(r.data_referencia), "periodo": r.periodo,
                     "recomendacao": r.recomendacao, "preco": float(r.preco)} for r in linhas]

    def fechamentos(self, simbolo: str, inicio: date, indice: bool = False) -> Optional[pd.Series]:
        try:
            historico = self.yfinanceService.buscarHistoricoDesde(simbolo, inicio, indice=indice)
        except Exception as erro:
            logger.warning("Sem preços de %s para avaliar a IA: %r", simbolo, erro)
            return None
        if historico is None or len(historico) == 0:
            return None
        serie = historico["Close"].dropna().astype(float)
        serie.index = [diaSemFuso(d) for d in serie.index]
        return serie

    @staticmethod
    def fechamentoEm(serie: pd.Series, dia: date) -> Optional[float]:
        """Último fechamento com data <= dia."""
        anteriores = serie[[d <= dia for d in serie.index]]
        return float(anteriores.iloc[-1]) if len(anteriores) else None

    def avaliar(self, fonte: str = "historico", horizonte: int = HORIZONTE_AVALIACAO) -> dict:
        casos = sorted(self.carregar(fonte), key=lambda c: (c["dataReferencia"], c["item"]))
        if not casos:
            return {"casos": [], "resumo": self.agregar([])}

        inicio = min(c["dataReferencia"] for c in casos) - pd.Timedelta(days=7)
        ibovespa = self.fechamentos(SIMBOLO_IBOVESPA, inicio, indice=True)
        series = {item: self.fechamentos(item, inicio) for item in {c["item"] for c in casos}}

        for caso in casos:
            caso.update({"retornoPct": None, "retornoIbovespaPct": None, "dataFutura": None})
            serie = series.get(caso["item"])
            if serie is None:
                continue
            datas = list(serie.index)
            posicao = next((i for i, d in enumerate(datas) if d >= caso["dataReferencia"]), None)
            if posicao is None or posicao + horizonte >= len(datas):
                continue  # pendente: o horizonte ainda não chegou
            futuro = datas[posicao + horizonte]
            caso["dataFutura"] = futuro
            caso["retornoPct"] = self.retornoFuturo(caso["preco"], serie.iloc[posicao + horizonte])
            if ibovespa is not None:
                antes = self.fechamentoEm(ibovespa, datas[posicao])
                depois = self.fechamentoEm(ibovespa, futuro)
                if antes and depois:
                    caso["retornoIbovespaPct"] = self.retornoFuturo(antes, depois)

        return {"casos": casos, "resumo": self.agregar(casos)}
