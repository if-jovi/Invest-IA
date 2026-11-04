"""Autocomplete de ativos do catálogo (spec: catalogo-ativos.md).

As opções são os códigos (PETR4); o que aparece na tela é "PETR4 — Nome".
O usuário também pode digitar um código que não está na lista.
"""
import streamlit as st
from src.models.services.ItensB3Service import ItensB3Service

PLACEHOLDER = "Busque por código ou nome (ex.: PETR4, Vale)"


@st.cache_data(ttl=600, show_spinner=False)
def rotulosCatalogo() -> dict:
    return {a["item"]: f"{a['item']} — {a['nome']}" for a in ItensB3Service().listarAtivos()}


def rotulo(codigo: str) -> str:
    return rotulosCatalogo().get(codigo, codigo)


def atualizarSeNovos(codigos: list) -> None:
    """Se um código novo foi cadastrado, recarrega a lista na próxima vez."""
    conhecidos = rotulosCatalogo()
    if any(c and c not in conhecidos for c in codigos):
        rotulosCatalogo.clear()


def listaDeOpcoes(jaEscolhidos: list) -> list:
    """Catálogo + códigos digitados que ainda não estão nele."""
    codigos = list(rotulosCatalogo())
    return codigos + [c for c in jaEscolhidos if c and c not in codigos]


def seletorAtivo(texto: str, key: str, container=st):
    return container.selectbox(
        texto,
        listaDeOpcoes([st.session_state.get(key)]),
        index=None,
        key=key,
        format_func=rotulo,
        accept_new_options=True,
        placeholder=PLACEHOLDER,
    )


def seletorAtivos(texto: str, key: str, limite: int, container=st) -> list:
    return container.multiselect(
        texto,
        listaDeOpcoes(st.session_state.get(key) or []),
        key=key,
        format_func=rotulo,
        accept_new_options=True,
        max_selections=limite,
        placeholder=PLACEHOLDER,
    )
