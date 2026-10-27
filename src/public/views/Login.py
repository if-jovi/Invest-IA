import streamlit as st
from src.controllers.AuthController import AuthController


def renderLogin() -> None:
    st.title("InvestIA")
    st.caption("Sistema Inteligente de Recomendação de Investimentos")

    abaLogin, abaCadastro = st.tabs(["Entrar", "Criar conta"])
    controller = AuthController()

    with abaLogin:
        with st.form("formLogin"):
            email = st.text_input("Email", key="loginEmail")
            senha = st.text_input("Senha", type="password", key="loginSenha")
            enviar = st.form_submit_button("Entrar", use_container_width=True, type="primary")

        if enviar:
            try:
                st.session_state["usuario"] = controller.login(email, senha)
            except ValueError as erro:
                st.error(str(erro))
            else:
                st.rerun()

    with abaCadastro:
        with st.form("formCadastro"):
            nome = st.text_input("Nome", key="cadastroNome")
            email = st.text_input("Email", key="cadastroEmail")
            senha = st.text_input("Senha", type="password", key="cadastroSenha")
            confirmarSenha = st.text_input(
                "Confirmar senha", type="password", key="cadastroConfirmarSenha"
            )
            enviar = st.form_submit_button("Criar conta", use_container_width=True, type="primary")

        if enviar:
            try:
                st.session_state["usuario"] = controller.cadastrar(
                    nome, email, senha, confirmarSenha
                )
            except ValueError as erro:
                st.error(str(erro))
            else:
                st.rerun()
