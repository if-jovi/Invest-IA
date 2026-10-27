from typing import Optional
from src.models.base import Session
from src.models.entities.ItensCarteirasEntity import ItensCarteirasEntity
from src.models.services.ItensB3Service import ItensB3Service

TOLERANCIA = 1e-9


class ItensCarteiraService:

    def __init__(self):
        self.itensB3Service = ItensB3Service()

    def paraDto(self, itemCarteira: ItensCarteirasEntity) -> dict:
        return {
            "item": itemCarteira.getItem(),
            "quantidade": float(itemCarteira.getQuantidade()),
            "precoMedio": float(itemCarteira.getPrecoMedio()),
        }

    def buscar(self, session, carteiraId: int, item: str) -> Optional[ItensCarteirasEntity]:
        return (
            session.query(ItensCarteirasEntity)
            .filter_by(carteira_id=carteiraId, item=item)
            .first()
        )

    def buscarExistente(self, session, carteiraId: int, item: str) -> ItensCarteirasEntity:
        itemCarteira = self.buscar(session, carteiraId, item)
        if itemCarteira is None:
            raise ValueError(f"O ativo {item} não está na sua carteira.")
        return itemCarteira

    def listarItens(self, carteiraId: int) -> list:
        with Session() as session:
            itens = (
                session.query(ItensCarteirasEntity)
                .filter_by(carteira_id=carteiraId)
                .order_by(ItensCarteirasEntity.item)
                .all()
            )
            return [i.getItem() for i in itens]

    def adicionarCompra(
        self, carteiraId: int, item: str, quantidade: float, precoUnitario: float
    ) -> dict:
        ativo = self.itensB3Service.obterOuCadastrar(item)

        with Session() as session:
            itemCarteira = self.buscar(session, carteiraId, ativo["item"])
            if itemCarteira is None:
                itemCarteira = ItensCarteirasEntity(
                    carteira_id=carteiraId, item=ativo["item"], quantidade=0, preco_medio=0
                )
                session.add(itemCarteira)

            itemCarteira.registrarCompra(quantidade, precoUnitario)
            session.commit()
            return self.paraDto(itemCarteira)

    def registrarVenda(self, carteiraId: int, item: str, quantidade: float) -> dict:
        item = self.itensB3Service.normalizar(item)
        with Session() as session:
            itemCarteira = self.buscarExistente(session, carteiraId, item)

            posicao = float(itemCarteira.getQuantidade())
            if quantidade > posicao + TOLERANCIA:
                raise ValueError(f"Você possui apenas {posicao:g} unidades de {item}.")

            itemCarteira.registrarVenda(quantidade)
            if float(itemCarteira.getQuantidade()) <= TOLERANCIA:
                session.delete(itemCarteira)
                session.commit()
                return {"item": item, "quantidade": 0.0, "precoMedio": 0.0, "removido": True}

            session.commit()
            return self.paraDto(itemCarteira) | {"removido": False}

    def definirPosicao(
        self, carteiraId: int, item: str, quantidade: float, precoMedio: float
    ) -> dict:
        item = self.itensB3Service.normalizar(item)
        with Session() as session:
            itemCarteira = self.buscarExistente(session, carteiraId, item)
            itemCarteira.setQuantidade(quantidade)
            itemCarteira.setPrecoMedio(precoMedio)
            session.commit()
            return self.paraDto(itemCarteira)

    def remover(self, carteiraId: int, item: str) -> None:
        item = self.itensB3Service.normalizar(item)
        with Session() as session:
            itemCarteira = self.buscarExistente(session, carteiraId, item)
            session.delete(itemCarteira)
            session.commit()
