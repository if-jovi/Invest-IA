import pandas as pd
import streamlit as st
from src.controllers.CarteiraController import CarteiraController
from src.controllers.ItensCarteiraController import ItensCarteiraController
from src.public.views import Paginas
from src.public.views.Formatacao import moeda, percentual, dataBr


def renderIndicadores(resumo: dict) -> None:
    colunas = st.columns(4)
    colunas[0].metric("Valor investido", moeda(resumo["valorInvestido"]))
    colunas[1].metric("Valor atual", moeda(resumo["valorAtual"]))
    colunas[2].metric(
        "Resultado",
        moeda(resumo["resultado"]),
        delta=percentual(resumo["resultadoPct"]) if resumo["resultadoPct"] is not None else None,
    )
    colunas[3].metric("Ativos na carteira", len(resumo["itens"]))

    if resumo["semCotacao"]:
        st.caption(
            f"{resumo['semCotacao']} ativo(s) sem cotação disponível no momento; "
            "eles não entram no valor atual nem no resultado."
        )


def renderTabela(resumo: dict) -> None:
    if not resumo["itens"]:
        st.info("Sua carteira ainda está vazia. Registre uma compra abaixo para começar.")
        return

    linhas = [
        {
            "Código": i["item"],
            "Empresa": i["nome"],
            "Setor": i["setor"],
            "Quantidade": i["quantidade"],
            "Preço médio": i["precoMedio"],
            "Cotação": i["cotacao"],
            "Valor atual": i["valorAtual"],
            "Resultado (R$)": i["resultado"],
            "Resultado (%)": i["resultadoPct"],
            "Recomendação": i["recomendacao"] or "Sem análise",
            "Data da análise": dataBr(i["dataRecomendacao"]),
        }
        for i in resumo["itens"]
    ]
    st.dataframe(
        pd.DataFrame(linhas),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Quantidade": st.column_config.NumberColumn(format="%.0f"),
            "Preço médio": st.column_config.NumberColumn(format="R$ %.2f"),
            "Cotação": st.column_config.NumberColumn(format="R$ %.2f"),
            "Valor atual": st.column_config.NumberColumn(format="R$ %.2f"),
            "Resultado (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
            "Resultado (%)": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def renderAtalhos(itens: list) -> None:
    if not itens:
        return

    st.subheader("Análise rápida")
    colunas = st.columns([2, 1, 1])
    escolhido = colunas[0].selectbox("Ativo da carteira", itens)
    colunas[1].button(
        "Analisar",
        key="atalhoAnalisar",
        use_container_width=True,
        on_click=Paginas.irPara,
        args=(Paginas.ANALISE, Paginas.CHAVE_ANALISE, escolhido),
    )
    colunas[2].button(
        "Backtesting",
        key="atalhoBacktest",
        use_container_width=True,
        on_click=Paginas.irPara,
        args=(Paginas.BACKTESTING, Paginas.CHAVE_BACKTEST, escolhido),
    )


def executar(acao, mensagem: str) -> None:
    try:
        with st.spinner("Processando..."):
            acao()
    except (ValueError, RuntimeError) as erro:
        st.error(str(erro))
        return
    Paginas.agendarMensagem("sucesso", mensagem)
    st.rerun()


def renderCompra(carteiraId: int, controller: ItensCarteiraController) -> None:
    with st.form("formCompra", clear_on_submit=True):
        item = st.text_input("Código do ativo", placeholder="Ex.: PETR4")
        quantidade = st.number_input("Quantidade", min_value=1, value=100, step=1)
        preco = st.number_input(
            "Preço unitário (R$)", min_value=0.01, value=10.00, step=0.01, format="%.2f"
        )
        enviar = st.form_submit_button("Registrar compra", type="primary")

    if enviar:
        executar(
            lambda: controller.adicionarCompra(carteiraId, item, quantidade, preco),
            f"Compra de {quantidade} unidade(s) de {item.strip().upper()} registrada.",
        )


def renderVenda(carteiraId: int, itens: list, controller: ItensCarteiraController) -> None:
    if not itens:
        st.info("Nenhum ativo na carteira.")
        return

    with st.form("formVenda", clear_on_submit=True):
        item = st.selectbox("Ativo", itens)
        quantidade = st.number_input("Quantidade vendida", min_value=1, value=1, step=1)
        enviar = st.form_submit_button("Registrar venda", type="primary")

    if enviar:
        executar(
            lambda: controller.registrarVenda(carteiraId, item, quantidade),
            f"Venda de {quantidade} unidade(s) de {item} registrada.",
        )


def renderCorrecao(carteiraId: int, itens: list, controller: ItensCarteiraController) -> None:
    if not itens:
        st.info("Nenhum ativo na carteira.")
        return

    with st.form("formCorrecao", clear_on_submit=True):
        item = st.selectbox("Ativo", itens)
        quantidade = st.number_input("Nova quantidade", min_value=1, value=100, step=1)
        precoMedio = st.number_input(
            "Novo preço médio (R$)", min_value=0.01, value=10.00, step=0.01, format="%.2f"
        )
        enviar = st.form_submit_button("Corrigir posição", type="primary")

    if enviar:
        executar(
            lambda: controller.definirPosicao(carteiraId, item, quantidade, precoMedio),
            f"Posição de {item} corrigida.",
        )


def renderRemocao(carteiraId: int, itens: list, controller: ItensCarteiraController) -> None:
    if not itens:
        st.info("Nenhum ativo na carteira.")
        return

    with st.form("formRemocao", clear_on_submit=True):
        item = st.selectbox("Ativo", itens)
        confirmar = st.checkbox("Confirmo que desejo remover este ativo da carteira")
        enviar = st.form_submit_button("Remover ativo")

    if enviar:
        if not confirmar:
            st.error("Marque a confirmação para remover o ativo.")
            return
        executar(lambda: controller.remover(carteiraId, item), f"{item} removido da carteira.")


def renderGerenciamento(carteiraId: int, itens: list) -> None:
    st.subheader("Gerenciar posições")
    controller = ItensCarteiraController()
    abas = st.tabs(["Registrar compra", "Registrar venda", "Corrigir posição", "Remover ativo"])

    with abas[0]:
        renderCompra(carteiraId, controller)
    with abas[1]:
        renderVenda(carteiraId, itens, controller)
    with abas[2]:
        renderCorrecao(carteiraId, itens, controller)
    with abas[3]:
        renderRemocao(carteiraId, itens, controller)


def renderDashboard() -> None:
    usuario = st.session_state["usuario"]
    Paginas.exibirMensagem()
    st.title(f"Carteira de {usuario['nome']}")

    try:
        with st.spinner("Atualizando cotações..."):
            resumo = CarteiraController().obterResumo(usuario["carteiraId"])
    except Exception as erro:
        st.error(f"Não foi possível carregar a carteira: {erro}")
        return

    renderIndicadores(resumo)
    st.divider()
    renderTabela(resumo)

    itens = [i["item"] for i in resumo["itens"]]
    renderAtalhos(itens)
    st.divider()
    renderGerenciamento(usuario["carteiraId"], itens)

    st.caption(
        "As cotações vêm do Yahoo Finance e podem ter atraso. "
        "Este sistema é um protótipo acadêmico e não constitui aconselhamento financeiro."
    )
