from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urljoin
import json
import time

import requests
from bs4 import BeautifulSoup

from .canonical import build_canonical_title, clean_norm_text, enrich_text_with_canonical_header
from .utils import clean_text, find_all_fields


SENATE_URN_API_URL = "https://legis.senado.leg.br/dadosabertos/legislacao/urn.json"


def fetch_json(session: requests.Session, url: str, params: dict | None = None, timeout: int = 30):
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def fetch_html(session: requests.Session, url: str, params: dict | None = None, timeout: int = 30) -> str:
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def _first_filled_from_lists(*lists):
    for items in lists:
        if isinstance(items, list):
            for item in items:
                if item not in (None, "", [], {}):
                    return item
    return None


def fetch_senate_metadata_by_urn(
    urn: str,
    api_version: int,
    session: requests.Session,
    max_attempts: int = 5,
    timeout: int = 30,
) -> dict:
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fetch_json(
                session,
                SENATE_URN_API_URL,
                params={"urn": urn, "v": api_version},
                timeout=timeout,
            )
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(2 * attempt)
    raise RuntimeError(
        f"Falha ao consultar a API oficial do Senado após {max_attempts} tentativas. Último erro: {last_error}"
    )


def extract_senate_metadata(raw_api: dict, fallback_urn: str | None = None) -> dict:
    if not isinstance(raw_api, dict):
        raise TypeError("raw_api precisa ser um dict retornado pela API do Senado.")

    urn = _first_filled_from_lists(find_all_fields(raw_api, "urn"), find_all_fields(raw_api, "URN"))
    ementa = _first_filled_from_lists(
        find_all_fields(raw_api, "ementa"),
        find_all_fields(raw_api, "Ementa"),
        find_all_fields(raw_api, "descricaoIdentificacao"),
        find_all_fields(raw_api, "DescricaoIdentificacao"),
        find_all_fields(raw_api, "textoEmenta"),
        find_all_fields(raw_api, "TextoEmenta"),
    )
    numero = _first_filled_from_lists(find_all_fields(raw_api, "numero"), find_all_fields(raw_api, "Numero"))
    ano = _first_filled_from_lists(find_all_fields(raw_api, "ano"), find_all_fields(raw_api, "Ano"))
    data_assinatura = _first_filled_from_lists(
        find_all_fields(raw_api, "dataAssinatura"),
        find_all_fields(raw_api, "dataassinatura"),
        find_all_fields(raw_api, "DataAssinatura"),
        find_all_fields(raw_api, "data"),
        find_all_fields(raw_api, "Data"),
    )
    title = _first_filled_from_lists(
        find_all_fields(raw_api, "titulo"),
        find_all_fields(raw_api, "Titulo"),
        find_all_fields(raw_api, "tituloNorma"),
        find_all_fields(raw_api, "TituloNorma"),
    )
    document_url = _first_filled_from_lists(
        find_all_fields(raw_api, "urlDocumento"),
        find_all_fields(raw_api, "UrlDocumento"),
        find_all_fields(raw_api, "linkInteiroTeor"),
        find_all_fields(raw_api, "LinkInteiroTeor"),
        find_all_fields(raw_api, "href"),
    )

    publications = []
    for key in ("publicacao", "publicacoes", "Publicacao", "Publicacoes"):
        found = find_all_fields(raw_api, key)
        for item in found:
            if isinstance(item, list):
                publications.extend(item)
            elif isinstance(item, dict):
                publications.append(item)

    unique_publications = []
    seen = set()
    for publication in publications:
        marker = json.dumps(publication, ensure_ascii=False, sort_keys=True) if isinstance(publication, dict) else str(publication)
        if marker not in seen:
            seen.add(marker)
            unique_publications.append(publication)

    return {
        "urn": str(urn) if urn is not None else fallback_urn,
        "ementa": str(ementa) if ementa is not None else None,
        "numero": str(numero) if numero is not None else None,
        "ano": str(ano) if ano is not None else None,
        "dataassinatura": str(data_assinatura) if data_assinatura is not None else None,
        "titulo_norma": str(title) if title is not None else None,
        "publicacoes": unique_publications,
        "urlDocumento": str(document_url) if document_url is not None else None,
    }


def empty_official_links(urn: str, lexml_error: str | None = None) -> dict:
    return {
        "lexml": f"https://www.lexml.gov.br/urn/{urn}",
        "camara": None,
        "senado": None,
        "planalto": None,
        "candidatos": {
            "camara_publicacao": None,
            "camara_metadado": None,
            "senado_publicacao": None,
            "senado_metadado": None,
            "planalto": None,
            "senado_api": None,
        },
        "erro_lexml": lexml_error,
    }


