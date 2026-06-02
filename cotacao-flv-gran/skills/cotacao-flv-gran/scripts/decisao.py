"""
decisao.py — Camada de decisão e correção factual da cotação.

Enriquece cada decisão da cotação com:
  - match CEASA com NÍVEL DE CONFIANÇA (alta/baixa) + dicionário de exceções;
    match duvidoso vira status 'perguntar' (a skill pergunta na rodada e grava a
    resposta em dados/dicionario_excecoes_ceasa.csv). NUNCA exibe número duvidoso.
  - conversão de unidade honesta: caixa-de-N-unidades/dúzias e cento; o que não dá
    pra comparar com segurança vira None ('conferir'), não número errado.
  - R$/semana EM JOGO = giro semanal × (preço de referência − melhor preço).
  - recomendação (TROCAR/MANTER/NEGOCIAR/BUSCAR/CONFERIR) + justificativa de 1 linha.
  - feedback do Hugo por produto×fornecedor (evitar/ruim/ok/preferido) aplicado.

Filosofia: dado real ou nada; perguntar quando incerto pra adquirir conhecimento.
"""
from __future__ import annotations
import os
import csv
import re
import unicodedata
from pathlib import Path

from flv_lib import peso_kg_da_unidade

SKILL_DIR = Path(__file__).resolve().parent.parent
# Dados mutáveis no PROJETO (gravável). COTACAO_DADOS = <projeto>/dados; fallback dev = dados/ local.
DADOS = Path(os.environ.get("COTACAO_DADOS") or (SKILL_DIR / "dados"))

_SEMANAS_60D = 8.6
_STOP = {"kg", "un", "und", "uni", "unidade", "pct", "pacote", "quilo", "kilo", "g", "gr",
         "cx", "sc", "saco", "mol", "duzia", "duzias", "cento", "bdj", "bandeja", "vacuo",
         "de", "da", "do", "com", "sem", "tipo", "premium", "graudo", "und."}


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "").lower()).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _sig(desc):
    return [w for w in _norm(desc).split() if w not in _STOP and not re.fullmatch(r"\d+\w*", w)]


# --------------------------------------------------------------------------- #
# Detecção de embalagem por contagem (onde NÃO dá pra normalizar com segurança)
# --------------------------------------------------------------------------- #
_RE_COUNT = re.compile(r"(\d+)\s*(unid|und|un|duzias?|dz)\b|[\bc](\d{1,3})\b", re.I)
_RE_CENTO = re.compile(r"\bcento\b", re.I)


def is_pack_contagem(unidade_ou_label: str) -> bool:
    """True para 'CX 30 UNID', '30 DUZIAS', 'C30', 'C12' — pack por contagem de peças."""
    u = str(unidade_ou_label or "")
    return bool(re.search(r"\d+\s*(unid|und|duzias?|dz)\b", u, re.I) or re.search(r"\bc\d{2,3}\b", u, re.I))


# --------------------------------------------------------------------------- #
# Feedback produto×fornecedor
# --------------------------------------------------------------------------- #
VEREDITOS = {"evitar", "ruim", "ok", "preferido"}


def carregar_feedback(path: Path | None = None) -> dict:
    """dados/feedback_fornecedor.csv: cod,item,fornecedor,veredito,nota.
    cod vazio = vale pra todos os itens daquele fornecedor.
    Retorna {(cod|None, FORN): {veredito, nota}}."""
    path = path or (DADOS / "feedback_fornecedor.csv")
    fb = {}
    if not Path(path).exists():
        return fb
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            forn = (row.get("fornecedor") or "").strip().upper()
            if not forn:
                continue
            cod = (row.get("cod") or "").strip()
            cod = int(cod) if cod.isdigit() else None
            ver = (row.get("veredito") or "").strip().lower()
            if ver not in VEREDITOS:
                continue
            fb[(cod, forn)] = {"veredito": ver, "nota": (row.get("nota") or "").strip()}
    return fb


