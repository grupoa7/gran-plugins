"""
parse_ceasa.py — Parser do Boletim CEASA-BA (âncora de benchmark).

Fonte: https://www.ba.gov.br/sde/boletim-informativo-ceasa (PDF ~3x/semana, atual).
Colunas: PRODUTO | UNIDADE | PROCEDÊNCIA | MÍNIMO | MAIS COMUM | MÁXIMO | SITUAÇÃO.
Usamos "MAIS COMUM" (preço modal) como âncora, normalizado para R$/kg pela UNIDADE.

IMPORTANTE (ver references/benchmark_ceasa.md):
  - O nome do PDF mais recente NÃO é previsível e a página de listagem pode vir
    em cache. Para pegar o boletim do dia, o Claude navega a listagem AO VIVO
    (Chrome MCP) e baixa o PDF do topo; este script só PARSEIA o PDF/texto.
  - Cobertura ~90 commodities (frutas/hortaliças/ovos) = os KVIs de maior giro.
    Itens fora do boletim caem na mediana entre fornecedores.
"""
from __future__ import annotations
import re
from flv_lib import parse_preco, peso_kg_da_unidade

_SECOES = {"CEREAIS", "FRUTAS", "HORTALIÇAS", "HORTALICAS", "OVOS", "PESCADO",
           "OUTROS GENEROS ALIMENTICIOS", "OUTROS GÊNEROS ALIMENTÍCIOS"}
# linha: PRODUTO  UNIDADE  PROCEDENCIA  MIN  COMUM  MAX  SIT
_RE_LINHA = re.compile(
    r"^(?P<prod>.+?)\s+(?P<und>(?:CX|SC|CENTO|UND|KG|MOL|FRD|FD|SACO)\.?.*?)\s+"
    r"(?P<proc>[A-Z]{2}(?:/[A-Z]{2})*)\s+"
    r"(?P<min>[\d.,]+)\s+(?P<comum>[\d.,]+)\s+(?P<max>[\d.,]+)\s+"
    r"(?P<sit>EST|FIR|FRA|ENT)\s*$")


def parse_boletim_texto(texto: str) -> dict:
    """Recebe o texto do boletim (de pdfplumber/extract_text). Devolve:
       {'data':..., 'itens':[{prod,unidade,comum,comum_kg,situacao,procedencia}]}"""
    itens, data = [], None
    for line in texto.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.search(r"EMISS[ÃA]O[:\s]+(\d{2}/\d{2}/\d{4})", s)
        if m:
            data = m.group(1)
        if s.upper() in _SECOES:
            continue
        mm = _RE_LINHA.match(s)
        if not mm:
            continue
        comum = parse_preco(mm.group("comum"))
        if comum is None:
            continue
        und = mm.group("und").strip()
        peso = peso_kg_da_unidade(und)
        comum_kg = round(comum / peso, 4) if peso else None
        itens.append({
            "prod": mm.group("prod").strip(),
            "unidade": und,
            "procedencia": mm.group("proc"),
            "comum": comum,
            "comum_kg": comum_kg,        # None p/ itens vendidos por peça (CENTO/UND)
            "situacao": mm.group("sit"),  # EST estável / FIR firme / FRA fraco / ENT entrando
        })
    return {"data": data, "itens": itens}


def parse_boletim_pdf(path: str) -> dict:
    import pdfplumber
    txt = []
    with pdfplumber.open(path) as pdf:
        for p in pdf.pages:
            txt.append(p.extract_text() or "")
    return parse_boletim_texto("\n".join(txt))


if __name__ == "__main__":
    # Teste com linhas reais do boletim de 13/03/2026 (observadas)
    amostra = """BOLETIM INFORMATIVO DIÁRIO
SALVADOR - BA EMISSÃO: 13/03/2026
FRUTAS
ABACATE GRANDE CX. 20KG BA/ES/SP 60,00 70,00 70,00 FIR
BANANA PRATA 1A CX 45 KG BA/PE 100,00 160,00 160,00 EST
MAMAO FORMOSA KG BA/PB/PE 3,00 4,00 4,00 ENT
MORANGO CX 1 KG BA/ES/GO/RS 25,00 25,00 30,00 EST
HORTALIÇAS
TOMATE EXTRA CX. 20 / 22 KG BA 130,00 130,00 140,00 EST
BATATINHA LISA ESP SC. C/ 50 kG BA/MG 270,00 300,00 340,00 FIR
CEBOLA PERA SC. C/ 20 KG BA/SC 65,00 65,00 65,00 EST
OVOS
OVOS BRANCOS GRANDE CX. 30 DUZIAS BA/ES/MG 200,00 200,00 215,00 EST"""
    r = parse_boletim_texto(amostra)
    print("data:", r["data"], "| itens:", len(r["itens"]))
    for it in r["itens"]:
        print(f"  {it['prod'][:24]:24s} {it['unidade']:14s} comum R${it['comum']:>7.2f} "
              f"-> R$/kg {it['comum_kg']} [{it['situacao']}]")
