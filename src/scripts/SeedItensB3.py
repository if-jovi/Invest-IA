"""Popula o catálogo de ativos (itens_b3).

Sem argumentos: grava as ações de src/data/ativos_b3.json (offline).
Com argumentos: valida cada código no Yahoo e cadastra.
Uso: python -m src.scripts.SeedItensB3 [PETR4 VALE3 ...]
"""
import sys
from src.models.base import criarTabelas
from src.models.services.ItensB3Service import ItensB3Service


def cadastrar(itens: list) -> None:
    service = ItensB3Service()
    for item in itens:
        try:
            ativo = service.obterOuCadastrar(item)
            print(f"{ativo['item']}: {ativo['nome']} ({ativo['setor']})")
        except Exception as erro:
            print(f"{item}: não cadastrado - {erro}")


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    criarTabelas()
    if argv:
        cadastrar(argv)
        return
    inseridos = ItensB3Service().semearCatalogo()
    print(f"{inseridos} ativo(s) do catálogo inseridos.")


if __name__ == "__main__":
    main()
