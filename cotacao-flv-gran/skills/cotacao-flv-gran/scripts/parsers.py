"""
parsers.py — Adaptadores de parsing por fornecedor.

Cada parser recebe o caminho do arquivo da tabela e devolve uma lista de registros:
    {"desc": <descrição do item como o fornecedor escreve>,
     "unidade": <string de unidade/embalagem>,
     "preco": <float em R$ na unidade indicada>}

Regra de ouro (ver references/regras_negocio.md): preço 0,00 / vazio = NÃO COTADO.
parse_preco() já devolve None nesses casos, e o registro é descartado.

Formatos cobertos (digitais — viram script):
  - D'onofrio  : texto WhatsApp / RTF  (categorias + "Item R$: X,XX UNID")
  - Shimizu    : PDF  (Nome | Preço CX | Preço KG/UND)
  - Doce Mel   : PDF  (Cod | Descrição | UN | Preço KG | Preço CX)

RML chega como IMAGEM -> não tem parser de script. O Claude lê a imagem (visão)
seguindo references/parsing_imagem_rml.md e grava um CSV (desc,unidade,preco) que
o motor consome igual aos demais. Ver carregar_csv_fornecedor().
"""
from __future__ import annotations
import csv
import re
from pathlib import Path

from flv_lib import parse_preco

_RE_DATA = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})")


# --------------------------------------------------------------------------- #
# D'onofrio — texto / RTF
# --------------------------------------------------------------------------- #
def parse_donofrio(path: str | Path) -> dict:
    raw = Path(path).read_text(errors="ignore")
    if raw.lstrip().startswith("{\\rtf"):
        from striprtf.striprtf import rtf_to_text
        raw = rtf_to_text(raw)
    itens, validade = [], None
    # linha de item: "Descrição R$: 3,67 KG"
    re_item = re.compile(r"^(.*?)\s*R\$:\s*([\d.,]+)\s*([A-Za-zçÇ]+)\s*$")
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "tabela de preço" in line.lower():
            m = _RE_DATA.search(line)
            if m:
                validade = m.group(0)
            continue
        m = re_item.match(line)
        if not m:
            continue  # cabeçalho de categoria (Frutas, Legumes...) ou ruído
        desc, preco_txt, unid = m.group(1).strip(), m.group(2), m.group(3).upper()
        preco = parse_preco(preco_txt)
        if preco is None:
            continue
        itens.append({"desc": desc, "unidade": unid, "preco": preco})
    return {"fornecedor": "DONOFRIO", "validade": validade, "itens": itens}


# --------------------------------------------------------------------------- #
# Shimizu — PDF (Nome | Preço CX | Preço KG/UND)
# --------------------------------------------------------------------------- #
def parse_shimizu(path: str | Path) -> dict:
    import pdfplumber
    itens, validade = [], None
    re_preco = re.compile(r"R\$\s*([\d.,]+)")
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").splitlines():
                line = line.strip()
                if not line:
                    continue
                if "ATÉ" in line.upper() and _RE_DATA.search(line):
                    validade = validade or line
                precos = re_preco.findall(line)
                if not precos:
                    continue
                nome = line[: line.find("R$")].strip()
                if not nome:
                    continue
                # A última coluna do Shimizu é SEMPRE "Preço KG OU UND" -> preço já é
                # por kg/un. A embalagem no nome (CX 20KG) NÃO é divisor de preço.
                preco_kg_und = parse_preco(precos[-1])
                if preco_kg_und is None:
                    continue
                itens.append({"desc": nome, "unidade": "KG/UND", "preco": preco_kg_und})
    return {"fornecedor": "SHIMIZU", "validade": validade, "itens": itens}


# --------------------------------------------------------------------------- #
# Doce Mel — PDF (Cod Descricao UN PrecoKG PrecoCX)
# --------------------------------------------------------------------------- #
def parse_docemel(path: str | Path) -> dict:
    import pdfplumber
    itens, validade = [], None
    # cód desc ... UN precoKG precoCX  (2 números no fim; UN é token de unidade antes deles)
    re_linha = re.compile(
        r"^(\d{3}\.\d{3})\s+(.*?)\s+([A-Z]{2,3})\s+([\d.,]+)\s+([\d.,]+)\s*$"
    )
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").splitlines():
                line = line.strip()
                if "SEMANA" in line.upper() and not validade:
                    validade = line
                m = re_linha.match(line)
                if not m:
                    continue
                cod, desc, un, preco_kg, _preco_cx = m.groups()
                preco = parse_preco(preco_kg)  # preço por KG (coluna Preco KG)
                if preco is None:
                    continue
                itens.append({"desc": desc.strip(), "unidade": "KG", "preco": preco,
                              "cod_fornecedor": cod})
    return {"fornecedor": "DOCE MEL", "validade": validade, "itens": itens}


