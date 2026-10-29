import pandas as pd
from src.models.base import Session
from src.models.entities.OperacoesEntity import OperacoesEntity
from src.models.services.YfinanceService import YfinanceService
from src.models.services.IndicatorsService import IndicatorsService
from src.models.services.ItensB3Service import ItensB3Service
from src.models.Parametros import RSI_OVERBOUGHT


class BacktestService:

    def __init__(self):
        self.yfinanceService = YfinanceService()
        self.indicatorsService = IndicatorsService()
        self.itensB3Service = ItensB3Service()

    def executar(self, item: str, periodo: str = "1y", usuarioId: int = None) -> dict:
        item = self.itensB3Service.normalizar(item)
        self.itensB3Service.validarFormato(item)

        historico = self.yfinanceService.buscarHistorico(item, periodo)
        indicadores = self.indicatorsService.calcular(item, historico)
        dados = indicadores.historico

        operacoes = self.simular(item, dados)
        metricas = self.calcularMetricas(operacoes, dados)
        persistido = self.salvarOperacoes(usuarioId, item, operacoes) if usuarioId else False

        return {
            "item": item,
            "periodo": periodo,
            "operacoes": operacoes,
            "metricas": metricas,
            "curvaAcumulada": self.curvaAcumulada(operacoes),
            "persistido": persistido,
        }

    def simular(self, item: str, dados: pd.DataFrame) -> list:
        operacoes = []
        emPosicao, precoEntrada, dataEntrada = False, None, None

        for i in range(1, len(dados)):
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
                precoSaida = float(atual["Close"])
                operacoes.append(
                    {
                        "item": item,
                        "dataEntrada": dataEntrada,
                        "precoEntrada": round(precoEntrada, 2),
                        "dataSaida": dados.index[i].date(),
                        "precoSaida": round(precoSaida, 2),
                        "resultadoPct": round((precoSaida - precoEntrada) / precoEntrada * 100, 2),
                    }
                )
                emPosicao = False

        return operacoes

    def buyAndHold(self, dados: pd.DataFrame) -> float:
        if len(dados) < 2:
            return 0.0
        inicio, fim = float(dados["Close"].iloc[0]), float(dados["Close"].iloc[-1])
        return round((fim - inicio) / inicio * 100, 2)

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
            }

        retornos = pd.Series([op["resultadoPct"] for op in operacoes])
        acumulado = (1 + retornos / 100).cumprod()
        drawdown = ((acumulado - acumulado.cummax()) / acumulado.cummax() * 100).min()
        desvio = retornos.std()

        return {
            "totalOperacoes": len(operacoes),
            "taxaAcerto": round(float((retornos > 0).mean() * 100), 2),
            "retornoAcumulado": round(float((acumulado.iloc[-1] - 1) * 100), 2),
            "retornoBuyHold": buyHold,
            "drawdownMaximo": round(float(drawdown), 2),
            "sharpe": round(float(retornos.mean() / desvio), 2) if desvio > 0 else 0.0,
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
            return False
