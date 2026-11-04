"""Atualiza src/data/ativos_b3.json com as ações da B3 listadas na brapi.dev.

Uso: python -m src.scripts.AtualizarCatalogoB3
Spec: .agents/docs/specs/catalogo-ativos.md
"""
import json
import re
import sys
from pathlib import Path
from typing import Optional
import httpx

URL_BRAPI = "https://brapi.dev/api/quote/list"
CAMINHO_PADRAO = Path(__file__).resolve().parents[1] / "data" / "ativos_b3.json"
MINIMO_ATIVOS = 300
TAMANHO_NOME = 150
NAO_DISPONIVEL = "Não disponível"
FORMATO_ITEM = re.compile(r"^[A-Z][A-Z0-9]{3}[0-9]{1,2}$")

SETORES_BRAPI = {
    "Finance": "Serviços Financeiros",
    "Utilities": "Utilidade Pública",
    "Energy Minerals": "Energia",
    "Non-Energy Minerals": "Materiais Básicos",
    "Process Industries": "Materiais Básicos",
    "Producer Manufacturing": "Industrial",
    "Industrial Services": "Industrial",
    "Transportation": "Industrial",
    "Retail Trade": "Consumo Cíclico",
    "Consumer Durables": "Consumo Cíclico",
    "Consumer Services": "Consumo Cíclico",
    "Consumer Non-Durables": "Consumo Não Cíclico",
    "Distribution Services": "Distribuição",
    "Commercial Services": "Serviços Comerciais",
    "Health Services": "Saúde",
    "Health Technology": "Saúde",
    "Technology Services": "Tecnologia",
    "Electronic Technology": "Tecnologia",
    "Communications": "Comunicação",
    "Miscellaneous": "Outros",
}


class FalhaCatalogo(Exception):
    pass


def traduzirSetor(setor: Optional[str]) -> str:
    return SETORES_BRAPI.get(setor or "", NAO_DISPONIVEL)


def baixarAtivos(cliente: httpx.Client) -> list:
    """Baixa a lista da brapi e devolve só as ações, ordenadas e sem repetição."""
    try:
        resposta = cliente.get(URL_BRAPI, params={"type": "stock", "limit": 5000}, timeout=60)
    except httpx.HTTPError as erro:
        raise FalhaCatalogo(f"Não foi possível acessar a brapi: {erro!r}")
    if resposta.status_code != 200:
        raise FalhaCatalogo(f"A brapi respondeu HTTP {resposta.status_code}.")

    try:
        acoes = resposta.json()["stocks"]
    except (ValueError, KeyError, TypeError):
        raise FalhaCatalogo("Resposta da brapi sem a lista 'stocks'.")

    porItem = {}
    for acao in acoes:
        item = str(acao.get("stock") or "").strip().upper()
        if acao.get("type") != "stock" or not FORMATO_ITEM.match(item):
            continue  # descarta fundos, BDRs e códigos do fracionário (ex.: PETR4F)
        porItem[item] = {
            "item": item,
            "nome": (str(acao.get("name") or "").strip() or item)[:TAMANHO_NOME],
            "setor": traduzirSetor(acao.get("sector")),
        }

    if len(porItem) < MINIMO_ATIVOS:
        raise FalhaCatalogo(
            f"A brapi devolveu só {len(porItem)} ações (mínimo {MINIMO_ATIVOS}); resposta truncada?"
        )
    return [porItem[item] for item in sorted(porItem)]


def gravar(ativos: list, caminho: Path) -> None:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(ativos, ensure_ascii=False, indent=1) + "\n"
    caminho.write_text(texto, encoding="utf-8")


def main(argv=None, cliente: Optional[httpx.Client] = None, caminho=None) -> int:
    caminho = Path(caminho or CAMINHO_PADRAO)
    proprio = cliente is None
    cliente = cliente or httpx.Client(headers={"User-Agent": "InvestIA-TCC"})
    try:
        ativos = baixarAtivos(cliente)
        gravar(ativos, caminho)
    except FalhaCatalogo as erro:
        print(f"Catálogo NÃO atualizado: {erro}", file=sys.stderr)
        return 1
    finally:
        if proprio:
            cliente.close()
    print(f"{len(ativos)} ações gravadas em {caminho}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