def extract_official_links_lexml(
    urn: str,
    session: requests.Session,
    max_attempts: int = 3,
    timeout: int = 20,
) -> dict:
    url_lexml = f"https://www.lexml.gov.br/urn/{urn}"
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(url_lexml, timeout=timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            links = empty_official_links(urn)

            for item in soup.find_all(class_="list-group-item"):
                text = item.get_text(" ", strip=True).lower()
                link_tag = item.find("a", href=True)
                if not link_tag:
                    continue

                url = urljoin(url_lexml, link_tag["href"])
                if "presidência da república" in text or "presidencia da republica" in text or "planalto" in text or "planalto" in url:
                    links["candidatos"]["planalto"] = url
                    links["planalto"] = links["planalto"] or url
                elif "câmara dos deputados" in text or "camara dos deputados" in text:
                    key = "camara_publicacao" if "publicacaooriginal" in url else "camara_metadado"
                    links["candidatos"][key] = url
                    links["camara"] = links["camara"] or url
                elif "senado federal" in text:
                    key = "senado_publicacao" if "/publicacao/" in url else "senado_metadado"
                    links["candidatos"][key] = url
                    links["senado"] = links["senado"] or url

            if links["candidatos"]["camara_publicacao"]:
                links["camara"] = links["candidatos"]["camara_publicacao"]
            if links["candidatos"]["senado_publicacao"]:
                links["senado"] = links["candidatos"]["senado_publicacao"]
            return links
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < max_attempts:
                time.sleep(min(2 * attempt, 5))

    return empty_official_links(urn, lexml_error=str(last_error))


def _prepare_clean_text(raw_text: str, metadata: dict | None) -> tuple[str, str | None, str | None]:
    metadata = metadata or {}
    numero = metadata.get("numero")
    title = metadata.get("titulo_norma") or build_canonical_title(numero, metadata.get("dataassinatura"))
    ementa = metadata.get("ementa")
    body = clean_norm_text(raw_text, numero_norma=numero, ementa_norma=ementa)
    return enrich_text_with_canonical_header(body, title, ementa), title, ementa


def extract_camara_text(url: str, session: requests.Session, metadata: dict | None = None) -> dict:
    html = fetch_html(session, url)
    soup = BeautifulSoup(html, "html.parser")
    block = soup.find("div", class_="texto")

    if block is None:
        best_block = None
        best_text = ""
        for tag, attrs in (
            ("div", {"class": "textoNorma"}),
            ("div", {"class": "documentContent"}),
            ("div", {"id": "content"}),
        ):
            candidate = soup.find(tag, attrs=attrs)
            if candidate:
                candidate_text = clean_text(candidate.get_text(" ", strip=True))
                if len(candidate_text) > len(best_text):
                    best_block = candidate
                    best_text = candidate_text
        block = best_block

    if block is None:
        raise ValueError("Não foi possível localizar o corpo do texto na Câmara.")

    html_block = str(block)
    raw_text = clean_text(block.get_text(" ", strip=True))
    cleaned_text, _, _ = _prepare_clean_text(raw_text, metadata)
    body_text = clean_norm_text(raw_text, numero_norma=(metadata or {}).get("numero"), ementa_norma=(metadata or {}).get("ementa"))
    return {
        "fonte": "camara",
        "url": url,
        "html": html_block,
        "texto_bruto": raw_text,
        "texto_corpo_limpo": body_text,
        "texto": cleaned_text,
        "tamanho_texto_bruto": len(raw_text),
        "tamanho_texto_corpo_limpo": len(body_text),
        "tamanho_texto": len(cleaned_text),
    }


def extract_senado_text(url: str, session: requests.Session, metadata: dict | None = None) -> dict:
    html = fetch_html(session, url)
    soup = BeautifulSoup(html, "html.parser")

    best_block = None
    best_text = ""
    for tag, attrs in (
        ("div", {"id": "conteudoPrincipal"}),
        ("main", {}),
        ("article", {}),
    ):
        block = soup.find(tag, attrs=attrs)
        if block:
            text = clean_text(block.get_text(" ", strip=True))
            if len(text) > len(best_text):
                best_block = block
                best_text = text

    if best_block is None:
        raise ValueError("Não foi possível localizar o corpo do texto no Senado.")

    html_block = str(best_block)
    raw_text = clean_text(best_block.get_text(" ", strip=True))
    cleaned_text, _, _ = _prepare_clean_text(raw_text, metadata)
    body_text = clean_norm_text(raw_text, numero_norma=(metadata or {}).get("numero"), ementa_norma=(metadata or {}).get("ementa"))
    return {
        "fonte": "senado",
        "url": url,
        "html": html_block,
        "texto_bruto": raw_text,
        "texto_corpo_limpo": body_text,
        "texto": cleaned_text,
        "tamanho_texto_bruto": len(raw_text),
        "tamanho_texto_corpo_limpo": len(body_text),
        "tamanho_texto": len(cleaned_text),
    }


def collect_norm_record(urn: str, api_version: int, session: requests.Session) -> dict:
    raw_api = fetch_senate_metadata_by_urn(urn, api_version, session)
    metadata = extract_senate_metadata(raw_api, fallback_urn=urn)
    links = extract_official_links_lexml(urn, session)

    if not links.get("senado") and metadata.get("urlDocumento"):
        links["senado"] = metadata["urlDocumento"]
        links["candidatos"]["senado_api"] = metadata["urlDocumento"]

    record = {
        "urn": urn,
        "coletado_em": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metadados_api_senado": metadata,
        "links_oficiais": links,
        "fontes_texto": {},
        "texto_preferido": None,
        "fonte_preferida": None,
    }

    if links.get("camara"):
        try:
            record["fontes_texto"]["camara"] = extract_camara_text(links["camara"], session, metadata)
        except Exception as exc:  # pragma: no cover - external source instability
            record["fontes_texto"]["camara_erro"] = str(exc)

    if links.get("senado"):
        try:
            record["fontes_texto"]["senado"] = extract_senado_text(links["senado"], session, metadata)
        except Exception as exc:  # pragma: no cover - external source instability
            record["fontes_texto"]["senado_erro"] = str(exc)

    if "camara" in record["fontes_texto"]:
        record["texto_preferido"] = record["fontes_texto"]["camara"]["texto"]
        record["fonte_preferida"] = "camara"
    elif "senado" in record["fontes_texto"]:
        record["texto_preferido"] = record["fontes_texto"]["senado"]["texto"]
        record["fonte_preferida"] = "senado"

    return record

