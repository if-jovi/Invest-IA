from typing import Optional
from src.models.base import Session
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity
from src.models.services.ClaudeService import ClaudeService


def numero(valor) -> Optional[float]:
    return float(valor) if valor is not None else None


class RecomendacoesService:

    def paraDto(self, rec: RecomendacoesEntity) -> dict:
        return {
            "id": rec.getId(),
            "item": rec.getItem(),
            "dataReferencia": rec.getDataReferencia(),
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
            "sobreEmpresa": ClaudeService.extrairSecao(rec.getRespostaCompleta(), "SOBRE_EMPRESA"),
            "justificativa": rec.getJustificativa() or "",
            "riscos": rec.getRiscos() or "",
            "geradoEm": rec.getGeradoEm(),
        }

    def salvar(self, rec: RecomendacoesEntity) -> dict:
        with Session() as session:
            session.add(rec)
            session.commit()
            return self.paraDto(rec)

    def buscarPorItemEData(self, item: str, dataReferencia: str) -> Optional[dict]:
        with Session() as session:
            rec = (
                session.query(RecomendacoesEntity)
                .filter_by(item=item, data_referencia=dataReferencia)
                .order_by(RecomendacoesEntity.gerado_em.desc())
                .first()
            )
            return self.paraDto(rec) if rec is not None else None

    def buscarUltimasPorItens(self, itens: list) -> dict:
        resultado = {}
        with Session() as session:
            for item in itens:
                rec = (
                    session.query(RecomendacoesEntity)
                    .filter_by(item=item)
                    .order_by(RecomendacoesEntity.gerado_em.desc())
                    .first()
                )
                if rec is not None:
                    resultado[item] = self.paraDto(rec)
        return resultado

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
