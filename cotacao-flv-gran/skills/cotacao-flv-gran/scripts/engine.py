"""
engine.py — Motor de cotação: casamento item->COD, normalização e alocação.

Fluxo: tabelas parseadas + CONTAGEM FLV + dicionário -> decisão por item.

Regras (references/regras_negocio.md):
  - Cherry-picking por item, nunca por pacote.
  - Exclusão por item: fornecedor barrado num item NÃO vence aquele item (mesmo + barato).
  - Âncoras: mediana entre fornecedores da semana; banda de sanidade via último custo.
  - Comparação contra o fornecedor titular do BI (quem o BI já escolheu).
  - Preço 0,00/vazio nunca entra (já filtrado no parser).
"""
from __future__ import annotations
import re
import statistics
from pathlib import Path

from flv_lib import (norm_texto, peso_kg_da_unidade, fora_da_banda,
                     resolver_peso_kg,
                     CANAL_BUSCA, DICIONARIO_FORNECEDORES)

# Mapa nome-do-titular-no-BI -> chave de fornecedor da cotação (quando temos tabela)
TITULAR_PARA_FORNECEDOR = {
    "AGRO COMERCIAL SHIMIZU": "SHIMIZU",
    "TRIELO": "DOCE MEL",
    "D ONOFRIO": "DONOFRIO",
    "RML": "RML",
    "ROTA (MICAEL)": "MICAEL",
}


def titular_key(nome_titular: str) -> str | None:
    n = (nome_titular or "").upper()
    for chave, forn in TITULAR_PARA_FORNECEDOR.items():
        if chave in n:
            return forn
    return None


def canal_do_fornecedor(forn: str) -> str:
    return "busca" if forn.upper() in CANAL_BUSCA else "entrega"


# --------------------------------------------------------------------------- #
# Casamento desc do fornecedor -> COD Gran
# --------------------------------------------------------------------------- #
def casar_tabela(tabela: dict, dic: dict) -> tuple[dict, list]:
    """Para uma tabela parseada, devolve ({cod: melhor_registro_normalizado}, nao_casados).
    'melhor' = menor preço normalizado quando várias linhas casam o mesmo COD.
    """
    forn = tabela["fornecedor"].upper()
    match_map = dic["match"].get(forn, {})
    keys_norm = list(match_map.keys())
    por_cod, nao_casados = {}, []
    for it in tabela["itens"]:
        nd = norm_texto(it["desc"])
        cod = match_map.get(nd)
        if cod is None:
            cod = _match_fallback(nd, keys_norm, match_map)
        if cod is None:
            nao_casados.append(it)
            continue
        gran_unit = dic["por_cod"].get(cod, {}).get("unidade")
        preco_norm, base, meta = normalizar_preco(it["preco"], it["unidade"], gran_unit, cod=cod)
        if preco_norm is None:
            nao_casados.append({**it, "motivo": "unidade nao normalizavel"})
            continue
        reg = {"fornecedor": tabela["fornecedor"], "desc_forn": it["desc"],
               "unidade_forn": it["unidade"], "preco_raw": it["preco"],
               "preco_norm": round(preco_norm, 4), "base": base,
               "peso_origem": meta.get("peso_origem"),        # 'explicito_fornecedor'|'ceasa_base'|'por_peca'
               "peso_kg_usado": meta.get("peso_kg_usado"),    # peso aplicado p/ normalizar (None=por_peca)
               "peso_nao_padrao": meta.get("peso_nao_padrao"),# True = commodity fora do padrão CEASA universal
               "peso_motivo": meta.get("peso_motivo", []),    # rastreio
               "prio": int(it.get("prio", 0)),
               "canal": canal_do_fornecedor(tabela["fornecedor"])}
        # Dedup por COD: preferência (prio asc) ANTES de preço (prio asc, preço asc).
        # prio é o "plano" do item (0=plano A/default, 1=plano B/alt tática, 9=fora);
        # assim o plano B (mais barato) só vence quando o plano A NÃO foi ofertado.
        # Fornecedores sem 'prio' = todos prio 0 -> dedup por menor preço (comportamento antigo).
        cur = por_cod.get(cod)
        if cur is None or (reg["prio"], reg["preco_norm"]) < (cur["prio"], cur["preco_norm"]):
            por_cod[cod] = reg
    return por_cod, nao_casados


def _match_fallback(nd: str, keys_norm: list, match_map: dict) -> int | None:
    """Match conservador por contenção quando o exato falha.
    Aceita só se uma chave do dicionário contém / é contida na descrição e o
    tamanho é compatível (evita casar 'uva' com 'uva italia cx').
    """
    if not nd:
        return None
    cand = [k for k in keys_norm if (k in nd or nd in k)]
    if not cand:
        return None
    # escolhe a chave mais longa contida (mais específica) com razão de tamanho >= 0.5
    cand.sort(key=len, reverse=True)
    for k in cand:
        menor, maior = sorted((len(k), len(nd)))
        if maior and menor / maior >= 0.5:
            return match_map[k]
    return None


# --------------------------------------------------------------------------- #
# Normalização final de preço dado a unidade do fornecedor e a unidade Gran
# --------------------------------------------------------------------------- #
_RE_BOX = re.compile(r"\b(cx|sc|saco|caixa|fd|frd)\b", re.I)


