"""Perfis de uso com K-Means.

Cada usuário vira um vetor com seus hábitos de recarga (horário médio, energia
média, frequência, ociosidade e uso em fim de semana). O K-Means agrupa usuários
parecidos; o número de grupos é escolhido pelo melhor coeficiente de silhueta.
Os grupos recebem um nome a partir dos seus centroides, e cada perfil tem uma
recomendação associada (exibida para o usuário e usada pelo assistente).
"""

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from app.config import config


@dataclass
class SessaoResumo:
    inicio: datetime
    fim_recarga: datetime
    fim: datetime
    energia_kwh: float


def features_usuario(sessoes: list[SessaoResumo], semanas_observadas: float) -> dict:
    angulos = [2 * math.pi * (s.inicio.hour + s.inicio.minute / 60) / 24 for s in sessoes]
    # Média circular da hora de início (média de 23h e 1h = 0h, e não 12h)
    seno = float(np.mean([math.sin(a) for a in angulos]))
    cosseno = float(np.mean([math.cos(a) for a in angulos]))
    hora_media = (math.atan2(seno, cosseno) * 24 / (2 * math.pi)) % 24
    return {
        "hora_sin": seno,
        "hora_cos": cosseno,
        "hora_media": round(hora_media, 1),
        "energia_media_kwh": round(float(np.mean([s.energia_kwh for s in sessoes])), 2),
        "sessoes_por_semana": round(len(sessoes) / max(semanas_observadas, 1), 2),
        "ociosidade_media_h": round(
            float(np.mean([(s.fim - s.fim_recarga).total_seconds() / 3600 for s in sessoes])), 2
        ),
        "fracao_fim_de_semana": round(sum(s.inicio.weekday() >= 5 for s in sessoes) / len(sessoes), 2),
    }


COLUNAS_MODELO = ["hora_sin", "hora_cos", "energia_media_kwh", "sessoes_por_semana",
                  "ociosidade_media_h", "fracao_fim_de_semana"]


def nomear_perfil(centroide: dict) -> tuple[str, str]:
    """Traduz o centroide de um grupo em nome + recomendação legíveis."""
    hora = centroide["hora_media"]
    if centroide["fracao_fim_de_semana"] >= 0.5:
        return ("Usuário de fim de semana",
                "Seu uso é concentrado no fim de semana, quando toda a energia é fora de ponta.")
    if hora >= 18 or hora < 5:
        if centroide["ociosidade_media_h"] >= 3:
            return ("Noturno que deixa conectado",
                    "Você costuma deixar o carro conectado por horas depois de carregar. "
                    "Desconectar ao terminar libera a vaga e evita a taxa de ocupação em horários disputados.")
        return ("Noturno",
                "Você recarrega à noite. Começar depois das 21h30 evita o horário de ponta da tarifa.")
    if centroide["sessoes_por_semana"] >= 3:
        return ("Diurno frequente",
                "Você usa o carregador quase todo dia. Os horários do fim da manhã costumam estar livres.")
    return ("Diurno ocasional",
            "Você usa pouco e de dia. Recargas antes das 16h30 ficam na tarifa fora de ponta.")


class AgrupadorPerfis:
    def __init__(self):
        self.perfis_usuarios: dict[str, dict] = {}
        self.grupos: list[dict] = []
        self.silhueta: float | None = None

    @property
    def treinado(self) -> bool:
        return bool(self.perfis_usuarios)

    def treinar(self, sessoes_por_usuario: dict[str, list[SessaoResumo]], semanas: float) -> bool:
        dados = {
            uid: features_usuario(sessoes, semanas)
            for uid, sessoes in sessoes_por_usuario.items() if len(sessoes) >= 3
        }
        if len(dados) < config.min_usuarios_perfis:
            return False

        ids = list(dados)
        x = StandardScaler().fit_transform([[dados[u][c] for c in COLUNAS_MODELO] for u in ids])

        melhor = None
        for k in range(2, min(5, len(ids) - 1) + 1):
            modelo = KMeans(n_clusters=k, n_init=10, random_state=42).fit(x)
            nota = silhouette_score(x, modelo.labels_)
            if melhor is None or nota > melhor[0]:
                melhor = (nota, modelo)
        self.silhueta, modelo = round(float(melhor[0]), 3), melhor[1]

        self.grupos, self.perfis_usuarios = [], {}
        for grupo in range(modelo.n_clusters):
            membros = [u for u, rotulo in zip(ids, modelo.labels_) if rotulo == grupo]
            centroide = {c: float(np.mean([dados[u][c] for u in membros])) for c in dados[ids[0]]}
            centroide["hora_media"] = hora_do_centroide(centroide)
            nome, recomendacao = nomear_perfil(centroide)
            self.grupos.append({
                "grupo": grupo,
                "nome": nome,
                "recomendacao": recomendacao,
                "usuarios": membros,
                "centroide": {k: round(v, 2) for k, v in centroide.items()},
            })
            for u in membros:
                self.perfis_usuarios[u] = {"grupo": grupo, "nome": nome,
                                           "recomendacao": recomendacao, "habitos": dados[u]}
        return True


def hora_do_centroide(centroide: dict) -> float:
    """Hora média do grupo recalculada a partir do seno/cosseno médios."""
    return round((math.atan2(centroide["hora_sin"], centroide["hora_cos"]) * 24 / (2 * math.pi)) % 24, 1)
