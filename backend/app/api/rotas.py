from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import config
from app.dados_demo import PERFIS, carregadores_simulados
from app.database import get_db
from app.ia.motor import motor
from app.integracoes.sems import SimuladorSems
from app.models import Carregador, Faturamento, Sessao, Usuario
from app.schemas import (CarregadorSaida, LeituraSessao, Pergunta, Revisao, SessaoSaida,
                         UsuarioCriar, UsuarioSaida)
from app.services import assistente
from app.services.faturamento import calcular_rateio_mensal, fechar_mes, sessoes_do_mes
from app.services.rateio import posto_tarifario
from app.services.sessoes import ErroRegistro, registrar_sessao, revisar_sessao

router = APIRouter()
fonte_sems = SimuladorSems(PERFIS, carregadores_simulados())

PADRAO_MES = r"^\d{4}-\d{2}$"


def _mes_atual() -> str:
    return datetime.now().strftime("%Y-%m")


# ---------- Cadastros ----------

@router.get("/usuarios", response_model=list[UsuarioSaida], tags=["cadastros"])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.scalars(select(Usuario).order_by(Usuario.apartamento)).all()


@router.post("/usuarios", response_model=UsuarioSaida, status_code=201, tags=["cadastros"])
def criar_usuario(dados: UsuarioCriar, db: Session = Depends(get_db)):
    usuario = Usuario(**dados.model_dump())
    db.add(usuario)
    db.commit()
    return usuario


@router.get("/carregadores", response_model=list[CarregadorSaida], tags=["cadastros"])
def listar_carregadores(db: Session = Depends(get_db)):
    return db.scalars(select(Carregador)).all()


# ---------- Sessões ----------

@router.post("/sessoes", status_code=201, tags=["sessões"])
def registrar(leitura: LeituraSessao, db: Session = Depends(get_db)):
    """Recebe a leitura de uma sessão do carregador, passa pela IA e calcula o custo."""
    try:
        sessao, detalhes = registrar_sessao(db, leitura)
    except ErroRegistro as erro:
        raise HTTPException(422, str(erro))
    return {"sessao": SessaoSaida.model_validate(sessao), **detalhes}


@router.get("/sessoes", response_model=list[SessaoSaida], tags=["sessões"])
def listar_sessoes(
    mes: str = Query(default_factory=_mes_atual, pattern=PADRAO_MES),
    status: str | None = None,
    usuario_id: str | None = None,
    db: Session = Depends(get_db),
):
    return list(reversed(sessoes_do_mes(db, mes, status, usuario_id)))


@router.post("/sessoes/{sessao_id}/revisao", response_model=SessaoSaida, tags=["sessões"])
def revisar(sessao_id: str, revisao: Revisao, db: Session = Depends(get_db)):
    sessao = db.get(Sessao, sessao_id)
    if sessao is None:
        raise HTTPException(404, "Sessão não encontrada")
    try:
        return revisar_sessao(db, sessao, revisao.decisao, revisao.observacao)
    except ErroRegistro as erro:
        raise HTTPException(422, str(erro))


@router.post("/integracao/sems/sincronizar", tags=["sessões"])
def sincronizar_sems(db: Session = Depends(get_db)):
    """Busca na fonte (simulador do SEMS) as sessões encerradas desde a última importada."""
    ultima = db.scalar(select(func.max(Sessao.fim)))
    agora = datetime.now().replace(second=0, microsecond=0)
    desde = ultima or agora - timedelta(days=1)
    importadas, em_revisao, erros = 0, 0, []
    for leitura in fonte_sems.buscar_sessoes(desde, agora):
        try:
            sessao, _ = registrar_sessao(db, leitura)
            importadas += 1
            em_revisao += sessao.status == "em_revisao"
        except ErroRegistro as erro:
            erros.append(str(erro))
    return {"desde": desde, "ate": agora, "importadas": importadas, "em_revisao": em_revisao, "erros": erros}


# ---------- Rateio ----------

@router.get("/rateio/{mes}", tags=["rateio"])
def rateio_do_mes(mes: str, db: Session = Depends(get_db)):
    return calcular_rateio_mensal(db, mes)


@router.post("/rateio/{mes}/fechar", tags=["rateio"])
def fechar(mes: str, db: Session = Depends(get_db)):
    registros = fechar_mes(db, mes)
    return {"mes": mes, "faturas_geradas": len(registros),
            "total": round(sum(r.valor_total for r in registros), 2)}