# --------------------------------------------------------------------------- #
# Genérico — CSV (usado pelo RML via visão e por fornecedores novos)
# --------------------------------------------------------------------------- #
def carregar_csv_fornecedor(path: str | Path, fornecedor: str) -> dict:
    """Lê CSV com colunas: desc, unidade, preco. Para RML e fornecedores novos."""
    itens = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            preco = parse_preco(row.get("preco"))
            if preco is None:
                continue
            itens.append({"desc": (row.get("desc") or "").strip(),
                          "unidade": (row.get("unidade") or "").strip().upper(),
                          "preco": preco})
    return {"fornecedor": fornecedor, "validade": None, "itens": itens}


_RE_UNID_NOME = re.compile(
    r"\b(CX\s*\d*\s*x?\s*\d*\s*KG|SACO?\s*\d+\s*KG|SC\s*\d+\s*KG|CX\s*\d+\s*UND?|"
    r"\d+\s*X\s*\d+\s*G|\d+\s*G|CENTO|MOL|BDJ|UND?|KG)\b", re.I)


def _extrai_unidade_do_nome(nome: str) -> str | None:
    m = _RE_UNID_NOME.search(nome)
    return m.group(0).upper() if m else None


# --------------------------------------------------------------------------- #
# Boa Citrus — texto WhatsApp / RTF (cítricos + abacate; preço POR CAIXA)
# --------------------------------------------------------------------------- #
# A vendedora manda os preços no corpo da mensagem, uma linha por item:
#   "• Laranja graúda — caixa com 24kg: R$ 30,00 (saindo aproximadamente R$ 1,25/kg)"
# Devolvemos o preço da CAIXA + unidade "CX NNKG"; o motor (normalizar_preco)
# divide pelo peso e chega no R$/kg. NÃO usamos o "/kg aproximado" do texto
# (é arredondado) — preço/peso é exato. Linhas de saudação/assinatura não casam.
def parse_boacitrus(path: str | Path) -> dict:
    raw = Path(path).read_text(errors="ignore")
    if raw.lstrip().startswith("{\\rtf"):
        from striprtf.striprtf import rtf_to_text
        raw = rtf_to_text(raw)
    itens, validade = [], None
    re_item = re.compile(
        r"^[••\-\*\s]*(.+?)\s*[—–—–\-]\s*caixa\s+com\s+(\d+)\s*kg\s*:"
        r"\s*R\$\s*([\d.,]+)", re.I)
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "tabela de preço" in line.lower() or "tabela atualizada" in line.lower():
            m = _RE_DATA.search(line)
            if m:
                validade = m.group(0)
            continue
        m = re_item.match(line)
        if not m:
            continue  # saudação, assinatura, texto solto
        nome, peso, preco_txt = m.group(1).strip(), m.group(2), m.group(3)
        preco = parse_preco(preco_txt)
        if preco is None:
            continue
        itens.append({"desc": nome, "unidade": f"CX {peso}KG", "preco": preco})
    return {"fornecedor": "BOA CITRUS", "validade": validade, "itens": itens}


# --------------------------------------------------------------------------- #
# Hortimix — PDF "Tabela Restaurante" (grade densa de 2 colunas)
# --------------------------------------------------------------------------- #
# extract_tables() devolve linhas com até 2 blocos [NOME, UNID, R$ PRECO]. O
# offset das colunas MUDA entre as páginas (pág.1 tem coluna separadora, pág.2
# não), então ancoramos na CÉLULA DE PREÇO e lemos unidade/nome à esquerda dela,
# pulando células vazias e o marcador "R$" isolado (às vezes o número vem na
# célula seguinte). FALTA / "R$ -" / vazio => parse_preco None => não cotado.
# A seção "POLPAS 1KG" (polpa de fruta congelada) é prefixada com "POLPA " para
# não casar com a fruta fresca de mesmo nome.
_HM_NUM = re.compile(r"[\d.,]*\d")
_HM_PRICEISH = re.compile(r"(?i)r\$|^\s*-?\s*[\d.,]+\s*$")


def _hm_preco_cel(cel) -> float | None:
    if cel is None:
        return None
    m = _HM_NUM.search(str(cel))      # ignora traço solto em "R$ - 98,00"
    return parse_preco(m.group(0)) if m else None


