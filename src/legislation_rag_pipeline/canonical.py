from __future__ import annotations

import re
from datetime import datetime, timezone

from .utils import (
    calculate_agreement_status,
    clean_text,
    extract_number_and_year_from_urn,
    extract_text_value,
    first_not_empty,
    split_non_empty_lines,
)


MONTHS_PTBR = {
    1: "JANEIRO",
    2: "FEVEREIRO",
    3: "MARCO",
    4: "ABRIL",
    5: "MAIO",
    6: "JUNHO",
    7: "JULHO",
    8: "AGOSTO",
    9: "SETEMBRO",
    10: "OUTUBRO",
    11: "NOVEMBRO",
    12: "DEZEMBRO",
}


def build_canonical_title(numero: str | None, data_assinatura: str | None) -> str | None:
    if not numero:
        return None
    if data_assinatura:
        match = re.match(r"(\d{2})/(\d{2})/(\d{4})", str(data_assinatura))
        if match:
            dia = int(match.group(1))
            mes = int(match.group(2))
            ano = match.group(3)
            nome_mes = MONTHS_PTBR.get(mes)
            if nome_mes:
                return f"LEI Nº {numero}, DE {dia} DE {nome_mes} DE {ano}"
    return f"LEI Nº {numero}"


def trim_norm_start(text: str, numero_norma: str | None = None) -> str:
    text = clean_text(text)
    if numero_norma:
        escaped = re.escape(str(numero_norma)).replace("\\.", r"\.")
        match = re.search(rf"LEI\s*N[º°o]\s*{escaped}\b", text)
        if match:
            return clean_text(text[match.start() :])

    for pattern in (
        r"O\s+PRESIDENTE\s+DA\s+REP[ÚU]BLICA",
        r"Art\.\s*1[º°]?",
    ):
        match = re.search(pattern, text)
        if match:
            return clean_text(text[match.start() :])
    return clean_text(text)


def trim_norm_end(text: str) -> str:
    text = clean_text(text)
    for pattern in (
        r"\nVoltar ao topo.*$",
        r"\nPágina atualizada em.*$",
        r"\nExibir outro ato.*$",
        r"\nImprimir.*$",
    ):
        text = re.sub(pattern, "", text, flags=re.DOTALL)
    return clean_text(text)


