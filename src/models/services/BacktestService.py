import logging
import numpy as np
import pandas as pd
from src.models.base import Session
from src.models.entities.OperacoesEntity import OperacoesEntity
from src.models.services.YfinanceService import YfinanceService
from src.models.services.IndicatorsService import IndicatorsService
from src.models.services.ItensB3Service import ItensB3Service
from src.models.Parametros import RSI_OVERBOUGHT, CUSTO_OPERACAO_PCT, SIMBOLO_IBOVESPA

logger = logging.getLogger(__name__)

DIAS_UTEIS_ANO = 252


class BacktestService:
    """Simula a estratégia MACD + RSI no período (spec backtesting.md).

    Custos: CUSTO_OPERACAO_PCT em cada compra e em cada venda. Uma posição ainda
    aberta no último pregão é encerrada pelo fechamento desse dia (emAberto).
    """

    def __init__(self, custoPct: float = None):
        self.custoPct = CUSTO_OPERACAO_PCT if custoPct is None else custoPct
        if not 0 <= self.custoPct < 100:
            raise ValueError("CUSTO_OPERACAO_PCT deve estar entre 0 e 100 (percentual por operação).")
        self.yfinanceService = YfinanceService()
        self.indicatorsService = IndicatorsService()
        self.itensB3Service = ItensB3Service()

    @property
    def custo(self) -> float:
        return self.custoPct / 100

    def executar(self, item: str, periodo: str = "1y", usuarioId: int = None) -> dict:
        item = self.itensB3Service.normalizar(item)
        self.itensB3Service.validarFormato(item)

        historico = self.yfinanceService.buscarHistorico(item, periodo)
        self.indicatorsService.calcular(item, historico, periodo)  # valida histórico suficiente
        dados = self.indicatorsService.calcularSerie(historico).dropna()
        inicio = self.indicatorsService.inicioPeriodo(historico, periodo)
        noPeriodo = dados[dados.index >= inicio]

        operacoes = self.simular(item, dados, inicio)
        metricas = self.calcularMetricas(operacoes, noPeriodo)
        metricas["retornoIbovespa"] = self.retornoIbovespa(noPeriodo, periodo)
        persistido = self.salvarOperacoes(usuarioId, item, operacoes) if usuarioId else False

        return {
            "item": item,
            "periodo": periodo,
            "operacoes": operacoes,
            "metricas": metricas,
            "curvaAcumulada": self.curvaAcumulada(operacoes),
            "pregoesSimulados": len(noPeriodo),
            "persistido": persistido,
        }

    def retornoIbovespa(self, noPeriodo: pd.DataFrame, periodo: str):
        try:
            indice = self.yfinanceService.buscarHistoricoIndice(SIMBOLO_IBOVESPA, periodo)
            comparacao = self.indicatorsService.compararIndice(noPeriodo, indice)
        except Exception as erro:
            logger.warning("Ibovespa indisponível no backtesting: %r", erro)
            return None
        return comparacao["retornoPct"] if comparacao else None

    def resultadoLiquido(self, precoEntrada: float, precoSaida: float) -> float:
        return round(((precoSaida * (1 - self.custo)) / (precoEntrada * (1 + self.custo)) - 1) * 100, 2)

    def simular(self, item: str, dados: pd.DataFrame, inicio=None) -> list:
        operacoes = []
        emPosicao, precoEntrada, dataEntrada = False, None, None
        primeiro = 1
        if inicio is not None:
            primeiro = max(1, int((dados.index < inicio).sum()))

        for i in range(primeiro, len(dados)):
            atual, anterior = dados.iloc[i], dados.iloc[i - 1]

            compra = (
                anterior["MACD"] <= anterior["MACD_Sig"]
                and atual["MACD"] > atual["MACD_Sig"]
                and atual["RSI"] < RSI_OVERBOUGHT
            )
            venda = (
                anterior["MACD"] >= anterior["MACD_Sig"] and atual["MACD"] < atual["MACD_Sig"]
            ) or atual["RSI"] > RSI_OVERBOUGHT

            if compra and not emPosicao:
                emPosicao = True
                precoEntrada = float(atual["Close"])
                dataEntrada = dados.index[i].date()
            elif venda and emPosicao:
                operacoes.append(self.operacao(item, dataEntrada, precoEntrada, dados.index[i].date(),
                                               float(atual["Close"]), emAberto=False))
                emPosicao = False

        if emPosicao:
            operacoes.append(self.operacao(item, dataEntrada, precoEntrada, dados.index[-1].date(),
                                           float(dados["Close"].iloc[-1]), emAberto=True))
        return operacoes

    def operacao(self, item, dataEntrada, precoEntrada, dataSaida, precoSaida, emAberto: bool) -> dict:
        return {
            "item": item,
            "dataEntrada": dataEntrada,
            "precoEntrada": round(precoEntrada, 2),
            "dataSaida": dataSaida,
            "precoSaida": round(precoSaida, 2),
            "resultadoPct": self.resultadoLiquido(precoEntrada, precoSaida),
            "emAberto": emAberto,
        }

    def retornosDiarios(self, operacoes: list, dados: pd.DataFrame) -> pd.Series:
        """Um retorno por pregão do período, a partir do 2º (backtesting.md, Definições)."""
        fechamentos = dados["Close"].astype(float)
        datas = [d.date() for d in dados.index]
        posicao = {d: i for i, d in enumerate(datas)}
        retornos = np.zeros(len(datas))

        for op in operacoes:
            iEntrada, iSaida = posicao.get(op["dataEntrada"]), posicao.get(op["dataSaida"])
            if iEntrada is None or iSaida is None:
                continue
            if iEntrada == iSaida:
                retornos[iEntrada] += (1 - self.custo) / (1 + self.custo) - 1
                continue
            retornos[iEntrada] += 1 / (1 + self.custo) - 1
            for i in range(iEntrada + 1, iSaida + 1):
                variacao = fechamentos.iloc[i] / fechamentos.iloc[i - 1]
                if i == iSaida:
                    variacao *= 1 - self.custo
                retornos[i] += variacao - 1

        return pd.Series(retornos[1:], index=dados.index[1:])

    def sharpe(self, retornos: pd.Series) -> float:
        if len(retornos) < 2:
            return 0.0
        desvio = float(retornos.std(ddof=1))
        if not desvio or np.isnan(desvio) or desvio < 1e-12:
            return 0.0
        return round(float(retornos.mean()) / desvio * float(np.sqrt(DIAS_UTEIS_ANO)), 2)

    def buyAndHold(self, dados: pd.DataFrame) -> float:
        if len(dados) < 2:
            return 0.0
        return self.resultadoLiquido(float(dados["Close"].iloc[0]), float(dados["Close"].iloc[-1]))

    def calcularMetricas(self, operacoes: list, dados: pd.DataFrame) -> dict:
        buyHold = self.buyAndHold(dados)
        if not operacoes:
            return {
                "totalOperacoes": 0,
                "taxaAcerto": 0.0,
                "retornoAcumulado": 0.0,
                "retornoBuyHold": buyHold,
                "drawdownMaximo": 0.0,
                "sharpe": 0.0,
                "custoOperacaoPct": self.custoPct,
            }

        retornos = pd.Series([op["resultadoPct"] for op in operacoes])
        acumulado = (1 + retornos / 100).cumprod()
        drawdown = ((acumulado - acumulado.cummax()) / acumulado.cummax() * 100).min()

        return {
            "totalOperacoes": len(operacoes),
            "taxaAcerto": round(float((retornos > 0).mean() * 100), 2),
            "retornoAcumulado": round(float((acumulado.iloc[-1] - 1) * 100), 2),
            "retornoBuyHold": buyHold,
            "drawdownMaximo": round(float(drawdown), 2),
            "sharpe": self.sharpe(self.retornosDiarios(operacoes, dados)),
            "custoOperacaoPct": self.custoPct,
        }

    def curvaAcumulada(self, operacoes: list) -> list:
        acumulado = 1.0
        curva = []
        for op in operacoes:
            acumulado *= 1 + op["resultadoPct"] / 100
            curva.append(round((acumulado - 1) * 100, 2))
        return curva

    def salvarOperacoes(self, usuarioId: int, item: str, operacoes: list) -> bool:
        try:
            with Session() as session:
                session.query(OperacoesEntity).filter_by(usuario_id=usuarioId, item=item).delete()
                for op in operacoes:
                    session.add(
                        OperacoesEntity(
                            usuario_id=usuarioId,
                            item=item,
                            data_entrada=op["dataEntrada"],
                            preco_entrada=op["precoEntrada"],
                            data_saida=op["dataSaida"],
                            preco_saida=op["precoSaida"],
                            resultado_pct=op["resultadoPct"],
                        )
                    )
                session.commit()
            return True
        except Exception:
            logger.exception("Falha ao salvar as operações do backtest de %s", item)
            return False
