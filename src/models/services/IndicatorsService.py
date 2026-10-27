import pandas as pd
import pandas_ta as ta
from src.models.entities.StockEntity import IndicatorsEntity
from config.settings import (
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

    def calcular(self, item: str, historico: pd.DataFrame) -> IndicatorsEntity:
        if len(historico) < SMA_LONG + 2:
            raise ValueError(MENSAGEM_HISTORICO)

        df = historico.copy()

        df["RSI"] = ta.rsi(df["Close"], length=RSI_PERIOD)

        macd = ta.macd(df["Close"], fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
        if macd is None:
            raise ValueError(MENSAGEM_HISTORICO)
        sufixo = f"{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"
        df["MACD"] = macd[f"MACD_{sufixo}"]
        df["MACD_Sig"] = macd[f"MACDs_{sufixo}"]
        df["MACD_Hist"] = macd[f"MACDh_{sufixo}"]

        df[f"SMA{SMA_SHORT}"] = ta.sma(df["Close"], length=SMA_SHORT)
        df[f"SMA{SMA_LONG}"] = ta.sma(df["Close"], length=SMA_LONG)

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
