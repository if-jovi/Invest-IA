from datetime import datetime
from typing import Optional


def moeda(valor: Optional[float]) -> str:
    if valor is None:
        return "-"
    texto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"-R$ {texto}" if valor < 0 else f"R$ {texto}"


def percentual(valor: Optional[float]) -> str:
    if valor is None:
        return "-"
    return f"{valor:+.2f}%".replace(".", ",")


def dataHora(valor: Optional[datetime]) -> str:
    return valor.strftime("%d/%m/%Y %H:%M") if valor else "-"


def dataBr(texto: Optional[str]) -> str:
    if not texto:
        return "-"
    ano, mes, dia = str(texto)[:10].split("-")
    return f"{dia}/{mes}/{ano}"
