# EV ChargeOps – Sprint 02: protótipo funcional

Enterprise Challenge 2026 – GoodWe / FIAP

Plataforma de gestão de recarga compartilhada de veículos elétricos: registra as sessões de recarga de cada usuário, calcula o consumo individual, aplica o modelo de rateio definido na sprint 01 e usa inteligência artificial para validar sessões, precificar a ocupação das vagas e orientar moradores e gestores.

A documentação da sprint 01 (pesquisa, base regulatória, arquitetura e modelo de rateio) está em [`docs/sprint01/`](docs/sprint01/).

## Integrantes

| Nome                            | RM        |
| ------------------------------- | --------- |
| Isaac Aurélio de Freitas Castro | RM 571175 |
| Julia Guimarães                 | RM 572241 |
| Samirah Pinotti Deranian        | RM 573375 |
| Luiz Pedro Pereira Duarte       | RM 568970 |

---

## 1. O que foi implementado

| Planejado na sprint 01                         | Situação na sprint 02 |
| ---------------------------------------------- | --------------------- |
| Backend em Python + FastAPI                    | Implementado (`backend/`) |
| Banco PostgreSQL (usuários, carregadores, sessões, faturamento) | Implementado, com SQLAlchemy. Roda em PostgreSQL no Docker e em SQLite no modo local |
| Integração com a API GoodWe SEMS Portal        | Interface pronta + simulador do SEMS (ver desvios, seção 8) |
| Modelo de rateio (energia + ocupação + manutenção) | Implementado (`backend/app/services/rateio.py`) |
| Previsão de demanda (regressão / séries temporais) | Implementado, e usado no cálculo da taxa de ocupação |
| Clusterização de perfis (K-Means)              | Implementado |
| Detecção de anomalias (Isolation Forest)       | Implementado, e usado como etapa obrigatória antes do rateio |
| Assistente inteligente                         | Implementado (classificador de intenção + respostas com dados reais) |
| Dashboard web em React / Next.js               | Implementado (`frontend/`) |
| Docker                                         | `docker-compose.yml` com banco, API e frontend |
| Testes integrados                              | 25 testes automatizados (`backend/tests/`) |

## 2. Arquitetura

```
Carregador GoodWe HCA G2 ──(RFID identifica o usuário)
          │
          ▼
Fonte de sessões (FonteSessoes)  ← hoje: SimuladorSems | futuro: cliente HTTP do SEMS Portal
          │  leitura: id, carregador, rfid, início, fim da recarga, desconexão, kWh
          ▼
Backend FastAPI ── registrar_sessao()
   1. identifica usuário e carregador
   2. IA: detector de anomalias  ──────────► anômala? status = em_revisao (fora do rateio)
   3. rateio: tarifa por horário + ocupação × fator da demanda prevista pela IA
   4. grava no PostgreSQL
          │
          ├── Rateio mensal (energia + ocupação + cota de manutenção)
          ├── MotorIA: retreino dos modelos com o histórico faturável
          └── API REST ──► Frontend Next.js (painel do gestor, área do morador, sessões, IA)
```

Estrutura do repositório:

```
backend/
  app/
    main.py              inicialização da API (cria tabelas, popula e treina a IA)
    config.py            tarifas, taxas e limites (todos configuráveis por variável de ambiente)
    models.py            tabelas do banco
    schemas.py           formatos de entrada e saída da API
    api/rotas.py         endpoints REST
    services/
      sessoes.py         fluxo principal: leitura -> IA -> custo -> banco
      rateio.py          cálculo de custo de cada sessão e divisão da manutenção
      faturamento.py     rateio mensal e fechamento do mês
      assistente.py      respostas do assistente com dados reais
    ia/
      anomalias.py       Isolation Forest + regra física + limite aprendido
      demanda.py         previsão de ocupação por hora (Ridge com variáveis sazonais)
      perfis.py          K-Means de hábitos dos usuários
      assistente.py      classificador de intenção (TF-IDF + regressão logística)
      motor.py           guarda os modelos treinados e faz o retreino
    integracoes/sems.py  interface da fonte de sessões + simulador do SEMS Portal
    dados_demo.py        cenário de demonstração (10 moradores, 2 carregadores)
    seed.py              gera 120 dias de histórico passando pelo fluxo real
    avaliacao.py         mede a IA em 5 cenários simulados
    demonstracao.py      roteiro que exercita a API de ponta a ponta
  tests/                 testes automatizados (pytest)
frontend/                Next.js 14 (app router) + Recharts
evidencias/              capturas de tela e saídas dos testes, da avaliação e da demonstração
docs/sprint01/           entregáveis da sprint 01
```

