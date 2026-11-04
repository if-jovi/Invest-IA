from html import escape
import streamlit as st
from src.models.base import criarTabelas
from src.models.services.ItensB3Service import ItensB3Service
from src.public.views import Estilo, Paginas
from src.public.views.Login import renderLogin

st.set_page_config(
    page_title="InvestIA",
    page_icon=":material/insights:",
    layout="wide",
    initial_sidebar_state="expanded",
)
Estilo.aplicarEstilo()


@st.cache_resource
def inicializarBanco() -> bool:
    criarTabelas()
    ItensB3Service().semearCatalogo()
    return True


def renderSidebar(usuario: dict) -> None:
    with st.sidebar:
        st.markdown(
            '<div class="ia-marca"><div class="ia-marca-icone">IA</div>InvestIA</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="ia-usuario"><strong>{escape(usuario["nome"])}</strong>'
            f'<span>{escape(usuario["email"])}</span></div>',
            unsafe_allow_html=True,
        )
        if st.button("Sair", icon=":material/logout:", width="stretch"):
            st.session_state.clear()
            st.rerun()
        st.divider()
        st.caption("TCC - João Vitor Martins · Horus Faculdades")


try:
    inicializarBanco()
except Exception as erro:
    st.error(f"Não foi possível conectar ao banco de dados: {erro}")
    st.stop()

if "usuario" not in st.session_state:
    renderLogin()
else:
    navegacao = st.navigation(Paginas.criarPaginas(), position="sidebar")
    renderSidebar(st.session_state["usuario"])
    try:
        navegacao.run()
    except Exception as erro:
        st.error(f"Ocorreu um erro inesperado nesta tela: {erro}")
