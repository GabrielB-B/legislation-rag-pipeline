# Architecture

## Visão geral

O projeto foi separado em quatro camadas principais:

1. `collectors.py`
Responsável por chamadas HTTP, resolução de URN, extração de metadados e captura do texto integral.

2. `canonical.py` e `chunking.py`
Responsáveis por limpeza textual, composição do JSON canônico e geração dos chunks jurídicos.

3. `storage/`
Responsável por persistência em arquivos e PostgreSQL.

4. `vector_search.py`
Responsável por embeddings locais e busca semântica sobre a base vetorial.

## Fluxo

1. Receber uma URN.
2. Consultar a API do Senado.
3. Resolver links oficiais com LexML.
4. Extrair texto da Câmara e do Senado.
5. Escolher a fonte preferida.
6. Gerar registro consolidado.
7. Produzir JSON canônico.
8. Gerar chunks jurídicos.
9. Salvar artefatos.
10. Opcionalmente persistir no PostgreSQL e materializar embeddings.

## Decisões importantes

- O notebook original foi mantido como artefato histórico, mas deixou de ser o ponto de entrada principal.
- O pipeline foi desenhado para rodar sem banco na fase inicial.
- A camada vetorial foi desacoplada da coleta para facilitar manutenção e reruns.
- A estrutura favorece auditoria: metadados, fonte escolhida e artefatos intermediários permanecem salvos.

