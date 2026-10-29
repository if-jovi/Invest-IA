import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from src.models.Parametros import SMA_SHORT, SMA_LONG


def renderGraficoTecnico(historico: pd.DataFrame, item: str) -> None:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.25, 0.20],
        subplot_titles=(f"Preço e médias móveis - {item}", "MACD", "RSI"),
        vertical_spacing=0.05,
    )

    fig.add_trace(
        go.Candlestick(
            x=historico.index,
            open=historico["Open"],
            high=historico["High"],
            low=historico["Low"],
            close=historico["Close"],
            name="Preço",
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=historico.index,
            y=historico[f"SMA{SMA_SHORT}"],
            name=f"Média {SMA_SHORT}",
            line=dict(color="orange", width=1.5),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=historico.index,
            y=historico[f"SMA{SMA_LONG}"],
            name=f"Média {SMA_LONG}",
            line=dict(color="#1565C0", width=1.5),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=historico.index,
            y=historico["MACD"],
            name="MACD",
            line=dict(color="purple"),
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=historico.index,
            y=historico["MACD_Sig"],
            name="Sinal",
            line=dict(color="red", dash="dash"),
        ),
        row=2,
        col=1,
    )
    cores = ["#26a69a" if valor >= 0 else "#ef5350" for valor in historico["MACD_Hist"]]
    fig.add_trace(
        go.Bar(
            x=historico.index,
            y=historico["MACD_Hist"],
            name="Histograma",
            marker_color=cores,
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=historico.index,
            y=historico["RSI"],
            name="RSI",
            line=dict(color="#2E7D32"),
        ),
        row=3,
        col=1,
    )
    fig.add_hline(y=70, line=dict(color="red", dash="dot", width=1), row=3, col=1)
    fig.add_hline(y=30, line=dict(color="blue", dash="dot", width=1), row=3, col=1)

    fig.update_layout(
        height=700, template="plotly_white", xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)


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
            line=dict(color="green", width=2),
        )
    )
    fig.add_hline(y=0, line=dict(color="gray", dash="dash"))
    fig.update_layout(
        title=f"Retorno acumulado do backtesting - {item}",
        xaxis_title="Operação",
        yaxis_title="Retorno acumulado (%)",
        template="plotly_white",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)
