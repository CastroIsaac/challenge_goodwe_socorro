"""Teste de ponta a ponta: popula um banco temporário com o histórico simulado
e exercita o fluxo principal pela API."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def cliente():
    with TestClient(app) as c:
        yield c


def test_modelos_treinados_apos_popular(cliente):
    status = cliente.get("/ia/status").json()
    assert all(status[m]["treinado"] for m in ["anomalias", "demanda", "perfis", "assistente"])


def nova_leitura(horas_atras, energia, ociosidade_h=0.2):
    inicio = (datetime.now() - timedelta(hours=horas_atras)).replace(second=0, microsecond=0)
    fim_recarga = inicio + timedelta(hours=energia / 6.6)
    return {
        "id_externo": f"TESTE-{inicio:%Y%m%d%H%M}-{energia}",
        "numero_serie_carregador": "HCAG2-0001",
        "rfid_tag": "RFID-C203",
        "inicio": inicio.isoformat(),
        "fim_recarga": fim_recarga.isoformat(),
        "fim": (fim_recarga + timedelta(hours=ociosidade_h)).isoformat(),
        "energia_kwh": energia,
    }


def test_sessao_normal_entra_no_rateio(cliente):
    resposta = cliente.post("/sessoes", json=nova_leitura(horas_atras=6, energia=14))
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["sessao"]["custo"] == round(corpo["custo"]["custo_energia"] + corpo["custo"]["custo_ocupacao"], 2)
    assert corpo["custo"]["custo_energia"] > 0


def test_sessao_impossivel_vai_para_revisao_e_fica_fora_da_fatura(cliente):
    mes = datetime.now().strftime("%Y-%m")
    antes = cliente.get(f"/rateio/{mes}").json()

    leitura = nova_leitura(horas_atras=10, energia=20)
    leitura["energia_kwh"] = 60  # mesma duração, energia impossível para 7 kW
    corpo = cliente.post("/sessoes", json=leitura).json()
    assert corpo["sessao"]["status"] == "em_revisao"
    assert corpo["ia"]["anomala"]

    depois = cliente.get(f"/rateio/{mes}").json()
    assert depois["total_arrecadado"] == antes["total_arrecadado"]
    assert depois["sessoes_em_revisao"] == antes["sessoes_em_revisao"] + 1

    # Gestor confirma que é erro: rejeita, e ela nunca é cobrada
    revisada = cliente.post(f"/sessoes/{corpo['sessao']['id']}/revisao",
                            json={"decisao": "rejeitar", "observacao": "erro do medidor"}).json()
    assert revisada["status"] == "rejeitada"


def test_sessao_duplicada_e_recusada(cliente):
    leitura = nova_leitura(horas_atras=30, energia=9)
    assert cliente.post("/sessoes", json=leitura).status_code == 201
    assert cliente.post("/sessoes", json=leitura).status_code == 422


def test_rateio_fecha_com_manutencao_exata(cliente):
    mes = datetime.now().strftime("%Y-%m")
    rateio = cliente.get(f"/rateio/{mes}").json()
    assert round(sum(i["valor_manutencao"] for i in rateio["itens"]), 2) == rateio["custo_manutencao_mensal"]
    fechamento = cliente.post(f"/rateio/{mes}/fechar").json()
    assert fechamento["total"] == rateio["total_arrecadado"]


def test_assistente_responde_com_dados_do_usuario(cliente):
    usuario = next(u for u in cliente.get("/usuarios").json() if u["rfid_tag"] == "RFID-C203")
    resposta = cliente.post("/assistente", json={"usuario_id": usuario["id"], "pergunta": "quanto devo pagar?"}).json()
    assert resposta["intencao"] == "valor_fatura"
    assert "R$" in resposta["resposta"]
