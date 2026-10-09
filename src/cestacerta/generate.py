"""Gerador de dados sintéticos no formato do backup do app Cesta Certa.

Não usa dados reais de ninguém. A semente fixa torna a saída reproduzível. Inclui sujeira
proposital (preço zero, nomes com variações, compra duplicada entre arquivos, total divergente)
para exercitar as regras de qualidade do pipeline.
"""
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

# (nome canônico, categoria, preço-base, modo, apelidos, volume em g/ml)
PRODUTOS = [
    ("Arroz Branco 5kg", "Grãos e Cereais", 28.9, "un", ["Arroz branco", "ARROZ BRANCO 5 KG"], 0),
    ("Feijão Carioca", "Grãos e Cereais", 8.4, "un", ["Feijao carioca", "Feijão Carioca 1kg"], 0),
    ("Macarrão Penne", "Grãos e Cereais", 5.9, "un", ["Macarrao Penne", "Macarrão penne 500g"], 0),
    ("Açúcar Refinado", "Grãos e Cereais", 4.6, "un", ["Acucar refinado", "Açúcar"], 0),
    ("Farinha de Trigo", "Grãos e Cereais", 5.2, "un", ["Farinha de trigo", "Farinha Trigo 1kg"], 0),
    ("Café Torrado", "Grãos e Cereais", 18.9, "un", ["Cafe torrado", "Café torrado 500g"], 0),
    ("Leite Integral", "Laticínios", 5.1, "un", ["Leite integral", "LEITE INTEGRAL 1L"], 0),
    ("Leite Condensado", "Laticínios", 7.5, "un", ["Leite Condensado MOÇA®", "Leite condensado"], 0),
    ("Manteiga", "Laticínios", 11.9, "un", ["Manteiga com sal", "manteiga"], 0),
    ("Queijo Mussarela", "Laticínios", 42.0, "kg", ["Queijo mussarela", "Mussarela fatiada"], 300),
    ("Ovos", "Laticínios", 14.5, "un", ["Ovos dúzia", "ovos"], 0),
    ("Iogurte Natural", "Laticínios", 3.9, "un", ["Iogurte natural", "Iogurtes naturais"], 0),
    ("Carne Moída", "Açougue", 36.0, "kg", ["Carne moida", "Carne moída 500g"], 500),
    ("Frango Inteiro", "Açougue", 12.9, "kg", ["Frango inteiro", "Frango"], 1800),
    ("Linguiça Toscana", "Açougue", 24.9, "kg", ["Linguica toscana", "Linguiça toscana"], 600),
    ("Peito de Frango", "Açougue", 19.9, "kg", ["Peito de frango", "Peito frango"], 1000),
    ("Coca-Cola", "Bebidas", 4.2, "un", ["Coca Cola", "Coca-Cola 269ml"], 269),
    ("Suco de Laranja", "Bebidas", 7.9, "un", ["Suco de laranja", "Suco laranja 1L"], 1000),
    ("Água Mineral", "Bebidas", 2.4, "un", ["Agua mineral", "Água mineral 1,5L"], 1500),
    ("Cerveja Pilsen", "Bebidas", 3.6, "un", ["Cerveja pilsen", "Cerveja Pilsen lata"], 350),
    ("Banana Prata", "Hortifrúti", 7.9, "kg", ["Banana prata", "Banana"], 1000),
    ("Maçã Gala", "Hortifrúti", 9.9, "kg", ["Maçã gala", "Maca gala"], 900),
    ("Tomate", "Hortifrúti", 7.5, "kg", ["Tomate", "Tomates"], 800),
    ("Cebola", "Hortifrúti", 5.9, "kg", ["Cebola", "Cebolas"], 1000),
    ("Batata", "Hortifrúti", 6.4, "kg", ["Batata inglesa", "Batatas"], 1500),
    ("Cenoura", "Hortifrúti", 5.5, "kg", ["Cenoura", "Cenouras"], 700),
    ("Alface", "Hortifrúti", 3.2, "un", ["Alface crespa", "alface"], 0),
    ("Limão", "Hortifrúti", 6.9, "kg", ["Limao", "Limão tahiti"], 500),
    ("Pão de Forma", "Padaria", 8.9, "un", ["Pao de forma", "Pão de forma tradicional"], 0),
    ("Pão Francês", "Padaria", 16.9, "kg", ["Pao frances", "Pão francês"], 500),
    ("Sabão em Pó", "Limpeza", 24.9, "un", ["Sabao em po", "Sabão em pó 1kg"], 0),
    ("Detergente", "Limpeza", 2.6, "un", ["Detergente líquido", "detergente"], 0),
    ("Água Sanitária", "Limpeza", 5.4, "un", ["Agua sanitaria", "Água sanitária 2L"], 0),
    ("Papel Higiênico", "Higiene", 19.9, "un", ["Papel higienico", "Papel higiênico 12 rolos"], 0),
    ("Shampoo", "Higiene", 14.9, "un", ["shampoo", "Shampoo 350ml"], 0),
    ("Creme Dental", "Higiene", 4.9, "un", ["Creme dental", "Pasta de dente"], 0),
    ("Atum em Lata", "Enlatados", 8.5, "un", ["Atum em lata", "Atum lata"], 0),
    ("Molho de Tomate", "Enlatados", 3.4, "un", ["Molho de tomate", "Molho tomate sachê"], 0),
    ("Milho Verde", "Enlatados", 4.1, "un", ["Milho verde", "Milho em lata"], 0),
    ("Biscoito Recheado", "Mercearia", 3.8, "un", ["Biscoito recheado", "Biscoitos recheados"], 0),
]

