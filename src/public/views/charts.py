import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from src.models.Parametros import SMA_SHORT, SMA_LONG, RSI_OVERBOUGHT, RSI_OVERSOLD
from src.public.views import Estilo

FONTE = dict(family="Inter, sans-serif", color=Estilo.CINZA_TEXTO)
GRADE = "rgba(101, 20, 36, 0.08)"


def layoutBase(fig: go.Figure, altura: int) -> None:
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=FONTE,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor=Estilo.BRANCO, font=FONTE),
        separators=",.",
    )
    fig.update_xaxes(gridcolor=GRADE, zeroline=False)
    fig.update_yaxes(gridcolor=GRADE, zeroline=False)


def renderGraficoTecnico(historico: pd.DataFrame, item: str) -> None:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.25, 0.20],
        subplot_titles=(f"Preço e médias móveis — {item}", "MACD", "RSI"),
        vertical_spacing=0.06,
    )

    fig.add_trace(
        go.Candlestick(
            x=historico.index,
            open=historico["Open"],
            high=historico["High"],
            low=historico["Low"],
            close=historico["Close"],
            name="Preço",
            increasing_line_color=Estilo.VERDE,
            decreasing_line_color=Estilo.VERMELHO,
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=historico.index, y=historico[f"SMA{SMA_SHORT}"], name=f"Média {SMA_SHORT}",
                   line=dict(color=Estilo.LARANJA, width=1.8)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=historico.index, y=historico[f"SMA{SMA_LONG}"], name=f"Média {SMA_LONG}",
                   line=dict(color=Estilo.VINHO, width=1.8)),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(x=historico.index, y=historico["MACD"], name="MACD",
                   line=dict(color=Estilo.VINHO, width=1.6)),
        row=2, col=1,
    )
    fig.add_trace(
        go.Scatter(x=historico.index, y=historico["MACD_Sig"], name="Sinal",
                   line=dict(color=Estilo.LARANJA, width=1.4, dash="dash")),
        row=2, col=1,
    )
    cores = [Estilo.VERDE if valor >= 0 else Estilo.VERMELHO for valor in historico["MACD_Hist"]]
    fig.add_trace(
        go.Bar(x=historico.index, y=historico["MACD_Hist"], name="Histograma", marker_color=cores, opacity=0.6),
        row=2, col=1,
    )

    fig.add_hrect(y0=RSI_OVERBOUGHT, y1=100, fillcolor=Estilo.VERMELHO, opacity=0.08, line_width=0, row=3, col=1)
    fig.add_hrect(y0=0, y1=RSI_OVERSOLD, fillcolor=Estilo.VERDE, opacity=0.08, line_width=0, row=3, col=1)
    fig.add_trace(
        go.Scatter(x=historico.index, y=historico["RSI"], name="RSI",
                   line=dict(color=Estilo.VINHO_ESCURO, width=1.6)),
        row=3, col=1,
    )
    fig.add_hline(y=RSI_OVERBOUGHT, line=dict(color=Estilo.VERMELHO, dash="dot", width=1), row=3, col=1)
    fig.add_hline(y=RSI_OVERSOLD, line=dict(color=Estilo.VERDE, dash="dot", width=1), row=3, col=1)
    fig.update_yaxes(range=[0, 100], row=3, col=1)

    layoutBase(fig, 720)
    fig.update_layout(xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, width="stretch", key=f"graficoTecnico{item}")


def renderGraficoBacktesting(curvaAcumulada: list, item: str) -> None:
    if not curvaAcumulada:
        st.info("Nenhuma operação simulada no período selecionado.")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(range(1, len(curvaAcumulada) + 1)),
            y=curvaAcumulada,
            mode="lines+markers",
            name="Retorno acumulado (%)",
            line=dict(color=Estilo.VINHO, width=2.5),
            marker=dict(color=Estilo.LARANJA, size=7),
            fill="tozeroy",
            fillcolor="rgba(255, 88, 37, 0.12)",
        )
    )
    fig.add_hline(y=0, line=dict(color=Estilo.CINZA_BORDA, dash="dash"))
    layoutBase(fig, 380)
    fig.update_layout(
        title=f"Retorno acumulado — {item}",
        xaxis_title="Operação",
        yaxis_title="Retorno acumulado (%)",
    )
    st.plotly_chart(fig, width="stretch", key=f"graficoBacktest{item}")


def renderGraficoAlocacao(itens: list) -> None:
    valores = {}
    for i in itens:
        valor = i["valorAtual"] if i.get("valorAtual") is not None else i["valorInvestido"]
        setor = i.get("setor") or "Não disponível"
        valores[setor] = valores.get(setor, 0) + valor
    if not valores:
        return

    fig = go.Figure(
        go.Pie(
            labels=list(valores),
            values=list(valores.values()),
            hole=0.62,
            sort=True,
            marker=dict(colors=Estilo.SEQUENCIA_GRAFICO, line=dict(color=Estilo.BRANCO, width=2)),
            textinfo="percent",
            hovertemplate="%{label}<br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
        )
    )
    layoutBase(fig, 340)
    fig.update_layout(
        title="Alocação por setor",
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, x=1.02),
        annotations=[dict(text=f"{len(itens)}<br>ativos", showarrow=False, font=dict(size=18, color=Estilo.VINHO))],
    )
    st.plotly_chart(fig, width="stretch", key="graficoAlocacao")