def feedback_de(fb, cod, forn):
    forn = (forn or "").upper()
    return fb.get((cod, forn)) or fb.get((None, forn))


def evitados_para_exclusoes(fb) -> dict:
    """Converte feedback 'evitar' em exclusões {cod: set(FORN)} para o motor de cotação.
    Feedback de fornecedor inteiro (cod None) é aplicado na hora da cotação (ver cotar.py)."""
    exc = {}
    for (cod, forn), v in fb.items():
        if v["veredito"] == "evitar" and cod is not None:
            exc.setdefault(cod, set()).add(forn)
    return exc


# --------------------------------------------------------------------------- #
# Match CEASA com confiança + exceções
# --------------------------------------------------------------------------- #
def carregar_excecoes_ceasa(path: Path | None = None) -> dict:
    """dados/dicionario_excecoes_ceasa.csv: cod,ceasa_produto. Mapeamentos confirmados
    pelo Hugo (crescem a cada rodada). ceasa_produto vazio = 'sem correspondente'."""
    path = path or (DADOS / "dicionario_excecoes_ceasa.csv")
    out = {}
    if not Path(path).exists():
        return out
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cod = (row.get("cod") or "").strip()
            if cod.isdigit():
                out[int(cod)] = (row.get("ceasa_produto") or "").strip()
    return out


# sinônimos de grafia Gran<->CEASA (cresce conforme aprendemos; precisão > cobertura)
_SYN = {"tahiti": "taiti", "tommyatkins": "tommy", "tommy": "tommy",
        "morkot": "murcote", "murcott": "murcote", "ponkan": "pokan"}


def _canon(w):
    return _SYN.get(w, w)


def _tok_match(w, toks):
    """Casa por token EXATO (com sinônimos de grafia). Sem prefixo solto pra não
    casar 'limao'~'lima' ou 'cebola'~'cebolinha'."""
    cw = _canon(w)
    return any(_canon(t) == cw for t in toks)


def _score_chave(chave, toks):
    """Quantas palavras da chave Gran aparecem nos tokens do produto CEASA."""
    return sum(1 for w in chave if _tok_match(w, toks))


def match_ceasa(d, ceasa_atual, excecoes):
    """Devolve (status, chave|None, reg|None, confianca).
    status: 'ok' (match confiável) | 'perguntar' (duvidoso) | 'sem' (sem candidato/definido sem corresp.)"""
    cod = d.get("cod")
    if cod in excecoes:
        alvo = excecoes[cod]
        if not alvo:                      # confirmado: não tem no CEASA
            return ("sem", None, None, "confirmado")
        na = _norm(alvo)
        # 1) match exato pelo nome do produto/chave
        for k, v in (ceasa_atual or {}).items():
            if _norm(v.get("produto", k)) == na or _norm(k) == na:
                return ("ok", k, v, "confirmado")
        # 2) match por contenção (ex 'maca imp gransmith' dentro de 'maca imp gransmith tp 80 125')
        for k, v in (ceasa_atual or {}).items():
            if na and na in _norm(v.get("produto", k)):
                return ("ok", k, v, "confirmado")
        return ("sem", None, None, "confirmado")
    ws = _sig(d.get("desc"))
    if not ws or not ceasa_atual:
        return ("sem", None, None, "")
    chave = ws[:2]
    cands = []
    for k, v in ceasa_atual.items():
        if len(k) > 60:
            continue
        toks = set(t for t in _norm(v.get("produto", k)).split() if not re.fullmatch(r"\d+\w*", t))
        if not toks or not _tok_match(chave[0], toks):   # 1ª palavra (produto-base) tem que bater
            continue
        sc = _score_chave(chave, toks)
        base = sorted(toks)[0] if toks else ""
        cands.append((sc, k, v, base))
    if not cands:
        return ("sem", None, None, "")
    cands.sort(key=lambda x: -x[0])
    maxsc = cands[0][0]
    top = [c for c in cands if c[0] == maxsc]

    casou_tudo = maxsc >= len(chave)                  # todas as palavras da chave bateram
    casou_base_so = maxsc == 1 and len(chave) == 1    # desc de 1 palavra (genérico)
    # CEASA só tem o nome genérico (1 token) e o Gran especifica cultivar -> genérico vira referência
    def _ntok(c):
        return len([t for t in _norm(c[2].get("produto", "")).split() if not re.fullmatch(r"\d+\w*", t)])
    top_generico = all(_ntok(c) <= 1 for c in top)
    # famílias do mesmo produto-base (todos os top compartilham a 1ª palavra)? -> agrega
    mesma_familia = len({c[3] for c in top}) == 1

    if (casou_tudo or casou_base_so or top_generico) and mesma_familia:
        import statistics
        regs = [c[2] for c in top]
        kgs = [r["comum_kg"] for r in regs if r.get("comum_kg")]
        uns = [r["comum_un"] for r in regs if r.get("comum_un")]
        syn = dict(top[0][2])
        if kgs:
            syn["comum_kg"] = round(statistics.median(kgs), 2)
        if uns:
            syn["comum_un"] = round(statistics.median(uns), 2)
        syn["produto"] = top[0][2].get("produto") if len(top) == 1 else " ".join(chave).upper()
        syn["n_variantes"] = len(top)
        conf = "alta" if len(top) == 1 else "media"
        return ("ok", top[0][1], syn, conf)
    # só a 1ª palavra bateu com chave de 2 palavras (cultivar diferente, ex manga palmer)
    # ou empate entre produtos diferentes -> incerto, perguntar
    return ("perguntar", cands[0][1], cands[0][2], "baixa")


