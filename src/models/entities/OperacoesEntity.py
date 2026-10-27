from datetime import date
from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import Base


class OperacoesEntity(Base):
    __tablename__ = "operacoes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    item = Column(String(20), nullable=False)
    data_entrada = Column(Date)
    preco_entrada = Column(Numeric(10, 2))
    data_saida = Column(Date)
    preco_saida = Column(Numeric(10, 2))
    resultado_pct = Column(Numeric(6, 2))

    usuario = relationship("UsuariosEntity", back_populates="operacao")

    def getId(self) -> int:
        return self.id

    def getUsuarioId(self) -> int:
        return self.usuario_id

    def getItem(self) -> str:
        return self.item

    def getDataEntrada(self) -> date:
        return self.data_entrada

    def setDataEntrada(self, dataEntrada: date) -> None:
        self.data_entrada = dataEntrada

    def getPrecoEntrada(self) -> float:
        return self.preco_entrada

    def setPrecoEntrada(self, precoEntrada: float) -> None:
        self.preco_entrada = precoEntrada

    def getDataSaida(self) -> date:
        return self.data_saida

    def setDataSaida(self, dataSaida: date) -> None:
        self.data_saida = dataSaida

    def getPrecoSaida(self) -> float:
        return self.preco_saida

    def setPrecoSaida(self, precoSaida: float) -> None:
        self.preco_saida = precoSaida

    def getResultadoPct(self) -> float:
        return self.resultado_pct

    def setResultadoPct(self, resultadoPct: float) -> None:
        self.resultado_pct = resultadoPct

    def isLucrativa(self) -> bool:
        return float(self.resultado_pct or 0) > 0

    def paraDicionario(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
