# Modelo de Banco de Dados

## Tabela usuarios

| Campo | Tipo |
|---------|---------|
| id | UUID |
| nome | VARCHAR |
| email | VARCHAR |
| apartamento | VARCHAR |

---

## Tabela carregadores

| Campo | Tipo |
|---------|---------|
| id | UUID |
| modelo | VARCHAR |
| status | VARCHAR |
| localizacao | VARCHAR |

---

## Tabela sessoes

| Campo | Tipo |
|---------|---------|
| id | UUID |
| usuario_id | UUID |
| carregador_id | UUID |
| inicio | TIMESTAMP |
| fim | TIMESTAMP |
| energia_kwh | FLOAT |
| custo | FLOAT |

---

## Tabela faturamento

| Campo | Tipo |
|---------|---------|
| id | UUID |
| usuario_id | UUID |
| mes | VARCHAR |
| valor_total | FLOAT |
| status_pagamento | VARCHAR |

---

## Relacionamentos

- Um usuário pode possuir várias sessões.
- Um carregador pode atender várias sessões.
- Cada faturamento pertence a um usuário.
