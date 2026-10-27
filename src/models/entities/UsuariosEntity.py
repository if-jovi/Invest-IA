from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from src.models.base import Base, agora


class UsuariosEntity(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    criado_em = Column(DateTime, default=agora)

    carteira = relationship(
        "CarteirasEntity", back_populates="usuario", uselist=False, cascade="all, delete-orphan"
    )
    operacao = relationship("OperacoesEntity", back_populates="usuario")

    def getId(self) -> int:
        return self.id

    def getNome(self) -> str:
        return self.nome

    def setNome(self, nome: str) -> None:
        self.nome = nome

    def getEmail(self) -> str:
        return self.email

    def setEmail(self, email: str) -> None:
        self.email = email

    def getSenhaHash(self) -> str:
        return self.senha_hash

    def setSenhaHash(self, senhaHash: str) -> None:
        self.senha_hash = senhaHash

    def getCriadoEm(self) -> datetime:
        return self.criado_em

    def getCarteira(self):
        return self.carteira

    def paraDicionario(self) -> dict:
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name != "senha_hash"
        }
