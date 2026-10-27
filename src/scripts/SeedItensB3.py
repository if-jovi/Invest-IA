import sys
from src.models.base import criarTabelas
from src.models.services.ItensB3Service import ItensB3Service

ITENS_PADRAO = [
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "BBAS3",
    "ABEV3",
    "WEGE3",
    "B3SA3",
    "RENT3",
    "SUZB3",
]


def cadastrar(itens: list) -> None:
    criarTabelas()
    service = ItensB3Service()

    for item in itens:
        try:
            ativo = service.obterOuCadastrar(item)
            print(f"{ativo['item']}: {ativo['nome']} ({ativo['setor']})")
        except Exception as erro:
            print(f"{item}: não cadastrado - {erro}")


if __name__ == "__main__":
    cadastrar(sys.argv[1:] or ITENS_PADRAO)
