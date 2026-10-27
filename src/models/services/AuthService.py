import hashlib
import hmac
import os
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from src.models.base import Session
from src.models.entities.UsuariosEntity import UsuariosEntity
from src.models.entities.CarteirasEntity import CarteirasEntity

ITERACOES = 200000
HASH_FALSO = "00" * 16 + "$" + "00" * 32


class AuthService:

    def gerarHashSenha(self, senha: str) -> str:
        salt = os.urandom(16)
        hashSenha = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, ITERACOES)
        return f"{salt.hex()}${hashSenha.hex()}"

    def verificarSenha(self, senha: str, senhaHash: str) -> bool:
        try:
            salt, hashArmazenado = senhaHash.split("$")
            hashCalculado = hashlib.pbkdf2_hmac(
                "sha256", senha.encode("utf-8"), bytes.fromhex(salt), ITERACOES
            ).hex()
        except ValueError:
            return False
        return hmac.compare_digest(hashCalculado, hashArmazenado)

    def paraDto(self, usuario: UsuariosEntity) -> dict:
        return {
            "id": usuario.getId(),
            "nome": usuario.getNome(),
            "email": usuario.getEmail(),
            "carteiraId": usuario.getCarteira().getId(),
        }

    def cadastrar(self, nome: str, email: str, senha: str) -> dict:
        try:
            with Session() as session:
                if session.query(UsuariosEntity).filter_by(email=email).first() is not None:
                    raise ValueError("Este email já está cadastrado.")

                usuario = UsuariosEntity(
                    nome=nome, email=email, senha_hash=self.gerarHashSenha(senha)
                )
                usuario.carteira = CarteirasEntity(nome="Minha carteira")

                session.add(usuario)
                session.commit()
                return self.paraDto(usuario)
        except IntegrityError:
            raise ValueError("Este email já está cadastrado.")

    def login(self, email: str, senha: str) -> dict:
        with Session() as session:
            usuario = (
                session.query(UsuariosEntity)
                .options(joinedload(UsuariosEntity.carteira))
                .filter_by(email=email)
                .first()
            )
            if usuario is None:
                self.verificarSenha(senha, HASH_FALSO)
                raise ValueError("Email ou senha inválidos.")
            if not self.verificarSenha(senha, usuario.getSenhaHash()):
                raise ValueError("Email ou senha inválidos.")
            return self.paraDto(usuario)
