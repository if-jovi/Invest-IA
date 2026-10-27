import pandas as pd


def rsi(close, length=14):
    delta = close.diff()
    ganho = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    perda = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    rs = ganho / perda
    return 100 - 100 / (1 + rs)


def macd(close, fast=12, slow=26, signal=9):
    linha = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    sinal = linha.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame(
        {
            f"MACD_{fast}_{slow}_{signal}": linha,
            f"MACDh_{fast}_{slow}_{signal}": linha - sinal,
            f"MACDs_{fast}_{slow}_{signal}": sinal,
        }
    )


def sma(close, length):
    return close.rolling(length).mean()
