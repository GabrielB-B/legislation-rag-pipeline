# Legislation RAG Pipeline

Pipeline em Python para coletar normas por URN, consolidar metadados oficiais, limpar o inteiro teor, gerar JSON canônico, segmentar a norma em chunks jurídicos e preparar persistência relacional/vetorial em PostgreSQL com `pgvector`.

Este projeto nasceu a partir de um notebook exploratório e foi reorganizado para uma estrutura mais profissional, com código modular, CLI, documentação e testes básicos.

## O que o projeto faz

- Consulta a API de Dados Abertos do Senado Federal por URN.
- Resolve links oficiais via LexML.
- Extrai e limpa o inteiro teor da Câmara e do Senado.
- Define uma fonte textual preferida e gera um registro consolidado.
- Monta um JSON canônico auditável.
- Segmenta a norma em chunks jurídicos por artigo, com hierarquia estrutural.
- Salva artefatos em `JSON` e `JSONL`.
- Carrega chunks e norma integral em PostgreSQL.
- Gera embeddings locais com `sentence-transformers`.
- Executa busca semântica via `pgvector`.

## Estrutura

```text
.
|-- docs/
|   |-- architecture.md
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

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

## Configuração opcional do banco

Você pode subir um PostgreSQL com `pgvector` via Docker:

```powershell
docker compose up -d
```

Variáveis suportadas:

- `PGHOST`
- `PGPORT`
- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD`

## Uso rápido

Coleta completa e geração de artefatos locais:

```powershell
legislation-rag collect --urn "urn:lex:br:federal:lei:1990-12-11;8112" --output-dir artifacts
```

Carga relacional dos chunks:

```powershell
legislation-rag load-postgres --chunks artifacts\norma_chunks_8112.json --canonical artifacts\norma_canonica_8112.json
```

Geração de embeddings:

```powershell
legislation-rag embed --model "intfloat/multilingual-e5-small"
```

Busca semântica:

```powershell
legislation-rag search --query "Quais são os requisitos para investidura em cargo público?"
```

## Origem da refatoração

O notebook original foi preservado em [notebooks/scrap_senado_original.ipynb](notebooks/scrap_senado_original.ipynb) como registro do processo exploratório. A base de produção agora fica concentrada em `src/`, com responsabilidades separadas por módulo.

## Limpeza aplicada

- Remoção de dependência de variáveis globais do notebook.
- Separação entre coleta, transformação, persistência e consulta vetorial.
- Extração das configurações de banco e embeddings para camadas específicas.
- Preservação do notebook como referência, sem mantê-lo como ponto único de execução.
- Criação de uma CLI simples para repetibilidade.

## Próximos passos recomendados

- adicionar testes de integração para a camada PostgreSQL
- versionar exemplos reais de saída em `artifacts/examples/`
- configurar CI com `pytest`
- publicar um README orientado a portfólio no repositório definitivo do GitHub

