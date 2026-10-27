from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from src.models.base import Base, agora


class TipoRecomendacao(str, Enum):
    COMPRA = "COMPRA"
    VENDA = "VENDA"
    MANTER = "MANTER"


class RecomendacoesEntity(Base):
    __tablename__ = "recomendacoes"
    __table_args__ = (Index("ix_recomendacoes_item_data", "item", "data_referencia"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    item = Column(String(20), ForeignKey("itens_b3.item"), nullable=False)
    data_referencia = Column(String(10), nullable=False)
    preco_atual = Column(Numeric(10, 2))
    rsi = Column(Numeric(6, 2))
    sinal_rsi = Column(String(20))
    macd = Column(Numeric(10, 4))
    macd_signal = Column(Numeric(10, 4))
    macd_cruzamento = Column(String(10))
    sma20 = Column(Numeric(10, 2))
    sma50 = Column(Numeric(10, 2))
    tendencia_sma = Column(String(10))
    recomendacao = Column(String(10), nullable=False)
    justificativa = Column(Text)
    riscos = Column(Text)
    resposta_completa = Column(Text)
    gerado_em = Column(DateTime, default=agora)

    item_ativo = relationship("ItensB3Entity")

    def getId(self) -> int:
        return self.id

    def getItem(self) -> str:
        return self.item

    def getItemAtivo(self):
        return self.item_ativo

    def getDataReferencia(self) -> str:
        return self.data_referencia

    def getPrecoAtual(self) -> float:
        return self.preco_atual

    def setPrecoAtual(self, precoAtual: float) -> None:
        self.preco_atual = precoAtual

    def getRsi(self) -> float:
        return self.rsi

    def setRsi(self, rsi: float) -> None:
        self.rsi = rsi

    def getSinalRsi(self) -> str:
        return self.sinal_rsi

    def setSinalRsi(self, sinalRsi: str) -> None:
        self.sinal_rsi = sinalRsi

    def getMacd(self) -> float:
        return self.macd

    def setMacd(self, macd: float) -> None:
        self.macd = macd

    def getMacdSignal(self) -> float:
        return self.macd_signal

    def setMacdSignal(self, macdSignal: float) -> None:
        self.macd_signal = macdSignal

    def getMacdCruzamento(self) -> str:
        return self.macd_cruzamento

    def setMacdCruzamento(self, macdCruzamento: str) -> None:
        self.macd_cruzamento = macdCruzamento

    def getSma20(self) -> float:
        return self.sma20

    def setSma20(self, sma20: float) -> None:
        self.sma20 = sma20

    def getSma50(self) -> float:
        return self.sma50

    def setSma50(self, sma50: float) -> None:
        self.sma50 = sma50

    def getTendenciaSma(self) -> str:
        return self.tendencia_sma

    def setTendenciaSma(self, tendenciaSma: str) -> None:
        self.tendencia_sma = tendenciaSma

    def getRecomendacao(self) -> str:
        return self.recomendacao

    def setRecomendacao(self, recomendacao: str) -> None:
        self.recomendacao = recomendacao

    def getJustificativa(self) -> str:
        return self.justificativa

    def setJustificativa(self, justificativa: str) -> None:
        self.justificativa = justificativa

    def getRiscos(self) -> str:
        return self.riscos

    def setRiscos(self, riscos: str) -> None:
        self.riscos = riscos

    def getRespostaCompleta(self) -> str:
        return self.resposta_completa

    def setRespostaCompleta(self, respostaCompleta: str) -> None:
        self.resposta_completa = respostaCompleta

    def getGeradoEm(self) -> datetime:
        return self.gerado_em

    def paraDicionario(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
