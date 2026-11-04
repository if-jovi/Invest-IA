import streamlit as st
from src.controllers.AuthController import AuthController

PAINEL = """
<div class="ia-painel-login">
  <div>
    <div class="ia-marca"><div class="ia-marca-icone">IA</div>InvestIA</div>
    <h1>Invista com <span class="ia-destaque">clareza</span>.</h1>
    <p>Recomendações de ações da B3 explicadas em linguagem simples.</p>
    <ul class="ia-recursos">
      <li><span class="ia-ponto">1</span><div><strong>Análise por IA</strong><br>
        RSI, MACD e médias móveis traduzidos em COMPRA, VENDA ou MANTER.</div></li>
      <li><span class="ia-ponto">2</span><div><strong>Carteira com cotação</strong><br>
        Acompanhe preço médio, resultado e a variação do dia dos seus ativos.</div></li>
      <li><span class="ia-ponto">3</span><div><strong>Backtesting</strong><br>
        Veja como a estratégia teria se saído no histórico do ativo.</div></li>
    </ul>
  </div>
  <div class="ia-rodape-login">Protótipo acadêmico de apoio à decisão — não é recomendação de investimento.</div>
</div>
"""


def entrar(controller: AuthController) -> None:
    with st.form("formLogin", border=False):
        email = st.text_input("Email", key="loginEmail", placeholder="voce@email.com")
        senha = st.text_input("Senha", type="password", key="loginSenha")
        enviar = st.form_submit_button("Entrar", width="stretch", type="primary")

    if enviar:
        try:
            st.session_state["usuario"] = controller.login(email, senha)
        except ValueError as erro:
            st.error(str(erro))
        else:
            st.rerun()


def cadastrar(controller: AuthController) -> None:
    with st.form("formCadastro", border=False):
        nome = st.text_input("Nome", key="cadastroNome")
        email = st.text_input("Email", key="cadastroEmail", placeholder="voce@email.com")
        senha = st.text_input("Senha", type="password", key="cadastroSenha", help="Mínimo de 6 caracteres.")
        confirmarSenha = st.text_input("Confirmar senha", type="password", key="cadastroConfirmarSenha")
        enviar = st.form_submit_button("Criar conta", width="stretch", type="primary")

    if enviar:
        try:
            st.session_state["usuario"] = controller.cadastrar(nome, email, senha, confirmarSenha)
        except ValueError as erro:
            st.error(str(erro))
        else:
            st.rerun()


def renderLogin() -> None:
    painel, formulario = st.columns([1.1, 1], gap="large", vertical_alignment="center")
    painel.markdown(PAINEL, unsafe_allow_html=True)

    with formulario:
        st.markdown(
            '<div class="ia-form-titulo"><h2>Bem-vindo(a)</h2>'
            "<p>Entre na sua conta ou crie uma nova para começar.</p></div>",
            unsafe_allow_html=True,
        )
        controller = AuthController()
        abaLogin, abaCadastro = st.tabs(["Entrar", "Criar conta"])
        with abaLogin:
            entrar(controller)
        with abaCadastro:
            cadastrar(controller)
