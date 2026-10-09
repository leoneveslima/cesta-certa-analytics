import json

import pytest

from cestacerta import generate, pipeline
from cestacerta.normalize import normalize_name, similar


@pytest.fixture(scope="module")
def dados(tmp_path_factory):
    base = tmp_path_factory.mktemp("cc")
    generate.gerar_arquivos(base / "raw", seed=7)
    resumo, testes = pipeline.executar(base / "raw", base / "wh.db")
    return base, resumo, testes


def test_normalize_igual_ao_app():
    assert normalize_name("Leite Condensado MOÇA® — 2 medidas") == "leite condensado moca"
    assert normalize_name("Maçãs 1kg") == "maca"
    assert normalize_name("Coca-Cola 269ml") == "coca cola"
    assert normalize_name("ARROZ BRANCO 5 KG") == normalize_name("Arroz branco")


def test_similar():
    assert similar("arroz branco", "arroz branco")
    assert not similar("leite integral", "leite condensado")


def test_pipeline_roda_sem_erros(dados):
    _, resumo, testes = dados
    assert resumo["itens_validos"] > 500
    assert not [t for t in testes if t[3] == "FALHOU"]


def test_quarentena_pega_itens_sem_preco(dados):
    base, resumo, _ = dados
    con = pipeline.conectar(base / "wh.db")
    motivos = {r[0] for r in con.execute("SELECT DISTINCT reason FROM silver_rejects")}
    assert motivos <= {"sem_preco", "nome_vazio", "quantidade_invalida"}
    assert resumo["itens_rejeitados"] > 0


def test_total_divergente_vira_alerta(dados):
    _, _, testes = dados
    t = {n: (st, f) for n, _, f, st in testes}
    assert t["06_purchase_total_matches"][0] == "alerta"


def test_casamento_agrupa_variacoes(dados):
    base, _, _ = dados
    con = pipeline.conectar(base / "wh.db")
    nomes_brutos = con.execute("SELECT COUNT(DISTINCT name) FROM bronze_items").fetchone()[0]
    produtos = con.execute("SELECT COUNT(DISTINCT product_id) FROM product_map").fetchone()[0]
    assert produtos < nomes_brutos                          # variações de grafia foram unificadas
    assert len(generate.PRODUTOS) <= produtos <= len(generate.PRODUTOS) + 2  # aliases curados resolvem o resto


def test_reprocessar_e_idempotente(dados):
    base, resumo, _ = dados
    r2, _ = pipeline.executar(base / "raw", base / "wh.db")
    assert r2["compras_novas"] == 0
    assert r2["compras_total"] == resumo["compras_total"]
    assert r2["itens_validos"] == resumo["itens_validos"]


def test_indice_comeca_em_100(dados):
    base, _, _ = dados
    con = pipeline.conectar(base / "wh.db")
    primeiro = con.execute("SELECT price_index FROM mart_price_index ORDER BY purchase_month LIMIT 1").fetchone()[0]
    ultimo = con.execute("SELECT price_index FROM mart_price_index ORDER BY purchase_month DESC LIMIT 1").fetchone()[0]
    assert primeiro == 100
    assert ultimo > 100  # a geração aplica inflação mensal


def test_modo_valor_total_divide_pela_quantidade(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    compra = {"id": "x1", "store": "A", "date": 1700000000000, "total": 24.0, "items": [
        {"name": "Maçã", "category": "Hortifrúti", "qty": 8, "price": 24, "vol": 0, "mode": "total", "total": 24}]}
    (raw / "b.json").write_text(json.dumps({"app": "cesta-certa", "v": 1, "state": {"purchases": [compra]}}))
    con = pipeline.conectar(tmp_path / "t.db")
    pipeline.ingerir(con, raw)
    pipeline.construir_product_map(con)
    pipeline.rodar_modelos(con, camadas=("silver",))
    assert con.execute("SELECT unit_price FROM stg_items").fetchone()[0] == 3.0


def test_arquivo_invalido_e_recusado(tmp_path):
    (tmp_path / "x.json").write_text(json.dumps({"app": "outro"}))
    con = pipeline.conectar(tmp_path / "t.db")
    with pytest.raises(ValueError):
        pipeline.ingerir(con, tmp_path)
