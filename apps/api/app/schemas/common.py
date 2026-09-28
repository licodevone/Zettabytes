from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """Base de todos os schemas: lê atributos de ORM e rejeita campos desconhecidos na entrada."""

    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)


class ErrorResponse(BaseModel):
    detail: str


class Message(BaseModel):
    message: str
