"""CLI:  python -m cestacerta generate | run"""
import argparse
import sys
from pathlib import Path

from . import generate, pipeline, report

RAIZ = pipeline.RAIZ


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cestacerta", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="gera backups sintéticos no formato do app")
    g.add_argument("--out", default=str(RAIZ / "data" / "raw"))
    g.add_argument("--seed", type=int, default=42)
    r = sub.add_parser("run", help="ingere, transforma, testa e gera o relatório")
    r.add_argument("--in", dest="entrada", default=str(RAIZ / "data" / "raw"))
    r.add_argument("--db", default=str(RAIZ / "data" / "warehouse.db"))
    r.add_argument("--reports", default=str(RAIZ / "reports"))
    a = ap.parse_args(argv)

    if a.cmd == "generate":
        for nome in generate.gerar_arquivos(a.out, seed=a.seed):
            print("gerado", Path(a.out) / nome)
        return 0

    resumo, testes = pipeline.executar(a.entrada, a.db)
    con = pipeline.conectar(a.db)
    report.exportar_csv(con, Path(a.reports) / "gold")
    (Path(a.reports) / "resumo.md").write_text(report.resumo_markdown(con, resumo, testes), encoding="utf-8")
    con.close()
    print(f"compras: {resumo['compras_total']} ({resumo['compras_novas']} novas) | itens válidos: "
          f"{resumo['itens_validos']} | em quarentena: {resumo['itens_rejeitados']} | produtos: {resumo['produtos']}")
    for nome, sev, falhas, status in testes:
        print(f"  [{status:>6}] {nome} ({sev}) linhas com problema: {falhas}")
    return 1 if any(t[3] == "FALHOU" for t in testes) else 0


if __name__ == "__main__":
    sys.exit(main())
