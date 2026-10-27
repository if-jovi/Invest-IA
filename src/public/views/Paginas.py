import streamlit as st

CARTEIRA = "Minha carteira"
ANALISE = "Análise de ativo"
BACKTESTING = "Backtesting"
TODAS = [CARTEIRA, ANALISE, BACKTESTING]

CHAVE_ANALISE = "analiseItem"
CHAVE_BACKTEST = "backtestItem"


def irPara(pagina: str, chave: str = None, valor: str = None) -> None:
    st.session_state["pagina"] = pagina
    if chave is not None:
        st.session_state[chave] = valor


def agendarMensagem(tipo: str, texto: str) -> None:
    st.session_state["mensagem"] = (tipo, texto)


def exibirMensagem() -> None:
    mensagem = st.session_state.pop("mensagem", None)
    if mensagem is None:
        return
    tipo, texto = mensagem
    if tipo == "sucesso":
        st.success(texto)
    else:
        st.info(texto)