def normalizar_preco(preco: float, unidade_forn: str, gran_unit: str | None,
                     cod: int | str | None = None):
    """Devolve (preco_normalizado, base, meta) com base em {'kg','un'}.

    REGRA (Hugo 2026-05-28): respeita peso explícito do fornecedor. Só consulta a base
    CEASA (embalagens.json) como FALLBACK quando a unidade vem como caixa sem peso
    (ex.: 'CX', 'CAIXA', vazia) E o Gran vende por kg.

    meta inclui rastreio do peso pra UI poder mostrar a flag amarela ('peso assumido CEASA'):
      - peso_origem:   explicito_fornecedor | ceasa_base | por_peca | nao_resolvido
      - peso_kg_usado: float | None
      - peso_nao_padrao: bool  (True = commodity fora do padrão; sistema deveria exigir kg)
      - peso_motivo:   list[str]
    Se não der pra converter de forma confiável, devolve (None, base, meta)."""
    u = (unidade_forn or "").upper()
    gran = (gran_unit or "").upper()
    quer_kg = gran in ("QUILO", "KG", "KILO")

    # Resolve peso via cascata (string explícita -> fallback CEASA-BA quando possível)
    r = resolver_peso_kg(unidade_forn, cod_gran=cod)
    peso = r["peso_kg"]
    meta = {"peso_origem": r["origem"], "peso_kg_usado": peso,
            "peso_nao_padrao": r["nao_padrao"], "peso_motivo": r["motivo"],
            "peso_commodity": r["commodity"]}
    is_box = bool(_RE_BOX.search(u)) or (u == "" and peso is not None)

    if quer_kg:
        # nao_padrao=True bloqueia conversão automática: força fornecedor declarar kg
        if r["nao_padrao"] and r["origem"] == "ceasa_base":
            return None, "kg", meta
        if is_box and peso:              # caixa/saca (com peso explícito OU via fallback CEASA)
            return preco / peso, "kg", meta
        if peso and peso != 1.0:         # pacote com peso (ex 250G) -> R$/kg
            return preco / peso, "kg", meta
        return preco, "kg", meta         # já é por kg (KG, KG/UND)
    else:                                # quer R$/un
        if "CENTO" in u:
            return preco / 100.0, "un", meta
        if is_box:                       # caixa com contagem desconhecida -> não comparável por un
            return None, "un", meta
        return preco, "un", meta         # por unidade/bandeja/maço


# --------------------------------------------------------------------------- #
# Cotação: decisão por item
# --------------------------------------------------------------------------- #
def cotar(contagem: list[dict], tabelas: list[dict], dic: dict,
          exclusoes: dict | None = None, banir: set | None = None) -> dict:
    """exclusoes: {cod: set(FORNECEDOR barrado)}. banir: set(FORNECEDOR) barrado em
    todos os itens (feedback 'evitar' de fornecedor inteiro). Retorna decisões + não-casados."""
    exclusoes = exclusoes or {}
    banir = {b.upper() for b in (banir or set())}
    casadas, nao_casados = {}, {}
    for tab in tabelas:
        m, nc = casar_tabela(tab, dic)
        casadas[tab["fornecedor"].upper()] = m
        if nc:
            nao_casados[tab["fornecedor"]] = nc

    decisoes = []
    for item in contagem:
        cod = item["cod"]
        # candidatos: todos os fornecedores que cotaram este COD
        cands = {}
        for forn, m in casadas.items():
            if cod in m:
                cands[forn] = m[cod]
        barrados = {b.upper() for b in exclusoes.get(cod, set())} | (banir & set(cands))
        elegiveis = {f: r for f, r in cands.items() if f not in barrados}

        custo_unit = None
        if item.get("custo_titular_total") and item.get("qtd"):
            custo_unit = item["custo_titular_total"] / item["qtd"]

        d = {**item, "n_fontes": len(cands), "candidatos": cands,
             "barrados": sorted(barrados & set(cands)), "custo_unit_titular": custo_unit}

        if not elegiveis:
            d["status"] = "sem_cotacao" if not cands else "todos_barrados"
            d["vencedor"] = None
            decisoes.append(d)
            continue

        precos = {f: r["preco_norm"] for f, r in elegiveis.items()}
        venc_forn = min(precos, key=precos.get)
        venc = elegiveis[venc_forn]
        mediana = statistics.median(precos.values())
        d["vencedor"] = {"fornecedor": venc_forn, **venc}
        d["mediana_mercado"] = round(mediana, 4)
        d["status"] = "ok"
        d["fonte_unica"] = len(precos) == 1

        # alertas
        alertas = []
        if custo_unit and fora_da_banda(venc["preco_norm"], custo_unit):
            alertas.append("FORA_DA_BANDA")  # destoa do último custo -> reconferir unidade/preço
        if len(precos) >= 3:
            for f, p in precos.items():
                if p > 1.20 * mediana:
                    alertas.append(f"ACIMA_MEDIANA:{f}")
        if d["fonte_unica"]:
            alertas.append("FONTE_UNICA")
        # peso veio da base CEASA-BA (fornecedor não declarou) -> flag amarela.
        # O vencedor usou peso assumido — Hugo confere antes de fechar.
        if venc.get("peso_origem") == "ceasa_base":
            alertas.append("PESO_ASSUMIDO_CEASA")
        d["alertas"] = alertas

        # comparação com titular do BI
        tk = titular_key(item["fornecedor_titular"])
        d["titular_forn"] = tk
        if tk and tk in precos:
            economia = (precos[tk] - precos[venc_forn]) * item["qtd"]
            d["titular_preco"] = precos[tk]
            d["economia_vs_titular"] = round(economia, 2)
            d["troca_recomendada"] = venc_forn != tk
        else:
            d["titular_preco"] = None
            d["economia_vs_titular"] = None
            d["troca_recomendada"] = None
        decisoes.append(d)

    return {"decisoes": decisoes, "nao_casados": nao_casados}