def _hm_vizinhos_esq(cells: list, j: int) -> tuple[str, str]:
    """Da célula de preço em j, anda à esquerda pulando '' e 'R$'. -> (nome, unidade)."""
    vals = []
    i = j - 1
    while i >= 0 and len(vals) < 2:
        c = str(cells[i]).strip()
        if c and c.upper() != "R$":
            vals.append(c)
        i -= 1
    unid = vals[0] if len(vals) >= 1 else ""
    nome = vals[1] if len(vals) >= 2 else ""
    return nome, unid


def parse_hortimix(path: str | Path) -> dict:
    import pdfplumber
    itens, validade = [], None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if not validade:
                for ln in txt.splitlines():
                    if "VALIDA" in ln.upper():
                        validade = ln.strip()
                        break
            for tbl in page.extract_tables():
                polpa_mode = False
                for row in tbl:
                    cells = [(c if c is not None else "") for c in row]
                    header_polpa = any("POLPAS" in str(c).upper() for c in cells)
                    for j in range(1, len(cells)):
                        cs = str(cells[j]).strip()
                        if cs.upper() == "R$":
                            continue  # marcador isolado; número vem na próxima célula
                        if not cs or not _HM_PRICEISH.search(cs):
                            continue
                        preco = _hm_preco_cel(cs)
                        if preco is None:
                            continue  # FALTA / "R$ -" / vazio = não cotado
                        nome, unid = _hm_vizinhos_esq(cells, j)
                        if not nome:
                            continue
                        nidx = cells.index(nome) if nome in cells else 0
                        if polpa_mode and nidx >= 3 and not nome.upper().startswith("POLPA"):
                            nome = "POLPA " + nome  # polpa congelada != fruta fresca
                        itens.append({"desc": nome, "unidade": unid, "preco": preco})
                    if header_polpa:
                        polpa_mode = True
    return {"fornecedor": "HORTIMIX", "validade": validade, "itens": itens}


# --------------------------------------------------------------------------- #
# Igarashi — texto WhatsApp / RTF (canal ENTREGA; preço POR CAIXA/SACA)
# --------------------------------------------------------------------------- #
# A Igarashi manda "Nome do item - preço", e o preço é por CAIXA/SACA (não por kg).
# Ela NÃO escreve o peso da embalagem (exceto a linha "MI 070", que traz "12,5"
# inline). Antes (≤27/05/2026) o peso vivia aqui em _ig_peso_familia hardcoded
# (alho 10 · batata 25 · cebola/cenoura 20 · repolho 19 · tomate 21 · maçã 18).
#
# A partir de 28/05/2026 (decisão Hugo): o peso é puxado da BASE MESTRE
# embalagens.json (commodity → kg padrão CEASA-BA Salvador). Cada família do
# Igarashi aponta pra um slug de commodity; o peso vem da base, não hardcoded.
# Vantagens: 1) fonte única — quando Hugo pesar no recebimento, basta atualizar a
# base e todos os parsers vêem; 2) calibração automática quando ≥2 pesagens
# divergem >10% do default. Override por peso INLINE na linha (MI-070 "12,5")
# continua mandando — fornecedor sempre vence base.
#
# Devolvemos o preço da CAIXA + unidade "CX/SC/SACO NNKG"; o motor (normalizar_preco)
# divide pelo peso -> R$/kg. Os atributos CAT/calibre/variedade entram no desc canônico
# (ex.: "MACA GALA CAT1 CAL120") para casar com o CARDÁPIO DEFAULT e aparecer no Mapa.
# Maçã é cherry-pick por calibre: só o calibre/categoria do default casa com o COD;
# os outros calibres ficam em nao_casados pra Hugo decidir (não deixar CAT3 barata vencer).
from flv_lib import norm_texto as _norm, peso_caixa_por_commodity as _peso_commodity

# preço pt-BR com 2 casas decimais. A linha "MI 070" traz "12,5" (PESO, 1 casa) -> não casa aqui.
_IG_PRECO = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")
# peso inline na própria linha (só a MI-070 tem: "12,5")
_IG_PESO_INLINE = re.compile(r"(?<![,\d])(\d{1,2}[.,]\d)(?![\d])")
# inteiro de 2-3 dígitos isolado (calibre da maçã: 070,080,...,250) — exclui o que faz parte de decimal
_IG_INT = re.compile(r"(?<![,\d])(\d{2,3})(?![,\d])")

