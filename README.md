# 📊 Cesta Certa Analytics

Pipeline de dados (bronze → silver → gold) que transforma o histórico de compras do app **[Cesta Certa: Lista de Compras](https://github.com/leoneveslima/cesta-certa)** em respostas: *qual mercado é mais barato para a minha cesta? quanto os preços subiram para mim? onde gasto mais?*

> 🤖 **Construído com IA.** Este projeto foi desenvolvido por conversa com o Claude (Anthropic), via Claude Code. O código, os testes e a documentação foram escritos pela IA; o autor definiu o problema e as regras de negócio, revisou as decisões e validou os resultados. O contexto que guiou a IA está em [CLAUDE.md](CLAUDE.md).

Todos os dados deste repositório são **sintéticos** (gerados com semente fixa). Nada vem de compras reais de ninguém.

## Arquitetura

```
 backup do app (JSON)             SQLite (data/warehouse.db)                       saídas
┌──────────────────┐   ingest   ┌────────────────────────┐
│ backup-2025.json │ ─────────▶ │ BRONZE                 │
│ backup-2026.json │ idempotente│  bronze_purchases      │
└──────────────────┘ (por id)   │  bronze_items          │
                                └───────────┬────────────┘
                                            │ limpeza + casamento de produtos
                                ┌───────────▼────────────┐
                                │ SILVER                 │
                                │  silver_rejects (quarentena com motivo)
                                │  stg_items             │
                                │  product_map           │   ◀── seeds/product_aliases.csv
                                │  fct_price_history     │
                                └───────────┬────────────┘
                                            │
                                ┌───────────▼────────────┐   reports/gold/*.csv
                                │ GOLD                   │ ─▶ reports/resumo.md
                                │  mart_price_by_store   │
                                │  mart_store_comparison │
                                │  mart_price_index      │
                                │  mart_monthly_spend    │
                                └───────────┬────────────┘
                                            │
                                ┌───────────▼────────────┐
                                │ TESTES DE QUALIDADE    │  falha de severidade "error"
                                │  sql/tests/*.sql       │  → código de saída 1
                                └────────────────────────┘
```

Veja um exemplo de saída em [reports/resumo.md](reports/resumo.md).

## Como rodar

Requer Python 3.10+. O pipeline usa só a biblioteca padrão (SQLite); `pytest` é a única dependência, de desenvolvimento.

```bash
python -m venv .venv && .venv/Scripts/activate        # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"

python -m cestacerta generate     # cria backups sintéticos em data/raw/ (formato do app)
python -m cestacerta run          # ingere, transforma, testa e gera reports/
pytest                            # testes automatizados
```

Para usar seus próprios dados: no app, **Config → Backup**, salve o texto em um `.json` dentro de `data/real/` e rode `python -m cestacerta run --in data/real`. A pasta `data/real/` está no `.gitignore`.

## Decisões de projeto

| Decisão | Motivo |
|---|---|
| **Ingestão idempotente** (chave `purchase_id`) | Backups se sobrepõem. Reprocessar o mesmo arquivo não duplica nada (coberto por teste). |
| **Quarentena em vez de descarte** (`silver_rejects`) | Itens sem preço ou quantidade inválida saem da análise, mas ficam registrados com o motivo. |
| **Regras de negócio iguais às do app** | O preço pode ser por unidade, valor total (8 maçãs por R$ 24) ou por kg. O `unit_price` normaliza os três modos, e só se compara "por kg" com "por kg". |
| **Casamento de produtos em duas etapas** | 1) nome normalizado + similaridade de Jaccard ≥ 0,8 (mesma regra do app); 2) tabela de aliases curada à mão (`seeds/`) para o que a similaridade não resolve. |
| **Veredito só sobre itens em comum** | Comparar cestas com produtos diferentes distorce o resultado, então cada par de mercados usa apenas os produtos que ambos têm. |
| **Índice de preços com cesta fixa** | Produtos comprados em ≥ 6 meses, ponderados pela quantidade média, base 100 no 1º mês. |
| **Testes de qualidade em SQL** | Cada teste devolve as linhas que violam a regra e tem severidade (`error` quebra o pipeline, `warn` só alerta). |
| **SQLite + SQL puro** | Roda em qualquer máquina sem instalar nada. A estrutura em camadas e os modelos `.sql` foram pensados para migrar para DuckDB + dbt (ver abaixo). |

## Testes

`pytest` cobre: normalização de nomes, casamento de variações de grafia, quarentena de itens sem preço, alerta de total divergente, idempotência do reprocessamento, índice começando em 100 e o modo "valor total".

## Limitações conhecidas

- Os dados são sintéticos; o índice e as comparações mostram que o pipeline funciona, não a realidade de nenhum mercado.
- O casamento de produtos ainda depende de aliases manuais para descrições muito diferentes (ex.: "Pasta de dente" × "Creme dental").
- O preço comparado é o **último** observado em cada mercado, que pode estar desatualizado.
- Sem orquestrador nem painel: a execução é por linha de comando.

## Próximos passos

- [ ] **Ingestão de notas fiscais (NFC-e)** pelo QR Code, com extração e limpeza dos itens.
- [ ] Migrar para **DuckDB + dbt** (modelos, testes e documentação gerada). O dbt ainda não funciona com o Python 3.14 usado no desenvolvimento, e o DuckDB foi bloqueado por política de segurança do Windows da máquina de desenvolvimento.
- [ ] Orquestração (Airflow/Dagster) e execução agendada.
- [ ] Painel (Streamlit/Metabase) com o índice da cesta e a comparação de mercados.
- [ ] Casamento de produtos por código de barras (EAN) e embeddings de texto.

## Licença

MIT. Veja [LICENSE](LICENSE).
