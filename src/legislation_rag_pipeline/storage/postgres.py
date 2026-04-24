from __future__ import annotations

from datetime import datetime, timezone

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.extras import Json, RealDictCursor, execute_batch, execute_values

from ..utils import extract_text_value, first_not_empty


def connect_postgres(config: dict):
    return psycopg2.connect(**config)


def connect_postgres_vector(config: dict):
    conn = connect_postgres(config)
    register_vector(conn)
    return conn


def test_postgres_connection(config: dict) -> dict:
    with connect_postgres(config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT current_database() AS banco_atual;")
            database = cur.fetchone()
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            extension = cur.fetchone()
    return {
        "banco_atual": database["banco_atual"],
        "pgvector_ativo": extension is not None,
    }


def create_chunks_table(config: dict) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS chunks_juridicos (
        id SERIAL PRIMARY KEY,
        chunk_id TEXT UNIQUE NOT NULL,
        urn TEXT NOT NULL,
        numero TEXT,
        ano TEXT,
        titulo_norma TEXT,
        ementa TEXT,
        fonte TEXT,
        tipo_bloco TEXT,
        artigo TEXT,
        paragrafo TEXT,
        inciso TEXT,
        hierarquia_titulo TEXT,
        hierarquia_capitulo TEXT,
        hierarquia_secao TEXT,
        hierarquia_subsecao TEXT,
        texto_chunk TEXT NOT NULL,
        texto_contextualizado TEXT,
        url_origem TEXT,
        coletado_em TEXT,
        pipeline_version TEXT,
        ordem_chunk INTEGER NOT NULL,
        metadata_json JSONB NOT NULL
    );
    """
    with connect_postgres(config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def transform_chunk_to_record(chunk: dict) -> dict:
    return {
        "chunk_id": chunk.get("chunk_id"),
        "urn": chunk.get("urn"),
        "numero": chunk.get("numero"),
        "ano": chunk.get("ano"),
        "titulo_norma": chunk.get("titulo_norma"),
        "ementa": chunk.get("ementa"),
        "fonte": chunk.get("fonte"),
        "tipo_bloco": chunk.get("tipo_bloco"),
        "artigo": chunk.get("artigo"),
        "paragrafo": chunk.get("paragrafo"),
        "inciso": chunk.get("inciso"),
        "hierarquia_titulo": chunk.get("hierarquia_titulo"),
        "hierarquia_capitulo": chunk.get("hierarquia_capitulo"),
        "hierarquia_secao": chunk.get("hierarquia_secao"),
        "hierarquia_subsecao": chunk.get("hierarquia_subsecao"),
        "texto_chunk": chunk.get("texto_chunk"),
        "texto_contextualizado": chunk.get("texto_contextualizado"),
        "url_origem": chunk.get("url_origem"),
        "coletado_em": chunk.get("coletado_em"),
        "pipeline_version": chunk.get("pipeline_version"),
        "ordem_chunk": chunk.get("ordem_chunk"),
        "metadata_json": Json(chunk),
    }


def load_chunks(config: dict, chunks: list[dict]) -> int:
    sql = """
    INSERT INTO chunks_juridicos (
        chunk_id, urn, numero, ano, titulo_norma, ementa, fonte, tipo_bloco, artigo,
        paragrafo, inciso, hierarquia_titulo, hierarquia_capitulo, hierarquia_secao,
        hierarquia_subsecao, texto_chunk, texto_contextualizado, url_origem,
        coletado_em, pipeline_version, ordem_chunk, metadata_json
    )
    VALUES %s
    ON CONFLICT (chunk_id)
    DO UPDATE SET
        urn = EXCLUDED.urn,
        numero = EXCLUDED.numero,
        ano = EXCLUDED.ano,
        titulo_norma = EXCLUDED.titulo_norma,
        ementa = EXCLUDED.ementa,
        fonte = EXCLUDED.fonte,
        tipo_bloco = EXCLUDED.tipo_bloco,
        artigo = EXCLUDED.artigo,
        paragrafo = EXCLUDED.paragrafo,
        inciso = EXCLUDED.inciso,
        hierarquia_titulo = EXCLUDED.hierarquia_titulo,
        hierarquia_capitulo = EXCLUDED.hierarquia_capitulo,
        hierarquia_secao = EXCLUDED.hierarquia_secao,
        hierarquia_subsecao = EXCLUDED.hierarquia_subsecao,
        texto_chunk = EXCLUDED.texto_chunk,
        texto_contextualizado = EXCLUDED.texto_contextualizado,
        url_origem = EXCLUDED.url_origem,
        coletado_em = EXCLUDED.coletado_em,
        pipeline_version = EXCLUDED.pipeline_version,
        ordem_chunk = EXCLUDED.ordem_chunk,
        metadata_json = EXCLUDED.metadata_json;
    """
    values = [
        (
            record["chunk_id"],
            record["urn"],
            record["numero"],
            record["ano"],
            record["titulo_norma"],
            record["ementa"],
            record["fonte"],
            record["tipo_bloco"],
            record["artigo"],
            record["paragrafo"],
            record["inciso"],
            record["hierarquia_titulo"],
            record["hierarquia_capitulo"],
            record["hierarquia_secao"],
            record["hierarquia_subsecao"],
            record["texto_chunk"],
            record["texto_contextualizado"],
            record["url_origem"],
            record["coletado_em"],
            record["pipeline_version"],
            record["ordem_chunk"],
            record["metadata_json"],
        )
        for record in map(transform_chunk_to_record, chunks)
    ]
    with connect_postgres(config) as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, values)
        conn.commit()
    return len(values)


def validate_chunk_load(config: dict) -> dict:
    with connect_postgres(config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS total FROM chunks_juridicos;")
            total = cur.fetchone()["total"]
            cur.execute(
                """
                SELECT chunk_id, tipo_bloco, artigo, ordem_chunk
                FROM chunks_juridicos
                ORDER BY ordem_chunk ASC
                LIMIT 1;
                """
            )
            first = cur.fetchone()
            cur.execute(
                """
                SELECT chunk_id, tipo_bloco, artigo, ordem_chunk
                FROM chunks_juridicos
                ORDER BY ordem_chunk DESC
                LIMIT 1;
                """
            )
            last = cur.fetchone()
    return {
        "total_registros": total,
        "primeiro_chunk": dict(first) if first else None,
        "ultimo_chunk": dict(last) if last else None,
    }


def add_vector_columns(config: dict, dimension: int) -> None:
    sql = f"""
    ALTER TABLE chunks_juridicos
        ADD COLUMN IF NOT EXISTS embedding vector({dimension}),
        ADD COLUMN IF NOT EXISTS embedding_modelo TEXT,
        ADD COLUMN IF NOT EXISTS embedding_campo_textual TEXT,
        ADD COLUMN IF NOT EXISTS embedding_normalizado BOOLEAN,
        ADD COLUMN IF NOT EXISTS embedding_atualizado_em TIMESTAMPTZ;
    """
    with connect_postgres_vector(config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def fetch_texts_for_embedding(config: dict) -> list[dict]:
    sql = """
    SELECT
        chunk_id,
        ordem_chunk,
        COALESCE(NULLIF(texto_contextualizado, ''), texto_chunk) AS texto_para_embedding
    FROM chunks_juridicos
    ORDER BY ordem_chunk ASC;
    """
    with connect_postgres_vector(config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()


def save_embeddings(config: dict, chunk_ids: list[str], embeddings, embedding_config: dict) -> int:
    sql = """
    UPDATE chunks_juridicos
    SET
        embedding = %s,
        embedding_modelo = %s,
        embedding_campo_textual = %s,
        embedding_normalizado = %s,
        embedding_atualizado_em = %s
    WHERE chunk_id = %s;
    """
    updated_at = datetime.now(timezone.utc)
    payload = [
        (
            embeddings[index],
            embedding_config["modelo_nome"],
            embedding_config["campo_textual_escolhido"],
            embedding_config["normalize_embeddings"],
            updated_at,
            chunk_ids[index],
        )
        for index in range(len(chunk_ids))
    ]
    with connect_postgres_vector(config) as conn:
        with conn.cursor() as cur:
            execute_batch(cur, sql, payload, page_size=100)
        conn.commit()
    return len(payload)


def validate_vector_fields(config: dict) -> dict:
    with connect_postgres_vector(config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total, COUNT(embedding) AS total_com_embedding
                FROM chunks_juridicos;
                """
            )
            summary = cur.fetchone()
            cur.execute(
                """
                SELECT chunk_id, embedding_modelo, embedding_campo_textual, embedding_normalizado
                FROM chunks_juridicos
                WHERE embedding IS NOT NULL
                ORDER BY ordem_chunk ASC
                LIMIT 1;
                """
            )
            sample = cur.fetchone()
    return {
        "total_registros": summary["total"],
        "total_com_embedding": summary["total_com_embedding"],
        "amostra": dict(sample) if sample else None,
    }