def carregar_conversao(path: Path | None = None) -> dict:
    """dados/conversao_unidade_gran.csv: cod,base(kg|un),fator. Converte o preço CEASA
    para a UNIDADE DE VENDA do Gran em casos atípicos confirmados pelo Hugo.
    Ex: alface (cod 201) -> base=kg, fator=0.4 (cada un do Gran ~400g);
        ovos dúzia (cod 6153) -> base=un, fator=12 (Gran vende a dúzia = 12 ovos)."""
    path = path or (DADOS / "conversao_unidade_gran.csv")
    out = {}
    if not Path(path).exists():
        return out
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cod = (row.get("cod") or "").strip()
            if cod.isdigit():
                try:
                    out[int(cod)] = ((row.get("base") or "kg").strip().lower(), float(row.get("fator")))
                except (ValueError, TypeError):
                    pass
    return out


def preco_ceasa(d, reg, conv=None):
    """Preço CEASA na UNIDADE DE VENDA do Gran. None se não der pra comparar com segurança."""
    if not reg:
        return None
    cod = d.get("cod")
    if conv and cod in conv and conv[cod][0] in ("kg", "un"):   # conversão atípica confirmada
        base, fator = conv[cod]
        val = reg.get("comum_kg") if base == "kg" else reg.get("comum_un")
        return round(val * fator, 3) if val else None
    # base=cx (preço por caixa do fornecedor) não tem correspondência direta no CEASA -> sem ref.
    if conv and cod in conv and conv[cod][0] == "cx":
        return None
    por_kg = _norm(d.get("und")) in ("kg", "quilo", "kilo")
    if por_kg:
        return reg.get("comum_kg")
    # item por unidade: o loader já converteu CENTO/DÚZIAS/UNID para preço por unidade
    return reg.get("comum_un")


# --------------------------------------------------------------------------- #
# R$ em jogo + recomendação
# --------------------------------------------------------------------------- #
def giro_semanal(cod, vendas):
    if not vendas or cod not in vendas:
        return None
    v = vendas[cod]
    # Fonte BI: giro já é semanal (MÉDIA FINAL diária × dias/semana).
    if v.get("giro_sem") is not None:
        return v["giro_sem"]
    q = v.get("qtd") or 0
    return q / _SEMANAS_60D if q else 0.0