## 3. Fluxo de uma sessão

1. O morador conecta o veículo e se identifica com a tag RFID no HCA G2.
2. Ao final, a sessão chega ao backend (`POST /sessoes` ou sincronização com o SEMS) com início, fim do fluxo de energia, desconexão e kWh.
3. O **detector de anomalias** avalia a sessão. Se ela for anômala, fica com status `em_revisao`, com o motivo explicado, e **não entra no rateio** até o gestor aprovar ou rejeitar no painel.
4. O **custo** é calculado: energia minuto a minuto pela tarifa do horário e ociosidade cobrada conforme a **demanda prevista pela IA** para cada minuto.
5. No fim do mês, o gestor fecha o rateio, que soma as sessões faturáveis e divide a manutenção. O resultado é gravado na tabela `faturamento`.

## 4. Modelo de rateio

Fórmula definida na sprint 01 (`docs/sprint01/modelo_rateio.md`):

```
Valor = (consumo kWh × tarifa) + (tempo de ocupação × taxa de ocupação) + taxa de manutenção compartilhada
```

Como cada parcela foi implementada:

| Parcela | Regra | Parâmetros padrão (`config.py`) |
| ------- | ----- | -------------------------------- |
| Energia | A energia da sessão é distribuída igualmente pelos minutos de recarga (potência constante) e cada minuto paga a tarifa do seu posto da Tarifa Branca. Fim de semana é todo fora de ponta. | Fora de ponta R$ 0,78; intermediário (16h30–17h30 e 20h30–21h30) R$ 1,12; ponta (17h30–20h30) R$ 1,79 por kWh |
| Ocupação | Só conta o tempo em que o carro fica **conectado sem carregar**, depois de uma tolerância. Cada minuto cobrado vale a taxa por hora multiplicada pelo fator do nível de demanda previsto pela IA. | Tolerância 30 min; R$ 4,00/h; fator 0× (demanda baixa), 1× (moderada), 2× (alta) |
| Manutenção | Custo mensal do carregador dividido igualmente entre os usuários que usaram no mês. A divisão é feita em centavos para a soma fechar exatamente (R$ 100 / 3 = 33,34 + 33,33 + 33,33). | R$ 150,00 por mês |

Exemplos reais do sistema (saída em `evidencias/demonstracao_api.txt`):

- **Carla**, 20 kWh das 22h à 1h e desconexão 20 min depois: 20 × R$ 0,78 = **R$ 15,60** de energia; 20 min ociosos estão dentro da tolerância, então ocupação = R$ 0,00.
- **Diego**, 10 kWh das 9h às 10h30 e mais 4 h conectado: energia 10 × 0,78 = R$ 7,80. Ociosidade de 240 min, 210 após a tolerância: 150 min em demanda moderada (150/60 × R$ 4,00 × 1 = R$ 10,00) e 60 min em demanda baixa (fator 0). Ocupação = **R$ 10,00**.
- Com 8 moradores ativos no mês, cada um paga **R$ 18,75** de cota de manutenção.

Os valores das tarifas são referências aproximadas e devem ser atualizados pelo gestor conforme a fatura da concessionária (variáveis `TARIFA_*`).

## 5. Módulo de inteligência artificial

A IA participa do fluxo principal: duas das quatro funções alteram diretamente o valor cobrado de cada usuário.

