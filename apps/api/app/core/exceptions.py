"""Exceções de domínio. Os services lançam estas; `main.py` as traduz para HTTP."""


class DomainError(Exception):
    status_code = 400
    default_detail = "Requisição inválida"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(DomainError):
    status_code = 404
    default_detail = "Recurso não encontrado"


class ConflictError(DomainError):
    status_code = 409
    default_detail = "Conflito com o estado atual do recurso"


class AuthenticationError(DomainError):
    status_code = 401
    default_detail = "Credenciais inválidas"


class PermissionDeniedError(DomainError):
    status_code = 403
    default_detail = "Permissão insuficiente"


class QuotaExceededError(DomainError):
    status_code = 402
    default_detail = "Limite do plano atingido"
