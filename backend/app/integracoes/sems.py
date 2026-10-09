"""Integração com o GoodWe SEMS Portal.

A equipe não teve credenciais de acesso à API do SEMS Portal para o carregador
HCA G2 do Energy Innovation Lab durante a sprint 02. Por isso o sistema depende
apenas da interface FonteSessoes: hoje ela é atendida pelo SimuladorSems, que
gera sessões realistas; quando houver acesso, basta implementar um cliente HTTP
com o mesmo método buscar_sessoes() e trocar a fonte em api/integracao.py.
"""

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol

from app.schemas import LeituraSessao


class FonteSessoes(Protocol):
    def buscar_sessoes(self, desde: datetime, ate: datetime) -> list[LeituraSessao]: ...


@dataclass
class PerfilSimulado:
    """Hábito de um usuário usado para gerar sessões sintéticas."""

    rfid_tag: str
    sessoes_por_semana: float
    hora_inicio: tuple[float, float]  # faixa de horário de chegada
    energia_kwh: tuple[float, float]
    ociosidade_h: tuple[float, float]  # tempo conectado depois de terminar
    so_fim_de_semana: bool = False
    so_dia_util: bool = False


@dataclass
class CarregadorSimulado:
    numero_serie: str
    potencia_kw: float
    livre_em: datetime = datetime.min


TIPOS_ANOMALIA = ["erro_medicao", "ociosidade_extrema", "horario_atipico"]


def gerar_sessoes(
    perfis: list[PerfilSimulado],
    carregadores: list[CarregadorSimulado],
    inicio: date,
    fim: datetime,
    rng: random.Random,
    prob_anomalia: float = 0.03,
) -> list[tuple[LeituraSessao, str | None]]:
    """Gera as sessões de cada dia. Se todos os carregadores estiverem ocupados
    na chegada do usuário, ele desiste (é exatamente a disputa que a taxa de
    ocupação tenta reduzir). Retorna (leitura, tipo_de_anomalia_injetada)."""
    resultado = []
    dia = inicio
    while dia <= fim.date():
        fim_de_semana = dia.weekday() >= 5
        chegadas = []
        for p in perfis:
            if (p.so_fim_de_semana and not fim_de_semana) or (p.so_dia_util and fim_de_semana):
                continue
            dias_possiveis = 2 if p.so_fim_de_semana else 5 if p.so_dia_util else 7
            if rng.random() < p.sessoes_por_semana / dias_possiveis:
                hora = rng.uniform(*p.hora_inicio)
                chegadas.append((datetime.combine(dia, datetime.min.time()) + timedelta(hours=hora), p))

        for chegada, p in sorted(chegadas, key=lambda c: c[0]):
            chegada = chegada.replace(second=0, microsecond=0)
            livre = [c for c in carregadores if c.livre_em <= chegada]
            if not livre:
                continue
            carregador = livre[0]
            energia = rng.uniform(*p.energia_kwh)
            ociosidade = rng.uniform(*p.ociosidade_h)
            anomalia = rng.choice(TIPOS_ANOMALIA) if rng.random() < prob_anomalia else None
            if anomalia == "ociosidade_extrema":
                ociosidade = rng.uniform(20, 30)
            elif anomalia == "horario_atipico":
                chegada = chegada.replace(hour=rng.randint(2, 4))
                energia = rng.uniform(45, 60)

            potencia_real = carregador.potencia_kw * rng.uniform(0.88, 0.97)
            fim_recarga = chegada + timedelta(hours=energia / potencia_real)
            saida = fim_recarga + timedelta(hours=ociosidade)
            if anomalia == "erro_medicao":
                energia *= rng.uniform(2.0, 3.0)  # medidor reporta mais energia do que é possível
            if saida > fim:
                continue
            carregador.livre_em = saida

            leitura = LeituraSessao(
                id_externo=f"SEMS-{carregador.numero_serie}-{chegada:%Y%m%d%H%M}",
                numero_serie_carregador=carregador.numero_serie,
                rfid_tag=p.rfid_tag,
                inicio=chegada,
                fim_recarga=fim_recarga.replace(microsecond=0),
                fim=saida.replace(microsecond=0),
                energia_kwh=round(energia, 2),
            )
            resultado.append((leitura, anomalia))
        dia += timedelta(days=1)
    return sorted(resultado, key=lambda r: r[0].fim)


class SimuladorSems:
    """Fonte de sessões que imita o SEMS Portal a partir dos perfis simulados."""

    def __init__(self, perfis: list[PerfilSimulado], carregadores: list[CarregadorSimulado], semente: int | None = None):
        self.perfis = perfis
        self.carregadores = carregadores
        self.rng = random.Random(semente)

    def buscar_sessoes(self, desde: datetime, ate: datetime) -> list[LeituraSessao]:
        for c in self.carregadores:
            c.livre_em = max(c.livre_em, desde)
        gerado = gerar_sessoes(self.perfis, self.carregadores, desde.date(), ate, self.rng)
        return [leitura for leitura, _ in gerado if leitura.inicio >= desde]
