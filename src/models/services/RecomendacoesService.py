from datetime import date
from typing import Optional
from sqlalchemy import func, select
from src.models.base import Session
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity
from src.models.services.ClaudeService import ClaudeService


def numero(valor) -> Optional[float]:
    return float(valor) if valor is not None else None


def dataIso(valor) -> Optional[str]:
    return valor.isoformat() if isinstance(valor, date) else valor


class RecomendacoesService:

    def paraDto(self, rec: RecomendacoesEntity) -> dict:
        return {
            "id": rec.getId(),
            "item": rec.getItem(),
            "dataReferencia": dataIso(rec.getDataReferencia()),
            "periodo": rec.getPeriodo(),
            "precoAtual": numero(rec.getPrecoAtual()),
            "rsi": numero(rec.getRsi()),
            "sinalRsi": rec.getSinalRsi(),
            "macd": numero(rec.getMacd()),
            "macdSignal": numero(rec.getMacdSignal()),
            "macdCruzamento": rec.getMacdCruzamento(),
            "sma20": numero(rec.getSma20()),
            "sma50": numero(rec.getSma50()),
            "tendenciaSma": rec.getTendenciaSma(),
            "recomendacao": rec.getRecomendacao(),
            "sobreEmpresa": rec.sobre_empresa
            or ClaudeService.extrairSecao(rec.getRespostaCompleta(), "SOBRE_EMPRESA"),
            "justificativa": rec.getJustificativa() or "",
            "riscos": rec.getRiscos() or "",
            "geradoEm": rec.getGeradoEm(),
        }

    def salvar(self, rec: RecomendacoesEntity) -> dict:
        with Session() as session:
            session.add(rec)
            session.commit()
            return self.paraDto(rec)

    def buscarPorItemDataEPeriodo(self, item: str, dataReferencia: str, periodo: str) -> Optional[dict]:
        if not periodo:
            return None
        with Session() as session:
            rec = (
                session.query(RecomendacoesEntity)
                .filter_by(item=item, data_referencia=dataReferencia, periodo=periodo)
                .order_by(RecomendacoesEntity.gerado_em.desc())
                .first()
            )
            return self.paraDto(rec) if rec is not None else None

    def buscarUltimasPorItens(self, itens: list) -> dict:
        if not itens:
            return {}
        ordem = (
            func.row_number()
            .over(
                partition_by=RecomendacoesEntity.item,
                order_by=(RecomendacoesEntity.gerado_em.desc(), RecomendacoesEntity.id.desc()),
            )
            .label("ordem")
        )
        ranking = (
            select(RecomendacoesEntity.id, ordem)
            .where(RecomendacoesEntity.item.in_(itens))
            .subquery()
        )
        consulta = (
            select(RecomendacoesEntity)
            .join(ranking, RecomendacoesEntity.id == ranking.c.id)
            .where(ranking.c.ordem == 1)
        )
        with Session() as session:
            return {rec.getItem(): self.paraDto(rec) for rec in session.scalars(consulta)}

    def buscarHistorico(self, item: str, limite: int = 20) -> list:
        with Session() as session:
            registros = (
                session.query(RecomendacoesEntity)
                .filter_by(item=item)
                .order_by(RecomendacoesEntity.gerado_em.desc())
                .limit(limite)
                .all()
            )
            return [self.paraDto(rec) for rec in registros]
