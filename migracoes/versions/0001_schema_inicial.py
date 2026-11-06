"""Schema inicial: o mesmo que o create_all gerava antes do Alembic.

Bancos criados pelo create_all (sem alembic_version) são marcados nesta
revisão por base.migrar() antes de aplicar as seguintes.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "itens_b3",
        sa.Column("item", sa.String(10), primary_key=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("setor", sa.String(100)),
        sa.Column("ativo", sa.Boolean),
    )
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("email", sa.String(150), nullable=False, unique=True),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("criado_em", sa.DateTime),
    )
    op.create_table(
        "carteiras",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False, unique=True),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("criado_em", sa.DateTime),
    )
    op.create_table(
        "operacoes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("usuario_id", sa.Integer, sa.ForeignKey("usuarios.id")),
        sa.Column("item", sa.String(20), nullable=False),
        sa.Column("data_entrada", sa.Date),
        sa.Column("preco_entrada", sa.Numeric(10, 2)),
        sa.Column("data_saida", sa.Date),
        sa.Column("preco_saida", sa.Numeric(10, 2)),
        sa.Column("resultado_pct", sa.Numeric(6, 2)),
    )
    op.create_table(
        "recomendacoes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("item", sa.String(20), sa.ForeignKey("itens_b3.item"), nullable=False),
        sa.Column("data_referencia", sa.String(10), nullable=False),
        sa.Column("preco_atual", sa.Numeric(10, 2)),
        sa.Column("rsi", sa.Numeric(6, 2)),
        sa.Column("sinal_rsi", sa.String(20)),
        sa.Column("macd", sa.Numeric(10, 4)),
        sa.Column("macd_signal", sa.Numeric(10, 4)),
        sa.Column("macd_cruzamento", sa.String(10)),
        sa.Column("sma20", sa.Numeric(10, 2)),
        sa.Column("sma50", sa.Numeric(10, 2)),
        sa.Column("tendencia_sma", sa.String(10)),
        sa.Column("recomendacao", sa.String(10), nullable=False),
        sa.Column("justificativa", sa.Text),
        sa.Column("riscos", sa.Text),
        sa.Column("resposta_completa", sa.Text),
        sa.Column("gerado_em", sa.DateTime),
    )
    op.create_index("ix_recomendacoes_item_data", "recomendacoes", ["item", "data_referencia"])
    op.create_table(
        "itens_carteiras",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("carteira_id", sa.Integer, sa.ForeignKey("carteiras.id"), nullable=False),
        sa.Column("item", sa.String(20), sa.ForeignKey("itens_b3.item"), nullable=False),
        sa.Column("quantidade", sa.Numeric(14, 4), nullable=False),
        sa.Column("preco_medio", sa.Numeric(10, 2), nullable=False),
        sa.Column("atualizado_em", sa.DateTime),
        sa.UniqueConstraint("carteira_id", "item", name="uq_carteira_item"),
    )


def downgrade() -> None:
    for tabela in ("itens_carteiras", "recomendacoes", "operacoes", "carteiras", "usuarios", "itens_b3"):
        op.drop_table(tabela)
