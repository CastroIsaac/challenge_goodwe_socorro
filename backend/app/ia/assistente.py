"""Classificador de intenção do assistente.

Converte a pergunta em texto livre em uma intenção conhecida usando TF-IDF de
n-gramas de caracteres (tolera erros de digitação e falta de acento) e
regressão logística. Perguntas fora do escopo são descartadas por dois
critérios: baixa confiança do classificador OU baixa similaridade (cosseno)
com todos os exemplos de treino. A resposta em si é montada com os dados reais do usuário
em services/assistente.py; aqui só decidimos O QUE a pessoa está perguntando.
"""

import unicodedata

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import make_pipeline

EXEMPLOS = {
    "consumo_mes": [
        "qual foi meu consumo este mês", "quanto eu consumi", "quantos kwh eu usei",
        "meu consumo de energia", "quanta energia gastei esse mes", "consumo do mês",
        "quantas recargas eu fiz", "quantas vezes carreguei o carro",
    ],
    "valor_fatura": [
        "quanto devo pagar", "qual o valor da minha fatura", "quanto vou pagar este mês",
        "valor da conta", "quanto está minha cobrança", "me mostra a fatura",
        "por que estou pagando isso", "detalhe do rateio",
    ],
    "horario_mais_usado": [
        "qual o horário mais utilizado", "que horas o carregador é mais usado", "horário de pico",
        "quando o carregador fica mais ocupado", "horário mais movimentado", "qual horario mais cheio",
    ],
    "melhor_horario": [
        "qual o melhor horário para carregar", "quando devo carregar", "quando o carregador está livre",
        "melhor hora para recarregar", "quando é mais barato carregar", "que horas tem vaga",
        "quando vai estar disponível amanhã",
    ],
    "perfil": [
        "qual é meu perfil", "como eu uso o carregador", "meus hábitos de recarga",
        "que tipo de usuário eu sou", "me dá uma dica", "como posso economizar",
    ],
    "sessoes_revisao": [
        "tenho alguma sessão em revisão", "por que minha sessão não foi cobrada",
        "sessão bloqueada", "minha recarga foi marcada como anomalia", "sessão suspeita",
    ],
}

LIMIAR_CONFIANCA = 0.30
# Medido com perguntas de teste: as válidas ficaram >= 0,57 e as fora do escopo
# ("qual a capital da França?", "bom dia") <= 0,32
LIMIAR_SIMILARIDADE = 0.40


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower().strip()


class ClassificadorIntencao:
    def __init__(self):
        frases, rotulos = [], []
        for intencao, exemplos in EXEMPLOS.items():
            frases += [normalizar(e) for e in exemplos]
            rotulos += [intencao] * len(exemplos)
        self.modelo = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)),
            LogisticRegression(C=10, solver="liblinear"),
        ).fit(frases, rotulos)
        self._vetorizador = self.modelo[0]
        self._exemplos = self._vetorizador.transform(frases)

    def classificar(self, pergunta: str) -> tuple[str, float]:
        """Retorna (intenção, confiança). Abaixo do limiar, a intenção é "desconhecida"."""
        texto = normalizar(pergunta)
        probabilidades = self.modelo.predict_proba([texto])[0]
        indice = probabilidades.argmax()
        confianca = float(probabilidades[indice])
        similaridade = cosine_similarity(self._vetorizador.transform([texto]), self._exemplos).max()
        if confianca < LIMIAR_CONFIANCA or similaridade < LIMIAR_SIMILARIDADE:
            return "desconhecida", confianca
        return str(self.modelo.classes_[indice]), confianca
