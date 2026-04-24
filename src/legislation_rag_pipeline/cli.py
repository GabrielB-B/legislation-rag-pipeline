from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import EmbeddingConfig, PipelineConfig, PostgresConfig
from .pipeline import run_collection_pipeline
from .storage.postgres import (
    add_vector_columns,
    build_full_norm_record,
    create_chunks_table,
    create_full_norms_table,
    create_indexes,
    fetch_texts_for_embedding,
    list_table_indexes,
    load_chunks,
    save_embeddings,
    save_full_norm,
    search_semantic_chunks,
    test_postgres_connection,
    validate_chunk_load,
    validate_vector_fields,
)
from .vector_search import embed_query, embed_texts, load_embedding_model


def _read_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def command_collect(args) -> int:
    result = run_collection_pipeline(
        PipelineConfig(
            urn=args.urn,
            api_version=args.api_version,
            output_dir=args.output_dir,
            pipeline_version=args.pipeline_version,
        )
    )
    print(json.dumps(result["artifacts"], ensure_ascii=False, indent=2))
    return 0


def command_load_postgres(args) -> int:
    pg_config = PostgresConfig.from_env().as_dict()
    chunks = _read_json(args.chunks)
    canonical_json = _read_json(args.canonical) if args.canonical else None

    print(json.dumps(test_postgres_connection(pg_config), ensure_ascii=False, indent=2))
    create_chunks_table(pg_config)
    processed = load_chunks(pg_config, chunks)
    print(json.dumps({"registros_processados": processed}, ensure_ascii=False, indent=2))
    print(json.dumps(validate_chunk_load(pg_config), ensure_ascii=False, indent=2))

    if canonical_json:
        create_full_norms_table(pg_config)
        full_norm = build_full_norm_record(canonical_json, chunks)
        save_full_norm(pg_config, full_norm)
        print(json.dumps({"norma_integral_salva": full_norm["urn"]}, ensure_ascii=False, indent=2))

    return 0


def command_embed(args) -> int:
    pg_config = PostgresConfig.from_env().as_dict()
    embedding_config = EmbeddingConfig(model_name=args.model_name)
    records = fetch_texts_for_embedding(pg_config)
    texts = [record["texto_para_embedding"] for record in records]
    chunk_ids = [record["chunk_id"] for record in records]

    model = load_embedding_model(embedding_config.model_name)
    embeddings = embed_texts(model, texts, normalize_embeddings=embedding_config.normalize)
    dimension = len(embeddings[0]) if len(embeddings) else 0
    if not dimension:
        raise RuntimeError("Nenhum texto foi encontrado para geração de embeddings.")

    add_vector_columns(pg_config, dimension)
    processed = save_embeddings(
        pg_config,
        chunk_ids,
        embeddings,
        {
            "modelo_nome": embedding_config.model_name,
            "campo_textual_escolhido": embedding_config.text_field,
            "normalize_embeddings": embedding_config.normalize,
        },
    )
    create_indexes(pg_config)
    print(json.dumps({"embeddings_gravados": processed}, ensure_ascii=False, indent=2))
    print(json.dumps(validate_vector_fields(pg_config), ensure_ascii=False, indent=2))
    print(json.dumps([dict(item) for item in list_table_indexes(pg_config, "chunks_juridicos")], ensure_ascii=False, indent=2))
    return 0


def command_search(args) -> int:
    pg_config = PostgresConfig.from_env().as_dict()
    embedding_config = EmbeddingConfig(model_name=args.model_name)
    model = load_embedding_model(embedding_config.model_name)
    query_vector = embed_query(model, args.query, normalize_embeddings=embedding_config.normalize)
    results = search_semantic_chunks(pg_config, query_vector, top_k=args.top_k)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Legislation RAG pipeline CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="Coleta a norma, gera JSON canônico e chunks.")
    collect.add_argument("--urn", required=True)
    collect.add_argument("--api-version", type=int, default=3)
    collect.add_argument("--output-dir", default="artifacts")
    collect.add_argument("--pipeline-version", default="v1")
    collect.set_defaults(func=command_collect)

    load = subparsers.add_parser("load-postgres", help="Carrega chunks no PostgreSQL.")
    load.add_argument("--chunks", required=True, help="Caminho para o JSON de chunks.")
    load.add_argument("--canonical", help="Caminho para o JSON canônico.")
    load.set_defaults(func=command_load_postgres)

    embed = subparsers.add_parser("embed", help="Gera embeddings e grava na tabela de chunks.")
    embed.add_argument("--model-name", default="intfloat/multilingual-e5-small")
    embed.set_defaults(func=command_embed)

    search = subparsers.add_parser("search", help="Executa consulta semântica nos chunks vetoriais.")
    search.add_argument("--query", required=True)
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("--model-name", default="intfloat/multilingual-e5-small")
    search.set_defaults(func=command_search)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

