"""Pipeline em camadas (bronze -> silver -> gold) sobre SQLite.

    bronze  dados brutos do backup do app (idempotente por purchase_id)
    silver  limpeza, quarentena de linhas inválidas e casamento de produtos
    gold    tabelas analíticas (histórico de preço, comparação de mercados, índice da cesta)

Os modelos são arquivos SQL em sql/<camada>/NN_nome.sql, executados em ordem.
Os testes de qualidade são SQL em sql/tests/, cada um devolve as linhas que violam a regra.
"""
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .normalize import normalize_name, similar

RAIZ = Path(__file__).resolve().parents[2]
SQL_DIR = RAIZ / "sql"
ALIASES = RAIZ / "seeds" / "product_aliases.csv"

DDL_BRONZE = """
CREATE TABLE IF NOT EXISTS bronze_purchases (
    purchase_id TEXT PRIMARY KEY, store TEXT, purchased_at_ms INTEGER, list_name TEXT,
    total REAL, source_file TEXT, ingested_at TEXT);
CREATE TABLE IF NOT EXISTS bronze_items (
    purchase_id TEXT, line_no INTEGER, name TEXT, category TEXT, qty REAL, price REAL,
    vol REAL, recipe TEXT, mode TEXT, total REAL, PRIMARY KEY (purchase_id, line_no));
"""


def conectar(caminho):
    con = sqlite3.connect(caminho)
    con.row_factory = sqlite3.Row
    con.create_function("norm_name", 1, normalize_name, deterministic=True)
    con.executescript(DDL_BRONZE)
    return con


# ---------- bronze ----------
def ingerir(con, pasta):
    """Lê backups *.json do app. Reprocessar o mesmo arquivo não duplica nada."""
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    novos = 0
    for arq in sorted(Path(pasta).glob("*.json")):
        dados = json.loads(arq.read_text(encoding="utf-8"))
        if dados.get("app") != "cesta-certa":
            raise ValueError(f"{arq.name}: não é um backup do Cesta Certa")
        for p in dados.get("state", {}).get("purchases", []):
            existe = con.execute("SELECT 1 FROM bronze_purchases WHERE purchase_id=?", (p["id"],)).fetchone()
            novos += 0 if existe else 1
            con.execute("INSERT OR REPLACE INTO bronze_purchases VALUES (?,?,?,?,?,?,?)",
                        (p["id"], p.get("store"), p.get("date"), p.get("listName"), p.get("total"), arq.name, agora))
            con.execute("DELETE FROM bronze_items WHERE purchase_id=?", (p["id"],))
            for n, i in enumerate(p.get("items", []), 1):
                con.execute("INSERT INTO bronze_items VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (p["id"], n, i.get("name"), i.get("category"), i.get("qty"), i.get("price"),
                             i.get("vol"), i.get("recipe"), i.get("mode"), i.get("total")))
    con.commit()
    return novos


# ---------- silver: casamento de produtos ----------
def _carregar_aliases(caminho):
    """seeds/product_aliases.csv: curadoria manual para o que a similaridade automática não resolve."""
    if not caminho or not Path(caminho).exists():
        return {}
    with open(caminho, encoding="utf-8", newline="") as f:
        return {normalize_name(r["alias"]): normalize_name(r["canonical"]) for r in csv.DictReader(f)}


def construir_product_map(con, aliases=ALIASES):
    """Agrupa nomes em um product_id estável: 1) Jaccard >= 0.8 sobre o nome normalizado; 2) tabela de aliases."""
    contagem, exemplos = Counter(), {}
    for r in con.execute("SELECT name FROM bronze_items"):
        n = normalize_name(r["name"])
        if n:
            contagem[n] += 1
            exemplos.setdefault(n, Counter())[r["name"]] += 1
    canonicos, mapa = [], {}
    for nome, _ in contagem.most_common():
        alvo = next((c for c in canonicos if similar(nome, c)), None)
        if alvo is None:
            canonicos.append(nome)
            alvo = nome
        mapa[nome] = alvo
    for alias, canon in _carregar_aliases(aliases).items():
        if alias in mapa and canon in mapa:
            mapa[alias] = mapa[canon]
    con.execute("DROP TABLE IF EXISTS product_map")
    con.execute("CREATE TABLE product_map (name_norm TEXT PRIMARY KEY, product_id TEXT, product_name TEXT)")
    for nome, canon in mapa.items():
        pid = "P" + hashlib.sha1(canon.encode()).hexdigest()[:8]
        exib = exemplos[canon].most_common(1)[0][0].split(" — ")[0]
        con.execute("INSERT INTO product_map VALUES (?,?,?)", (nome, pid, exib))
    con.commit()
    return len(canonicos)


# ---------- modelos SQL ----------
def rodar_modelos(con, camadas=("silver", "gold")):
    executados = []
    for camada in camadas:
        for arq in sorted((SQL_DIR / camada).glob("*.sql")):
            con.executescript(arq.read_text(encoding="utf-8"))
            executados.append(f"{camada}/{arq.stem}")
    con.commit()
    return executados


# ---------- qualidade ----------
def rodar_testes(con):
    """Cada teste em sql/tests devolve as linhas violadoras; severidade vem do cabeçalho `-- severity:`."""
    con.execute("DROP TABLE IF EXISTS dq_results")
    con.execute("CREATE TABLE dq_results (test TEXT, severity TEXT, failed_rows INTEGER, status TEXT, description TEXT)")
    resultados = []
    for arq in sorted((SQL_DIR / "tests").glob("*.sql")):
        sql = arq.read_text(encoding="utf-8")
        sev = (re.search(r"--\s*severity:\s*(\w+)", sql) or [None, "error"])[1]
        desc = (re.search(r"--\s*description:\s*(.+)", sql) or [None, ""])[1].strip()
        falhas = len(con.execute(sql).fetchall())
        status = "ok" if falhas == 0 else ("FALHOU" if sev == "error" else "alerta")
        con.execute("INSERT INTO dq_results VALUES (?,?,?,?,?)", (arq.stem, sev, falhas, status, desc))
        resultados.append((arq.stem, sev, falhas, status))
    con.commit()
    return resultados


def executar(pasta_entrada, banco):
    """Pipeline completo. Retorna um resumo e os resultados dos testes."""
    con = conectar(banco)
    novas = ingerir(con, pasta_entrada)
    construir_product_map(con)
    modelos = rodar_modelos(con)
    testes = rodar_testes(con)
    resumo = {
        "compras_novas": novas,
        "compras_total": con.execute("SELECT COUNT(*) FROM bronze_purchases").fetchone()[0],
        "itens_validos": con.execute("SELECT COUNT(*) FROM stg_items").fetchone()[0],
        "itens_rejeitados": con.execute("SELECT COUNT(*) FROM silver_rejects").fetchone()[0],
        "produtos": con.execute("SELECT COUNT(DISTINCT product_id) FROM product_map").fetchone()[0],
        "modelos": modelos,
    }
    con.close()
    return resumo, testes
