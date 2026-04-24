from legislation_rag_pipeline.chunking import extract_article_identifier, split_into_articles


def test_extract_article_identifier_matches_real_article_header():
    assert extract_article_identifier("Art. 37 A investidura em cargo público...") == "37"


def test_extract_article_identifier_ignores_internal_reference():
    assert extract_article_identifier("Conforme o art. 37 da Constituição...") is None


def test_split_into_articles_preserves_order():
    text = "LEI Nº 8.112\nArt. 1º Texto do artigo 1.\nArt. 2º Texto do artigo 2."
    articles = split_into_articles(text, "urn:teste", "senado")
    assert [article["artigo"] for article in articles] == ["bloco_0", "1º", "2º"]