# Família Igarashi -> (slug em embalagens.json, rótulo embalagem, peso fallback, override)
#  - slug: commodity na base CEASA-BA. None = sem mapeamento confiável (usa só fallback).
#  - override=True: peso ESPECÍFICO da Igarashi diverge da praça CEASA — não consulta a base
#    (calibração entra via registrar_pesagem com a Igarashi como fornecedor).
# Pesos fallback (Hugo 25/05/2026 + reverse-check com cardápio default + CEASA-BA 22/05):
#   alho 10 (nacional) · batata 25 (Igarashi entrega SC menor que CEASA 50) · cebola/cenoura 20
#   · repolho 19 · tomate 21 · maçã 18
_IG_FAMILIAS = [
    ("alho",    "alho_importado",                       "CX",   10.0, True),   # base cota importado; Hugo compra nacional
    ("batata",  "batata_batatinha",                     "SC",   25.0, True),   # Igarashi entrega 25kg, CEASA cota 50kg
    ("cebola",  "cebola",                               "SACO", 20.0, False),
    ("cenoura", "cenoura",                              "SACO", 20.0, False),
    ("repolho", "repolho",                              "CX",   19.0, False),
    ("tomate",  "tomate_extra_primeira_salada_italiano","CX",   21.0, False),
]


def _ig_peso_familia(nd: str):
    """Peso/rótulo de embalagem por família. Consulta embalagens.json (CEASA-BA Salvador)
    quando override=False; usa o fallback hardcoded quando override=True (família com
    embalagem específica da Igarashi divergente da praça)."""
    for token, slug, lbl, peso_fallback, override in _IG_FAMILIAS:
        if token in nd:
            if override or not slug:
                return peso_fallback, lbl
            peso_base, _, _ = _peso_commodity(slug)
            return (float(peso_base) if peso_base is not None else peso_fallback), lbl
    return None, None


def _ig_maca(desc_raw: str, cat_secao: str | None, preco: float) -> dict:
    nd = _norm(desc_raw)
    mc = re.search(r"cat\s*0*([123])", nd)
    cat = mc.group(1) if mc else (cat_secao or "1")
    if "belgala" in nd:  var = "BELGALA"
    elif "fuji" in nd:   var = "FUJI"
    else:                var = "GALA"          # default (linhas MI sem variedade explícita)
    premium = "premium" in nd
    mi = bool(re.search(r"\bmi\b", nd))
    # maçã = caixa 18kg padrão (Igarashi). Consulta base CEASA — se não houver, fallback 18.
    _peso_base, _, _ = _peso_commodity("maca")
    peso = float(_peso_base) if _peso_base is not None else 18.0
    mw = _IG_PESO_INLINE.search(desc_raw)
    if mw:                                       # linha MI-070 traz "12,5" -> caixa de 12,5kg
        peso = float(mw.group(1).replace(",", "."))
    cals = _IG_INT.findall(desc_raw)             # último inteiro 2-3 díg. isolado = calibre
    calibre = cals[-1] if cals else "?"
    # MI/PREMIUM vêm ANTES do calibre de propósito: assim o desc do default
    # ("MACA GALA CAT1 CAL120") nunca é substring de uma variação ("...MI CAL120"),
    # senão o _match_fallback por contenção casaria a MI miúda (mais barata) ao mesmo COD.
    qualif = (" MI" if mi else "") + (" PREMIUM" if premium else "")
    desc = f"MACA {var}{qualif} CAT{cat} CAL{calibre}"
    unid = f"CX {peso:g}KG"
    # prio (plano A→B): A=CAT1 Gala calibre 110/120 (default cardapio); B=CAT2 Gala 120
    # (alt tatica). Fora disso (CAT3, 165/180/250, Fuji, Belgala, MI) = 9 (nao compete).
    if cat == "1" and var == "GALA" and calibre in ("110", "120") and not mi and not premium:
        prio = 0
    elif cat == "2" and var == "GALA" and calibre == "120" and not mi:
        prio = 1
    else:
        prio = 9
    return {"desc": desc, "unidade": unid, "preco": preco, "familia": "MACA", "prio": prio,
            "cat": cat, "calibre": calibre, "variedade": var, "mi": mi, "premium": premium}


