# EV ChargeOps – Sistema Inteligente de Gestão de Recarga Compartilhada para Veículos Elétricos

## Enterprise Challenge 2026 – GoodWe

---

# Integrantes

| Nome                            | RM        |
| ------------------------------- | --------- |
| Isaac Aurélio de Freitas Castro | RM 571175 |
| Julia Guimarães                 | RM 572241 |
| Samirah Pinotti Deranian        | RM 573375 |
| Luiz Pedro Pereira Duarte       | RM 568970 |

---

# Sumário

1. Introdução
2. Contextualização do Problema
3. Objetivos do Projeto
4. Frente 1 – Pesquisa e Análise de Mercado
5. Frente 2 – Base Regulatória e Técnica
6. Frente 3 – Arquitetura da Solução
7. Modelo de Banco de Dados
8. Modelo de Rateio
9. Aplicação de Inteligência Artificial
10. Fluxo Operacional da Plataforma
11. Tecnologias Utilizadas
12. Plano de Desenvolvimento da Sprint 02
13. Benefícios da Solução
14. Conclusão
15. Referências

---

# 1. Introdução

A eletrificação da mobilidade urbana vem crescendo rapidamente em todo o mundo. No Brasil, o aumento da venda de veículos elétricos e híbridos tem impulsionado a necessidade de infraestrutura adequada para recarga.

Em condomínios residenciais, estacionamentos corporativos e centros comerciais, a adoção de carregadores compartilhados apresenta novos desafios relacionados ao gerenciamento da energia, controle dos usuários e cobrança do consumo.

Diante desse cenário, foi desenvolvida a proposta do EV ChargeOps, uma plataforma inteligente voltada para monitoramento, gestão e análise de dados provenientes de carregadores compartilhados de veículos elétricos.

A solução integra equipamentos GoodWe, APIs, banco de dados, dashboards gerenciais e inteligência artificial para otimizar a utilização da infraestrutura e garantir transparência no consumo energético.

---

# 2. Contextualização do Problema

Atualmente, muitos condomínios utilizam carregadores compartilhados sem mecanismos adequados para:

* Identificação dos usuários;
* Controle individual do consumo;
* Rateio justo dos custos;
* Monitoramento da infraestrutura;
* Planejamento de expansão da rede elétrica;
* Identificação de falhas operacionais.

Em diversos casos, o valor da energia consumida é dividido igualmente entre todos os moradores, independentemente do uso real da estação de recarga.

Esse modelo gera problemas financeiros, operacionais e administrativos.

Além disso, administradores e síndicos possuem pouca visibilidade sobre:

* Horários de maior utilização;
* Quantidade de sessões realizadas;
* Taxa de ocupação dos carregadores;
* Crescimento da demanda;
* Necessidade futura de expansão.

---

# 3. Objetivos do Projeto

## Objetivo Geral

Desenvolver uma plataforma inteligente capaz de gerenciar carregadores compartilhados de veículos elétricos utilizando análise de dados e inteligência artificial.

## Objetivos Específicos

* Monitorar sessões de recarga em tempo real;
* Registrar dados operacionais dos carregadores;
* Automatizar o cálculo do consumo energético;
* Realizar rateio individualizado;
* Aplicar algoritmos de inteligência artificial;
* Fornecer dashboards para gestores e usuários;
* Melhorar a eficiência operacional da infraestrutura.

---

# 4. Frente 1 – Pesquisa e Análise de Mercado

## ChargePoint

A ChargePoint é uma das maiores redes de carregamento de veículos elétricos do mundo.

### Funcionalidades

* Gestão remota;
* Controle de usuários;
* Relatórios analíticos;
* Aplicativo mobile;
* Integração em nuvem.

### Pontos Fortes

* Grande escala;
* Plataforma consolidada;
* Recursos corporativos.

### Limitações

* Alto custo;
* Foco em mercados internacionais.

---

## Zaptec

Empresa europeia especializada em carregamento inteligente.

### Funcionalidades

* Balanceamento de carga;
* Gestão centralizada;
* Monitoramento remoto.

### Pontos Fortes

* Excelente gerenciamento energético.

### Limitações

* Menor presença no mercado brasileiro.

---

## Wallbox

Empresa especializada em carregadores inteligentes residenciais.

### Funcionalidades

* Controle via aplicativo;
* Monitoramento remoto;
* Configuração simplificada.

### Pontos Fortes

* Facilidade de uso.

### Limitações

* Menor foco em ambientes compartilhados.

---

## Comparação das Soluções

| Critério             | ChargePoint | Zaptec | Wallbox |
| -------------------- | ----------- | ------ | ------- |
| Gestão compartilhada | Alta        | Alta   | Média   |
| IA aplicada          | Média       | Média  | Baixa   |
| Escalabilidade       | Alta        | Alta   | Média   |
| Foco residencial     | Médio       | Médio  | Alto    |

---

## Conclusão da Pesquisa

As soluções analisadas apresentam excelente infraestrutura de monitoramento, porém poucas exploram inteligência artificial voltada para previsão de demanda, otimização de uso e modelos inteligentes de rateio.

---

# 5. Frente 2 – Base Regulatória e Técnica

## Resolução Normativa ANEEL nº 1000/2021

A resolução estabelece diretrizes para fornecimento de energia elétrica e regulamenta aspectos relacionados à utilização da rede.