def reformat_legislative_text(text: str, numero_norma: str | None = None, ementa_norma: str | None = None) -> str:
    text = clean_text(text)
    text = re.sub(r"\s+", " ", text).strip()

    if numero_norma:
        escaped = re.escape(str(numero_norma)).replace("\\.", r"\.")
        text = re.sub(rf"(LEI\s*N[º°o]\s*{escaped}\b[^A-Z]{{0,120}}?\d{{4}})\s+", r"\1\n", text)

    if ementa_norma:
        escaped = re.escape(ementa_norma.strip())
        text = re.sub(rf"(\b\d{{4}})\s+({escaped})", r"\1\n\2", text)
        text = re.sub(rf"({escaped})\s+(O\s+PRESIDENTE\s+DA\s+REP[ÚU]BLICA)", r"\1\n\n\2", text)

    text = re.sub(r"\s*(O\s+PRESIDENTE\s+DA\s+REP[ÚU]BLICA)", r"\n\n\1", text)

    for pattern in (
        r"(TÍTULO\s+[IVXLCDM]+)",
        r"(CAPÍTULO\s+[IVXLCDM]+)",
        r"(Seção\s+[IVXLCDM]+)",
        r"(Subseção\s+[IVXLCDM]+)",
    ):
        text = re.sub(rf"\s*{pattern}", r"\n\n\1", text)

    text = re.sub(r"\s*(Art\.\s*\d+[A-Z\-]*[º°]?)", r"\n\1", text)
    text = re.sub(r"\s*(Parágrafo único\.)", r"\n\1", text)
    text = re.sub(r"\s*(§\s*\d+[º°]?)", r"\n\1", text)
    text = re.sub(r"\s*([IVXLCDM]+\s*-\s)", r"\n\1", text)
    text = re.sub(r"(TÍTULO\s+[IVXLCDM]+)\s+(CAPÍTULO\s+[IVXLCDM]+)", r"\1\n\2", text)
    text = re.sub(r"(CAPÍTULO\s+[IVXLCDM]+)\s+(Seção\s+[IVXLCDM]+)", r"\1\n\2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_norm_text(text: str, numero_norma: str | None = None, ementa_norma: str | None = None) -> str:
    text = clean_text(text)
    text = trim_norm_start(text, numero_norma=numero_norma)
    text = trim_norm_end(text)
    return reformat_legislative_text(text, numero_norma=numero_norma, ementa_norma=ementa_norma)


def enrich_text_with_canonical_header(text: str, title: str | None, ementa: str | None) -> str:
    text = clean_text(text)
    beginning = text[:1200].lower()
    parts = []
    if title and title.lower() not in beginning:
        parts.append(title)
    if ementa and ementa.strip() and ementa.lower() not in beginning:
        parts.append(ementa.strip())
    parts.append(text)
    return "\n".join(parts).strip()


def extract_title_and_ementa_from_text(text: str | None):
    lines = split_non_empty_lines(text)
    ignored = {
        "[Detalhes da Norma]",
        "Este texto não substitui o original publicado no Diário Oficial.",
    }
    lines = [line for line in lines if line not in ignored]

    title = None
    ementa = None
    for index, line in enumerate(lines):
        if re.match(r"^LEI\s+N[º°]?\s*", line, flags=re.IGNORECASE):
            title = line.strip()
            for next_line in lines[index + 1 : index + 6]:
                if not re.match(
                    r"^(O\s+PRESIDENTE\s+DA\s+REP[ÚU]BLICA|TÍTULO\s+[IVXLCDM]+|CAPÍTULO\s+[IVXLCDM]+|Art\.)",
                    next_line,
                    flags=re.IGNORECASE,
                ):
                    ementa = next_line.strip()
                    break
            break
    return title, ementa


def build_canonical_json(record: dict, target_urn: str, pipeline_version: str = "v1") -> dict:
    numero_urn, ano_urn = extract_number_and_year_from_urn(target_urn)

    senate_metadata = record.get("metadados_api_senado", {})
    official_links = record.get("links_oficiais", {})
    text_sources = record.get("fontes_texto", {})

    camara_text = extract_text_value(text_sources.get("camara"))
    senado_text = extract_text_value(text_sources.get("senado"))
    preferred_text = extract_text_value(record.get("texto_preferido"))
    preferred_source = record.get("fonte_preferida") or "camara"

    if not preferred_text:
        preferred_text = first_not_empty(
            camara_text if preferred_source == "camara" else senado_text,
            senado_text if preferred_source == "camara" else camara_text,
        )

    preferred_title, preferred_ementa = extract_title_and_ementa_from_text(preferred_text)
    camara_title, camara_ementa = extract_title_and_ementa_from_text(camara_text)
    senado_title, senado_ementa = extract_title_and_ementa_from_text(senado_text)

    title_api = first_not_empty(senate_metadata.get("titulo_norma"), senate_metadata.get("titulo"))
    ementa_api = first_not_empty(senate_metadata.get("ementa"))
    title_lexml = first_not_empty(record.get("titulo_lexml"))
    ementa_lexml = first_not_empty(record.get("ementa_lexml"))

    numero = first_not_empty(senate_metadata.get("numero"), record.get("numero"), numero_urn)
    ano = first_not_empty(senate_metadata.get("ano"), record.get("ano"), ano_urn)

    title_values = {
        "api_senado": title_api,
        "lexml": title_lexml,
        "texto_preferido": preferred_title,
        "camara_texto": camara_title,
        "senado_texto": senado_title,
    }
    ementa_values = {
        "api_senado": ementa_api,
        "lexml": ementa_lexml,
        "texto_preferido": preferred_ementa,
        "camara_texto": camara_ementa,
        "senado_texto": senado_ementa,
    }

    canonical_title = first_not_empty(title_api, title_lexml, preferred_title, camara_title, senado_title)
    canonical_ementa = first_not_empty(ementa_api, ementa_lexml, preferred_ementa, camara_ementa, senado_ementa)
    if not canonical_title and numero:
        canonical_title = f"LEI Nº {numero}"

    return {
        "urn": target_urn,
        "canonical": {
            "titulo_norma": canonical_title,
            "ementa": canonical_ementa,
            "numero": str(numero) if numero is not None else None,
            "ano": str(ano) if ano is not None else None,
        },
        "provenance": {
            "titulo_norma": {
                "chosen_from": (
                    "api_senado"
                    if title_api
                    else "lexml"
                    if title_lexml
                    else "texto_preferido"
                    if preferred_title
                    else "camara_texto"
                    if camara_title
                    else "senado_texto"
                ),
                "agreement_status": calculate_agreement_status(title_values),
                "values_by_source": title_values,
            },
            "ementa": {
                "chosen_from": (
                    "api_senado"
                    if ementa_api
                    else "lexml"
                    if ementa_lexml
                    else "texto_preferido"
                    if preferred_ementa
                    else "camara_texto"
                    if camara_ementa
                    else "senado_texto"
                ),
                "agreement_status": calculate_agreement_status(ementa_values),
                "values_by_source": ementa_values,
            },
        },
        "links_oficiais": official_links,
        "texto": {
            "fonte_preferida": preferred_source,
            "texto_para_embedding": preferred_text,
            "texto_camara": camara_text,
            "texto_senado": senado_text,
        },
        "pipeline": {
            "coletado_em": record.get("coletado_em") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "versao_pipeline": pipeline_version,
        },
    }

