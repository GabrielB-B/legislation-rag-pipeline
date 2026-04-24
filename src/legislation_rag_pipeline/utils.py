from __future__ import annotations

from pathlib import Path
import re
import unicodedata

import requests


def build_session(user_agent: str | None = None) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": user_agent or "legislation-rag-pipeline/0.1 (+https://github.com/GabrielB-B)",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.7",
        }
    )
    return session


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\ufeff", " ")
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def find_all_fields(obj, target_key):
    results = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == target_key:
                results.append(value)
            results.extend(find_all_fields(value, target_key))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_all_fields(item, target_key))
    return results


def find_first_field(obj, target_key, default=None):
    found = find_all_fields(obj, target_key)
    return found[0] if found else default


def first_not_empty(*values):
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def normalize_for_comparison(value):
    if value is None:
        return None
    value = str(value).strip().lower()
    value = value.replace("n°", "n").replace("nº", "n").replace("no.", "n").replace("n.", "n")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\bn\s+o\b", "n", value)
    value = value.translate(str.maketrans("", "", ".,;:"))
    return value.strip(" .")


def filter_filled_values(data: dict) -> dict:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def calculate_agreement_status(values_by_source: dict) -> str:
    values = [value for value in values_by_source.values() if value not in (None, "")]
    if not values:
        return "missing_in_some_sources"

    normalized = [normalize_for_comparison(value) for value in values]
    if len(set(values)) == 1 and len(values) == len(values_by_source):
        return "all_equal"
    if len(set(normalized)) == 1:
        return "normalized_equal" if len(values) == len(values_by_source) else "missing_in_some_sources"
    if len(values) < len(values_by_source):
        return "missing_in_some_sources"
    return "conflict"


def slugify_urn(urn: str) -> str:
    slug = urn.lower()
    slug = unicodedata.normalize("NFKD", slug)
    slug = "".join(ch for ch in slug if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return re.sub(r"_+", "_", slug).strip("_")


def slugify_article(article: str | None) -> str | None:
    if not article:
        return None
    article = str(article).strip()
    article = unicodedata.normalize("NFKD", article)
    article = "".join(ch for ch in article if not unicodedata.combining(ch))
    article = article.replace("º", "").replace("°", "").replace("–", "-").lower()
    article = re.sub(r"(?<=\d)o(?=[\-_]|\b)", "", article)
    article = re.sub(r"[^0-9a-z\-]+", "_", article)
    article = re.sub(r"_+", "_", article).strip("_")
    return article.replace("-", "_")


def extract_number_and_year_from_urn(urn: str):
    match = re.search(r"lei:(\d{4})-\d{2}-\d{2};([^:]+)$", urn)
    if not match:
        return None, None
    return match.group(2), match.group(1)


def extract_text_value(source):
    if source is None:
        return None
    if isinstance(source, str):
        return source
    if isinstance(source, dict):
        for key in (
            "texto",
            "texto_preferido",
            "texto_para_embedding",
            "texto_limpo",
            "texto_final",
            "conteudo",
            "conteudo_limpo",
            "texto_integral",
        ):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def split_non_empty_lines(text: str | None) -> list[str]:
    if not text or not isinstance(text, str):
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]
