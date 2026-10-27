from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.models.base import Base, agora


class ItensCarteirasEntity(Base):
    __tablename__ = "itens_carteiras"
    __table_args__ = (UniqueConstraint("carteira_id", "item", name="uq_carteira_item"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    carteira_id = Column(Integer, ForeignKey("carteiras.id"), nullable=False)
    item = Column(String(20), ForeignKey("itens_b3.item"), nullable=False)
    quantidade = Column(Numeric(14, 4), nullable=False, default=0)
    preco_medio = Column(Numeric(10, 2), nullable=False, default=0)
    atualizado_em = Column(DateTime, default=agora, onupdate=agora)

    carteira = relationship("CarteirasEntity", back_populates="itens")
    item_ativo = relationship("ItensB3Entity")

    def getId(self) -> int:
        return self.id

    def getCarteiraId(self) -> int:
        return self.carteira_id

    def getItem(self) -> str:
        return self.item

    def getItemAtivo(self):
        return self.item_ativo

    def getQuantidade(self) -> float:
        return self.quantidade

    def setQuantidade(self, quantidade: float) -> None:
        self.quantidade = quantidade

    def getPrecoMedio(self) -> float:
        return self.preco_medio

    def setPrecoMedio(self, precoMedio: float) -> None:
        self.preco_medio = precoMedio

    def getAtualizadoEm(self) -> datetime:
        return self.atualizado_em

    def registrarCompra(self, quantidade: float, precoUnitario: float) -> None:
        qtdAtual = float(self.getQuantidade() or 0)
        precoAtual = float(self.getPrecoMedio() or 0)
        novaQtd = qtdAtual + quantidade
        self.setPrecoMedio(
            ((qtdAtual * precoAtual) + (quantidade * precoUnitario)) / novaQtd
        )
        self.setQuantidade(novaQtd)

    def registrarVenda(self, quantidade: float) -> None:
        self.setQuantidade(float(self.getQuantidade() or 0) - quantidade)

    def paraDicionario(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
