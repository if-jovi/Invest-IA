from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import selectinload
from src.models.base import Session
from src.models.entities.CarteirasEntity import CarteirasEntity
from src.models.entities.ItensCarteirasEntity import ItensCarteirasEntity
from src.models.services.YfinanceService import YfinanceService
from src.models.services.RecomendacoesService import RecomendacoesService


class CarteiraService:

    def __init__(self):
        self.yfinanceService = YfinanceService()
        self.recomendacoesService = RecomendacoesService()

    def carregarItens(self, carteiraId: int) -> dict:
        with Session() as session:
            carteira = (
                session.query(CarteirasEntity)
                .options(
                    selectinload(CarteirasEntity.itens).joinedload(ItensCarteirasEntity.item_ativo)
                )
                .filter_by(id=carteiraId)
                .first()
            )
            if carteira is None:
                raise ValueError("Carteira não encontrada.")

            itens = []
            for i in sorted(carteira.getItens(), key=lambda x: x.getItem()):
                ativo = i.getItemAtivo()
                itens.append(
                    {
                        "item": i.getItem(),
                        "nome": ativo.getNome() if ativo else i.getItem(),
                        "setor": ativo.getSetor() if ativo else None,
                        "quantidade": float(i.getQuantidade()),
                        "precoMedio": float(i.getPrecoMedio()),
                    }
                )
            return {"id": carteira.getId(), "nome": carteira.getNome(), "itens": itens}

    def enriquecer(self, itens: list) -> None:
        if not itens:
            return

        codigos = [i["item"] for i in itens]
        recomendacoes = self.recomendacoesService.buscarUltimasPorItens(codigos)
        with ThreadPoolExecutor(max_workers=min(8, len(codigos))) as pool:
            cotacoes = dict(zip(codigos, pool.map(self.yfinanceService.buscarPrecoAtual, codigos)))

        for i in itens:
            investido = i["quantidade"] * i["precoMedio"]
            cotacao = cotacoes[i["item"]]
            rec = recomendacoes.get(i["item"])

            i["valorInvestido"] = investido
            i["cotacao"] = cotacao
            i["valorAtual"] = cotacao * i["quantidade"] if cotacao is not None else None
            i["resultado"] = i["valorAtual"] - investido if cotacao is not None else None
            i["resultadoPct"] = (
                (i["resultado"] / investido) * 100 if cotacao is not None and investido > 0 else None
            )
            i["recomendacao"] = rec["recomendacao"] if rec else None
            i["dataRecomendacao"] = rec["dataReferencia"] if rec else None

    def obterResumo(self, carteiraId: int) -> dict:
        resumo = self.carregarItens(carteiraId)
        itens = resumo["itens"]
        self.enriquecer(itens)

        investido = sum(i["valorInvestido"] for i in itens)
        cotados = [i for i in itens if i["cotacao"] is not None]
        investidoCotado = sum(i["valorInvestido"] for i in cotados)
        valorAtual = sum(i["valorAtual"] for i in cotados)
        resultado = valorAtual - investidoCotado

        resumo["valorInvestido"] = investido
        resumo["valorAtual"] = valorAtual if cotados else None
        resumo["resultado"] = resultado if cotados else None
        resumo["resultadoPct"] = (resultado / investidoCotado) * 100 if investidoCotado > 0 else None
        resumo["semCotacao"] = len(itens) - len(cotados)
        return resumo
