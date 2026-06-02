"""
ceasa_temporal.py — Motor de análise temporal do CEASA-BA (trimestre).

Lê dados/ceasa_historico/ceasa_trimestre.json (capturado do boletim oficial via
navegador, 13 semanas) e monta séries de preço por item ao longo do trimestre:
  - preço "mais comum" normalizado para R$/kg
  - tendência (variação % no trimestre, direção)
  - situação de mercado mais recente (firme/estável/fraco)

Reaproveitável: a cada rodada o boletim novo é anexado e a série cresce.
Ver references/captura_ceasa.md para como capturar novos boletins.
"""
from __future__ import annotations
import os
import json
import re
import statistics
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
# Dados mutáveis no PROJETO (gravável). COTACAO_DADOS = <projeto>/dados; fallback dev = dados/ local.
HIST = Path(os.environ.get("COTACAO_DADOS") or (SKILL_DIR / "dados")) / "ceasa_historico" / "ceasa_trimestre.json"

_SIT = {"FIR": "firme", "EST": "estável", "FRA": "fraco", "ENT": "entrando"}
_RE_KG = re.compile(r"(\d+(?:[.,]\d+)?)\s*KG", re.I)
_RE_GR = re.compile(r"(\d+(?:[.,]\d+)?)\s*GR?\b", re.I)


def _num(s):
    try:
        return float(str(s).replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        return None


def _peso_kg(label: str):
    """Peso em kg embutido no rótulo do CEASA (ex 'CX. 10 KG'->10, 'MOL. 800GR'->0.8,
    'KG MAMAO'->1, 'CX 25 / 27'->26)."""
    u = str(label).upper()
    if re.match(r"^\s*KG\b", u):          # unidade é o próprio quilo (preço já por kg)
        return 1.0
    m = _RE_KG.search(label)
    if m:
        return float(m.group(1).replace(",", "."))
    m = _RE_GR.search(label)
    if m:
        return float(m.group(1).replace(",", ".")) / 1000.0
    # caixa com faixa de peso sem 'KG' explícito, ex 'CX 25 / 27' -> média
    m = re.search(r"\b(?:CX|SC|SACO|CAIXA)\.?\s*(\d{1,3})\s*/\s*(\d{1,3})\b", u)
    if m:
        return (int(m.group(1)) + int(m.group(2))) / 2.0
    return None


def _produto(label: str) -> str:
    """Remove a unidade/embalagem do início do rótulo, devolve o nome do produto."""
    s = re.sub(r"^(CX|SC|SACO|CAIXA|MOL|FRD|FD)\.?\s*(C/)?\s*[\d.,/\s]*\s*(KG|GR|G)?\b", "", label, flags=re.I)
    s = re.sub(r"^(CENTO|UND|UNID|DUZIAS?|KG)\.?\s*", "", s, flags=re.I)
    s = re.sub(r"^(C/\s*\d+\s*(KG|GR|G)?)\b", "", s, flags=re.I)
    return re.sub(r"\s+", " ", s).strip()


def carregar_series(path: Path | None = None) -> dict:
    """Retorna {produto: {'unidade_base','serie':[(date,comum_kg)],'sit','tend_pct','dir',
       'atual','min','max'}}. Só itens com peso (R$/kg) entram."""
    path = path or HIST
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    # data: [{date, rows:[[label, comum, sit]]}] mais recente primeiro
    data = sorted(data, key=lambda b: b["date"])  # cronológico
    series = {}
    for bol in data:
        date = bol["date"]
        for label, comum, sit in bol["rows"]:
            peso = _peso_kg(label)
            comum_v = _num(comum)
            if peso is None or not peso or comum_v is None:
                continue
            prod = _produto(label)
            if not prod or len(prod) < 3:
                continue
            kg = round(comum_v / peso, 3)
            s = series.setdefault(prod, {"serie": [], "labels": set()})
            s["serie"].append((date, kg))
            s["labels"].add(label)
            s["sit"] = _SIT.get(sit, sit)
    # consolidar
    out = {}
    for prod, s in series.items():
        pts = sorted(s["serie"])
        if len(pts) < 2:
            continue
        vals = [v for _, v in pts]
        ini, fim = vals[0], vals[-1]
        tend = (fim / ini - 1) * 100 if ini else 0
        out[prod] = {
            "serie": pts,
            "atual": fim,
            "min": min(vals),
            "max": max(vals),
            "media": round(statistics.mean(vals), 2),
            "tend_pct": round(tend, 1),
            "dir": "alta" if tend > 5 else ("queda" if tend < -5 else "estável"),
            "sit": s.get("sit", ""),
            "n": len(pts),
        }
    return out


def carregar_ceasa_atual(path: Path | None = None) -> dict:
    """Boletim mais recente do trimestre -> {produto_norm: {comum_kg, comum_un, sit, label, data}}.
    Usado para plugar o CEASA na matriz de cotação."""
    data = json.loads(Path(path or HIST).read_text(encoding="utf-8"))
    data = sorted(data, key=lambda b: b["date"])
    if not data:
        return {}
    bol = data[-1]
    out = {}
    for label, comum, sit in bol["rows"]:
        comum_v = _num(comum)
        if comum_v is None:
            continue
        prod = _produto(label)
        if not prod or len(prod) < 3:
            continue
        peso = _peso_kg(label)
        comum_kg = round(comum_v / peso, 2) if peso else None
        comum_un = None
        lab = label.upper()
        # Usa a MEDIDA que o próprio boletim informa para achar o preço por unidade:
        #   'CENTO'->/100 ; 'N DUZIAS'->/(N*12) ; 'N UNID'->/N ; 'UND' avulsa->preço cheio.
        count = None
        m = re.search(r"(\d+)\s*DUZIAS?", lab)
        if m:
            count = int(m.group(1)) * 12
        elif "CENTO" in lab:
            count = 100
        else:
            m2 = re.search(r"(\d+)\s*UN(?:ID|D)?\b", lab)
            if m2:
                count = int(m2.group(1))
        if peso is None and count:
            comum_un = round(comum_v / count, 3)
        elif peso is None and re.search(r"\bUND\b", lab):
            comum_un = comum_v
        out[_norm_simple(prod)] = {"produto": prod, "comum_kg": comum_kg,
                                   "comum_un": comum_un, "sit": _SIT.get(sit, sit),
                                   "label": label, "data": bol["date"]}
    return out


def _norm_simple(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s).lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()


def datas_trimestre(path: Path | None = None) -> list:
    data = json.loads(Path(path or HIST).read_text(encoding="utf-8"))
    return sorted(b["date"] for b in data)


if __name__ == "__main__":
    s = carregar_series()
    print(f"Itens com série R$/kg: {len(s)}  | semanas: {len(datas_trimestre())}")
    # destaques: maiores altas e quedas no trimestre
    ranked = sorted(s.items(), key=lambda kv: kv[1]["tend_pct"])
    print("\nMAIORES QUEDAS no trimestre:")
    for p, d in ranked[:6]:
        print(f"  {p[:34]:34s} {d['tend_pct']:+6.1f}%  R$/kg {d['serie'][0][1]:.2f}->{d['atual']:.2f} [{d['sit']}] n={d['n']}")
    print("\nMAIORES ALTAS no trimestre:")
    for p, d in ranked[-6:]:
        print(f"  {p[:34]:34s} {d['tend_pct']:+6.1f}%  R$/kg {d['serie'][0][1]:.2f}->{d['atual']:.2f} [{d['sit']}] n={d['n']}")
