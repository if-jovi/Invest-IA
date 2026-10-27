from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class StockEntity:
    item: str
    nome: str = "Não disponível"
    setor: str = "Não disponível"
    segmento: str = "Não disponível"
    descricao: str = "Não disponível"
    preco_atual: Optional[float] = None
    moeda: str = "BRL"
    pais: str = "Brasil"
    site: str = ""

    def paraDicionario(self) -> dict:
        return self.__dict__.copy()


@dataclass
class IndicatorsEntity:
    item: str
    data_referencia: str
    preco_atual: float
    rsi: float = 0.0
    sinal_rsi: str = "neutro"
    macd: float = 0.0
    macd_signal: float = 0.0
    macd_hist: float = 0.0
    macd_cruzamento: str = "neutro"
    sma_short: float = 0.0
    sma_long: float = 0.0
    tendencia_sma: str = "neutro"
    historico: Optional[pd.DataFrame] = field(default=None, repr=False)

    def paraDicionario(self) -> dict:
        dados = self.__dict__.copy()
        dados.pop("historico", None)
        return dados
