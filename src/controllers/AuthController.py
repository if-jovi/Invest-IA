import re
from src.models.services.AuthService import AuthService

FORMATO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthController:

    def __init__(self):
        self.authService = AuthService()

    def cadastrar(self, nome: str, email: str, senha: str, confirmarSenha: str) -> dict:
        nome = (nome or "").strip()
        email = (email or "").strip().lower()

        if not nome or not email or not senha:
            raise ValueError("Preencha todos os campos.")
        if not FORMATO_EMAIL.match(email):
            raise ValueError("Informe um email válido.")
        if len(senha) < 6:
            raise ValueError("A senha precisa ter no mínimo 6 caracteres.")
        if senha != confirmarSenha:
            raise ValueError("As senhas não coincidem.")

        return self.authService.cadastrar(nome, email, senha)

    def login(self, email: str, senha: str) -> dict:
        email = (email or "").strip().lower()
        if not email or not senha:
            raise ValueError("Preencha email e senha.")
        return self.authService.login(email, senha)
