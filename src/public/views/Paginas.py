import streamlit as st

CARTEIRA = "carteira"
ANALISE = "analise"
BACKTESTING = "backtesting"
DESEMPENHO = "desempenho"

PAGINAS = {
    CARTEIRA: ("paginas/carteira.py", "Minha carteira", ":material/account_balance_wallet:"),
    ANALISE: ("paginas/analise.py", "Análise de ativo", ":material/insights:"),
    BACKTESTING: ("paginas/backtesting.py", "Backtesting", ":material/history:"),
    DESEMPENHO: ("paginas/desempenho.py", "Desempenho da IA", ":material/verified:"),
}

CHAVE_ANALISE = "analiseItens"
CHAVE_BACKTEST = "backtestItem"


def criarPaginas() -> list:
    return [
        st.Page(arquivo, title=titulo, icon=icone, url_path=chave, default=chave == CARTEIRA)
        for chave, (arquivo, titulo, icone) in PAGINAS.items()
    ]


def irPara(pagina: str, chave: str = None, valor=None) -> None:
    if chave is not None:
        st.session_state[chave] = valor
    st.switch_page(PAGINAS[pagina][0])


def agendarMensagem(tipo: str, texto: str) -> None:
    st.session_state["mensagem"] = (tipo, texto)


def exibirMensagem() -> None:
    mensagem = st.session_state.pop("mensagem", None)
    if mensagem is None:
        return
    tipo, texto = mensagem
    if tipo == "sucesso":
        st.success(texto, icon=":material/check_circle:")
    else:
        st.info(texto)
