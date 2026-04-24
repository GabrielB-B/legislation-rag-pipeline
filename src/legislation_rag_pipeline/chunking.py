from __future__ import annotations

import re

from .utils import clean_text, slugify_article, slugify_urn, split_non_empty_lines


def split_into_articles(text: str, urn: str, source: str) -> list[dict]:
    if not text:
        return []
    parts = re.split(r"(?=Art\.\s*\d+[º°]?)", text)
    articles = []
    for index, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        match = re.match(r"Art\.\s*(\d+[º°]?)", part)
        article_id = match.group(1) if match else f"bloco_{index}"
        articles.append({"urn": urn, "fonte": source, "artigo": article_id, "texto": part})
    return articles


def generate_chunk_id(urn: str, article: str | None, chunk_order: int) -> str:
    base = slugify_urn(urn)
    if article:
        return f"{base}__art_{slugify_article(article)}__chunk_{chunk_order}"
    return f"{base}__chunk_{chunk_order}"


def build_contextualized_text(title, ementa, article, chunk_text):
    parts = []
    if title:
        parts.append(title)
    if ementa:
        parts.append(ementa)
    if article:
        parts.append(f"Art. {article}")
    parts.append(chunk_text)
    return " ".join(parts).strip()


def extract_article_identifier(line: str) -> str | None:
    match = re.match(r"^Art\.\s*([0-9]+(?:[-–][A-Z]+)?[º°]?)", line)
    if not match:
        return None
    article = match.group(1).replace("º", "").replace("°", "").replace("–", "-")
    return article


def generate_article_chunks(canonical_json: dict) -> list[dict]:
    urn = canonical_json["urn"]
    title = canonical_json["canonical"]["titulo_norma"]
    ementa = canonical_json["canonical"]["ementa"]
    numero = canonical_json["canonical"]["numero"]
    ano = canonical_json["canonical"]["ano"]
    source = canonical_json["texto"]["fonte_preferida"]
    source_url = canonical_json["links_oficiais"].get(source)
    collected_at = canonical_json["pipeline"]["coletado_em"]
    pipeline_version = canonical_json["pipeline"]["versao_pipeline"]
    text = canonical_json["texto"]["texto_para_embedding"]
    lines = split_non_empty_lines(text)

    chunks = []
    current_title = None
    current_chapter = None
    current_section = None
    current_subsection = None

    article_title = None
    article_chapter = None
    article_section = None
    article_subsection = None

    preamble = []
    article_number = None
    article_lines = []
    chunk_order = 0

    def save_article():
        nonlocal chunk_order, article_number, article_lines
        if not article_number or not article_lines:
            return

        chunk_order += 1
        chunk_text = clean_text(" ".join(article_lines))
        chunks.append(
            {
                "chunk_id": generate_chunk_id(urn, article_number, chunk_order),
                "urn": urn,
                "numero": numero,
                "ano": ano,
                "titulo_norma": title,
                "ementa": ementa,
                "fonte": source,
                "ordem_chunk": chunk_order,
                "tipo_bloco": "artigo",
                "artigo": article_number,
                "paragrafo": None,
                "inciso": None,
                "hierarquia_titulo": article_title,
                "hierarquia_capitulo": article_chapter,
                "hierarquia_secao": article_section,
                "hierarquia_subsecao": article_subsection,
                "texto_chunk": chunk_text,
                "texto_contextualizado": build_contextualized_text(title, ementa, article_number, chunk_text),
                "url_origem": source_url,
                "coletado_em": collected_at,
                "pipeline_version": pipeline_version,
            }
        )

    for line in lines:
        if re.match(r"^TÍTULO\s+[IVXLCDM]+", line):
            current_title = line
            current_chapter = None
            current_section = None
            current_subsection = None
            continue
        if re.match(r"^CAPÍTULO\s+[IVXLCDM]+", line):
            current_chapter = line
            current_section = None
            current_subsection = None
            continue
        if re.match(r"^Seção\s+[IVXLCDM]+", line):
            current_section = line
            current_subsection = None
            continue
        if re.match(r"^Subseção\s+[IVXLCDM]+", line):
            current_subsection = line
            continue

        detected_article = extract_article_identifier(line)
        if detected_article:
            if article_lines:
                save_article()
            article_number = detected_article
            article_lines = [line]
            article_title = current_title
            article_chapter = current_chapter
            article_section = current_section
            article_subsection = current_subsection
            continue

        if article_number is None:
            preamble.append(line)
        else:
            article_lines.append(line)

    if article_lines:
        save_article()

    if preamble:
        preamble_text = clean_text(" ".join(preamble))
        if preamble_text:
            chunks.insert(
                0,
                {
                    "chunk_id": generate_chunk_id(urn, None, 0),
                    "urn": urn,
                    "numero": numero,
                    "ano": ano,
                    "titulo_norma": title,
                    "ementa": ementa,
                    "fonte": source,
                    "ordem_chunk": 0,
                    "tipo_bloco": "cabecalho_preambulo",
                    "artigo": None,
                    "paragrafo": None,
                    "inciso": None,
                    "hierarquia_titulo": None,
                    "hierarquia_capitulo": None,
                    "hierarquia_secao": None,
                    "hierarquia_subsecao": None,
                    "texto_chunk": preamble_text,
                    "texto_contextualizado": build_contextualized_text(title, ementa, None, preamble_text),
                    "url_origem": source_url,
                    "coletado_em": collected_at,
                    "pipeline_version": pipeline_version,
                },
            )
    return chunks

