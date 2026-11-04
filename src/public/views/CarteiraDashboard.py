from html import escape
import pandas as pd
import streamlit as st
from src.controllers.CarteiraController import CarteiraController
from src.controllers.ItensCarteiraController import ItensCarteiraController
from src.public.views import Estilo, Paginas, Seletores
from src.public.views.charts import renderGraficoAlocacao
from src.public.views.Formatacao import moeda, variacao, quantidade, dataBr, hora

INTERVALO_ATUALIZACAO = 60

COLUNAS_TABELA = {
    "Código": st.column_config.TextColumn(width="small", pinned=True),
    "Empresa": st.column_config.TextColumn(width="medium"),
    "Quantidade": st.column_config.TextColumn(width="small"),
    "Preço médio": st.column_config.TextColumn(width="small"),
    "Cotação": st.column_config.TextColumn(width="small"),
    "Variação do dia": st.column_config.TextColumn(width="small"),
    "Resultado": st.column_config.TextColumn(width="small"),
    "Resultado (%)": st.column_config.TextColumn(width="small"),
    "Recomendação": st.column_config.TextColumn(width="small"),
}


def renderCards(resumo: dict) -> None:
    linha = st.columns(5)
    linha[0].metric("Valor investido", moeda(resumo["valorInvestido"]))
    linha[1].metric("Valor atual", moeda(resumo["valorAtual"]))
    linha[2].metric(
        "Resultado",
        moeda(resumo["resultado"]),
        delta=variacao(resumo["resultadoPct"]) if resumo["resultadoPct"] is not None else None,
    )
    linha[3].metric(
        "Variação do dia",
        variacao(resumo["variacaoDia"]),
        delta=moeda(ganhoDoDia(resumo["itens"])) if resumo["variacaoDia"] is not None else None,
    )
    linha[4].metric("Ativos na carteira", len(resumo["itens"]))


def ganhoDoDia(itens: list) -> float:
    return sum(
        i["quantidade"] * (i["cotacao"] - i["fechamentoAnterior"])
        for i in itens
        if i.get("cotacao") is not None and i.get("fechamentoAnterior")
    )


def legendaCotacoes(resumo: dict) -> str:
    partes = [f"Cotações do Yahoo Finance com atraso de até 15 min · atualizado às {hora(resumo['atualizadoEm'])}"]
    if resumo["semCotacao"]:
        partes.append(
            f"{resumo['semCotacao']} ativo(s) sem cotação disponível; eles não entram no valor atual nem no resultado"
        )
    if resumo["cotacoesDesatualizadas"]:
        partes.append(f"{resumo['cotacoesDesatualizadas']} ativo(s) com cotação desatualizada")
    return " · ".join(partes)


def colorirResultado(valor: str) -> str:
    if not isinstance(valor, str) or valor == "-":
        return ""
    if valor.startswith(("-R$", "-")):
        return f"color: {Estilo.VERMELHO}; font-weight: 600"
    if valor.startswith("+") or (valor.startswith("R$") and valor != "R$ 0,00"):
        return f"color: {Estilo.VERDE}; font-weight: 600"
    return ""


def colorirRecomendacao(valor: str) -> str:
    if valor in Estilo.CORES_RECOMENDACAO:
        return f"color: {Estilo.corRecomendacao(valor)}; font-weight: 700"
    return ""


def renderTabela(itens: list) -> None:
    linhas = [
        {
            "Código": i["item"],
            "Empresa": i["nome"],
            "Quantidade": quantidade(i["quantidade"]),
            "Preço médio": moeda(i["precoMedio"]),
            "Cotação": moeda(i["cotacao"]) + (" *" if i.get("desatualizada") else ""),
            "Variação do dia": variacao(i["variacaoDia"]),
            "Resultado": moeda(i["resultado"]),
            "Resultado (%)": variacao(i["resultadoPct"]),
            "Recomendação": i["recomendacao"] or "Sem análise",
            "Valor atual": moeda(i["valorAtual"]),
            "Setor": i["setor"] or "-",
            "Data da análise": dataBr(i["dataRecomendacao"]),
        }
        for i in itens
    ]
    tabela = (
        pd.DataFrame(linhas)
        .style.map(colorirResultado, subset=["Variação do dia", "Resultado", "Resultado (%)"])
        .map(colorirRecomendacao, subset=["Recomendação"])
    )
    st.dataframe(tabela, width="stretch", hide_index=True, column_config=COLUNAS_TABELA)


def renderVazio() -> None:
    st.markdown(
        '<div class="ia-vazio"><div class="ia-vazio-icone">📈</div>'
        "<h3>Sua carteira ainda está vazia</h3>"
        "<p>Registre a sua primeira compra em <strong>Gerenciar posições</strong>, logo abaixo, "
        "para acompanhar cotação, resultado e recomendações.</p></div>",
        unsafe_allow_html=True,
    )


