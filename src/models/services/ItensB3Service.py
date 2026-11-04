import json
import logging
import re
from pathlib import Path
from typing import Optional
from sqlalchemy.exc import IntegrityError
from src.models.base import Session
from src.models.entities.ItensB3Entity import ItensB3Entity
from src.models.services.YfinanceService import YfinanceService

logger = logging.getLogger(__name__)

FORMATO_ITEM = re.compile(r"^[A-Z][A-Z0-9]{3}[0-9]{1,2}$")
CATALOGO_PADRAO = Path(__file__).resolve().parents[2] / "data" / "ativos_b3.json"


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

    def listarAtivos(self) -> list:
        with Session() as session:
            itens = (
                session.query(ItensB3Entity)
                .filter(ItensB3Entity.ativo.is_(True))
                .order_by(ItensB3Entity.item)
                .all()
            )
            return [self.paraDto(i) for i in itens]

    @staticmethod
    def carregarCatalogo(caminho=None) -> list:
        caminho = Path(caminho or CATALOGO_PADRAO)
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            logger.warning("Catálogo de ativos indisponível (%s): %r", caminho, erro)
            return []
        if not isinstance(dados, list):
            logger.warning("Catálogo de ativos em formato inesperado: %s", caminho)
            return []
        return [
            a for a in dados
            if isinstance(a, dict) and FORMATO_ITEM.match(str(a.get("item") or "")) and a.get("nome")
        ]

    def semearCatalogo(self, caminho=None) -> int:
        catalogo = self.carregarCatalogo(caminho)
        if not catalogo:
            return 0
        with Session() as session:
            existentes = {linha[0] for linha in session.query(ItensB3Entity.item).all()}
            novos = [
                ItensB3Entity(
                    item=a["item"], nome=a["nome"], setor=a.get("setor") or "Não disponível", ativo=True
                )
                for a in catalogo
                if a["item"] not in existentes
            ]
            session.add_all(novos)
            session.commit()
            return len(novos)

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