def rebuild_integral_text_from_chunks(chunks: list[dict]) -> str:
    ordered = sorted(chunks, key=lambda chunk: chunk.get("ordem_chunk", 0))
    parts = [(chunk.get("texto_chunk") or "").strip() for chunk in ordered]
    return "\n\n".join(part for part in parts if part).strip()


def build_full_norm_record(canonical_json: dict, chunks: list[dict]) -> dict:
    canonical = canonical_json.get("canonical", {})
    text_info = canonical_json.get("texto", {})
    first_chunk = chunks[0] if chunks else {}

    full_text = first_not_empty(
        text_info.get("texto_integral"),
        text_info.get("texto_para_embedding"),
        extract_text_value(text_info),
        rebuild_integral_text_from_chunks(chunks),
    )

    record = {
        "urn": first_not_empty(canonical_json.get("urn"), first_chunk.get("urn")),
        "titulo_norma": first_not_empty(canonical.get("titulo_norma"), first_chunk.get("titulo_norma")),
        "ementa": first_not_empty(canonical.get("ementa"), first_chunk.get("ementa")),
        "fonte_preferida": first_not_empty(text_info.get("fonte_preferida"), first_chunk.get("fonte")),
        "url_origem": canonical_json.get("links_oficiais", {}).get(text_info.get("fonte_preferida")),
        "texto_integral": full_text,
        "quantidade_caracteres": len(full_text or ""),
        "coletado_em": canonical_json.get("pipeline", {}).get("coletado_em"),
        "pipeline_version": canonical_json.get("pipeline", {}).get("versao_pipeline"),
        "json_canonico": Json(canonical_json),
    }
    return record


