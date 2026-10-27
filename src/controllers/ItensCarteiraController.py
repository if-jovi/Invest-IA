from src.models.services.ItensCarteiraService import ItensCarteiraService


class ItensCarteiraController:

    def __init__(self):
        self.itensCarteiraService = ItensCarteiraService()

    def exigirPositivo(self, valor: float, nome: str) -> None:
        if valor is None or valor <= 0:
            raise ValueError(f"{nome} deve ser maior que zero.")

    def listarItens(self, carteiraId: int) -> list:
        return self.itensCarteiraService.listarItens(carteiraId)

    def adicionarCompra(
        self, carteiraId: int, item: str, quantidade: float, precoUnitario: float
    ) -> dict:
        self.exigirPositivo(quantidade, "A quantidade")
        self.exigirPositivo(precoUnitario, "O preço")
        return self.itensCarteiraService.adicionarCompra(carteiraId, item, quantidade, precoUnitario)

    def registrarVenda(self, carteiraId: int, item: str, quantidade: float) -> dict:
        self.exigirPositivo(quantidade, "A quantidade")
        return self.itensCarteiraService.registrarVenda(carteiraId, item, quantidade)

    def definirPosicao(
        self, carteiraId: int, item: str, quantidade: float, precoMedio: float
    ) -> dict:
        self.exigirPositivo(quantidade, "A quantidade")
        self.exigirPositivo(precoMedio, "O preço médio")
        return self.itensCarteiraService.definirPosicao(carteiraId, item, quantidade, precoMedio)

    def remover(self, carteiraId: int, item: str) -> None:
        self.itensCarteiraService.remover(carteiraId, item)