def _ig_generico(desc_raw: str, preco: float) -> dict | None:
    nd = _norm(desc_raw)
    peso, lbl = _ig_peso_familia(nd)
    if peso is None:
        return None
    unid = f"{lbl} {peso:g}KG"
    base = {"unidade": unid, "preco": preco}
    # prio (plano A→B): 0=plano A (default cardapio), 1=plano B (alt tatica), 9=fora da gondola.
    if "alho" in nd:
        m = re.search(r"\b([456])\b", nd)
        cal = m.group(1) if m else "?"
        prio = {"5": 0, "4": 1}.get(cal, 9)   # default cal5; alt cal4; cal6=premium/fora
        return {"desc": f"ALHO NACIONAL TOALETADO CAL{cal}", "familia": "ALHO",
                "calibre": cal, "prio": prio, **base}
    if "batata" in nd:
        tipo = "ESPECIAL CHAPADA" if "especial" in nd else (
               "BICA CHAPADA" if "bica" in nd else desc_raw.upper())
        prio = 0 if "especial" in nd else (1 if "bica" in nd else 9)  # Especial default, Bica alt
        return {"desc": f"BATATA {tipo}", "familia": "BATATA", "tipo": tipo, "prio": prio, **base}
    if "cebola" in nd:
        cor = "ROXA" if "roxa" in nd else "BRANCA"
        m = re.search(r"cx\s*0*([234])", nd)
        cx = m.group(1) if m else "?"
        if cor == "BRANCA":
            prio = {"3": 0, "4": 1}.get(cx, 9)   # branca: CX3 default, CX4 alt, CX2 fora
        else:
            prio = {"3": 0, "2": 1}.get(cx, 9)   # roxa: CX3 default, CX2 alt (se faltar margem)
        return {"desc": f"CEBOLA {cor} CX{cx}", "familia": "CEBOLA",
                "cor": cor, "calibre": f"CX{cx}", "prio": prio, **base}
    if "cenoura" in nd:
        return {"desc": "CENOURA 3A", "familia": "CENOURA", "calibre": "3A", "prio": 0, **base}
    if "repolho" in nd:
        return {"desc": "REPOLHO VERDE", "familia": "REPOLHO", "prio": 0, **base}
    if "tomate" in nd:
        if "b7" in nd:                       tipo, prio = "B7", 0              # -> COD139 (salada)
        elif "graud" in nd:                  tipo, prio = "SALADETE GRAUDO", 9 # nao comprar default
        elif "medio" in nd:                  tipo, prio = "SALADETE MEDIO", 0  # -> COD138 (italiano)
        else:                                tipo, prio = desc_raw.upper(), 9
        return {"desc": f"TOMATE {tipo}", "familia": "TOMATE", "tipo": tipo, "prio": prio, **base}
    return None


def parse_igarashi(path: str | Path) -> dict:
    raw = Path(path).read_text(errors="ignore")
    if raw.lstrip().startswith("{\\rtf"):
        from striprtf.striprtf import rtf_to_text
        raw = rtf_to_text(raw)
    itens, validade = [], None
    secao_maca, cat_secao = False, None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        nl = _norm(line)
        if nl.startswith(("prezado", "seguem", "boa ")) or not nl:
            continue
        # cabeçalho de bloco de maçã (sem preço): liga a seção e captura a CAT
        if re.match(r"^maca\b", nl) and not _IG_PRECO.search(line):
            secao_maca = True
            mc = re.search(r"cat\s*0*([123])", nl)
            if mc:
                cat_secao = mc.group(1)
            continue
        precos = _IG_PRECO.findall(line)
        if not precos:
            continue
        preco = parse_preco(precos[-1])
        if preco is None:
            continue
        idx = line.rfind(precos[-1])
        desc_raw = line[:idx].rstrip(" -–—\t")
        eh_maca = secao_maca or bool(re.match(r"^(cat|belgala)\b", nl))
        it = _ig_maca(desc_raw, cat_secao, preco) if eh_maca else _ig_generico(desc_raw, preco)
        if it:
            itens.append(it)
    return {"fornecedor": "IGARASHI", "validade": validade, "itens": itens}


PARSERS = {
    "DONOFRIO": parse_donofrio,
    "SHIMIZU": parse_shimizu,
    "DOCE MEL": parse_docemel,
    "HORTIMIX": parse_hortimix,
    "BOA CITRUS": parse_boacitrus,
    "IGARASHI": parse_igarashi,
}


if __name__ == "__main__":
    import sys
    UP = "/sessions/loving-affectionate-goodall/mnt/uploads"
    for nome, fn, arq in [
        ("DONOFRIO", parse_donofrio, f"{UP}/Tabela Donofrio.rtf"),
        ("SHIMIZU", parse_shimizu, f"{UP}/Consulta Produto ATUALIZADO 16-05.pdf"),
        ("DOCE MEL", parse_docemel, f"{UP}/TABELA 0% SEMANA 21..pdf"),
    ]:
        r = fn(arq)
        print(f"\n{nome}: {len(r['itens'])} itens | validade={r['validade']!r}")
        for it in r["itens"][:4]:
            print("   ", it)