Aspectos relevantes:

* Segurança elétrica;
* Medição adequada do consumo;
* Conformidade técnica;
* Transparência operacional.

## GoodWe HCA G2

O carregador GoodWe HCA G2 foi escolhido como referência para o projeto.

### Interfaces Disponíveis

* Wi-Fi
* LAN
* Bluetooth
* RFID
* RS-485

## API GoodWe SEMS Portal

A API fornece:

* Histórico de sessões;
* Energia consumida;
* Status operacional;
* Informações do carregador;
* Eventos e notificações.

Esses dados serão utilizados para alimentar o sistema EV ChargeOps.

---

# 6. Frente 3 – Arquitetura da Solução

## Visão Geral da Arquitetura

Veículo Elétrico → Carregador GoodWe → API SEMS Portal → Backend EV ChargeOps → Banco de Dados → Módulo de IA → Dashboard Web

## Backend

Responsável por:

* Receber dados das APIs;
* Processar sessões;
* Calcular rateios;
* Gerar relatórios;
* Integrar os módulos da plataforma.

Tecnologias:

* Python
* FastAPI

## Frontend

Responsável pela visualização dos dados.

Tecnologias:

* React
* Next.js

## Banco de Dados

Tecnologia escolhida:

PostgreSQL

---

# 7. Modelo de Banco de Dados

## Tabela Usuários

| Campo       | Tipo    |
| ----------- | ------- |
| id          | UUID    |
| nome        | VARCHAR |
| email       | VARCHAR |
| apartamento | VARCHAR |

## Tabela Carregadores

| Campo       | Tipo    |
| ----------- | ------- |
| id          | UUID    |
| modelo      | VARCHAR |
| status      | VARCHAR |
| localizacao | VARCHAR |

## Tabela Sessões

| Campo         | Tipo      |
| ------------- | --------- |
| id            | UUID      |
| usuario_id    | UUID      |
| carregador_id | UUID      |
| inicio        | TIMESTAMP |
| fim           | TIMESTAMP |
| energia_kwh   | FLOAT     |
| custo         | FLOAT     |

---

# 8. Modelo de Rateio

O sistema realizará rateio baseado no consumo real.

### Fórmula

Valor Final =

(Consumo em kWh × Tarifa)

*

(Tempo de utilização × Taxa de ocupação)

*

(Taxa de manutenção compartilhada)

### Benefícios

* Justiça financeira;
* Transparência;
* Escalabilidade;
* Controle individual.

---

# 9. Aplicação de Inteligência Artificial

## Previsão de Demanda

Objetivo: prever horários de maior utilização.

Técnicas:

* Regressão Linear;
* Séries Temporais.

## Clusterização

Objetivo: identificar perfis de uso.

Algoritmo:

* K-Means.

## Detecção de Anomalias

Objetivo:

* Detectar falhas;
* Detectar consumos anormais;
* Identificar possíveis fraudes.

Algoritmo:

* Isolation Forest.

## Assistente Inteligente

Permite consultas como:

* Qual foi meu consumo este mês?
* Qual o horário mais utilizado?
* Quanto devo pagar?

---

# 10. Fluxo Operacional

1. Usuário conecta o veículo.
2. Carregador inicia a sessão.
3. API GoodWe registra os dados.
4. Backend processa as informações.
5. Banco de dados armazena o histórico.
6. IA realiza análises.
7. Dashboard exibe resultados.
8. Sistema calcula o rateio.

---

# 11. Tecnologias Utilizadas

| Camada         | Tecnologia   |
| -------------- | ------------ |
| Backend        | FastAPI      |
| Frontend       | React        |
| Banco de Dados | PostgreSQL   |
| IA             | Scikit-Learn |
| APIs           | REST         |
| Infraestrutura | Docker       |
| Cloud          | AWS          |

---

# 12. Plano Sprint 02

## Etapa 1

Implementação do backend.

## Etapa 2

Modelagem e criação do banco de dados.

## Etapa 3

Integração com APIs GoodWe.

## Etapa 4

Desenvolvimento do dashboard.

## Etapa 5

Implementação dos modelos de IA.

## Etapa 6

Testes integrados.

---

# 13. Benefícios da Solução

## Para os Usuários

* Cobrança justa;
* Transparência;
* Histórico de consumo.

## Para os Administradores

* Controle operacional;
* Monitoramento em tempo real;
* Relatórios automatizados.

## Para a Infraestrutura

* Melhor utilização dos carregadores;
* Redução de desperdícios;
* Planejamento de expansão.

---

# 14. Conclusão

O EV ChargeOps propõe uma abordagem moderna para gestão de carregadores compartilhados de veículos elétricos.

A utilização de APIs, banco de dados estruturado, dashboards analíticos e inteligência artificial permite transformar dados operacionais em informações estratégicas.

A solução apresenta potencial para melhorar significativamente a eficiência, transparência e sustentabilidade da infraestrutura de recarga compartilhada.

---

# 15. Referências

* ANEEL. Resolução Normativa nº 1000/2021.
* GoodWe. Documentação Técnica HCA G2.
* GoodWe SEMS Portal API Documentation.
* ChargePoint Developer Documentation.
* Wallbox Documentation.
* Zaptec Documentation.
* PostgreSQL Official Documentation.
* FastAPI Official Documentation.
* Scikit-Learn Documentation.
* Open Charge Map API Documentation.
