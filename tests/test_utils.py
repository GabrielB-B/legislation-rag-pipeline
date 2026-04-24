from legislation_rag_pipeline.utils import (
    calculate_agreement_status,
    normalize_for_comparison,
    slugify_article,
    slugify_urn,
)


def test_slugify_urn():
    assert slugify_urn("urn:lex:br:federal:lei:1990-12-11;8112") == "urn_lex_br_federal_lei_1990_12_11_8112"


def test_slugify_article():
    assert slugify_article("5º-A") == "5_a"


def test_normalize_for_comparison_removes_accents_and_punctuation():
    assert normalize_for_comparison("Lei nº 8.112,") == "lei n 8112"


def test_calculate_agreement_status_normalized_equal():
    values = {
        "api": "Lei nº 8.112",
        "texto": "Lei n. 8112",
    }
    assert calculate_agreement_status(values) == "normalized_equal"