| Modelo | Algoritmo | Papel no fluxo |
| ------ | --------- | -------------- |
| Detector de anomalias | Isolation Forest + regra física + limite aprendido do histórico | Toda sessão passa por ele antes do rateio. Sessão anômala fica fora da cobrança até revisão do gestor. Protege contra erro de medição, cobrança indevida e uso suspeito. |
| Previsão de demanda | Regressão linear regularizada (Ridge) com variáveis sazonais (dia da semana e hora, separando dia útil e fim de semana) | Define o nível de demanda (baixa/moderada/alta) de cada minuto ocioso e, com isso, o preço da ocupação. Ocupar a vaga quando ninguém precisa não é cobrado; ocupar no horário disputado custa o dobro. Também recomenda os horários mais livres. |
| Perfis de uso | K-Means sobre os hábitos de cada usuário (horário médio circular, kWh médio, frequência, ociosidade, uso no fim de semana); k escolhido pelo coeficiente de silhueta | Gera o perfil e a recomendação personalizada exibidos ao morador e usados pelo assistente. |
| Assistente | TF-IDF de n-gramas de caracteres + regressão logística, com descarte por baixa confiança ou baixa similaridade | Entende perguntas em texto livre (tolera erro de digitação e falta de acento) e responde com dados reais: consumo, fatura, horário de pico, melhor horário, perfil e sessões em revisão. |

**Treino.** O `MotorIA` treina com as sessões faturáveis (as rejeitadas e em revisão ficam de fora para não contaminar o modelo). O seed simula a operação: as sessões entram em ordem cronológica e os modelos são retreinados a cada 7 dias. O detector só é ativado com 60 sessões de histórico e a previsão de demanda com 14 dias. Antes disso valem a regra física e a taxa de ocupação base. Há também o botão "Retreinar" na página Modelos de IA (`POST /ia/treinar`).

**Resultados** (`python -m app.avaliacao`, 5 cenários simulados com sementes diferentes, saída em `evidencias/avaliacao_ia.txt`):

- Detector de anomalias, comparado ao gabarito das anomalias injetadas pelo simulador: **precisão 0,65, recall 0,95**, com 4,4% das sessões enviadas para revisão manual.
- Previsão de demanda, validada nas 2 últimas semanas: erro médio absoluto de 0,20 a 0,25 contra 0,26 a 0,30 da média simples (cerca de 20% menor).
- Perfis: silhueta de 0,6. O K-Means encontrou os 5 grupos de hábito usados para gerar os dados, sem ter acesso a eles.

**Calibração do detector.** A primeira versão (contaminação de 4% e mínimo de 30 sessões) mandava cerca de 15% das sessões para revisão, com precisão de 0,20. Testamos combinações de contaminação e histórico mínimo e escolhemos 1% e 60 sessões, porque um falso positivo custa só uma revisão manual, mas um excesso deles torna a fila inútil para o síndico.

**Limitação encontrada no Isolation Forest.** Nos testes, uma sessão com 26 h de ociosidade não era sinalizada. O motivo é que o Isolation Forest não extrapola: um valor além do maior valor de treino percorre as árvores pelo mesmo caminho desse maior valor e parece normal. Por isso acrescentamos uma terceira camada, um limite por característica aprendido do histórico (percentil 99,5 + 1,5 × intervalo interquartil). Sem essa camada, parte das sessões com ociosidade extrema passava despercebida nos testes; com ela, nenhuma desse tipo foi perdida.

## 6. Como executar

### Opção A: Docker (recomendado)

Requisito: Docker Desktop.

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- API e documentação interativa (Swagger): http://localhost:8000/docs

Na primeira subida o banco está vazio. A API gera 120 dias de histórico simulado e treina os modelos automaticamente (alguns segundos). Para recomeçar do zero: `docker compose down -v`.

### Opção B: local, sem Docker

Requisitos: Python 3.12 e Node.js 20. Usa SQLite, sem instalar banco.

