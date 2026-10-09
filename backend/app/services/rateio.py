"""Modelo de rateio definido na sprint 01:

    Valor = (consumo kWh × tarifa) + (tempo de ocupação × taxa de ocupação)
            + taxa de manutenção compartilhada

- Tarifa: depende do horário (Tarifa Branca: ponta, intermediário, fora de ponta).
- Ocupação: só o tempo conectado SEM carregar, depois da tolerância. O valor por
  hora é multiplicado pelo fator do nível de demanda que a IA prevê para aquele
  horário (ocupar a vaga quando ninguém precisa dela não é cobrado).
- Manutenção: custo mensal fixo dividido igualmente entre quem usou no mês.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Callable

from app.config import config

NivelDemanda = Callable[[datetime], str]

TARIFAS = {
    "fora_ponta": config.tarifa_fora_ponta,
    "intermediario": config.tarifa_intermediaria,
    "ponta": config.tarifa_ponta,
}

FATORES_DEMANDA = {
    "baixa": config.fator_demanda_baixa,
    "moderada": config.fator_demanda_moderada,
    "alta": config.fator_demanda_alta,
}


def posto_tarifario(momento: datetime) -> str:
    """Postos da Tarifa Branca (Enel SP). Fim de semana é todo fora de ponta."""
    if momento.weekday() >= 5:
        return "fora_ponta"
    t = momento.time()
    if time(17, 30) <= t < time(20, 30):
        return "ponta"
    if time(16, 30) <= t < time(17, 30) or time(20, 30) <= t < time(21, 30):
        return "intermediario"
    return "fora_ponta"


def minutos_do_intervalo(inicio: datetime, fim: datetime) -> list[datetime]:
    """Lista com o início de cada minuto do intervalo [inicio, fim)."""
    total = round((fim - inicio).total_seconds() / 60)
    return [inicio + timedelta(minutes=i) for i in range(total)]


@dataclass
class CustoSessao:
    energia_por_posto: dict[str, float]
    custo_energia: float
    minutos_ociosos: int
    minutos_ociosos_cobrados: int
    custo_ocupacao: float
    ociosidade_por_nivel: dict[str, int] = field(default_factory=dict)

    @property
    def custo_total(self) -> float:
        return round(self.custo_energia + self.custo_ocupacao, 2)


def calcular_custo_sessao(
    inicio: datetime,
    fim_recarga: datetime,
    fim: datetime,
    energia_kwh: float,
    nivel_demanda: NivelDemanda,
) -> CustoSessao:
    # 1) Energia: assume potência constante durante a recarga e distribui os kWh
    #    minuto a minuto, cada minuto com a tarifa do seu posto.
    minutos_recarga = minutos_do_intervalo(inicio, fim_recarga) or [inicio]
    kwh_por_minuto = energia_kwh / len(minutos_recarga)
    energia_por_posto: dict[str, float] = defaultdict(float)
    for minuto in minutos_recarga:
        energia_por_posto[posto_tarifario(minuto)] += kwh_por_minuto
    custo_energia = sum(kwh * TARIFAS[posto] for posto, kwh in energia_por_posto.items())

    # 2) Ocupação: minutos ociosos depois da tolerância, cobrados conforme a demanda prevista
    minutos_ociosos = minutos_do_intervalo(fim_recarga, fim)
    cobrados = minutos_ociosos[config.tolerancia_ociosidade_min:]
    ociosidade_por_nivel: dict[str, int] = defaultdict(int)
    custo_ocupacao = 0.0
    for minuto in cobrados:
        nivel = nivel_demanda(minuto)
        ociosidade_por_nivel[nivel] += 1
        custo_ocupacao += config.taxa_ocupacao_hora / 60 * FATORES_DEMANDA[nivel]

    return CustoSessao(
        energia_por_posto={p: round(k, 3) for p, k in energia_por_posto.items()},
        custo_energia=round(custo_energia, 2),
        minutos_ociosos=len(minutos_ociosos),
        minutos_ociosos_cobrados=len(cobrados),
        custo_ocupacao=round(custo_ocupacao, 2),
        ociosidade_por_nivel=dict(ociosidade_por_nivel),
    )


def dividir_em_centavos(valor: float, partes: int) -> list[float]:
    """Divide um valor em partes iguais sem perder centavos no arredondamento.
    Ex.: R$ 100,00 / 3 -> [33,34, 33,33, 33,33] (soma exata = 100,00)."""
    if partes <= 0:
        return []
    centavos = round(valor * 100)
    base, sobra = divmod(centavos, partes)
    return [(base + (1 if i < sobra else 0)) / 100 for i in range(partes)]
