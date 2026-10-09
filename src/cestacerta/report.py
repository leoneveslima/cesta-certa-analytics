"""Exporta as tabelas gold em CSV e gera um resumo em Markdown."""
import csv
from pathlib import Path

GOLD = ["mart_price_by_store", "mart_store_comparison", "mart_price_index", "mart_monthly_spend", "dq_results"]


def exportar_csv(con, pasta):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for tabela in GOLD:
        linhas = con.execute(f"SELECT * FROM {tabela}").fetchall()
        with open(pasta / f"{tabela}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(linhas[0].keys() if linhas else [])
            w.writerows([tuple(r) for r in linhas])


def _tabela(cabecalho, linhas):
    out = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    out += ["| " + " | ".join(str(c) for c in l) + " |" for l in linhas]
    return "\n".join(out)


def resumo_markdown(con, resumo, testes):
    idx = con.execute("SELECT purchase_month, price_index, products_in_basket FROM mart_price_index").fetchall()
    primeiro, ultimo = idx[0], idx[-1]
    comp = con.execute("""SELECT store_a, store_b, common_products, basket_a, basket_b, cheaper, diff_pct
                          FROM mart_store_comparison ORDER BY diff_pct DESC""").fetchall()
    alta = con.execute("""
        WITH p AS (SELECT product_id, MAX(product_name) nome, mode,
                          AVG(CASE WHEN purchase_month <= (SELECT MIN(purchase_month) FROM fct_price_history) THEN unit_price END) ini,
                          AVG(CASE WHEN purchase_month = (SELECT MAX(purchase_month) FROM fct_price_history) THEN unit_price END) fim
                   FROM fct_price_history GROUP BY product_id, mode)
        SELECT nome, ROUND(ini,2), ROUND(fim,2), ROUND(100.0*(fim-ini)/ini,1) FROM p
        WHERE ini IS NOT NULL AND fim IS NOT NULL ORDER BY 4 DESC LIMIT 5""").fetchall()
    gasto = con.execute("""SELECT category, ROUND(SUM(spend),2) FROM mart_monthly_spend
                           GROUP BY category ORDER BY 2 DESC LIMIT 5""").fetchall()
    md = [
        "# Resumo da última execução", "",
        f"- Compras processadas: **{resumo['compras_total']}** ({resumo['compras_novas']} novas nesta execução)",
        f"- Itens válidos: **{resumo['itens_validos']}** · em quarentena: **{resumo['itens_rejeitados']}**",
        f"- Produtos distintos após o casamento de nomes: **{resumo['produtos']}**", "",
        "## Índice de preços da cesta (base 100)", "",
        f"De **{primeiro[0]}** (100,0) até **{ultimo[0]}** (**{str(ultimo[1]).replace('.', ',')}**), cesta com {ultimo[2]} produtos.", "",
        "## Comparação entre mercados (itens em comum)", "",
        _tabela(["Mercado A", "Mercado B", "Em comum", "Cesta A", "Cesta B", "Mais barato", "Diferença %"], comp), "",
        "## Produtos que mais subiram (1º mês × último mês)", "",
        _tabela(["Produto", "Preço inicial", "Preço final", "Variação %"], alta), "",
        "## Maiores categorias de gasto", "",
        _tabela(["Categoria", "Gasto total (R$)"], gasto), "",
        "## Testes de qualidade", "",
        _tabela(["Teste", "Severidade", "Linhas com problema", "Status"], testes), "",
    ]
    return "\n".join(md)