```bash
# Backend
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (outro terminal)
cd frontend
npm install
npm run dev
```

### Comandos úteis (na pasta `backend`, com o ambiente ativado)

```bash
pytest -v                    # testes automatizados
python -m app.seed           # recria o banco com novo histórico simulado
python -m app.avaliacao      # avaliação da IA em 5 cenários
python -m app.demonstracao   # roteiro de demonstração contra a API rodando
```

### Principais endpoints

| Método | Rota | Função |
| ------ | ---- | ------ |
| POST | `/sessoes` | Registra a leitura de uma sessão (passa pela IA e calcula o custo) |
| GET | `/sessoes?mes=AAAA-MM&status=&usuario_id=` | Lista sessões |
| POST | `/sessoes/{id}/revisao` | Gestor aprova ou rejeita uma sessão barrada |
| POST | `/integracao/sems/sincronizar` | Importa da fonte as sessões encerradas desde a última |
| GET | `/rateio/{mes}` | Rateio do mês por usuário |
| POST | `/rateio/{mes}/fechar` | Grava o fechamento na tabela `faturamento` |
| GET | `/painel?mes=` | Indicadores do painel do gestor |
| GET | `/ia/status`, `/ia/previsao-demanda`, `/ia/perfis` | Estado e saídas dos modelos |
| POST | `/ia/treinar` | Retreina os modelos com o histórico |
| POST | `/assistente` | Pergunta em texto livre |
| GET | `/parametros` | Tarifas, taxas e limites em vigor |

## 7. Evidências de funcionamento

Na pasta [`evidencias/`](evidencias/):

| Arquivo | Conteúdo |
| ------- | -------- |
| `screenshots/painel_gestor.png` | KPIs, uso por horário, energia por posto tarifário, mapa de calor da demanda prevista, fila de revisão da IA e tabela de rateio |
| `screenshots/area_morador.png` | Fatura detalhada, perfil de uso identificado pelo K-Means, dica personalizada e histórico de sessões |
| `screenshots/sessoes.png` | Formulário de leitura do carregador e lista de sessões com score e motivo da IA |
| `screenshots/modelos_ia.png` | Métricas dos modelos, papel de cada um no fluxo e perfis descobertos |
| `demonstracao_api.txt` | Execução de ponta a ponta: sessão normal, sessão com ociosidade, sessão impossível barrada pela IA e rejeitada pelo gestor (o total do rateio não muda), rateio do mês e seis perguntas ao assistente |
| `avaliacao_ia.txt` | Precisão e recall do detector e erro da previsão de demanda em 5 cenários |
| `testes_pytest.txt` | Saída dos 25 testes automatizados |

Para ver a IA agindo ao vivo: na página **Sessões**, registre uma leitura com 60 kWh em 3 h de recarga. A sessão aparece como "Em revisão", com o motivo, e surge na fila do Painel do gestor.

## 8. Decisões técnicas e desvios em relação à sprint 01

