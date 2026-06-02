"""
revisao.py — Camada de revisão crítica de preços anômalos.

Filosofia (decisão Hugo 28/05/2026): preços muito fora da banda PODEM ser realidade
(fornecedor sistematicamente caro em um item), mas merecem checagem manual antes
de fechar o pedido. O motor não bloqueia; apenas marca e exibe na aba Alertas
do Mapa de Decisão, agrupado por motivo, com a referência usada (custo BI, CEASA,
mediana dos concorrentes) pra Hugo bater o olho e decidir.

Detectores (todos R$/kg, só itens 'ok' com vencedor):

  A. VENCEDOR_VS_BI       — vencedor > FATOR_BI × custo do BI
  B. VENCEDOR_VS_CEASA    — vencedor > FATOR_CEASA × "mais comum" CEASA-BA (kg)
  C. FORNECEDOR_OUTLIER   — algum candidato (mesmo não-vencedor) > FATOR_OUTLIER × mediana dos demais
                            (geralmente indica erro de embalagem/parse a corrigir)
  D. SALTO_VS_SEMANA      — vencedor variou > FATOR_SALTO contra mesmo fornecedor/item na semana anterior
  E. VENCEDOR_BAIXO_DEMAIS — vencedor < custo_BI/FATOR_BAIXO (suspeita de erro de unidade)

Fora do escopo aqui: itens sem cotação, fornecedor barrado, fonte única — já cobertos
no _panel_alertas existente.
"""
from __future__ import annotations
import csv
import statistics
from pathlib import Path

# Parâmetros — calibrados em 28/05/2026 com a primeira rodada da camada.
FATOR_BI = 2.0
FATOR_BAIXO = 2.0
FATOR_CEASA = 1.5
FATOR_OUTLIER = 2.0
FATOR_SALTO = 0.30

_SEV_ALTA = "alta"
_SEV_MEDIA = "media"


