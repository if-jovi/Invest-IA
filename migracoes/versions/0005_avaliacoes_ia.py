"""Tabela avaliacoes_ia: recomendações da IA para datas passadas (spec desempenho-ia.md).

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "avaliacoes_ia",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("item", sa.String(20), nullable=False),
        sa.Column("data_referencia", sa.Date, nullable=False),
        sa.Column("periodo", sa.String(3), nullable=False),
        sa.Column("recomendacao", sa.String(10), nullable=False),
        sa.Column("preco", sa.Numeric(10, 2), nullable=False),
        sa.Column("provedor", sa.String(20)),
        sa.Column("modelo", sa.String(120), nullable=False),
        sa.Column("resposta_completa", sa.Text),
        sa.Column("gerado_em", sa.DateTime),
        sa.UniqueConstraint("item", "data_referencia", "periodo", "modelo", name="uq_avaliacoes_ia_item_data"),
    )


def downgrade() -> None:
    op.drop_table("avaliacoes_ia")
