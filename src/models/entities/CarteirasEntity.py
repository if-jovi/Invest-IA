from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import Base, agora


class CarteirasEntity(Base):
    __tablename__ = "carteiras"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True)
    nome = Column(String(100), nullable=False, default="Minha carteira")
    criado_em = Column(DateTime, default=agora)

    usuario = relationship("UsuariosEntity", back_populates="carteira")
    itens = relationship(
        "ItensCarteirasEntity", back_populates="carteira", cascade="all, delete-orphan"
    )

    def getId(self) -> int:
        return self.id

    def getUsuarioId(self) -> int:
        return self.usuario_id

    def getNome(self) -> str:
        return self.nome

    def setNome(self, nome: str) -> None:
        self.nome = nome

    def getCriadoEm(self) -> datetime:
        return self.criado_em

    def getItens(self) -> list:
        return self.itens

    def getValorInvestido(self) -> float:
        return sum(
            float(i.getQuantidade()) * float(i.getPrecoMedio()) for i in self.itens
        )

    def paraDicionario(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
