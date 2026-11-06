"""recomendacoes.periodo e cache por ativo + data + período (spec analise-periodo.md).

Recomendações antigas ficam com periodo nulo e nunca são reaproveitadas.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("recomendacoes", sa.Column("periodo", sa.String(3), nullable=True))
    op.drop_index("ix_recomendacoes_item_data", table_name="recomendacoes")
    op.create_index("ix_recomendacoes_item_data_periodo", "recomendacoes", ["item", "data_referencia", "periodo"])


def downgrade() -> None:
    op.drop_index("ix_recomendacoes_item_data_periodo", table_name="recomendacoes")
    op.create_index("ix_recomendacoes_item_data", "recomendacoes", ["item", "data_referencia"])
    with op.batch_alter_table("recomendacoes") as tabela:
        tabela.drop_column("periodo")
