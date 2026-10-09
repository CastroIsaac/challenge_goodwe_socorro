"""Cenário de demonstração: condomínio com 10 moradores e 2 carregadores HCA G2.
Os perfis abaixo só servem para GERAR os dados sintéticos; o sistema não os
conhece. Os perfis que aparecem no painel são descobertos pelo K-Means."""

from app.integracoes.sems import CarregadorSimulado, PerfilSimulado

CARREGADORES = [
    {"modelo": "GoodWe HCA G2 7kW", "numero_serie": "HCAG2-0001", "potencia_kw": 7.0,
     "localizacao": "Garagem G1 - vaga 01"},
    {"modelo": "GoodWe HCA G2 7kW", "numero_serie": "HCAG2-0002", "potencia_kw": 7.0,
     "localizacao": "Garagem G1 - vaga 02"},
]

USUARIOS = [
    {"nome": "Ana Ribeiro", "email": "ana@exemplo.com", "apartamento": "101", "rfid_tag": "RFID-A101"},
    {"nome": "Bruno Tanaka", "email": "bruno@exemplo.com", "apartamento": "102", "rfid_tag": "RFID-B102"},
    {"nome": "Carla Mendes", "email": "carla@exemplo.com", "apartamento": "203", "rfid_tag": "RFID-C203"},
    {"nome": "Diego Alves", "email": "diego@exemplo.com", "apartamento": "204", "rfid_tag": "RFID-D204"},
    {"nome": "Elisa Prado", "email": "elisa@exemplo.com", "apartamento": "305", "rfid_tag": "RFID-E305"},
    {"nome": "Fábio Rocha", "email": "fabio@exemplo.com", "apartamento": "306", "rfid_tag": "RFID-F306"},
    {"nome": "Gabriela Lima", "email": "gabriela@exemplo.com", "apartamento": "407", "rfid_tag": "RFID-G407"},
    {"nome": "Henrique Souza", "email": "henrique@exemplo.com", "apartamento": "408", "rfid_tag": "RFID-H408"},
    {"nome": "Isabela Costa", "email": "isabela@exemplo.com", "apartamento": "509", "rfid_tag": "RFID-I509"},
    {"nome": "João Pereira", "email": "joao@exemplo.com", "apartamento": "510", "rfid_tag": "RFID-J510"},
]

PERFIS = [
    # Chegam à noite e só tiram o carro de manhã
    PerfilSimulado("RFID-A101", 3.0, (19.5, 22.0), (18, 30), (6, 9)),
    PerfilSimulado("RFID-B102", 2.5, (20.0, 22.5), (15, 28), (5, 8)),
    # Noturnos que desconectam logo depois de terminar
    PerfilSimulado("RFID-C203", 2.0, (21.5, 23.0), (15, 25), (0, 0.6)),
    PerfilSimulado("RFID-J510", 2.0, (21.0, 23.5), (12, 22), (0, 0.8)),
    # Diurnos frequentes (home office)
    PerfilSimulado("RFID-D204", 4.5, (8.5, 11.5), (8, 15), (0, 1.5), so_dia_util=True),
    PerfilSimulado("RFID-E305", 4.0, (13.0, 15.5), (8, 14), (0, 1.0), so_dia_util=True),
    # Fim de semana
    PerfilSimulado("RFID-F306", 1.6, (9.0, 14.0), (25, 40), (0, 2.0), so_fim_de_semana=True),
    PerfilSimulado("RFID-G407", 1.4, (10.0, 16.0), (20, 35), (0, 1.5), so_fim_de_semana=True),
    # Ocasionais
    PerfilSimulado("RFID-H408", 1.0, (10.0, 17.0), (6, 14), (0, 1.0)),
    PerfilSimulado("RFID-I509", 0.8, (11.0, 18.0), (5, 12), (0, 0.7)),
]


def carregadores_simulados() -> list[CarregadorSimulado]:
    return [CarregadorSimulado(c["numero_serie"], c["potencia_kw"]) for c in CARREGADORES]
