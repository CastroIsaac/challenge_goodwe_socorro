"""Roteiro de demonstração do fluxo completo contra a API em execução.

Registra uma sessão normal e uma impossível, mostra a decisão da IA e o custo,
revisa a sessão barrada, consulta o rateio e conversa com o assistente.

Uso (com a API rodando em localhost:8000):  python -m app.demonstracao
"""

import json
import os
from datetime import datetime, timedelta

import httpx

API = os.getenv("API_URL", "http://localhost:8000")


def mostrar(titulo: str, dados) -> None:
    print(f"\n=== {titulo} ===")
    print(json.dumps(dados, ensure_ascii=False, indent=2, default=str))


def leitura(id_externo: str, rfid: str, inicio: datetime, horas_recarga: float, horas_ociosas: float, kwh: float) -> dict:
    fim_recarga = inicio + timedelta(hours=horas_recarga)
    return {
        "id_externo": id_externo,
        "numero_serie_carregador": "HCAG2-0002",
        "rfid_tag": rfid,
        "inicio": inicio.isoformat(),
        "fim_recarga": fim_recarga.isoformat(),
        "fim": (fim_recarga + timedelta(hours=horas_ociosas)).isoformat(),
        "energia_kwh": kwh,
    }


def main():
    cliente = httpx.Client(base_url=API, timeout=30)
    ontem = (datetime.now() - timedelta(days=1)).replace(second=0, microsecond=0)
    marca = datetime.now().strftime("%H%M%S")

    mostrar("Status dos modelos de IA", cliente.get("/ia/status").json())

    # 1) Sessão normal: Carla carrega 20 kWh das 22h às 1h e desconecta 20 min depois
    normal = cliente.post("/sessoes", json=leitura(
        f"DEMO-{marca}-1", "RFID-C203", ontem.replace(hour=22, minute=0), 3.0, 0.33, 20.0)).json()
    mostrar("Sessão normal registrada", normal)

    # 2) Sessão com ociosidade longa em horário disputado: Diego deixa o carro 4 h depois de carregar
    ociosa = cliente.post("/sessoes", json=leitura(
        f"DEMO-{marca}-2", "RFID-D204", ontem.replace(hour=9, minute=0), 1.5, 4.0, 10.0)).json()
    mostrar("Sessão com ociosidade (taxa de ocupação pela demanda prevista)", ociosa["custo"])

    # 3) Sessão impossível: 55 kWh em 2 h num carregador de 7 kW
    suspeita = cliente.post("/sessoes", json=leitura(
        f"DEMO-{marca}-3", "RFID-H408", ontem.replace(hour=14, minute=0), 2.0, 0.2, 55.0)).json()
    mostrar("Sessão suspeita: decisão da IA", {"status": suspeita["sessao"]["status"], **suspeita["ia"]})

    mes = ontem.strftime("%Y-%m")
    antes = cliente.get(f"/rateio/{mes}").json()["total_arrecadado"]
    revisada = cliente.post(f"/sessoes/{suspeita['sessao']['id']}/revisao",
                            json={"decisao": "rejeitar", "observacao": "Leitura duplicada do medidor"}).json()
    mostrar("Gestor rejeita a sessão suspeita", {"status": revisada["status"], "observacao": revisada["observacao_gestor"]})
    depois = cliente.get(f"/rateio/{mes}").json()
    mostrar("Total do rateio antes/depois da revisão (a sessão rejeitada nunca entra)",
            {"antes": antes, "depois": depois["total_arrecadado"]})

    mostrar(f"Rateio de {mes}", depois)

    carla = next(u for u in cliente.get("/usuarios").json() if u["rfid_tag"] == "RFID-C203")
    for pergunta in ["quanto eu vou pagar esse mes?", "qnts kwh consumi", "qual o melhor horario pra carregar?",
                     "qual o horário de pico?", "qual é meu perfil?", "qual a capital da França?"]:
        resposta = cliente.post("/assistente", json={"usuario_id": carla["id"], "pergunta": pergunta}).json()
        mostrar(f"Assistente (Carla) — \"{pergunta}\"", resposta)


if __name__ == "__main__":
    main()
