"""Tabelas do banco. Seguem o modelo da sprint 01 (usuarios, carregadores,
sessoes, faturamento) com campos extras necessários para o rateio e a IA."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    nome: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    apartamento: Mapped[str] = mapped_column(String(20))
    # Tag RFID lida pelo HCA G2: é assim que a sessão é ligada ao usuário
    rfid_tag: Mapped[str] = mapped_column(String(40), unique=True)

    sessoes: Mapped[list["Sessao"]] = relationship(back_populates="usuario")


class Carregador(Base):
    __tablename__ = "carregadores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    modelo: Mapped[str] = mapped_column(String(60))
    numero_serie: Mapped[str] = mapped_column(String(40), unique=True)
    potencia_kw: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="disponivel")
    localizacao: Mapped[str] = mapped_column(String(120))


class Sessao(Base):
    __tablename__ = "sessoes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Identificador da sessão no SEMS Portal; evita importar a mesma sessão duas vezes
    id_externo: Mapped[str] = mapped_column(String(60), unique=True)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    carregador_id: Mapped[str] = mapped_column(ForeignKey("carregadores.id"))

    inicio: Mapped[datetime] = mapped_column(DateTime)
    fim_recarga: Mapped[datetime] = mapped_column(DateTime)  # fim do fluxo de energia
    fim: Mapped[datetime] = mapped_column(DateTime)  # desconexão do veículo
    energia_kwh: Mapped[float] = mapped_column(Float)

    custo_energia: Mapped[float] = mapped_column(Float)
    custo_ocupacao: Mapped[float] = mapped_column(Float)
    custo: Mapped[float] = mapped_column(Float)  # energia + ocupação

    # faturavel | em_revisao | rejeitada
    status: Mapped[str] = mapped_column(String(20), default="faturavel")
    score_anomalia: Mapped[float | None] = mapped_column(Float, nullable=True)
    motivo_revisao: Mapped[str | None] = mapped_column(String(300), nullable=True)
    observacao_gestor: Mapped[str | None] = mapped_column(String(300), nullable=True)

    usuario: Mapped[Usuario] = relationship(back_populates="sessoes")
    carregador: Mapped[Carregador] = relationship()


class Faturamento(Base):
    """Fechamento mensal do rateio, gravado quando o gestor fecha o mês."""

    __tablename__ = "faturamento"
    __table_args__ = (UniqueConstraint("usuario_id", "mes"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    usuario_id: Mapped[str] = mapped_column(ForeignKey("usuarios.id"))
    mes: Mapped[str] = mapped_column(String(7))  # AAAA-MM
    energia_kwh: Mapped[float] = mapped_column(Float)
    valor_energia: Mapped[float] = mapped_column(Float)
    valor_ocupacao: Mapped[float] = mapped_column(Float)
    valor_manutencao: Mapped[float] = mapped_column(Float)
    valor_total: Mapped[float] = mapped_column(Float)
    status_pagamento: Mapped[str] = mapped_column(String(20), default="pendente")
    gerado_em: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
