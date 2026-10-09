from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeituraSessao(BaseModel):
    """Sessão como chega do carregador / SEMS Portal."""

    id_externo: str
    numero_serie_carregador: str
    rfid_tag: str
    inicio: datetime
    fim_recarga: datetime
    fim: datetime
    energia_kwh: float = Field(ge=0)

    @model_validator(mode="after")
    def validar_ordem(self):
        if not (self.inicio <= self.fim_recarga <= self.fim):
            raise ValueError("É preciso que inicio <= fim_recarga <= fim")
        return self


class UsuarioCriar(BaseModel):
    nome: str
    email: str
    apartamento: str
    rfid_tag: str


class UsuarioSaida(UsuarioCriar):
    model_config = ConfigDict(from_attributes=True)
    id: str


class CarregadorSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    modelo: str
    numero_serie: str
    potencia_kw: float
    status: str
    localizacao: str


class SessaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    id_externo: str
    usuario_id: str
    carregador_id: str
    inicio: datetime
    fim_recarga: datetime
    fim: datetime
    energia_kwh: float
    custo_energia: float
    custo_ocupacao: float
    custo: float
    status: str
    score_anomalia: float | None
    motivo_revisao: str | None
    observacao_gestor: str | None


class Revisao(BaseModel):
    decisao: Literal["aprovar", "rejeitar"]
    observacao: str | None = None


class Pergunta(BaseModel):
    usuario_id: str
    pergunta: str