@st.fragment(run_every=INTERVALO_ATUALIZACAO)
def renderPainel(carteiraId: int) -> None:
    topo = st.columns([4, 1], vertical_alignment="center")
    forcar = topo[1].button("Atualizar cotações", icon=":material/refresh:", width="stretch")

    try:
        resumo = CarteiraController().obterResumo(carteiraId, forcar=forcar)
    except Exception as erro:
        st.error(f"Não foi possível carregar a carteira: {erro}")
        return

    topo[0].caption(legendaCotacoes(resumo))
    if not resumo["itens"]:
        renderVazio()
        return

    renderCards(resumo)
    tabela, grafico = st.columns([1.9, 1], gap="medium")
    with tabela:
        st.subheader("Posições")
        renderTabela(resumo["itens"])
        if resumo["cotacoesDesatualizadas"]:
            st.caption("* cotação desatualizada (última conhecida).")
    with grafico:
        renderGraficoAlocacao(resumo["itens"])


def renderAtalhos(itens: list) -> None:
    if not itens:
        return

    with st.container(border=True):
        st.markdown("**Análise rápida** — escolha um ativo da carteira")
        colunas = st.columns([2, 1, 1], vertical_alignment="bottom")
        escolhido = colunas[0].selectbox("Ativo da carteira", itens, key="atalhoItem")
        if colunas[1].button("Analisar", key="atalhoAnalisar", icon=":material/insights:", width="stretch"):
            Paginas.irPara(Paginas.ANALISE, Paginas.CHAVE_ANALISE, [escolhido])
        if colunas[2].button("Backtesting", key="atalhoBacktest", icon=":material/history:", width="stretch"):
            Paginas.irPara(Paginas.BACKTESTING, Paginas.CHAVE_BACKTEST, escolhido)


def executar(acao, mensagem: str, codigo: str = None) -> None:
    try:
        with st.spinner("Processando..."):
            acao()
    except (ValueError, RuntimeError) as erro:
        st.error(str(erro))
        return
    if codigo:
        Seletores.atualizarSeNovos([codigo])
    Paginas.agendarMensagem("sucesso", mensagem)
    st.rerun()


def codigoDe(item) -> str:
    valor = (item or "").strip().upper()
    return valor[:-3] if valor.endswith(".SA") else valor


def renderCompra(carteiraId: int, controller: ItensCarteiraController) -> None:
    with st.form("formCompra", clear_on_submit=True, border=False):
        item = Seletores.seletorAtivo("Ativo", key="compraItem")
        colunas = st.columns(2)
        qtd = colunas[0].number_input("Quantidade", min_value=1, value=100, step=1, key="compraQuantidade")
        preco = colunas[1].number_input(
            "Preço unitário (R$)", min_value=0.01, value=10.00, step=0.01, format="%.2f", key="compraPreco"
        )
        enviar = st.form_submit_button("Registrar compra", type="primary")

    if enviar:
        executar(
            lambda: controller.adicionarCompra(carteiraId, item, qtd, preco),
            f"Compra de {qtd} unidade(s) de {codigoDe(item)} registrada.",
            codigoDe(item),
        )


def renderVenda(carteiraId: int, itens: list, controller: ItensCarteiraController) -> None:
    if not itens:
        st.info("Nenhum ativo na carteira.")
        return

    with st.form("formVenda", clear_on_submit=True, border=False):
        item = st.selectbox("Ativo", itens, key="vendaItem")
        qtd = st.number_input("Quantidade vendida", min_value=1, value=1, step=1, key="vendaQuantidade")
        enviar = st.form_submit_button("Registrar venda", type="primary")

    if enviar:
        executar(
            lambda: controller.registrarVenda(carteiraId, item, qtd),
            f"Venda de {qtd} unidade(s) de {item} registrada.",
        )


def renderCorrecao(carteiraId: int, itens: list, controller: ItensCarteiraController) -> None:
    if not itens:
        st.info("Nenhum ativo na carteira.")
        return

    with st.form("formCorrecao", clear_on_submit=True, border=False):
        item = st.selectbox("Ativo", itens, key="correcaoItem")
        colunas = st.columns(2)
        qtd = colunas[0].number_input("Nova quantidade", min_value=1, value=100, step=1)
        precoMedio = colunas[1].number_input(
            "Novo preço médio (R$)", min_value=0.01, value=10.00, step=0.01, format="%.2f"
        )
        enviar = st.form_submit_button("Corrigir posição", type="primary")

    if enviar:
        executar(
            lambda: controller.definirPosicao(carteiraId, item, qtd, precoMedio),
            f"Posição de {item} corrigida.",
        )


def renderRemocao(carteiraId: int, itens: list, controller: ItensCarteiraController) -> None:
    if not itens:
        st.info("Nenhum ativo na carteira.")
        return

    with st.form("formRemocao", clear_on_submit=True, border=False):
        item = st.selectbox("Ativo", itens, key="remocaoItem")
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
    with st.container(border=True):
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
    primeiroNome = usuario["nome"].split()[0] if usuario["nome"].strip() else usuario["nome"]
    st.markdown(
        f'<div class="ia-cabecalho"><h1>Olá, {escape(primeiroNome)}</h1>'
        "<p>Sua carteira com cotações atualizadas automaticamente a cada minuto.</p></div>",
        unsafe_allow_html=True,
    )
    Paginas.exibirMensagem()

    renderPainel(usuario["carteiraId"])

    itens = ItensCarteiraController().listarItens(usuario["carteiraId"])
    renderAtalhos(itens)
    renderGerenciamento(usuario["carteiraId"], itens)

    st.caption(
        "Este sistema é um protótipo acadêmico e não constitui aconselhamento financeiro."
    )