def enriquecer(resultado, vendas=None, ceasa_atual=None, ceasa_series=None,
               feedback=None, excecoes=None):
    """Adiciona a cada decisão: ceasa{status,preco,sit,produto,confianca}, giro_sem,
    r_em_jogo, recomendacao, justificativa, fb (feedback do vencedor). Ordena por R$ em jogo."""
    feedback = feedback or {}
    excecoes = excecoes or {}
    conv = carregar_conversao()
    perguntar = []  # itens cujo match CEASA precisa de confirmação do Hugo
    for d in resultado["decisoes"]:
        cod = d.get("cod")
        st, chave, reg, conf = match_ceasa(d, ceasa_atual, excecoes)
        pc = preco_ceasa(d, reg, conv) if st == "ok" else None
        d["ceasa"] = {"status": st, "preco": pc, "confianca": conf,
                      "produto": (reg or {}).get("produto") if reg else None,
                      "sit": (reg or {}).get("sit") if reg else None,
                      "candidato": (reg or {}).get("produto") if st == "perguntar" else None}
        if st == "perguntar":
            perguntar.append({"cod": cod, "item": d.get("desc"),
                              "candidato_ceasa": (reg or {}).get("produto")})
        gs = giro_semanal(cod, vendas)
        d["giro_sem"] = gs
        v = d.get("vencedor")
        # feedback do fornecedor vencedor
        d["fb"] = feedback_de(feedback, cod, v["fornecedor"]) if v else None

        if not v:
            d["r_em_jogo"] = 0.0
            d["recomendacao"] = "DEFINIR"
            d["justificativa"] = "Sem cotação — buscar no CEASA ou seedar pelo custo do BI."
            continue

        # indicadores financeiros SEMANAIS (na unidade de venda do Gran, base = giro).
        # Os três se reconciliam: Custo atual − Custo pós-cotação = Economia.
        vinfo = (vendas.get(cod) or {}) if vendas else {}
        pv = vinfo.get("preco_venda")
        cu = vinfo.get("custo_unit")            # CUSTO ATUAL do produto (P.CUSTO do BI)
        d["venda_sem"] = round((gs or 0) * pv, 2) if pv else None
        # Custo/sem = giro × custo ATUAL do BI (o que o Gran gasta hoje com esse giro).
        d["custo_sem"] = round((gs or 0) * cu, 2) if cu else None

        # PREÇO DO VENCEDOR NA UNIDADE DE VENDA DO GRAN (+ trava de confiabilidade).
        # O custo pós-cotação só faz sentido se o preço do vencedor está na mesma unidade
        # do Gran. Quando o Gran vende por UNIDADE mas o fornecedor cota por PESO/CAIXA/MAÇO,
        # o preço NÃO é por unidade — projetar daria número errado (ex.: ovos R$200/cx).
        # Se houver fator confirmado (conversao_unidade_gran.csv) e ele casar com a unidade
        # cotada, CONVERTEMOS e recuperamos o item; senão, suprimimos a projeção e marcamos
        # CONFERIR (preço do fornecedor ainda aparece na matriz para comparação visual).
        por_kg = _norm(d.get("und")) in ("kg", "quilo", "kilo")
        vforn = _norm(v.get("unidade_forn"))
        peso_forn = peso_kg_da_unidade(v.get("unidade_forn"))
        preco_gran = v["preco_norm"]
        unid_confiavel = True
        if por_kg:
            unid_confiavel = (v.get("base") == "kg")
        elif cod in conv:
            base_c, fat_c = conv[cod]
            eh_peca = peso_forn is None and bool(re.search(r"\b(und?|uni|mco|maco|mol|bdj|bandeja)\b", vforn))
            if base_c == "cx":                              # fornecedor cota por CAIXA
                # fat_c = quantas unidades de venda do Gran cabem em 1 caixa do fornecedor
                # (ex.: ovos — Gran vende a bandeja de 30; caixa = 10 bandejas -> fat_c=10).
                preco_gran = round(v["preco_norm"] / fat_c, 4) if fat_c else v["preco_norm"]
                unid_confiavel = bool(fat_c)
            elif peso_forn is not None:                     # fornecedor cota por PESO (kg)
                if base_c == "kg":
                    preco_gran = round(v["preco_norm"] * fat_c, 4)   # R$/kg × (kg por un do Gran)
                else:
                    unid_confiavel = False                  # fator é por peça, mas veio peso -> não casa
            elif eh_peca:                                    # fornecedor cota por PEÇA/MAÇO/UND
                # base=un: fator peça→un (ex.: dúzia=12, maço=1). base=kg: já é por unidade -> ×1.
                preco_gran = round(v["preco_norm"] * (fat_c if base_c == "un" else 1.0), 4)
            else:                                            # caixa/saco: contagem desconhecida
                unid_confiavel = False        # fator não casa com a unidade cotada (ex.: ovos por caixa)
        else:                                  # Gran por unidade, sem fator confirmado
            eh_caixa = bool(re.search(r"\b(cx|caixa|sc|saco|fardo|frd)\b", vforn))
            eh_maco = bool(re.search(r"\b(mco|maco|mol|duzia|cento)\b", vforn))
            unid_confiavel = not (peso_forn is not None or eh_caixa or eh_maco)
        d["unid_confiavel"] = unid_confiavel
        d["preco_vencedor_gran"] = preco_gran if unid_confiavel else None

        if not unid_confiavel:
            d["custo_pos_sem"] = None
            d["economia_sem"] = None
            d["economia_pct"] = 0.0
            d["r_em_jogo"] = 0.0
        else:
            d["custo_pos_sem"] = round((gs or 0) * preco_gran, 2)
            if d["custo_sem"] is not None:
                eco = round(d["custo_sem"] - d["custo_pos_sem"], 2)
                d["economia_sem"] = eco
                d["economia_pct"] = round(eco / d["custo_sem"] * 100, 1) if d["custo_sem"] else 0.0
            else:
                d["economia_sem"] = None
                d["economia_pct"] = 0.0
            d["r_em_jogo"] = max(0.0, d["economia_sem"] or 0.0)   # prioridade: só economia positiva

        # Validação MATRIZ vs CEASA-BA da semana: quando temos referência confiável
        # E o R$/kg do vencedor diverge muito (>40%), provável erro de peso/embalagem.
        # Tolerância larga (40%) pra evitar falso positivo do regional vs CEASA atacado;
        # mira o caso em que peso assumido da base CEASA tá errado.
        por_kg_vencedor = v.get("base") == "kg"
        if por_kg_vencedor and pc and pc > 0 and v.get("preco_norm"):
            razao = v["preco_norm"] / pc
            if razao > 1.4 or razao < 0.6:
                if "DIVERG_CEASA" not in d.get("alertas", []):
                    d.setdefault("alertas", []).append("DIVERG_CEASA")
                d["divergencia_ceasa_pct"] = round((razao - 1) * 100, 1)

        rec, jus = _recomendar(d, v, pc)
        d["recomendacao"] = rec
        d["justificativa"] = jus
        # "Por quê" só destaca quando o motivo vai ALÉM de preço mais barato (a premissa óbvia).
        # Preço-puro (COMPRAR/TROCAR/MANTER) => vazio. Exceções (negociar/conferir/feedback) => mostra.
        # PESO_ASSUMIDO_CEASA também força destaque (flag amarela visível).
        eh_excecao = (rec in ("NEGOCIAR", "CONFERIR", "ATENÇÃO") or bool(d.get("fb"))
                      or "PESO_ASSUMIDO_CEASA" in d.get("alertas", []))
        d["motivo_extra"] = jus if eh_excecao else ""

    resultado["decisoes"].sort(key=lambda d: -(d.get("r_em_jogo") or 0))
    resultado["perguntar_ceasa"] = perguntar
    return resultado


