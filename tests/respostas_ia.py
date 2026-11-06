"""Respostas simuladas da IA no contrato JSON (spec analise-ia.md)."""
import json


def respostaJson(recomendacao="COMPRA", sobre="A empresa atua no setor de energia.",
                 justificativa="O RSI esta neutro e o MACD cruzou para cima.",
                 riscos=("Volatilidade do petroleo",)) -> str:
    return json.dumps({
        "recomendacao": recomendacao,
        "sobre_empresa": sobre,
        "justificativa": justificativa,
        "riscos": list(riscos),
    }, ensure_ascii=False)
