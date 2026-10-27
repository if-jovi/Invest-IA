from sqlalchemy import Column, String, Boolean
from src.models.base import Base


class ItensB3Entity(Base):
    __tablename__ = "itens_b3"

    item = Column(String(10), primary_key=True)
    nome = Column(String(150), nullable=False)
    setor = Column(String(100), default="Não disponível")
    ativo = Column(Boolean, default=True)

    def getItem(self) -> str:
        return self.item

    def getNome(self) -> str:
        return self.nome

    def setNome(self, nome: str) -> None:
        self.nome = nome

    def getSetor(self) -> str:
        return self.setor

    def setSetor(self, setor: str) -> None:
        self.setor = setor

    def isAtivo(self) -> bool:
        return self.ativo

    def setAtivo(self, ativo: bool) -> None:
        self.ativo = ativo

    def paraDicionario(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
