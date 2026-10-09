"""Ponto único de acesso aos modelos de IA.

O MotorIA guarda os modelos treinados em memória e sabe retreiná-los a partir do
banco. Os serviços (ingestão de sessões, rateio, assistente) usam sempre esta
instância, então um retreino passa a valer imediatamente para as próximas sessões.
"""

from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ia.anomalias import DetectorAnomalias, extrair_features
from app.ia.assistente import ClassificadorIntencao
from app.ia.demanda import PrevisorDemanda
from app.ia.perfis import AgrupadorPerfis, SessaoResumo
from app.models import Carregador, Sessao


class MotorIA:
    def __init__(self):
        self.detector = DetectorAnomalias()
        self.previsor = PrevisorDemanda()
        self.perfis = AgrupadorPerfis()
        self.assistente = ClassificadorIntencao()
        self.treinado_em: datetime | None = None
        self.treinado_ate: datetime | None = None

    def treinar(self, db: Session, ate: datetime | None = None) -> dict:
        """Retreina os modelos com as sessões faturáveis (opcionalmente só até uma data,
        o que permite simular retreinos periódicos ao popular o histórico)."""
        consulta = select(Sessao).where(Sessao.status == "faturavel")
        if ate is not None:
            consulta = consulta.where(Sessao.fim <= ate)
        sessoes = db.scalars(consulta).all()
        n_carregadores = db.scalar(select(func.count()).select_from(Carregador)) or 1

        anomalias_ok = self.detector.treinar(
            [extrair_features(s.inicio, s.fim_recarga, s.fim, s.energia_kwh) for s in sessoes]
        )
        demanda_ok = self.previsor.treinar([(s.inicio, s.fim) for s in sessoes], n_carregadores)

        por_usuario = defaultdict(list)
        for s in sessoes:
            por_usuario[s.usuario_id].append(SessaoResumo(s.inicio, s.fim_recarga, s.fim, s.energia_kwh))
        semanas = 0.0
        if sessoes:
            semanas = (max(s.fim for s in sessoes) - min(s.inicio for s in sessoes)).days / 7
        perfis_ok = self.perfis.treinar(por_usuario, semanas)

        self.treinado_em = datetime.now()
        self.treinado_ate = ate
        return {"anomalias": anomalias_ok, "demanda": demanda_ok, "perfis": perfis_ok,
                "sessoes_usadas": len(sessoes)}

    def status(self) -> dict:
        return {
            "treinado_em": self.treinado_em,
            "anomalias": {
                "treinado": self.detector.treinado,
                "algoritmo": "Isolation Forest + regra de potência máxima",
                "amostras_treino": self.detector.amostras_treino,
                "contaminacao": self.detector.contaminacao,
            },
            "demanda": {
                "treinado": self.previsor.treinado,
                "algoritmo": "Regressão linear regularizada (Ridge) com variáveis sazonais (dia da semana x hora)",
                "metricas": self.previsor.metricas,
            },
            "perfis": {
                "treinado": self.perfis.treinado,
                "algoritmo": "K-Means (k escolhido por silhueta)",
                "silhueta": self.perfis.silhueta,
                "grupos": len(self.perfis.grupos),
            },
            "assistente": {
                "treinado": True,
                "algoritmo": "TF-IDF (n-gramas de caracteres) + regressão logística",
            },
        }


motor = MotorIA()