LOJAS = {  # nome: (fator de preço, peso de escolha)
    "Supermercados Guanabara": (1.00, 5),
    "Supermercados Mundial": (1.04, 3),
    "Assaí Atacadista": (0.93, 2),
}
INFLACAO_MENSAL = 0.006


def _ms(ano, mes, dia):
    return int(datetime(ano, mes, dia, 14, 0, tzinfo=timezone.utc).timestamp() * 1000)


def gerar_compras(seed=42, meses=18, ano_fim=2026, mes_fim=9):
    """Retorna a lista de compras no formato `state.purchases` do app."""
    rng = random.Random(seed)
    nomes, pesos = list(LOJAS), [LOJAS[n][1] for n in LOJAS]
    compras = []
    ano, mes = ano_fim, mes_fim
    meses_lista = []
    for _ in range(meses):
        meses_lista.append((ano, mes))
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    meses_lista.reverse()

    for m, (ano, mes) in enumerate(meses_lista):
        for _ in range(rng.randint(2, 4)):
            loja = rng.choices(nomes, pesos)[0]
            dia = rng.randint(1, 28)
            itens = []
            for nome, cat, base, modo, apelidos, vol in rng.sample(PRODUTOS, rng.randint(8, 15)):
                sazonal = 1 + 0.12 * math.sin(2 * math.pi * m / 12) if cat == "Hortifrúti" else 1
                preco = base * (1 + INFLACAO_MENSAL) ** m * LOJAS[loja][0] * sazonal * rng.uniform(0.96, 1.04)
                preco = round(preco, 2)
                qtd = 1 if modo == "kg" else rng.randint(1, 4)
                peso = int(vol * rng.uniform(0.7, 1.4)) if modo == "kg" else vol
                if rng.random() < 0.012:
                    preco = 0  # item sem preço informado
                total = round(preco * peso / 1000, 2) if modo == "kg" else round(preco * qtd, 2)
                itens.append({"name": rng.choice([nome] + apelidos), "category": cat, "qty": qtd,
                              "price": preco, "vol": peso, "recipe": "", "mode": modo, "total": total})
            compras.append({"id": f"p{ano}{mes:02d}{dia:02d}{len(compras):03d}", "store": loja,
                            "date": _ms(ano, mes, dia), "listName": "Compra do Mês",
                            "total": round(sum(i["total"] for i in itens), 2), "items": itens})
    compras[len(compras) // 2]["total"] += 25.0  # total divergente: deve virar alerta de qualidade
    return compras


def _backup(compras, exportado_em):
    return {"app": "cesta-certa", "v": 1, "exportedAt": exportado_em,
            "state": {"lists": [], "purchases": compras, "stores": list(LOJAS)}}


def gerar_arquivos(destino, seed=42, meses=18):
    """Grava dois backups com sobreposição (para testar reprocessamento idempotente)."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    compras = gerar_compras(seed, meses)
    corte = int(len(compras) * 0.65)
    partes = {"backup-2025.json": compras[:corte], "backup-2026.json": compras[corte - 5:]}
    for nome, parte in partes.items():
        (destino / nome).write_text(json.dumps(_backup(parte, "2026-10-01T12:00:00Z"), ensure_ascii=False),
                                    encoding="utf-8")
    return sorted(partes)