| # | Sprint 01 | Sprint 02 | Justificativa |
| - | --------- | --------- | ------------- |
| 1 | Integração com a API GoodWe SEMS Portal | Interface `FonteSessoes` + `SimuladorSems` | A equipe não teve credenciais da API do SEMS Portal para o HCA G2 do Energy Innovation Lab durante a sprint. O sistema depende só da interface `buscar_sessoes(desde, ate)`; ao obter acesso, basta implementar um cliente HTTP com esse método. O simulador gera sessões realistas (perfis de uso, disputa por vaga, potência real de 88% a 97% da nominal) e injeta anomalias conhecidas, o que também permitiu medir a IA. |
| 2 | Fórmula de rateio com sinais divergentes (no README da sprint 01 aparece "×" entre as parcelas e em `modelo_rateio.md` aparece "+") | Parcelas somadas | O exemplo numérico da própria sprint 01 (R$ 33,25 + R$ 5,00 = R$ 38,25) soma as parcelas. Multiplicar não faria sentido: uma sessão sem ociosidade custaria zero. |
| 3 | "Tempo de utilização × taxa de ocupação" | Só o tempo **ocioso** (conectado sem carregar), após 30 min de tolerância, com fator definido pela demanda prevista | Cobrar o tempo de recarga em dobro, já que a energia já paga por ele, penalizaria quem carrega devagar. O problema real em vaga compartilhada é o carro que termina e continua ocupando a vaga. Ligar o fator à previsão de demanda torna a cobrança justa (não cobra quando ninguém precisa da vaga) e dá à IA um papel direto no rateio. |
| 4 | Tarifa única no exemplo (R$ 0,95) | Tarifa Branca por posto horário | A sprint 01 lista "horário de uso" entre as variáveis do rateio. A Tarifa Branca da ANEEL é a forma regulada de refletir isso. |
| 5 | "Taxa de manutenção compartilhada" (R$ 5,00 fixo no exemplo) | Custo mensal dividido entre os usuários ativos no mês | Torna a parcela de fato compartilhada: o custo total do condomínio é coberto exatamente, independentemente de quantos usaram. |
| 6 | Regressão linear / séries temporais | Ridge (regressão linear regularizada) com variáveis sazonais | Com as variáveis de dia da semana e hora em one-hot, a regressão linear comum fica com colunas colineares e coeficientes instáveis. O Ridge resolve isso mantendo o modelo linear e interpretável. |
| 7 | Isolation Forest | Isolation Forest + regra física + limite aprendido | A regra física funciona desde o primeiro dia, sem histórico. O limite aprendido cobre a limitação de extrapolação do Isolation Forest, encontrada em teste (seção 5). |
| 8 | Assistente inteligente (técnica não definida) | Classificador de intenção local + respostas montadas com consultas ao banco | Roda sem custo, sem chave de API externa e sem risco de inventar números: o texto da resposta sai sempre dos dados reais do usuário. Um modelo de linguagem pode ser colocado no lugar do classificador no futuro sem mudar o restante. |
| 9 | Tabelas `usuarios`, `carregadores`, `sessoes` e `faturamento` | Mesmas tabelas com campos extras | `rfid_tag` (identificação no HCA G2), `fim_recarga` (separa recarga de ociosidade), `status`, `score_anomalia`, `motivo_revisao` e `observacao_gestor` (fluxo de revisão), `custo_energia` e `custo_ocupacao` (transparência da fatura) e `numero_serie`/`potencia_kw` no carregador (usado na regra física). |
| 10 | Cloud AWS | Execução local via Docker Compose | O foco da sprint foi o protótipo funcional. As imagens Docker são o primeiro passo para publicar na AWS (por exemplo, ECS + RDS PostgreSQL). |
| 11 | React / Next.js | Next.js 14 em JavaScript, com Recharts | JavaScript em vez de TypeScript para manter o código simples para toda a equipe. |

Outras decisões:

- **Custo calculado e gravado no registro da sessão.** Se a previsão de demanda mudar depois de um retreino, as sessões já registradas não mudam de preço.
- **Horários em hora local (America/Sao_Paulo), sem fuso.** Simplifica o protótipo, já que todo o cenário está em um único fuso.
- **Sessão duplicada é recusada** pelo `id_externo` (identificador da sessão no SEMS), para que uma sincronização repetida não cobre duas vezes.

## 9. Limitações e próximos passos

- Conectar ao SEMS Portal real assim que houver credenciais, e validar os perfis e a previsão com dados reais do HCA G2 do Energy Innovation Lab.
- Autenticação e perfis de acesso (morador vê só os próprios dados; hoje a área do morador tem um seletor para demonstração).
- A distribuição da energia por minuto supõe potência constante. Com a curva de potência do SEMS, a tarifação por posto fica exata.
- Detector de anomalias por usuário (comparar cada sessão com o histórico do próprio morador) para reduzir falsos positivos.
- Publicação na AWS e retreino agendado (hoje o retreino é manual ou feito no seed).
