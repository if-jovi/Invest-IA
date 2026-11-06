import numpy as np
import pandas as pd
from src.models.entities.StockEntity import IndicatorsEntity
from src.models.Parametros import (
    RSI_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    SMA_SHORT,
    SMA_LONG,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    MESES_PERIODO,
)

MENSAGEM_HISTORICO = "Histórico insuficiente para calcular os indicadores. Escolha um período maior."


class IndicatorsService:

    def sma(self, fechamento: pd.Series, periodo: int) -> pd.Series:
        return fechamento.rolling(window=periodo).mean()

    def ema(self, serie: pd.Series, periodo: int) -> pd.Series:
        valores = serie.to_numpy(dtype=float)
        validos = ~np.isnan(valores)
        resultado = pd.Series(np.nan, index=serie.index)
        if not validos.any():
            return resultado

        inicio = int(validos.argmax())
        semente = inicio + periodo - 1
        if semente >= len(valores):
            return resultado

        base = valores.copy()
        base[:semente] = np.nan
        base[semente] = valores[inicio : semente + 1].mean()
        return pd.Series(base, index=serie.index).ewm(span=periodo, adjust=False).mean()

    def rsi(self, fechamento: pd.Series, periodo: int) -> pd.Series:
        variacao = fechamento.diff()
        ganhos = variacao.clip(lower=0)
        perdas = (-variacao).clip(lower=0)
        mediaGanhos = ganhos.ewm(alpha=1 / periodo, adjust=False).mean()
        mediaPerdas = perdas.ewm(alpha=1 / periodo, adjust=False).mean()
        return 100 * mediaGanhos / (mediaGanhos + mediaPerdas)

    def macd(self, fechamento: pd.Series, rapida: int, lenta: int, sinal: int) -> pd.DataFrame:
        linha = self.ema(fechamento, rapida) - self.ema(fechamento, lenta)
        linhaSinal = self.ema(linha, sinal)
        return pd.DataFrame({"MACD": linha, "MACD_Sig": linhaSinal, "MACD_Hist": linha - linhaSinal})

    @staticmethod
    def resumirPeriodo(historico: pd.DataFrame) -> dict:
        fechamentos = historico["Close"].dropna().astype(float)
        primeiro, ultimo = float(fechamentos.iloc[0]), float(fechamentos.iloc[-1])
        maxima, minima = float(fechamentos.max()), float(fechamentos.min())
        retornos = fechamentos.pct_change(fill_method=None).dropna()
        desvio = float(retornos.std(ddof=1)) if len(retornos) > 1 else 0.0
        drawdown = float((fechamentos / fechamentos.cummax() - 1).min())

        def arredondar(valor: float) -> float:
            valor = round(float(valor), 2)
            return 0.0 if valor == 0 or np.isnan(valor) else valor

        return {
            "retornoPct": arredondar((ultimo / primeiro - 1) * 100),
            "maxima": arredondar(maxima),
            "minima": arredondar(minima),
            "distanciaMaximaPct": arredondar((ultimo / maxima - 1) * 100),
            "distanciaMinimaPct": arredondar((ultimo / minima - 1) * 100),
            "volatilidadeAnualPct": arredondar(desvio * np.sqrt(252) * 100),
            "drawdownMaximoPct": arredondar(drawdown * 100),
        }

    @staticmethod
    def inicioPeriodo(historico: pd.DataFrame, periodo: str) -> pd.Timestamp:
        """1º pregão com data >= último pregão - N meses (historico-aquecimento.md)."""
        limite = historico.index[-1] - pd.DateOffset(months=MESES_PERIODO[periodo])
        return historico.index[historico.index >= limite][0]

    def recortarPeriodo(self, historico: pd.DataFrame, periodo: str) -> pd.DataFrame:
        if not periodo:
            return historico
        return historico[historico.index >= self.inicioPeriodo(historico, periodo)]

    def calcularSerie(self, historico: pd.DataFrame) -> pd.DataFrame:
        """Indicadores dia a dia sobre o histórico inteiro (aquecimento + período)."""
        df = historico.copy()
        df["RSI"] = self.rsi(df["Close"], RSI_PERIOD)
        df = df.join(self.macd(df["Close"], MACD_FAST, MACD_SLOW, MACD_SIGNAL))
        df[f"SMA{SMA_SHORT}"] = self.sma(df["Close"], SMA_SHORT)
        df[f"SMA{SMA_LONG}"] = self.sma(df["Close"], SMA_LONG)
        return df

    @staticmethod
    def compararIndice(periodoAtivo: pd.DataFrame, indice) -> dict:
        """Retorno do índice no mesmo intervalo do período do ativo (comparacao-ibovespa.md)."""
        if indice is None or len(indice) == 0 or len(periodoAtivo) < 2:
            return None

        def dias(index):
            index = pd.DatetimeIndex(index)
            return (index.tz_localize(None) if index.tz is not None else index).normalize()

        fechamentosIndice = indice["Close"].dropna().astype(float)
        datasIndice = dias(fechamentosIndice.index)
        datasAtivo = dias(periodoAtivo.index)
        janela = fechamentosIndice[(datasIndice >= datasAtivo[0]) & (datasIndice <= datasAtivo[-1])]
        if len(janela) < 2:
            return None
        retornoIndice = (float(janela.iloc[-1]) / float(janela.iloc[0]) - 1) * 100
        fechamentosAtivo = periodoAtivo["Close"].dropna().astype(float)
        retornoAtivo = (float(fechamentosAtivo.iloc[-1]) / float(fechamentosAtivo.iloc[0]) - 1) * 100
        return {
            "retornoPct": round(retornoIndice, 2) + 0.0,
            "diferencaPct": round(retornoAtivo - retornoIndice, 2) + 0.0,
        }

    def calcular(self, item: str, historico: pd.DataFrame, periodo: str = None) -> IndicatorsEntity:
        if len(historico) < SMA_LONG + 2:
            raise ValueError(MENSAGEM_HISTORICO)
        noPeriodo = self.recortarPeriodo(historico, periodo)
        resumoPeriodo = self.resumirPeriodo(noPeriodo)

        completo = self.calcularSerie(historico).dropna()
        df = completo[completo.index >= noPeriodo.index[0]]
        if len(df) < 2:
            raise ValueError(MENSAGEM_HISTORICO)

        ultimo = df.iloc[-1]
        rsi = round(float(ultimo["RSI"]), 2)
        smaCurta = round(float(ultimo[f"SMA{SMA_SHORT}"]), 2)
        smaLonga = round(float(ultimo[f"SMA{SMA_LONG}"]), 2)

        return IndicatorsEntity(
            item=item.upper(),
            data_referencia=str(df.index[-1].date()),
            preco_atual=round(float(ultimo["Close"]), 2),
            rsi=rsi,
            sinal_rsi=self.sinalRsi(rsi),
            macd=round(float(ultimo["MACD"]), 4),
            macd_signal=round(float(ultimo["MACD_Sig"]), 4),
            macd_hist=round(float(ultimo["MACD_Hist"]), 4),
            macd_cruzamento=self.cruzamentoMacd(completo),
            sma_short=smaCurta,
            sma_long=smaLonga,
            tendencia_sma="alta" if smaCurta > smaLonga else "baixa",
            historico=df,
            periodo=periodo,
            resumo_periodo=resumoPeriodo,
        )

    def sinalRsi(self, rsi: float) -> str:
        if rsi > RSI_OVERBOUGHT:
            return "sobrecompra"
        if rsi < RSI_OVERSOLD:
            return "sobrevenda"
        return "neutro"

    def cruzamentoMacd(self, df: pd.DataFrame) -> str:
        if len(df) < 2:
            return "neutro"
        macdHoje, sinalHoje = df["MACD"].iloc[-1], df["MACD_Sig"].iloc[-1]
        macdAntes, sinalAntes = df["MACD"].iloc[-2], df["MACD_Sig"].iloc[-2]
        if macdAntes <= sinalAntes and macdHoje > sinalHoje:
            return "alta"
        if macdAntes >= sinalAntes and macdHoje < sinalHoje:
            return "baixa"
        return "alta" if macdHoje > sinalHoje else "baixa"