@router.get("/faturamento", tags=["rateio"])
def faturas_fechadas(usuario_id: str | None = None, db: Session = Depends(get_db)):
    consulta = select(Faturamento).order_by(Faturamento.mes.desc())
    if usuario_id:
        consulta = consulta.where(Faturamento.usuario_id == usuario_id)
    return db.scalars(consulta).all()


@router.get("/parametros", tags=["rateio"])
def parametros():
    """Parâmetros do modelo de rateio em vigor (tarifas, taxas e limites)."""
    ocultos = {"database_url", "cors_origens", "popular_banco_se_vazio"}
    return {k: v for k, v in asdict(config).items() if k not in ocultos}


# ---------- Painel ----------

@router.get("/painel", tags=["painel"])
def painel(mes: str = Query(default_factory=_mes_atual, pattern=PADRAO_MES), db: Session = Depends(get_db)):
    sessoes = sessoes_do_mes(db, mes)
    faturaveis = [s for s in sessoes if s.status == "faturavel"]
    rateio = calcular_rateio_mensal(db, mes)

    por_hora = [{"hora": h, "sessoes": 0, "energia_kwh": 0.0} for h in range(24)]
    energia_por_posto = defaultdict(float)
    for s in faturaveis:
        por_hora[s.inicio.hour]["sessoes"] += 1
        por_hora[s.inicio.hour]["energia_kwh"] += s.energia_kwh
        minutos = max(round((s.fim_recarga - s.inicio).total_seconds() / 60), 1)
        for i in range(minutos):
            energia_por_posto[posto_tarifario(s.inicio + timedelta(minutes=i))] += s.energia_kwh / minutos
    for h in por_hora:
        h["energia_kwh"] = round(h["energia_kwh"], 1)

    horas_conectado = sum((s.fim - s.inicio).total_seconds() for s in faturaveis) / 3600
    horas_carregando = sum((s.fim_recarga - s.inicio).total_seconds() for s in faturaveis) / 3600

    return {
        "mes": mes,
        "indicadores": {
            "sessoes": len(faturaveis),
            "energia_kwh": rateio["total_energia_kwh"],
            "total_arrecadado": rateio["total_arrecadado"],
            "usuarios_ativos": rateio["usuarios_ativos"],
            "sessoes_em_revisao": rateio["sessoes_em_revisao"],
            "sessoes_rejeitadas": sum(1 for s in sessoes if s.status == "rejeitada"),
            "horas_conectado": round(horas_conectado, 1),
            "horas_carregando": round(horas_carregando, 1),
            "fracao_ociosa": round(1 - horas_carregando / horas_conectado, 3) if horas_conectado else 0,
        },
        "uso_por_hora": por_hora,
        "energia_por_posto": {p: round(k, 1) for p, k in energia_por_posto.items()},
    }


# ---------- IA ----------

@router.get("/ia/status", tags=["ia"])
def status_ia():
    return motor.status()


@router.post("/ia/treinar", tags=["ia"])
def treinar_ia(db: Session = Depends(get_db)):
    return motor.treinar(db)


@router.get("/ia/previsao-demanda", tags=["ia"])
def previsao_demanda(horas: int = Query(168, le=336)):
    agora = datetime.now()
    return {
        "previsao": motor.previsor.proximas_horas(agora, horas),
        "melhores_horarios": motor.previsor.melhores_horarios(agora),
        "limites": {"moderada": config.limite_demanda_moderada, "alta": config.limite_demanda_alta},
    }


@router.get("/ia/perfis", tags=["ia"])
def perfis(db: Session = Depends(get_db)):
    nomes = {u.id: f"{u.nome} (ap. {u.apartamento})" for u in db.scalars(select(Usuario)).all()}
    return {
        "silhueta": motor.perfis.silhueta,
        "grupos": [g | {"usuarios": [{"id": u, "nome": nomes.get(u, u)} for u in g["usuarios"]]}
                   for g in motor.perfis.grupos],
    }


@router.get("/ia/perfis/{usuario_id}", tags=["ia"])
def perfil_usuario(usuario_id: str):
    perfil = motor.perfis.perfis_usuarios.get(usuario_id)
    if perfil is None:
        raise HTTPException(404, "Usuário sem histórico suficiente para perfil")
    return perfil


@router.post("/assistente", tags=["ia"])
def perguntar(pergunta: Pergunta, db: Session = Depends(get_db)):
    usuario = db.get(Usuario, pergunta.usuario_id)
    if usuario is None:
        raise HTTPException(404, "Usuário não encontrado")
    return assistente.responder(db, usuario, pergunta.pergunta)