def create_full_norms_table(config: dict) -> None:
    sql = """
    CREATE TABLE IF NOT EXISTS normas_integras (
        id SERIAL PRIMARY KEY,
        urn TEXT UNIQUE NOT NULL,
        titulo_norma TEXT,
        ementa TEXT,
        fonte_preferida TEXT,
        url_origem TEXT,
        texto_integral TEXT NOT NULL,
        quantidade_caracteres INTEGER NOT NULL,
        coletado_em TEXT,
        pipeline_version TEXT,
        json_canonico JSONB NOT NULL
    );
    """
    with connect_postgres(config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def save_full_norm(config: dict, record: dict) -> None:
    sql = """
    INSERT INTO normas_integras (
        urn, titulo_norma, ementa, fonte_preferida, url_origem, texto_integral,
        quantidade_caracteres, coletado_em, pipeline_version, json_canonico
    )
    VALUES (
        %(urn)s, %(titulo_norma)s, %(ementa)s, %(fonte_preferida)s, %(url_origem)s, %(texto_integral)s,
        %(quantidade_caracteres)s, %(coletado_em)s, %(pipeline_version)s, %(json_canonico)s
    )
    ON CONFLICT (urn)
    DO UPDATE SET
        titulo_norma = EXCLUDED.titulo_norma,
        ementa = EXCLUDED.ementa,
        fonte_preferida = EXCLUDED.fonte_preferida,
        url_origem = EXCLUDED.url_origem,
        texto_integral = EXCLUDED.texto_integral,
        quantidade_caracteres = EXCLUDED.quantidade_caracteres,
        coletado_em = EXCLUDED.coletado_em,
        pipeline_version = EXCLUDED.pipeline_version,
        json_canonico = EXCLUDED.json_canonico;
    """
    with connect_postgres(config) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, record)
        conn.commit()


def validate_full_norm(config: dict, urn: str) -> dict:
    sql = """
    SELECT urn, titulo_norma, fonte_preferida, quantidade_caracteres,
           LEFT(texto_integral, 500) AS amostra_inicio_texto
    FROM normas_integras
    WHERE urn = %s;
    """
    with connect_postgres(config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (urn,))
            result = cur.fetchone()
    return dict(result) if result else {}


def search_semantic_chunks(config: dict, query_vector: list[float], top_k: int = 5) -> list[dict]:
    sql = """
    SELECT
        chunk_id,
        tipo_bloco,
        artigo,
        ordem_chunk,
        texto_chunk,
        embedding <=> %s::vector AS distancia
    FROM chunks_juridicos
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> %s::vector ASC
    LIMIT %s;
    """
    with connect_postgres_vector(config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (query_vector, query_vector, top_k))
            return [dict(row) for row in cur.fetchall()]


def create_indexes(config: dict) -> None:
    statements = [
        """
        CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
        ON chunks_juridicos
        USING hnsw (embedding vector_cosine_ops);
        """,
        "CREATE INDEX IF NOT EXISTS idx_chunks_artigo ON chunks_juridicos (artigo);",
        "CREATE INDEX IF NOT EXISTS idx_chunks_ordem_chunk ON chunks_juridicos (ordem_chunk);",
    ]
    with connect_postgres_vector(config) as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)
        conn.commit()


def list_table_indexes(config: dict, table_name: str) -> list[dict]:
    sql = """
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = %s
    ORDER BY indexname;
    """
    with connect_postgres(config) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (table_name,))
            return cur.fetchall()

