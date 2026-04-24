# Legislation RAG Pipeline

![Status](https://img.shields.io/badge/status-phase_2-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![Database](https://img.shields.io/badge/postgresql-pgvector-336791)
![CLI](https://img.shields.io/badge/interface-CLI-5A3FC0)
![Scope](https://img.shields.io/badge/focus-Brazilian%20legislation-0A7E8C)

Pipeline em Python para coleta, normalizacao, enriquecimento e preparo RAG de legislacao brasileira a partir de URNs oficiais. O projeto consulta fontes institucionais, consolida metadados, limpa o inteiro teor, gera JSON canonico, cria chunks juridicos e deixa a base pronta para persistencia relacional e busca semantica com PostgreSQL + pgvector.

Este repositorio representa a evolucao de um notebook exploratorio para uma estrutura de projeto profissional, com `src/`, CLI, testes, documentacao e separacao clara de responsabilidades.

## Portfolio Snapshot

- Coleta oficial por URN via API do Senado Federal.
- Resolucao de links oficiais com LexML.
- Extracao e limpeza de texto integral da Camara e do Senado.
- Consolidacao em registro auditavel e JSON canonico.
- Segmentacao juridica por artigos e hierarquia normativa.
- Persistencia local em `JSON` e `JSONL`.
- Camada pronta para PostgreSQL e `pgvector`.
- Busca semantica prevista na arquitetura da fase 2.

## Current Stage

O projeto esta atualmente em `fase 2`.

- `Fase 1`: concluida
  Coleta, limpeza textual, JSON canonico, chunking e exportacao local.
- `Fase 2`: em andamento
  Persistencia relacional/vetorial, embeddings locais e busca semantica.

Importante:
- o nucleo do pipeline roda sem Docker e sem banco
- PostgreSQL/pgvector sao componentes opcionais para a etapa vetorial
- a arquitetura dessa camada ja foi publicada, mas a validacao fim a fim depende de um banco disponivel no ambiente

## What This Project Demonstrates

- engenharia de dados juridicos
- web scraping orientado a fontes oficiais
- normalizacao e limpeza de texto legislativo
- modelagem de artefatos canonicos para auditoria
- chunking juridico para RAG
- organizacao de projeto Python para portfolio tecnico
- preparacao de arquitetura para busca vetorial local

## Project Structure

```text
.
|-- docs/
|   |-- architecture.md
|   |-- roadmap.md
|-- notebooks/
|   |-- README.md
|   |-- scrap_senado_original.ipynb
|-- src/legislation_rag_pipeline/
|   |-- cli.py
|   |-- collectors.py
|   |-- config.py
|   |-- canonical.py
|   |-- chunking.py
|   |-- pipeline.py
|   |-- utils.py
|   |-- vector_search.py
|   |-- storage/
|       |-- files.py
|       |-- postgres.py
|-- tests/
|   |-- test_chunking.py
|   |-- test_utils.py
|-- .env.example
|-- .gitignore
|-- docker-compose.yml
|-- pyproject.toml
|-- README.md
```

## Pipeline Flow

1. Receber uma `URN`.
2. Consultar a API de Dados Abertos do Senado.
3. Resolver fontes oficiais via LexML.
4. Extrair inteiro teor da Camara e do Senado.
5. Escolher uma fonte textual preferida.
6. Montar um registro consolidado da norma.
7. Gerar um JSON canonico auditavel.
8. Criar chunks juridicos por artigo.
9. Salvar artefatos locais.
10. Opcionalmente carregar no PostgreSQL, gerar embeddings e consultar semanticamente.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

## Quick Start

Coleta completa e geracao de artefatos locais:

```powershell
legislation-rag collect --urn "urn:lex:br:federal:lei:1990-12-11;8112" --output-dir artifacts
```

O comando acima gera:

- `artifacts/urn_lex_br_federal_lei_1990_12_11_8112_registro_norma.json`
- `artifacts/norma_canonica_8112.json`
- `artifacts/norma_chunks_8112.json`
- `artifacts/norma_chunks_8112.jsonl`

## Optional Database Layer

Docker nao e obrigatorio.

Use Docker apenas se quiser um ambiente rapido e reproduzivel para a fase vetorial:

```powershell
docker compose up -d
```

Variaveis suportadas:

- `PGHOST`
- `PGPORT`
- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD`

### PostgreSQL commands

Carga relacional dos chunks:

```powershell
legislation-rag load-postgres --chunks artifacts\norma_chunks_8112.json --canonical artifacts\norma_canonica_8112.json
```

Geracao de embeddings:

```powershell
legislation-rag embed --model-name "intfloat/multilingual-e5-small"
```

Busca semantica:

```powershell
legislation-rag search --query "Quais sao os requisitos para investidura em cargo publico?"
```

## Validation Performed

Validacoes feitas nesta versao publicada:

- `pytest -q`
- `legislation-rag --help`
- `legislation-rag collect --urn "urn:lex:br:federal:lei:1990-12-11;8112" --output-dir artifacts`

Observacao:
- a camada PostgreSQL/pgvector esta preparada no codigo e na CLI
- a integracao completa com banco depende de um ambiente com PostgreSQL disponivel

## Notebook Origin

O notebook original foi preservado em [notebooks/scrap_senado_original.ipynb](notebooks/scrap_senado_original.ipynb) como registro do processo exploratorio.

Ele continua util como trilha de raciocinio e historico de desenvolvimento, mas o ponto principal de execucao agora esta em `src/`.

## Refactoring Highlights

- remocao de dependencia de variaveis globais do notebook
- separacao entre coleta, transformacao, persistencia e camada vetorial
- criacao de CLI para repetibilidade
- testes basicos para utilitarios e chunking
- documentacao de arquitetura e roadmap
- preservacao do notebook original sem mantelo como codigo de producao

## Roadmap

Resumo curto:

- `Fase 1`: coleta oficial e artefatos locais
- `Fase 2`: banco relacional e vetorial
- `Fase 3`: hardening para demonstracao profissional, CI e exemplos reproduciveis

Detalhes em [docs/roadmap.md](docs/roadmap.md).

## Architecture

Visao de modulos e responsabilidades em [docs/architecture.md](docs/architecture.md).

## Repository Notes

Este repositorio foi organizado com foco em portfolio tecnico. A intencao principal e demonstrar:

- capacidade de transformar pesquisa em projeto estruturado
- preocupacao com auditabilidade de dados juridicos
- transicao de notebook para arquitetura reutilizavel
- preparo para integracao com RAG e busca vetorial local

