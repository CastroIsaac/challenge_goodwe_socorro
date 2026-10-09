"""Detecção de anomalias em sessões de recarga.

Toda sessão nova passa por aqui ANTES de entrar no rateio. Se for considerada
anômala, ela fica com status "em_revisao" e não é cobrada até o gestor aprovar.

Três camadas:
1. Regra física: a potência média não pode passar da potência nominal do
   carregador (com 10% de margem). Funciona mesmo sem histórico.
2. Isolation Forest treinado no histórico de sessões faturáveis: aponta sessões
   com combinação atípica de duração, energia, potência, ociosidade e horário.
3. Limite aprendido do histórico (percentil 99,5 + 1,5 x IQR) por característica.
   Necessário porque o Isolation Forest não extrapola: um valor muito além do
   maior valor de treino segue o mesmo caminho nas árvores que esse maior valor
   e acaba parecendo normal (vimos isso com sessões de 20 h+ de ociosidade).
"""

import math
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from sklearn.ensemble import IsolationForest

from app.config import config

NOMES_FEATURES = [
    "duracao_recarga_h",
    "energia_kwh",
    "potencia_media_kw",
    "ociosidade_h",
    "hora_inicio_sin",
    "hora_inicio_cos",
]

MARGEM_POTENCIA = 1.10


def extrair_features(inicio: datetime, fim_recarga: datetime, fim: datetime, energia_kwh: float) -> list[float]:
    duracao_h = max((fim_recarga - inicio).total_seconds() / 3600, 1 / 60)
    ociosidade_h = max((fim - fim_recarga).total_seconds() / 3600, 0)
    # Hora em forma circular: 23h e 0h ficam próximas, como de fato são
    hora = inicio.hour + inicio.minute / 60
    angulo = 2 * math.pi * hora / 24
    return [duracao_h, energia_kwh, energia_kwh / duracao_h, ociosidade_h, math.sin(angulo), math.cos(angulo)]


@dataclass
class ResultadoAnomalia:
    anomala: bool
    score: float | None  # quanto maior, mais atípica (None se o modelo não está treinado)
    motivos: list[str] = field(default_factory=list)


DESCRICOES = {
    "duracao_recarga_h": "duração da recarga",
    "energia_kwh": "energia entregue",
    "potencia_media_kw": "potência média",
    "ociosidade_h": "tempo ocioso conectado",
}


class DetectorAnomalias:
    def __init__(self, contaminacao: float = 0.01):
        self.contaminacao = contaminacao
        self.modelo: IsolationForest | None = None
        self.amostras_treino = 0
        # Média e desvio do treino: usados só para explicar o motivo ao gestor
        self._media = np.zeros(len(NOMES_FEATURES))
        self._desvio = np.ones(len(NOMES_FEATURES))
        self._limite_superior = np.full(len(NOMES_FEATURES), np.inf)

    @property
    def treinado(self) -> bool:
        return self.modelo is not None

    def treinar(self, features: list[list[float]]) -> bool:
        if len(features) < config.min_sessoes_anomalia:
            return False
        x = np.array(features)
        self.modelo = IsolationForest(
            n_estimators=200, contamination=self.contaminacao, random_state=42
        ).fit(x)
        self.amostras_treino = len(features)
        self._media = x.mean(axis=0)
        self._desvio = x.std(axis=0) + 1e-9
        q1, q3 = np.percentile(x, [25, 75], axis=0)
        self._limite_superior = np.percentile(x, 99.5, axis=0) + 1.5 * (q3 - q1)
        return True

    def avaliar(self, features: list[float], potencia_nominal_kw: float) -> ResultadoAnomalia:
        motivos = []
        potencia_media = features[NOMES_FEATURES.index("potencia_media_kw")]
        if potencia_media > potencia_nominal_kw * MARGEM_POTENCIA:
            motivos.append(
                f"Potência média de {potencia_media:.1f} kW acima do limite do carregador "
                f"({potencia_nominal_kw:.1f} kW): possível erro de medição"
            )

        score = None
        if self.modelo is not None:
            x = np.array([features])
            # decision_function < 0 = fora do padrão; invertemos o sinal para ler "maior = mais atípica"
            score = round(float(-self.modelo.decision_function(x)[0]), 4)
            if self.modelo.predict(x)[0] == -1:
                motivos.append(self._explicar(features))
            for i, nome in enumerate(NOMES_FEATURES):
                if nome in DESCRICOES and features[i] > self._limite_superior[i]:
                    motivos.append(f"{DESCRICOES[nome].capitalize()} ({features[i]:.1f}) acima do "
                                   f"limite aprendido do histórico ({self._limite_superior[i]:.1f})")

        return ResultadoAnomalia(anomala=bool(motivos), score=score, motivos=motivos)

    def _explicar(self, features: list[float]) -> str:
        """Aponta a característica que mais se afasta da média do histórico (em desvios-padrão)."""
        z = (np.array(features) - self._media) / self._desvio
        candidatas = {nome: z[i] for i, nome in enumerate(NOMES_FEATURES) if nome in DESCRICOES}
        nome, valor = max(candidatas.items(), key=lambda item: abs(item[1]))
        if abs(valor) < 2:
            return "Padrão atípico (Isolation Forest): combinação incomum de horário e consumo"
        direcao = "acima" if valor > 0 else "abaixo"
        return f"Padrão atípico (Isolation Forest): {DESCRICOES[nome]} muito {direcao} do histórico"
