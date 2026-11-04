from datetime import date, datetime
from typing import Optional, Union

VAZIO = "-"


def numeroBr(valor: float, casas: int = 2) -> str:
    texto = f"{abs(valor):,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def moeda(valor: Optional[float]) -> str:
    if valor is None:
        return VAZIO
    texto = numeroBr(valor)
    return f"-R$ {texto}" if round(valor, 2) < 0 else f"R$ {texto}"


def percentual(valor: Optional[float]) -> str:
    if valor is None:
        return VAZIO
    sinal = "-" if round(valor, 2) < 0 else ""
    return f"{sinal}{numeroBr(valor)}%"


def variacao(valor: Optional[float]) -> str:
    if valor is None:
        return VAZIO
    arredondado = round(valor, 2)
    sinal = "+" if arredondado > 0 else "-" if arredondado < 0 else ""
    return f"{sinal}{numeroBr(valor)}%"


def quantidade(valor: Optional[float]) -> str:
    if valor is None:
        return VAZIO
    return numeroBr(valor, 0) if float(valor).is_integer() else numeroBr(valor, 4).rstrip("0").rstrip(",")


def decimal(valor: Optional[float], casas: int = 2) -> str:
    if valor is None:
        return VAZIO
    return ("-" if round(valor, casas) < 0 else "") + numeroBr(valor, casas)


def dataBr(valor: Optional[Union[str, date]]) -> str:
    if not valor:
        return VAZIO
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    ano, mes, dia = str(valor)[:10].split("-")
    return f"{dia}/{mes}/{ano}"


def dataHora(valor: Optional[datetime]) -> str:
    return valor.strftime("%d/%m/%Y %H:%M") if valor else VAZIO


def hora(valor: Optional[datetime]) -> str:
    return valor.strftime("%H:%M") if valor else VAZIO
