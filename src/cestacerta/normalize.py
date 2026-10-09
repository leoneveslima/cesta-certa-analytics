"""Normalização e casamento de nomes de produtos.

Port em Python do `normNome`/`similar` do app (index.html), para que o pipeline
chegue à mesma conclusão de "é o mesmo produto" que o app. Diferença intencional: aqui também se
descartam unidades soltas ("kg", "ml"), que aparecem quando o texto vem como "5 KG".
"""
import re
import unicodedata

_STOP = {"de", "da", "do", "das", "dos", "com", "sem", "e", "em", "para"}
_MEDIDA = re.compile(r"\d+(ml|l|g|kg|un)?|ml|l|g|kg|un")


def normalize_name(nome):
    """'Leite Condensado MOÇA® — 2 medidas' -> 'leite condensado moca'."""
    s = str(nome or "").split(" — ")[0].lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = s.replace("®", "").replace("™", "")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    tokens = [t for t in s.split() if t and t not in _STOP and not _MEDIDA.fullmatch(t)]
    tokens = [t[:-1] if len(t) > 3 and t.endswith("s") else t for t in tokens]
    return " ".join(tokens)


def similar(a, b, limiar=0.8):
    """Jaccard de tokens >= limiar (mesma regra do app)."""
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = set(a.split()), set(b.split())
    return len(ta & tb) / len(ta | tb) >= limiar
