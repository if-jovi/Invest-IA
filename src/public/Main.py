import streamlit as st
from src.models.base import criarTabelas
from src.public.views import Paginas
from src.public.views.Login import renderLogin
from src.public.views.CarteiraDashboard import renderDashboard
from src.public.views.AnaliseView import renderAnalise
from src.public.views.BacktestView import renderBacktest

st.set_page_config(page_title="InvestIA", layout="wide")

PAGINAS = {
    Paginas.CARTEIRA: renderDashboard,
    Paginas.ANALISE: renderAnalise,
    Paginas.BACKTESTING: renderBacktest,
}


@st.cache_resource
def inicializarBanco() -> bool:
    criarTabelas()
    return True


def renderSidebar(usuario: dict) -> None:
    with st.sidebar:
        st.title("InvestIA")
        st.caption(usuario["nome"])
        st.caption(usuario["email"])
        st.divider()

        st.session_state.setdefault("pagina", Paginas.CARTEIRA)
        st.radio("Navegação", Paginas.TODAS, key="pagina")

        st.divider()
        if st.button("Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

        st.caption("TCC - João Vitor Martins")
        st.caption("Horus Faculdades")


try:
    inicializarBanco()
except Exception as erro:
    st.error(f"Não foi possível conectar ao banco de dados: {erro}")
    st.stop()

if "usuario" not in st.session_state:
    renderLogin()
else:
    renderSidebar(st.session_state["usuario"])
    try:
        PAGINAS[st.session_state["pagina"]]()
    except Exception as erro:
        st.error(f"Ocorreu um erro inesperado nesta tela: {erro}")
