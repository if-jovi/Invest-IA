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

    def enriquecer(self, itens: list, forcar: bool = False) -> None:
        if not itens:
            return

        codigos = [i["item"] for i in itens]
        recomendacoes = self.recomendacoesService.buscarUltimasPorItens(codigos)
        cotacoes = self.yfinanceService.buscarCotacoes(codigos, forcar=forcar)

        for i in itens:
            investido = i["quantidade"] * i["precoMedio"]
            cotacao = cotacoes.get(i["item"])
            preco = cotacao["preco"] if cotacao else None
            rec = recomendacoes.get(i["item"])

            i["valorInvestido"] = investido
            i["cotacao"] = preco
            i["fechamentoAnterior"] = cotacao["fechamentoAnterior"] if cotacao else None
            i["variacaoDia"] = cotacao["variacaoDia"] if cotacao else None
            i["atualizadoEm"] = cotacao["atualizadoEm"] if cotacao else None
            i["desatualizada"] = bool(cotacao and cotacao["desatualizada"])
            i["valorAtual"] = preco * i["quantidade"] if preco is not None else None
            i["resultado"] = i["valorAtual"] - investido if preco is not None else None
            i["resultadoPct"] = (
                (i["resultado"] / investido) * 100 if preco is not None and investido > 0 else None
            )
            i["recomendacao"] = rec["recomendacao"] if rec else None
            i["dataRecomendacao"] = rec["dataReferencia"] if rec else None

    @staticmethod
    def variacaoDiaCarteira(itens: list):
        comVariacao = [
            i for i in itens if i.get("cotacao") is not None and i.get("fechamentoAnterior")
        ]
        base = sum(i["quantidade"] * i["fechamentoAnterior"] for i in comVariacao)
        if base <= 0:
            return None
        ganho = sum(i["quantidade"] * (i["cotacao"] - i["fechamentoAnterior"]) for i in comVariacao)
        return ganho / base * 100

    def obterResumo(self, carteiraId: int, forcar: bool = False) -> dict:
        resumo = self.carregarItens(carteiraId)
        itens = resumo["itens"]
        self.enriquecer(itens, forcar)

        investido = sum(i["valorInvestido"] for i in itens)
        cotados = [i for i in itens if i["cotacao"] is not None]
        investidoCotado = sum(i["valorInvestido"] for i in cotados)
        valorAtual = sum(i["valorAtual"] for i in cotados)
        resultado = valorAtual - investidoCotado
        horarios = [i["atualizadoEm"] for i in cotados if i["atualizadoEm"] is not None]

        resumo["valorInvestido"] = investido
        resumo["valorAtual"] = valorAtual if cotados else None
        resumo["resultado"] = resultado if cotados else None
        resumo["resultadoPct"] = (resultado / investidoCotado) * 100 if investidoCotado > 0 else None
        resumo["variacaoDia"] = self.variacaoDiaCarteira(itens)
        resumo["semCotacao"] = len(itens) - len(cotados)
        resumo["cotacoesDesatualizadas"] = sum(1 for i in cotados if i["desatualizada"])
        resumo["atualizadoEm"] = max(horarios) if horarios else None
        return resumo
