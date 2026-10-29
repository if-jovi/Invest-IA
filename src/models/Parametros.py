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
