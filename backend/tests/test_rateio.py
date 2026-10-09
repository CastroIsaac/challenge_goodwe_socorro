from datetime import datetime

import pytest

from app.config import config
from app.services.rateio import calcular_custo_sessao, dividir_em_centavos, posto_tarifario

# 08/10/2026 é uma quinta-feira; 10/10/2026 é sábado
QUINTA = datetime(2026, 10, 8)
SABADO = datetime(2026, 10, 10)


def sempre(nivel):
    return lambda momento: nivel


@pytest.mark.parametrize("hora, minuto, esperado", [
    (10, 0, "fora_ponta"),
    (16, 30, "intermediario"),
    (17, 29, "intermediario"),
    (17, 30, "ponta"),
    (20, 29, "ponta"),
    (20, 30, "intermediario"),
    (21, 30, "fora_ponta"),
])
def test_postos_tarifa_branca_dia_util(hora, minuto, esperado):
    assert posto_tarifario(QUINTA.replace(hour=hora, minute=minuto)) == esperado


def test_fim_de_semana_e_sempre_fora_de_ponta():
    assert posto_tarifario(SABADO.replace(hour=18)) == "fora_ponta"


def test_exemplo_da_sprint01_fora_de_ponta():
    """35 kWh carregados fora de ponta e retirada imediata: só energia."""
    custo = calcular_custo_sessao(
        QUINTA.replace(hour=1), QUINTA.replace(hour=6), QUINTA.replace(hour=6), 35, sempre("alta")
    )
    assert custo.custo_energia == round(35 * config.tarifa_fora_ponta, 2)
    assert custo.custo_ocupacao == 0


def test_energia_dividida_entre_postos():
    """Recarga de 17h a 19h: 30 min intermediário + 90 min ponta, 12 kWh distribuídos por igual."""
    custo = calcular_custo_sessao(
        QUINTA.replace(hour=17), QUINTA.replace(hour=19), QUINTA.replace(hour=19), 12, sempre("baixa")
    )
    assert custo.energia_por_posto == {"intermediario": 3.0, "ponta": 9.0}
    esperado = 3 * config.tarifa_intermediaria + 9 * config.tarifa_ponta
    assert custo.custo_energia == round(esperado, 2)


def test_ocupacao_respeita_tolerancia_e_nivel_de_demanda():
    inicio = QUINTA.replace(hour=9)
    fim_recarga = QUINTA.replace(hour=10)
    fim = QUINTA.replace(hour=12)  # 120 min ociosos, 30 de tolerância -> 90 cobrados
    alta = calcular_custo_sessao(inicio, fim_recarga, fim, 7, sempre("alta"))
    baixa = calcular_custo_sessao(inicio, fim_recarga, fim, 7, sempre("baixa"))

    assert alta.minutos_ociosos == 120
    assert alta.minutos_ociosos_cobrados == 90
    assert alta.custo_ocupacao == round(1.5 * config.taxa_ocupacao_hora * config.fator_demanda_alta, 2)
    assert baixa.custo_ocupacao == 0  # ninguém precisava da vaga: não cobra


def test_divisao_em_centavos_nao_perde_dinheiro():
    partes = dividir_em_centavos(100, 3)
    assert partes == [33.34, 33.33, 33.33]
    assert round(sum(partes), 2) == 100
    assert dividir_em_centavos(150, 0) == []
