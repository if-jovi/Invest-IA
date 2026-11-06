"""recomendacoes.data_referencia: VARCHAR(10) 'AAAA-MM-DD' -> DATE.

Antes de alterar, confere se todos os valores estão no formato; se algum não
estiver, falha com mensagem clara em vez de gravar data errada.

Revision ID: 0002
Revises: 0001
"""
import re
from datetime import date

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

FORMATO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def valida(valor) -> bool:
    if not FORMATO.match(str(valor)):
        return False
    try:
        date.fromisoformat(str(valor))
    except ValueError:
        return False
    return True


def upgrade() -> None:
    valores = op.get_bind().execute(sa.text("SELECT DISTINCT data_referencia FROM recomendacoes")).scalars()
    invalidos = sorted(str(v) for v in valores if not valida(v))
    if invalidos:
        raise RuntimeError(
            "Não foi possível converter recomendacoes.data_referencia para data: "
            f"{len(invalidos)} valor(es) fora do formato AAAA-MM-DD, ex.: {', '.join(invalidos[:5])}. "
            "Corrija esses registros e inicie o sistema de novo."
        )
    if op.get_bind().dialect.name == "postgresql":
        op.alter_column(
            "recomendacoes",
            "data_referencia",
            existing_type=sa.String(10),
            type_=sa.Date(),
            existing_nullable=False,
            postgresql_using="data_referencia::date",
        )
        return

    # SQLite: o batch converteria com CAST(... AS DATE), que vira número
    # ('2026-10-02' -> 2026). Copia o texto para uma coluna DATE nova e troca.
    op.drop_index("ix_recomendacoes_item_data", table_name="recomendacoes")
    op.add_column("recomendacoes", sa.Column("data_referencia_nova", sa.Date(), nullable=True))
    op.execute("UPDATE recomendacoes SET data_referencia_nova = data_referencia")
    with op.batch_alter_table("recomendacoes") as tabela:
        tabela.drop_column("data_referencia")
        tabela.alter_column(
            "data_referencia_nova",
            new_column_name="data_referencia",
            existing_type=sa.Date(),
            nullable=False,
        )
    op.create_index("ix_recomendacoes_item_data", "recomendacoes", ["item", "data_referencia"])


def downgrade() -> None:
    with op.batch_alter_table("recomendacoes") as tabela:
        tabela.alter_column(
            "data_referencia",
            existing_type=sa.Date(),
            type_=sa.String(10),
            existing_nullable=False,
            postgresql_using="to_char(data_referencia, 'YYYY-MM-DD')",
        )