def _norm_simple(s: str) -> str:
    import re, unicodedata
    s = unicodedata.normalize("NFKD", str(s).lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", s).strip()


def _ceasa_kg_para_item(desc: str, ceasa_atual: dict):
    if not ceasa_atual:
        return None, None
    alvo = _norm_simple(desc)
    palavras = [p for p in alvo.split() if len(p) >= 3]
    if not palavras:
        return None, None
    for k, v in ceasa_atual.items():
        if v.get("comum_kg") is None:
            continue
        nk = _norm_simple(v.get("produto", k))
        if all(p in nk for p in palavras):
            return v["comum_kg"], v.get("label")
    return None, None


def _carregar_semana_anterior(historico_csv, semana_atual):
    if not historico_csv or not Path(historico_csv).exists():
        return {}
    semanas, dados = set(), {}
    with open(historico_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sem = row.get("semana", "")
            if not sem:
                continue
            semanas.add(sem)
            try:
                preco = float(row["preco_norm"])
            except (ValueError, TypeError):
                continue
            dados.setdefault(sem, {})[(int(row["cod"]), row["fornecedor"])] = preco
    semanas = sorted(semanas)
    if semana_atual not in semanas:
        return {}
    idx = semanas.index(semana_atual)
    if idx == 0:
        return {}
    return dados.get(semanas[idx - 1], {})


def detectar_anomalias(decisoes, bi, ceasa_atual, historico_csv=None, semana_atual=None):
    anteriores = _carregar_semana_anterior(historico_csv, semana_atual) if historico_csv else {}
    eventos = []

    for d in decisoes:
        if d.get("status") != "ok":
            continue
        cod = d["cod"]
        desc = d.get("desc", "")
        v = d.get("vencedor") or {}
        venc_forn = v.get("fornecedor")
        venc_preco = v.get("preco_norm")
        base = v.get("base", "kg")
        r_em_jogo = d.get("r_em_jogo") or 0
        custo_bi = ((bi.get(cod) or {}).get("custo_unit")) if bi else None

        if venc_preco and custo_bi and base == "kg":
            if venc_preco > FATOR_BI * custo_bi:
                eventos.append({
                    "cod": cod, "desc": desc, "tipo": "VENCEDOR_VS_BI",
                    "severidade": _SEV_ALTA,
                    "fornecedor": venc_forn, "preco_kg": round(venc_preco, 2),
                    "ref": round(custo_bi, 2), "ref_label": "custo BI",
                    "razao": round(venc_preco / custo_bi, 1),
                    "r_em_jogo": round(r_em_jogo, 2),
                    "motivo": f"Vencedor {venc_forn} a R$ {venc_preco:.2f}/kg = {venc_preco/custo_bi:.1f}× custo BI "
                              f"(R$ {custo_bi:.2f}/kg). Conferir embalagem/unidade ou negociar.",
                })
            elif venc_preco < custo_bi / FATOR_BAIXO:
                eventos.append({
                    "cod": cod, "desc": desc, "tipo": "VENCEDOR_BAIXO_DEMAIS",
                    "severidade": _SEV_ALTA,
                    "fornecedor": venc_forn, "preco_kg": round(venc_preco, 2),
                    "ref": round(custo_bi, 2), "ref_label": "custo BI",
                    "razao": round(venc_preco / custo_bi, 2),
                    "r_em_jogo": round(r_em_jogo, 2),
                    "motivo": f"Vencedor {venc_forn} a R$ {venc_preco:.2f}/kg = {venc_preco/custo_bi:.2f}× custo BI. "
                              f"Suspeita de unidade trocada (cabeça/dúzia × kg).",
                })

        if venc_preco and base == "kg":
            ceasa_kg, ceasa_label = _ceasa_kg_para_item(desc, ceasa_atual or {})
            if ceasa_kg and venc_preco > FATOR_CEASA * ceasa_kg:
                eventos.append({
                    "cod": cod, "desc": desc, "tipo": "VENCEDOR_VS_CEASA",
                    "severidade": _SEV_MEDIA,
                    "fornecedor": venc_forn, "preco_kg": round(venc_preco, 2),
                    "ref": round(ceasa_kg, 2), "ref_label": f"CEASA-BA ({ceasa_label or 'mais comum'})",
                    "razao": round(venc_preco / ceasa_kg, 1),
                    "r_em_jogo": round(r_em_jogo, 2),
                    "motivo": f"Vencedor {venc_forn} a R$ {venc_preco:.2f}/kg = {venc_preco/ceasa_kg:.1f}× CEASA-BA "
                              f"(R$ {ceasa_kg:.2f}/kg). Margem para negociar ou rotacionar.",
                })

        cands = d.get("candidatos") or {}
        precos_kg = {f: r.get("preco_norm") for f, r in cands.items()
                     if r.get("base") == "kg" and r.get("preco_norm")}
        if len(precos_kg) >= 3:
            for f, p in precos_kg.items():
                outros = [pp for ff, pp in precos_kg.items() if ff != f]
                if not outros:
                    continue
                med_outros = statistics.median(outros)
                if med_outros and p > FATOR_OUTLIER * med_outros:
                    eventos.append({
                        "cod": cod, "desc": desc, "tipo": "FORNECEDOR_OUTLIER",
                        "severidade": _SEV_ALTA if f == venc_forn else _SEV_MEDIA,
                        "fornecedor": f, "preco_kg": round(p, 2),
                        "ref": round(med_outros, 2),
                        "ref_label": f"mediana de {len(outros)} fornecedores",
                        "razao": round(p / med_outros, 1),
                        "r_em_jogo": round(r_em_jogo if f == venc_forn else 0, 2),
                        "motivo": f"{f} cotou R$ {p:.2f}/kg, {p/med_outros:.1f}× a mediana dos demais "
                                  f"(R$ {med_outros:.2f}/kg). Provável erro de embalagem/parse ou fornecedor caro.",
                    })

        if anteriores and venc_preco and base == "kg":
            ant = anteriores.get((cod, venc_forn))
            if ant and ant > 0:
                delta = (venc_preco - ant) / ant
                if abs(delta) > FATOR_SALTO:
                    direcao = "subiu" if delta > 0 else "caiu"
                    eventos.append({
                        "cod": cod, "desc": desc, "tipo": "SALTO_VS_SEMANA",
                        "severidade": _SEV_MEDIA,
                        "fornecedor": venc_forn, "preco_kg": round(venc_preco, 2),
                        "ref": round(ant, 2), "ref_label": "semana anterior (mesmo fornecedor)",
                        "razao": round(1 + delta, 2),
                        "r_em_jogo": round(r_em_jogo, 2),
                        "motivo": f"{venc_forn} {direcao} {abs(delta)*100:.0f}% vs semana anterior "
                                  f"(R$ {ant:.2f} → R$ {venc_preco:.2f}/kg). Confirmar se mudou tabela.",
                    })

    sev_ordem = {_SEV_ALTA: 0, _SEV_MEDIA: 1}
    eventos.sort(key=lambda e: (sev_ordem.get(e["severidade"], 9), -float(e.get("r_em_jogo") or 0)))
    return eventos


def resumo_por_tipo(eventos):
    out = {}
    for e in eventos:
        out[e["tipo"]] = out.get(e["tipo"], 0) + 1
    return out
