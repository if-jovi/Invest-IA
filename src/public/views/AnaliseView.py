import pandas as pd
import streamlit as st
from config.settings import SMA_SHORT, SMA_LONG
from src.controllers.AnaliseController import AnaliseController
from src.controllers.ItensCarteiraController import ItensCarteiraController
from src.public.views import Paginas
from src.public.views.charts import renderGraficoTecnico
from src.public.views.Formatacao import moeda, dataBr, dataHora

ROTULOS_PERIODO = {"3mo": "3 meses", "6mo": "6 meses", "1y": "1 ano", "2y": "2 anos"}


def renderIntroducao() -> None:
    st.info("Informe o código de uma ação da B3 e clique em Analisar.")
    st.markdown(
        """
| Etapa | O que acontece |
|-------|----------------|
| 1. Entrada | Você informa o código do ativo (ex.: PETR4) |
| 2. Coleta | O histórico de preços é obtido pelo yfinance |
| 3. Indicadores | RSI, MACD e médias móveis são calculados |
| 4. Interpretação | A IA traduz os indicadores em linguagem simples |
| 5. Resultado | COMPRA, VENDA ou MANTER, com a justificativa |
"""
    )


def renderRecomendacao(recomendacao: dict, doCache: bool) -> None:
    tipo = recomendacao["recomendacao"]
    texto = f"Recomendação: {tipo}"
    if tipo == "COMPRA":
        st.success(texto)
    elif tipo == "VENDA":
        st.error(texto)
    else:
        st.warning(texto)

    if doCache:
        st.caption(
            f"Recomendação reaproveitada, gerada em {dataHora(recomendacao['geradoEm'])} "
            "para esta mesma data de referência. Marque 'Gerar nova análise' para solicitar outra."
        )

    if recomendacao["sobreEmpresa"]:
        with st.expander("Sobre a empresa", expanded=True):
            st.markdown(recomendacao["sobreEmpresa"])

    with st.expander("Por que esta recomendação?", expanded=True):
        st.markdown(recomendacao["justificativa"])

    if recomendacao["riscos"]:
        with st.expander("Riscos identificados"):
            st.markdown(recomendacao["riscos"])


def renderIndicadores(ind) -> None:
    st.subheader("Indicadores técnicos")
    colunas = st.columns(4)
    colunas[0].metric("RSI (14)", f"{ind.rsi}", delta=ind.sinal_rsi, delta_color="off")
    colunas[1].metric(
        "MACD", f"{ind.macd:.4f}", delta=f"cruzamento de {ind.macd_cruzamento}", delta_color="off"
    )
    colunas[2].metric(f"Média {SMA_SHORT}", moeda(ind.sma_short))
    colunas[3].metric(
        f"Média {SMA_LONG}", moeda(ind.sma_long), delta=f"tendência de {ind.tendencia_sma}", delta_color="off"
    )

    with st.expander("Como ler estes indicadores"):
        st.markdown(
            "- **RSI**: mede a força dos movimentos de preço. Acima de 70 indica possível sobrecompra "
            "(ativo esticado); abaixo de 30 indica possível sobrevenda (ativo barato no curto prazo).\n"
            "- **MACD**: compara médias móveis exponenciais para mostrar o momento do preço. "
            "O cruzamento de alta sugere força compradora; o de baixa, força vendedora.\n"
            f"- **Médias móveis ({SMA_SHORT} e {SMA_LONG} períodos)**: suavizam o preço. "
            "Média curta acima da longa indica tendência de alta; abaixo, tendência de baixa."
        )


def renderHistorico(controller: AnaliseController, item: str) -> None:
    historico = controller.buscarHistorico(item)
    if not historico:
        return

    st.subheader("Histórico de recomendações")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Data de referência": dataBr(h["dataReferencia"]),
                    "Recomendação": h["recomendacao"],
                    "Preço": h["precoAtual"],
                    "RSI": h["rsi"],
                    "Gerada em": dataHora(h["geradoEm"]),
                }
                for h in historico
            ]
        ),
        use_container_width=True,
        hide_index=True,
        column_config={"Preço": st.column_config.NumberColumn(format="R$ %.2f")},
    )


def renderRegistroCompra(usuario: dict, item: str) -> None:
    with st.expander("Registrar compra deste ativo na carteira"):
        with st.form("formCompraAnalise", clear_on_submit=True):
            quantidade = st.number_input("Quantidade", min_value=1, value=100, step=1)
            preco = st.number_input(
                "Preço unitário (R$)", min_value=0.01, value=10.00, step=0.01, format="%.2f"
            )
            enviar = st.form_submit_button("Registrar compra", type="primary")

        if enviar:
            try:
                ItensCarteiraController().adicionarCompra(
                    usuario["carteiraId"], item, quantidade, preco
                )
            except (ValueError, RuntimeError) as erro:
                st.error(str(erro))
            else:
                st.success(f"Compra de {quantidade} unidade(s) de {item} registrada na carteira.")


def renderResultado(controller: AnaliseController, resultado: dict, usuario: dict) -> None:
    ativo, ind = resultado["ativo"], resultado["indicadores"]

    colunas = st.columns([2, 1, 1])
    colunas[0].subheader(f"{ativo['nome']} ({ativo['item']})")
    colunas[0].caption(f"Setor: {ativo['setor']}")
    colunas[1].metric("Preço atual", moeda(ind.preco_atual))
    colunas[2].metric("Data de referência", dataBr(ind.data_referencia))

    st.divider()
    renderRecomendacao(resultado["recomendacao"], resultado["doCache"])
    st.divider()
    renderIndicadores(ind)

    st.subheader("Gráfico histórico")
    renderGraficoTecnico(ind.historico, ativo["item"])

    renderHistorico(controller, ativo["item"])
    renderRegistroCompra(usuario, ativo["item"])

    st.warning(
        "Este sistema é um protótipo acadêmico de apoio à decisão e não constitui aconselhamento "
        "financeiro. A decisão final e a responsabilidade pelo investimento são do investidor."
    )


def renderAnalise() -> None:
    usuario = st.session_state["usuario"]
    controller = AnaliseController()

    st.title("Análise de ativo")
    st.caption("Indicadores técnicos interpretados pela IA em linguagem acessível.")

    colunas = st.columns([2, 1, 1])
    item = colunas[0].text_input(
        "Código do ativo na B3", key=Paginas.CHAVE_ANALISE, placeholder="Ex.: PETR4, VALE3, ITUB4"
    )
    periodo = colunas[1].selectbox(
        "Período", list(ROTULOS_PERIODO), index=2, format_func=lambda p: ROTULOS_PERIODO[p]
    )
    forcar = colunas[2].checkbox("Gerar nova análise", help="Ignora a recomendação já gerada hoje.")

    if st.button("Analisar", type="primary"):
        try:
            with st.spinner(f"Analisando {item.strip().upper()}..."):
                st.session_state["analiseResultado"] = controller.analisar(item, periodo, forcar)
        except (ValueError, RuntimeError) as erro:
            st.error(str(erro))
        except Exception as erro:
            st.error(f"Não foi possível concluir a análise: {erro}")

    resultado = st.session_state.get("analiseResultado")
    if resultado is None:
        renderIntroducao()
    else:
        renderResultado(controller, resultado, usuario)
