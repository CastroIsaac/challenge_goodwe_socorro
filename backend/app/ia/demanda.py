"""Previsão de demanda (ocupação do carregador por hora).

Alvo: fração de cada hora em que o carregador ficou ocupado (0 a 1), somando
todos os carregadores do local.
Modelo: regressão linear com variáveis sazonais (dia da semana e hora do dia,
com a hora separada entre dia útil e fim de semana, porque o padrão muda).

A previsão é usada em dois pontos do fluxo:
- no rateio: define o nível de demanda (baixa/moderada/alta) de cada minuto
  ocioso e, portanto, quanto a taxa de ocupação custa naquele horário;
- no painel e no assistente: recomenda os horários mais livres para recarregar.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error

from app.config import config
from app.services.rateio import posto_tarifario

Intervalo = tuple[datetime, datetime]


def ocupacao_por_hora(intervalos: list[Intervalo], n_carregadores: int) -> dict[tuple[date, int], float]:
    """Soma os minutos ocupados em cada (dia, hora) e divide pela capacidade da hora."""
    minutos = defaultdict(float)
    for inicio, fim in intervalos:
        atual = inicio
        while atual < fim:
            proxima_hora = atual.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            trecho_fim = min(fim, proxima_hora)
            minutos[(atual.date(), atual.hour)] += (trecho_fim - atual).total_seconds() / 60
            atual = trecho_fim
    return {chave: min(m / (60 * n_carregadores), 1.0) for chave, m in minutos.items()}


def features_sazonais(dia: date, hora: int) -> list[float]:
    """One-hot de dia da semana (7) + one-hot de hora em dia útil (24) + hora no fim de semana (24)."""
    vetor = [0.0] * (7 + 48)
    vetor[dia.weekday()] = 1.0
    deslocamento = 7 + (24 if dia.weekday() >= 5 else 0)
    vetor[deslocamento + hora] = 1.0
    return vetor


def classificar_nivel(ocupacao: float) -> str:
    if ocupacao >= config.limite_demanda_alta:
        return "alta"
    if ocupacao >= config.limite_demanda_moderada:
        return "moderada"
    return "baixa"


class PrevisorDemanda:
    def __init__(self):
        self.modelo: Ridge | None = None
        # Previsão já calculada para as 168 horas da semana (dia_da_semana, hora)
        self._tabela: dict[tuple[int, int], float] = {}
        self.metricas: dict = {}

    @property
    def treinado(self) -> bool:
        return self.modelo is not None

    def treinar(self, intervalos: list[Intervalo], n_carregadores: int) -> bool:
        if not intervalos:
            return False
        primeiro_dia = min(i[0] for i in intervalos).date()
        ultimo_dia = max(i[1] for i in intervalos).date()
        dias = [primeiro_dia + timedelta(days=n) for n in range((ultimo_dia - primeiro_dia).days + 1)]
        if len(dias) < config.min_dias_demanda:
            return False

        # Horas sem nenhuma sessão também são exemplos (ocupação zero)
        ocupacao = ocupacao_por_hora(intervalos, n_carregadores)
        x = np.array([features_sazonais(d, h) for d in dias for h in range(24)])
        y = np.array([ocupacao.get((d, h), 0.0) for d in dias for h in range(24)])

        self.metricas = self._avaliar_holdout(x, y)
        self.modelo = Ridge(alpha=1.0).fit(x, y)
        self.metricas["dias_historico"] = len(dias)

        segunda_referencia = date(2024, 1, 1)  # uma segunda-feira qualquer
        for dia_semana in range(7):
            dia = segunda_referencia + timedelta(days=dia_semana)
            previsoes = self.modelo.predict(np.array([features_sazonais(dia, h) for h in range(24)]))
            for hora, valor in enumerate(previsoes):
                self._tabela[(dia_semana, hora)] = float(np.clip(valor, 0, 1))
        return True

    @staticmethod
    def _avaliar_holdout(x: np.ndarray, y: np.ndarray) -> dict:
        """Treina sem as 2 últimas semanas e mede o erro nelas, comparando com a média simples."""
        corte = len(y) - 14 * 24
        if corte < 7 * 24:
            return {}
        modelo = Ridge(alpha=1.0).fit(x[:corte], y[:corte])
        previsto = np.clip(modelo.predict(x[corte:]), 0, 1)
        baseline = np.full_like(y[corte:], y[:corte].mean())
        return {
            "mae_modelo": round(float(mean_absolute_error(y[corte:], previsto)), 4),
            "mae_baseline_media": round(float(mean_absolute_error(y[corte:], baseline)), 4),
        }

    def prever(self, momento: datetime) -> float | None:
        if not self.treinado:
            return None
        return self._tabela[(momento.weekday(), momento.hour)]

    def nivel(self, momento: datetime) -> str:
        """Sem modelo treinado, assume demanda moderada (cobra a taxa de ocupação base)."""
        previsao = self.prever(momento)
        return "moderada" if previsao is None else classificar_nivel(previsao)

    def proximas_horas(self, a_partir: datetime, horas: int = 7 * 24) -> list[dict]:
        inicio = a_partir.replace(minute=0, second=0, microsecond=0)
        resultado = []
        for n in range(horas):
            momento = inicio + timedelta(hours=n)
            previsao = self.prever(momento)
            resultado.append({
                "momento": momento,
                "ocupacao_prevista": None if previsao is None else round(previsao, 3),
                "nivel": self.nivel(momento),
            })
        return resultado

    def melhores_horarios(self, a_partir: datetime, quantidade: int = 3) -> list[dict]:
        """Horários das próximas 48h com menor ocupação prevista, entre 6h e 23h e
        fora do horário de ponta/intermediário da tarifa (livre E barato)."""
        candidatos = [
            h for h in self.proximas_horas(a_partir + timedelta(hours=1), 48)
            if 6 <= h["momento"].hour <= 23
            and h["ocupacao_prevista"] is not None
            and posto_tarifario(h["momento"]) == "fora_ponta"
        ]
        return sorted(candidatos, key=lambda h: h["ocupacao_prevista"])[:quantidade]
