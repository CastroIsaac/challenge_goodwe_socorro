"""Parâmetros do sistema. Todos podem ser sobrescritos por variáveis de ambiente.

Os valores de tarifa são referências aproximadas da Tarifa Branca (grupo B1)
praticada em São Paulo e devem ser atualizados pelo gestor conforme a fatura
real da concessionária.
"""

import os
from dataclasses import dataclass


def _float(nome: str, padrao: float) -> float:
    return float(os.getenv(nome, str(padrao)))


@dataclass(frozen=True)
class Config:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./evchargeops.db")
    popular_banco_se_vazio: bool = os.getenv("POPULAR_BANCO_SE_VAZIO", "true") == "true"
    cors_origens: str = os.getenv("CORS_ORIGENS", "http://localhost:3000")

    # Tarifa Branca (R$/kWh, com impostos) por posto tarifário
    tarifa_fora_ponta: float = _float("TARIFA_FORA_PONTA", 0.78)
    tarifa_intermediaria: float = _float("TARIFA_INTERMEDIARIA", 1.12)
    tarifa_ponta: float = _float("TARIFA_PONTA", 1.79)

    # Taxa de ocupação: cobrada sobre o tempo em que o veículo fica conectado
    # SEM carregar, depois da tolerância. O valor por hora é multiplicado por
    # um fator que depende da demanda prevista pela IA para aquele horário.
    tolerancia_ociosidade_min: int = int(os.getenv("TOLERANCIA_OCIOSIDADE_MIN", "30"))
    taxa_ocupacao_hora: float = _float("TAXA_OCUPACAO_HORA", 4.00)
    fator_demanda_baixa: float = _float("FATOR_DEMANDA_BAIXA", 0.0)
    fator_demanda_moderada: float = _float("FATOR_DEMANDA_MODERADA", 1.0)
    fator_demanda_alta: float = _float("FATOR_DEMANDA_ALTA", 2.0)

    # Limites (ocupação prevista, de 0 a 1) que separam os níveis de demanda
    limite_demanda_moderada: float = _float("LIMITE_DEMANDA_MODERADA", 0.20)
    limite_demanda_alta: float = _float("LIMITE_DEMANDA_ALTA", 0.45)

    # Custo mensal de manutenção do carregador, dividido entre usuários ativos
    custo_manutencao_mensal: float = _float("CUSTO_MANUTENCAO_MENSAL", 150.00)

    # Mínimo de histórico para os modelos de IA serem treinados
    min_sessoes_anomalia: int = 60
    min_dias_demanda: int = 14
    min_usuarios_perfis: int = 4


config = Config()
