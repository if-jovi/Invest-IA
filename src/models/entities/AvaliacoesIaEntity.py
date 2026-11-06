from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from src.models.base import Base, DataIso, agora


class AvaliacoesIaEntity(Base):
    """Recomendação da IA para uma data passada (avaliação histórica, spec desempenho-ia.md)."""

    __tablename__ = "avaliacoes_ia"
    __table_args__ = (
        UniqueConstraint("item", "data_referencia", "periodo", "modelo", name="uq_avaliacoes_ia_item_data"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    item = Column(String(20), nullable=False)
    data_referencia = Column(DataIso, nullable=False)
    periodo = Column(String(3), nullable=False)
    recomendacao = Column(String(10), nullable=False)
    preco = Column(Numeric(10, 2), nullable=False)
    provedor = Column(String(20))
    modelo = Column(String(120), nullable=False)
    resposta_completa = Column(Text)
    gerado_em = Column(DateTime, default=agora)