def _recomendar(d, v, preco_ceasa_v):
    forn = v["fornecedor"]
    fb = d.get("fb")
    # 1) conferência factual tem prioridade
    if "FORA_DA_BANDA" in d.get("alertas", []):
        return ("CONFERIR", f"Preço de {forn} destoa do histórico — conferir embalagem/valor antes de fechar.")
    # 1.2) peso da caixa foi assumido da base CEASA-BA (fornecedor não declarou) -> confirma com fornecedor
    if "PESO_ASSUMIDO_CEASA" in d.get("alertas", []):
        peso_kg = v.get("peso_kg_usado")
        peso_txt = f"{peso_kg:g}kg" if peso_kg else "kg padrão"
        return ("CONFERIR",
                f"{forn} cotou só preço da caixa; usei peso assumido CEASA-BA ({peso_txt}) "
                f"pra calcular R$/kg. Confirma o peso real com {forn} antes de fechar — divergência "
                f"vira pesagem real (registrar_pesagem.py).")
    # 1.3) divergência grande contra preço de referência CEASA da semana (matriz)
    if "DIVERG_CEASA" in d.get("alertas", []):
        return ("CONFERIR",
                f"R$/kg do vencedor ({forn}) diverge >40% da referência CEASA-BA da semana — "
                f"provavelmente embalagem/peso errado. Reconferir antes de fechar.")
    # 1.5) unidade do fornecedor não casa com a venda por unidade do Gran -> não dá pra projetar
    if not d.get("unid_confiavel", True):
        return ("CONFERIR",
                f"{forn} cota em {v.get('unidade_forn')}, mas o Gran vende por unidade — definir a conversão (peso do maço/dúzia) antes de comparar preço e economia.")
    # 2) feedback manual sobrepõe
    if fb and fb["veredito"] == "ruim":
        nota = f" ({fb['nota']})" if fb.get("nota") else ""
        return ("ATENÇÃO", f"Mais barato é {forn}, mas seu histórico marca ruim neste item{nota} — avalie outro.")
    canal_txt = " · buscar no CEASA (Micael)" if v["canal"] == "busca" else ""
    pref = " · fornecedor preferido" if (fb and fb["veredito"] == "preferido") else ""
    # 3) negociar quando fonte única e acima do atacado
    if d.get("fonte_unica") and preco_ceasa_v and v["preco_norm"] > preco_ceasa_v * 1.15:
        return ("NEGOCIAR",
                f"Só {forn} cotou (R$ {_p(v['preco_norm'])}); atacado CEASA está R$ {_p(preco_ceasa_v)} — use pra negociar.{canal_txt}")
    eco = d.get("economia_sem")
    # 4) cotação NÃO bate o custo atual do BI -> não há ganho em trocar por preço
    if eco is not None and eco <= 0:
        return ("MANTER",
                f"Melhor cotação ({forn} R$ {_p(v['preco_norm'])}/{v['base']}) não fica abaixo do seu custo atual — sem ganho em trocar por preço; conferir/negociar.{canal_txt}")
    # 5) troca recomendada (economia medida vs CUSTO ATUAL do BI)
    if d.get("troca_recomendada") and (eco or d.get("economia_vs_titular") or 0) > 0:
        val = eco if eco is not None else d.get("economia_vs_titular")
        return ("TROCAR",
                f"Trocar {d.get('titular_forn')}→{forn}: −R$ {_p(val,0)}/sem vs seu custo atual.{pref}{canal_txt}")
    # 6) manter titular (já é o vencedor)
    if d.get("titular_forn") and d.get("titular_forn") == forn:
        return ("MANTER", f"{forn} (titular do BI) já é o melhor preço da semana.{pref}{canal_txt}")
    return ("COMPRAR", f"Melhor preço com {forn} a R$ {_p(v['preco_norm'])}/{v['base']}.{pref}{canal_txt}")


def _p(v, dec=2):
    s = f"{float(v or 0):,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
