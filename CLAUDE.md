# CLAUDE.md — Cesta Certa Analytics

Pipeline de dados (bronze/silver/gold, SQLite + SQL puro, Python stdlib) sobre o backup JSON do app Cesta Certa (repositório irmão `cesta-certa`). Projeto de portfólio de engenharia de dados, **construído com IA (Claude)** — manter essa declaração no README.

## Regra nº 1
Toda mudança de código, regra ou decisão atualiza o `README.md` (decisões, limitações, próximos passos) e este arquivo na mesma sessão.

## Mapa
- `src/cestacerta/`: `generate.py` (dados sintéticos, semente fixa), `pipeline.py` (ingestão, product_map, modelos, testes), `normalize.py` (port do `normNome`/`similar` do app), `report.py`, `__main__.py` (CLI).
- `sql/silver|gold/NN_nome.sql`: modelos executados em ordem. `sql/tests/*.sql`: devolvem as linhas violadoras; cabeçalho `-- severity: error|warn`.
- `seeds/product_aliases.csv`: aliases curados (alias → canônico).
- `reports/`: saída de exemplo (versionada, dados sintéticos). `data/raw`, `data/*.db`, `data/real`: nunca versionar.

## Comandos
`python -m cestacerta generate` · `python -m cestacerta run` · `pytest` (com `PYTHONPATH=src` ou `pip install -e ".[dev]"`).

## Regras de negócio herdadas do app
- Preço do item tem 3 modos: `un` (preço × qtd), `total` (preço já é o total: `unit_price = price/qty`), `kg` (preço por kg/L × `vol`/1000). Só comparar `un` com `un` e `kg` com `kg`.
- Comparação entre mercados: veredito só sobre produtos em comum.
- Itens sem preço (≤ 0) vão para `silver_rejects`, não são apagados.

## Ambiente
- Python 3.14 no Windows. **dbt-core não funciona no 3.14** (erro do mashumaro) e o **DuckDB foi bloqueado por política de Controle de Aplicativo do Windows**. Por isso o projeto usa SQLite. Não tente contornar a política; para migrar, usar outro ambiente (Python 3.12 + DuckDB/dbt).
- Pasta do projeto fica fora do OneDrive (`C:\Users\<usuario>\cesta-certa-analytics`).
- Scripts com acentos: escrever com a ferramenta Write. Não publicar nada externo (GitHub) sem confirmar com o usuário.
