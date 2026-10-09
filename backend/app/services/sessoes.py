"""Registro de sessões: o fluxo principal do sistema.

    leitura do carregador -> identifica usuário (RFID) -> IA de anomalias
    -> cálculo do custo (tarifa por horário + ocupação pela demanda prevista)
    -> grava com status "faturavel" ou "em_revisao"
"""

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ia.anomalias import extrair_features
from app.ia.motor import motor
from app.models import Carregador, Sessao, Usuario
from app.schemas import LeituraSessao
from app.services.rateio import calcular_custo_sessao


class ErroRegistro(Exception):
    pass


def registrar_sessao(db: Session, leitura: LeituraSessao) -> tuple[Sessao, dict]:
    existente = db.scalar(select(Sessao).where(Sessao.id_externo == leitura.id_externo))
    if existente:
        raise ErroRegistro(f"Sessão {leitura.id_externo} já registrada")

    usuario = db.scalar(select(Usuario).where(Usuario.rfid_tag == leitura.rfid_tag))
    if usuario is None:
        raise ErroRegistro(f"Tag RFID {leitura.rfid_tag} não pertence a nenhum usuário")
    carregador = db.scalar(select(Carregador).where(Carregador.numero_serie == leitura.numero_serie_carregador))
    if carregador is None:
        raise ErroRegistro(f"Carregador {leitura.numero_serie_carregador} não cadastrado")

    features = extrair_features(leitura.inicio, leitura.fim_recarga, leitura.fim, leitura.energia_kwh)
    analise = motor.detector.avaliar(features, carregador.potencia_kw)

    custo = calcular_custo_sessao(
        leitura.inicio, leitura.fim_recarga, leitura.fim, leitura.energia_kwh,
        nivel_demanda=motor.previsor.nivel,
    )

    sessao = Sessao(
        id_externo=leitura.id_externo,
        usuario_id=usuario.id,
        carregador_id=carregador.id,
        inicio=leitura.inicio,
        fim_recarga=leitura.fim_recarga,
        fim=leitura.fim,
        energia_kwh=leitura.energia_kwh,
        custo_energia=custo.custo_energia,
        custo_ocupacao=custo.custo_ocupacao,
        custo=custo.custo_total,
        status="em_revisao" if analise.anomala else "faturavel",
        score_anomalia=analise.score,
        motivo_revisao="; ".join(analise.motivos) or None,
    )
    db.add(sessao)
    db.commit()

    detalhes = {
        "custo": asdict(custo) | {"custo_total": custo.custo_total},
        "ia": {
            "anomala": analise.anomala,
            "score": analise.score,
            "motivos": analise.motivos,
            "modelo_anomalias_treinado": motor.detector.treinado,
            "modelo_demanda_treinado": motor.previsor.treinado,
        },
    }
    return sessao, detalhes


def revisar_sessao(db: Session, sessao: Sessao, decisao: str, observacao: str | None) -> Sessao:
    """Decisão do gestor sobre uma sessão barrada pela IA."""
    if sessao.status != "em_revisao":
        raise ErroRegistro("Só sessões em revisão podem ser aprovadas ou rejeitadas")
    sessao.status = "faturavel" if decisao == "aprovar" else "rejeitada"
    sessao.observacao_gestor = observacao
    db.commit()
    return sessao
