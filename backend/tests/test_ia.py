import random
from datetime import datetime, timedelta

from app.ia.anomalias import DetectorAnomalias, extrair_features
from app.ia.assistente import ClassificadorIntencao
from app.ia.demanda import PrevisorDemanda, ocupacao_por_hora


def sessoes_normais(n=80, semente=1):
    rng = random.Random(semente)
    base = datetime(2026, 9, 1)
    feats = []
    for i in range(n):
        inicio = base + timedelta(days=i % 30, hours=rng.uniform(19, 22))
        energia = rng.uniform(15, 25)
        fim_recarga = inicio + timedelta(hours=energia / 6.5)
        fim = fim_recarga + timedelta(hours=rng.uniform(0, 1))
        feats.append(extrair_features(inicio, fim_recarga, fim, energia))
    return feats


def test_regra_fisica_funciona_sem_modelo_treinado():
    detector = DetectorAnomalias()
    inicio = datetime(2026, 9, 1, 20)
    # 40 kWh em 2 h = 20 kW num carregador de 7 kW: impossível
    resultado = detector.avaliar(extrair_features(inicio, inicio + timedelta(hours=2), inicio + timedelta(hours=2), 40), 7.0)
    assert resultado.anomala
    assert "limite do carregador" in resultado.motivos[0]
    assert resultado.score is None


def test_isolation_forest_sinaliza_sessao_atipica_e_aceita_normal():
    detector = DetectorAnomalias()
    assert detector.treinar(sessoes_normais())

    inicio = datetime(2026, 9, 10, 20, 30)
    normal = extrair_features(inicio, inicio + timedelta(hours=3), inicio + timedelta(hours=3.5), 19.5)
    assert not detector.avaliar(normal, 7.0).anomala

    # mesma recarga, mas o carro ficou 26 h conectado depois de terminar
    atipica = extrair_features(inicio, inicio + timedelta(hours=3), inicio + timedelta(hours=29), 19.5)
    resultado = detector.avaliar(atipica, 7.0)
    assert resultado.anomala
    assert any("tempo ocioso" in m.lower() for m in resultado.motivos)


def test_detector_exige_historico_minimo():
    assert not DetectorAnomalias().treinar(sessoes_normais(n=10))


def test_ocupacao_por_hora_divide_minutos_entre_horas():
    inicio = datetime(2026, 9, 1, 10, 30)
    ocupacao = ocupacao_por_hora([(inicio, inicio + timedelta(hours=1))], n_carregadores=1)
    assert ocupacao[(inicio.date(), 10)] == 0.5
    assert ocupacao[(inicio.date(), 11)] == 0.5


def test_previsor_aprende_padrao_semanal():
    # Carregador sempre ocupado das 20h às 23h, todos os dias, por 4 semanas
    base = datetime(2026, 8, 3)
    intervalos = [(base + timedelta(days=d, hours=20), base + timedelta(days=d, hours=23)) for d in range(28)]
    previsor = PrevisorDemanda()
    assert previsor.treinar(intervalos, n_carregadores=1)
    assert previsor.nivel(datetime(2026, 10, 7, 21)) == "alta"
    assert previsor.nivel(datetime(2026, 10, 7, 10)) == "baixa"


def test_assistente_entende_variacoes_e_erros_de_digitacao():
    classificador = ClassificadorIntencao()
    assert classificador.classificar("quanto eu vou pagar esse mes?")[0] == "valor_fatura"
    assert classificador.classificar("qnts kwh consumi")[0] == "consumo_mes"
    assert classificador.classificar("melhor horario pra carregar amanha")[0] == "melhor_horario"


def test_assistente_descarta_perguntas_fora_do_escopo():
    classificador = ClassificadorIntencao()
    assert classificador.classificar("qual a capital da França?")[0] == "desconhecida"
    assert classificador.classificar("bom dia")[0] == "desconhecida"
