import os
from config import settings

ANTHROPIC_API_KEY = getattr(
    settings, "ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", "")
)
CLAUDE_MODEL = getattr(settings, "CLAUDE_MODEL", "claude-sonnet-5-5")

DEFAULT_PERIOD = getattr(settings, "DEFAULT_PERIOD", "1y")
DEFAULT_INTERVAL = getattr(settings, "DEFAULT_INTERVAL", "1d")

RSI_PERIOD = getattr(settings, "RSI_PERIOD", 14)
MACD_FAST = getattr(settings, "MACD_FAST", 12)
MACD_SLOW = getattr(settings, "MACD_SLOW", 26)
MACD_SIGNAL = getattr(settings, "MACD_SIGNAL", 9)
SMA_SHORT = getattr(settings, "SMA_SHORT", 20)
SMA_LONG = getattr(settings, "SMA_LONG", 50)

RSI_OVERSOLD = getattr(settings, "RSI_OVERSOLD", 30)
RSI_OVERBOUGHT = getattr(settings, "RSI_OVERBOUGHT", 70)

ROTULOS_PERIODO = {"3mo": "3 meses", "6mo": "6 meses", "1y": "1 ano", "2y": "2 anos"}
MESES_PERIODO = {"3mo": 3, "6mo": 6, "1y": 12, "2y": 24}
# Pregões extras antes do período, só para o cálculo dos indicadores (historico-aquecimento.md)
DIAS_AQUECIMENTO = getattr(settings, "DIAS_AQUECIMENTO", 150)

# IA: seed fixo para respostas mais estáveis (analise-ia.md)
SEED_IA = int(os.getenv("SEED_IA") or getattr(settings, "SEED_IA", 42))

# Backtesting: custo por compra e por venda, em % (emolumentos + liquidação B3)
CUSTO_OPERACAO_PCT = getattr(settings, "CUSTO_OPERACAO_PCT", 0.03)

# Desempenho da IA (desempenho-ia.md)
HORIZONTE_AVALIACAO = getattr(settings, "HORIZONTE_AVALIACAO", 20)
FAIXA_MANTER_PCT = getattr(settings, "FAIXA_MANTER_PCT", 3.0)
SIMBOLO_IBOVESPA = "^BVSP"
