"""Monta a resposta do assistente: a IA identifica a intenção e aqui buscamos os
dados reais (sessões, rateio, previsão de demanda, perfil) para responder."""

from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ia.motor import motor
from app.models import Sessao, Usuario
from app.services.faturamento import calcular_rateio_mensal, sessoes_do_mes

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def _brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _quando(momento: datetime) -> str:
    return f"{DIAS[momento.weekday()]} às {momento.hour}h"


def responder(db: Session, usuario: Usuario, pergunta: str, agora: datetime | None = None) -> dict:
    agora = agora or datetime.now()
    mes = agora.strftime("%Y-%m")
    intencao, confianca = motor.assistente.classificar(pergunta)

    if intencao == "consumo_mes":
        sessoes = sessoes_do_mes(db, mes, status="faturavel", usuario_id=usuario.id)
        kwh = sum(s.energia_kwh for s in sessoes)
        texto = (f"Neste mês você fez {len(sessoes)} recargas e consumiu {kwh:.1f} kWh."
                 if sessoes else "Você ainda não tem recargas faturáveis neste mês.")

    elif intencao == "valor_fatura":
        item = next((i for i in calcular_rateio_mensal(db, mes)["itens"] if i["usuario_id"] == usuario.id), None)
        if item is None:
            texto = "Você não usou o carregador neste mês, então não há valor a pagar."
        else:
            texto = (f"Até agora sua parte do mês é {_brl(item['valor_total'])}: "
                     f"{_brl(item['valor_energia'])} de energia, {_brl(item['valor_ocupacao'])} de ocupação "
                     f"e {_brl(item['valor_manutencao'])} da cota de manutenção.")

    elif intencao == "horario_mais_usado":
        inicios = db.scalars(select(Sessao.inicio).where(Sessao.status == "faturavel")).all()
        if not inicios:
            texto = "Ainda não há sessões suficientes para identificar o horário de pico."
        else:
            hora, qtd = Counter(i.hour for i in inicios).most_common(1)[0]
            texto = f"O horário em que mais recargas começam é às {hora}h ({qtd} sessões no histórico)."
            pico = max(motor.previsor.proximas_horas(agora, 48), key=lambda h: h["ocupacao_prevista"] or 0)
            if pico["ocupacao_prevista"]:
                texto += (f" Nas próximas 48h, o pico previsto é {_quando(pico['momento'])}, "
                          f"com {pico['ocupacao_prevista']:.0%} de ocupação.")

    elif intencao == "melhor_horario":
        melhores = motor.previsor.melhores_horarios(agora)
        if not melhores:
            texto = "O modelo de demanda ainda não tem histórico suficiente para recomendar horários."
        else:
            lista = ", ".join(f"{_quando(h['momento'])} ({h['ocupacao_prevista']:.0%})" for h in melhores)
            texto = (f"Pela previsão de demanda, os horários mais livres nas próximas 48h são: {lista}. "
                     "Lembre que entre 17h30 e 20h30 dos dias úteis a tarifa é de ponta.")

    elif intencao == "perfil":
        perfil = motor.perfis.perfis_usuarios.get(usuario.id)
        texto = (f"Seu perfil de uso é \"{perfil['nome']}\". {perfil['recomendacao']}"
                 if perfil else "Ainda não há sessões suficientes para definir seu perfil.")

    elif intencao == "sessoes_revisao":
        pendentes = db.scalars(select(Sessao).where(
            Sessao.usuario_id == usuario.id, Sessao.status == "em_revisao")).all()
        if not pendentes:
            texto = "Você não tem nenhuma sessão em revisão."
        else:
            s = pendentes[-1]
            texto = (f"Você tem {len(pendentes)} sessão(ões) em revisão. Elas não entram na fatura até o "
                     f"gestor validar. A mais recente ({s.inicio:%d/%m %Hh%M}) foi marcada por: {s.motivo_revisao}.")

    else:
        texto = ("Não entendi. Posso responder sobre seu consumo do mês, quanto você vai pagar, "
                 "horário de pico, melhor horário para carregar, seu perfil de uso e sessões em revisão.")

    return {"intencao": intencao, "confianca": round(confianca, 2), "resposta": texto}
