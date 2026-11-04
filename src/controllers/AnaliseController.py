import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.models.services.AnaliseService import AnaliseService

logger = logging.getLogger(__name__)

PERIODOS = ("3mo", "6mo", "1y", "2y")
LIMITE_ATIVOS_ANALISE = 5
ANALISES_SIMULTANEAS = 2


def normalizarItem(item: str) -> str:
    valor = (item or "").strip().upper()
    return valor[:-3] if valor.endswith(".SA") else valor


class AnaliseController:

    def __init__(self):
        self.analiseService = AnaliseService()

    def validarPeriodo(self, periodo: str) -> None:
        if periodo not in PERIODOS:
            raise ValueError("Período inválido.")

    def analisar(self, item: str, periodo: str = "1y", forcar: bool = False) -> dict:
        if not (item or "").strip():
            raise ValueError("Informe o código do ativo.")
        self.validarPeriodo(periodo)
        return self.analiseService.analisar(item, periodo, forcar)

    def analisarVarios(
        self, itens: list, periodo: str = "1y", forcar: bool = False, aoProgredir=None
    ) -> dict:
        codigos = list(dict.fromkeys(c for c in (normalizarItem(i) for i in itens or []) if c))
        if not codigos:
            raise ValueError("Informe ao menos um ativo.")
        if len(codigos) > LIMITE_ATIVOS_ANALISE:
            raise ValueError(f"Selecione no máximo {LIMITE_ATIVOS_ANALISE} ativos por análise.")
        self.validarPeriodo(periodo)

        def executar(codigo: str):
            try:
                return codigo, self.analiseService.analisar(codigo, periodo, forcar), None
            except (ValueError, RuntimeError) as erro:
                return codigo, None, str(erro)
            except Exception as erro:
                logger.exception("Falha inesperada ao analisar %s", codigo)
                return codigo, None, f"Não foi possível concluir a análise: {erro}"

        with ThreadPoolExecutor(max_workers=ANALISES_SIMULTANEAS) as pool:
            futuros = [pool.submit(executar, codigo) for codigo in codigos]
            if aoProgredir is not None:
                aoProgredir(0, len(codigos), None)
                for concluidos, futuro in enumerate(as_completed(futuros), start=1):
                    aoProgredir(concluidos, len(codigos), futuro.result()[0])
            saidas = [futuro.result() for futuro in futuros]

        return {
            "resultados": [resultado for _, resultado, erro in saidas if erro is None],
            "erros": [{"item": codigo, "mensagem": erro} for codigo, _, erro in saidas if erro is not None],
        }

    def buscarHistorico(self, item: str, limite: int = 20) -> list:
        return self.analiseService.buscarHistorico(item, limite)
