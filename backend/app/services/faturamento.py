"""Rateio mensal: soma as sessões faturáveis de cada usuário e divide o custo de
manutenção entre quem usou o carregador no mês."""

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import config
from app.models import Faturamento, Sessao, Usuario
from app.services.rateio import dividir_em_centavos


def limites_do_mes(mes: str) -> tuple[datetime, datetime]:
    ano, m = map(int, mes.split("-"))
    inicio = datetime(ano, m, 1)
    fim = datetime(ano + (m == 12), m % 12 + 1, 1)
    return inicio, fim


def sessoes_do_mes(db: Session, mes: str, status: str | None = None, usuario_id: str | None = None):
    inicio, fim = limites_do_mes(mes)
    consulta = select(Sessao).where(Sessao.inicio >= inicio, Sessao.inicio < fim).order_by(Sessao.inicio)
    if status:
        consulta = consulta.where(Sessao.status == status)
    if usuario_id:
        consulta = consulta.where(Sessao.usuario_id == usuario_id)
    return db.scalars(consulta).all()


def calcular_rateio_mensal(db: Session, mes: str) -> dict:
    faturaveis = sessoes_do_mes(db, mes, status="faturavel")
    em_revisao = sessoes_do_mes(db, mes, status="em_revisao")

    por_usuario = defaultdict(list)
    for s in faturaveis:
        por_usuario[s.usuario_id].append(s)

    usuarios = {u.id: u for u in db.scalars(select(Usuario)).all()}
    ativos = sorted(por_usuario, key=lambda uid: usuarios[uid].apartamento)
    cotas = dividir_em_centavos(config.custo_manutencao_mensal, len(ativos))

    itens = []
    for uid, cota in zip(ativos, cotas):
        sessoes = por_usuario[uid]
        energia = round(sum(s.custo_energia for s in sessoes), 2)
        ocupacao = round(sum(s.custo_ocupacao for s in sessoes), 2)
        itens.append({
            "usuario_id": uid,
            "nome": usuarios[uid].nome,
            "apartamento": usuarios[uid].apartamento,
            "sessoes": len(sessoes),
            "energia_kwh": round(sum(s.energia_kwh for s in sessoes), 2),
            "valor_energia": energia,
            "valor_ocupacao": ocupacao,
            "valor_manutencao": cota,
            "valor_total": round(energia + ocupacao + cota, 2),
            "sessoes_em_revisao": sum(1 for s in em_revisao if s.usuario_id == uid),
        })

    return {
        "mes": mes,
        "usuarios_ativos": len(ativos),
        "custo_manutencao_mensal": config.custo_manutencao_mensal,
        "total_energia_kwh": round(sum(i["energia_kwh"] for i in itens), 2),
        "total_arrecadado": round(sum(i["valor_total"] for i in itens), 2),
        "sessoes_em_revisao": len(em_revisao),
        "itens": itens,
    }


def fechar_mes(db: Session, mes: str) -> list[Faturamento]:
    """Grava o rateio do mês na tabela faturamento (substitui um fechamento anterior)."""
    rateio = calcular_rateio_mensal(db, mes)
    for antigo in db.scalars(select(Faturamento).where(Faturamento.mes == mes)).all():
        db.delete(antigo)
    registros = [
        Faturamento(
            usuario_id=i["usuario_id"], mes=mes, energia_kwh=i["energia_kwh"],
            valor_energia=i["valor_energia"], valor_ocupacao=i["valor_ocupacao"],
            valor_manutencao=i["valor_manutencao"], valor_total=i["valor_total"],
        )
        for i in rateio["itens"]
    ]
    db.add_all(registros)
    db.commit()
    return registros
