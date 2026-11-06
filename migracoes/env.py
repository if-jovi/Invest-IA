from alembic import context

config = context.config


def executar(conexao) -> None:
    context.configure(connection=conexao, target_metadata=None, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


conexao = config.attributes.get("connection")
if conexao is not None:
    executar(conexao)
else:
    from src.models.base import engine

    with engine.begin() as nova:
        executar(nova)
