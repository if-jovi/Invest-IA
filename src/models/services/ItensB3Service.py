import re
from typing import Optional
from sqlalchemy.exc import IntegrityError
from src.models.base import Session
from src.models.entities.ItensB3Entity import ItensB3Entity
from src.models.services.YfinanceService import YfinanceService

FORMATO_ITEM = re.compile(r"^[A-Z][A-Z0-9]{3}[0-9]{1,2}$")


class ItensB3Service:

    def __init__(self):
        self.yfinanceService = YfinanceService()

    def normalizar(self, item: str) -> str:
        return self.yfinanceService.normalizarItem(item)

    def validarFormato(self, item: str) -> None:
        if not FORMATO_ITEM.match(item):
            raise ValueError("Código inválido. Use o código da B3, por exemplo PETR4 ou VALE3.")

    def paraDto(self, itemB3: ItensB3Entity) -> dict:
        return {
            "item": itemB3.getItem(),
            "nome": itemB3.getNome(),
            "setor": itemB3.getSetor(),
            "ativo": bool(itemB3.isAtivo()),
        }

    def buscarPorItem(self, item: str) -> Optional[dict]:
        with Session() as session:
            itemB3 = session.query(ItensB3Entity).filter_by(item=item).first()
            return self.paraDto(itemB3) if itemB3 is not None else None

    def obterOuCadastrar(self, item: str) -> dict:
        item = self.normalizar(item)
        self.validarFormato(item)

        existente = self.buscarPorItem(item)
        if existente is not None:
            if not existente["ativo"]:
                raise ValueError(f"O ativo {item} está desativado no catálogo.")
            return existente

        dados = self.yfinanceService.buscarInfoAtivo(item)
        try:
            with Session() as session:
                novo = ItensB3Entity(item=dados["item"], nome=dados["nome"], setor=dados["setor"])
                session.add(novo)
                session.commit()
                return self.paraDto(novo)
        except IntegrityError:
            return self.buscarPorItem(item)
