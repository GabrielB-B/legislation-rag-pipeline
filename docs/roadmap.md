# Roadmap

## Phase 1

Status: concluida

Objetivos cobertos:

- consulta oficial por URN
- resolucao de links via LexML
- extracao textual da Camara e do Senado
- limpeza e consolidacao do inteiro teor
- geracao do registro da norma
- JSON canonico
- chunks juridicos por artigo
- exportacao local em JSON e JSONL

## Phase 2

Status: em andamento

Objetivos planejados ou ja estruturados:

- persistencia relacional em PostgreSQL
- tabela da norma integral
- carga idempotente dos chunks
- embeddings locais com `sentence-transformers`
- armazenamento vetorial com `pgvector`
- busca semantica por similaridade
- indices de apoio para camada vetorial e relacional

## Phase 3

Status: proxima etapa

Melhorias recomendadas:

- testes de integracao com PostgreSQL
- fixture de exemplo para demonstracao automatizada
- GitHub Actions para `pytest`
- amostras pequenas de artefatos em `examples/`
- refinamento do README para estudo de caso mais forte
- possivel camada de servico ou API para consultas

## Notas de maturidade

Hoje o projeto ja esta suficientemente estruturado para portfolio e revisao tecnica.

O principal ponto ainda dependente de ambiente externo e a homologacao fim a fim da camada de banco vetorial, que exige PostgreSQL com `pgvector` disponivel.
