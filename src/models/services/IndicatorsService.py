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

    def calcular(self, item: str, historico: pd.DataFrame) -> IndicatorsEntity:
        if len(historico) < SMA_LONG + 2:
            raise ValueError(MENSAGEM_HISTORICO)

        df = historico.copy()
        df["RSI"] = self.rsi(df["Close"], RSI_PERIOD)
        df = df.join(self.macd(df["Close"], MACD_FAST, MACD_SLOW, MACD_SIGNAL))
        df[f"SMA{SMA_SHORT}"] = self.sma(df["Close"], SMA_SHORT)
        df[f"SMA{SMA_LONG}"] = self.sma(df["Close"], SMA_LONG)

        df = df.dropna()
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
            macd_cruzamento=self.cruzamentoMacd(df),
            sma_short=smaCurta,
            sma_long=smaLonga,
            tendencia_sma="alta" if smaCurta > smaLonga else "baixa",
            historico=df,
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
