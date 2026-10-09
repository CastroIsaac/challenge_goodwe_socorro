"""Popula o banco com ~4 meses de histórico simulado.

As sessões passam pelo MESMO fluxo de produção (registrar_sessao), em ordem
cronológica, e os modelos de IA são retreinados a cada 7 dias simulados, como
aconteceria em operação. Sessões do início do histórico, antes de existir
modelo treinado, ficam só com a regra física e a taxa de ocupação base.

Ao final imprime a avaliação do detector de anomalias contra as anomalias que
o simulador injetou de propósito (o sistema não tem acesso a esse gabarito).

Uso:  python -m app.seed
"""

import random
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select

from app.dados_demo import CARREGADORES, PERFIS, USUARIOS, carregadores_simulados
from app.database import Base, SessionLocal, engine
from app.ia.motor import motor
from app.integracoes.sems import gerar_sessoes
from app.models import Carregador, Sessao, Usuario
from app.services.sessoes import registrar_sessao

DIAS_HISTORICO = 120
INTERVALO_RETREINO = timedelta(days=7)


def popular(agora: datetime | None = None, semente: int = 2026, verboso: bool = True) -> dict:
    agora = (agora or datetime.now()).replace(second=0, microsecond=0)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        db.add_all([Usuario(**u) for u in USUARIOS] + [Carregador(**c) for c in CARREGADORES])
        db.commit()

        inicio = (agora - timedelta(days=DIAS_HISTORICO)).date()
        geradas = gerar_sessoes(PERFIS, carregadores_simulados(), inicio, agora, random.Random(semente))

        motor.__init__()  # começa sem modelos, como um sistema recém-instalado
        proximo_retreino = datetime.combine(inicio, datetime.min.time()) + INTERVALO_RETREINO
        gabarito = {}
        for leitura, anomalia_injetada in geradas:
            while leitura.fim >= proximo_retreino:
                motor.treinar(db, ate=proximo_retreino)
                proximo_retreino += INTERVALO_RETREINO
            sessao, detalhes = registrar_sessao(db, leitura)
            gabarito[sessao.id] = (anomalia_injetada, detalhes["ia"]["modelo_anomalias_treinado"])

        resultado_treino = motor.treinar(db)
        avaliacao = avaliar_detector(db, gabarito)

    if verboso:
        print(f"Sessões geradas: {len(geradas)} ({inicio} a {agora:%Y-%m-%d})")
        print(f"Treino final: {resultado_treino}")
        print("Avaliação do detector de anomalias (apenas sessões com modelo já treinado):")
        for chave, valor in avaliacao.items():
            print(f"  {chave}: {valor}")
    return {"sessoes": len(geradas), "treino": resultado_treino, "avaliacao_anomalias": avaliacao}


def avaliar_detector(db, gabarito: dict) -> dict:
    vp = fp = fn = vn = 0
    tipos_detectados, tipos_perdidos = Counter(), Counter()
    for sessao in db.scalars(select(Sessao)).all():
        injetada, modelo_ativo = gabarito[sessao.id]
        if not modelo_ativo:
            continue
        sinalizada = sessao.status == "em_revisao"
        if injetada and sinalizada:
            vp += 1
            tipos_detectados[injetada] += 1
        elif injetada:
            fn += 1
            tipos_perdidos[injetada] += 1
        elif sinalizada:
            fp += 1
        else:
            vn += 1
    return {
        "verdadeiros_positivos": vp,
        "falsos_positivos": fp,
        "falsos_negativos": fn,
        "verdadeiros_negativos": vn,
        "precisao": round(vp / (vp + fp), 3) if vp + fp else None,
        "recall": round(vp / (vp + fn), 3) if vp + fn else None,
        "detectadas_por_tipo": dict(tipos_detectados),
        "perdidas_por_tipo": dict(tipos_perdidos),
    }


if __name__ == "__main__":
    popular()
