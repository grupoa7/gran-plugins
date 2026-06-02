"""
cotar.py — Orquestrador do comando /cotar.

Junta: tabelas dos fornecedores + CONTAGEM FLV + dicionário -> decisão ->
2 entregáveis (Mapa de Decisão HTML + Pedidos WhatsApp) + histórico de preços.

Uso (teste):
    python cotar.py --semana 2026-W21 --contagem <xlsx> \
        --donofrio <rtf> --shimizu <pdf> --docemel <pdf> --rml <csv> --out <dir>

Em produção o roteiro do SKILL.md aponta os arquivos da pasta da semana.
Tabela em IMAGEM (ex: RML) é transcrita pelo Claude para CSV antes
(ver references/parsing_imagem_rml.md).
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Resolve a pasta de DADOS do projeto ANTES de importar os módulos (eles leem o env no load).
# Dados mutáveis vivem no projeto (gravável); o pacote da skill é read-only quando instalado.
for _i, _a in enumerate(sys.argv):
    if _a == "--projeto" and _i + 1 < len(sys.argv):
        os.environ["COTACAO_DADOS"] = str(Path(sys.argv[_i + 1]) / "dados")

import flv_lib as L
import parsers as P
import engine as E
import outputs as O
import decisao as DEC
import revisao as REV


def montar_tabelas_auto(entradas_dir: str) -> list[dict]:
    """QUADRO FIXO: lê o roster (templates/fornecedores.json) e, p/ cada fornecedor,
    acha a tabela dele na pasta da semana (por palavra-chave do nome do arquivo) e
    parseia com o parser registrado. Assim o Mapa inclui TODOS os fornecedores ativos
    sem precisar passar flag a flag — basta dropar as tabelas na pasta."""
    reg = L.carregar_fornecedores()
    arquivos = sorted(Path(entradas_dir).iterdir())
    usados, tabelas, achados, faltando = set(), [], [], []
    for f in reg:
        kws = [k.lower() for k in f.get("arquivo_kw", [])]
        alvo = next((a for a in arquivos
                     if a not in usados and a.is_file()
                     and any(k in a.name.lower() for k in kws)), None)
        if not alvo:
            faltando.append(f["nome"])
            continue
        usados.add(alvo)
        parser = getattr(P, f["parser"])
        tab = parser(str(alvo), f["nome"]) if f["parser"] == "carregar_csv_fornecedor" else parser(str(alvo))
        tabelas.append(tab)
        achados.append(f"{f['nome']}<-{alvo.name}")
    print(f"[roster] achados: {', '.join(achados)}", file=sys.stderr)
    if faltando:
        print(f"[roster] SEM tabela nesta semana: {', '.join(faltando)}", file=sys.stderr)
    return tabelas


def montar_tabelas(args) -> list[dict]:
    if args.entradas:
        return montar_tabelas_auto(args.entradas)
    tabelas = []
    if args.donofrio:
        tabelas.append(P.parse_donofrio(args.donofrio))
    if args.shimizu:
        tabelas.append(P.parse_shimizu(args.shimizu))
    if args.docemel:
        tabelas.append(P.parse_docemel(args.docemel))
    if args.rml:
        tabelas.append(P.carregar_csv_fornecedor(args.rml, "RML"))
    if args.hortimix:
        tabelas.append(P.parse_hortimix(args.hortimix))
    if args.boacitrus:
        tabelas.append(P.parse_boacitrus(args.boacitrus))
    if args.igarashi:
        tabelas.append(P.parse_igarashi(args.igarashi))
    for csv_path, nome in (args.extra or []):
        tabelas.append(P.carregar_csv_fornecedor(csv_path, nome))
    return tabelas


def validar_fornecedores() -> list[str]:
    """Valida o QUADRO FIXO (templates/fornecedores.json): cada fornecedor precisa ter
    um parser existente e estar mapeado no dicionário. Evita 'fornecedor fantasma'
    (registrado mas que não parseia ou não casa COD). Devolve lista de avisos."""
    avisos = []
    for f in L.carregar_fornecedores():
        nome, parser = f.get("nome"), f.get("parser")
        if not parser or not hasattr(P, parser):
            avisos.append(f"{nome}: parser '{parser}' não existe em parsers.py")
        if nome not in L.DICIONARIO_FORNECEDORES:
            avisos.append(f"{nome}: sem coluna no dicionário (col_dict)")
    return avisos


def auditar(resultado: dict, bi: dict) -> dict:
    """Auditoria automática de integridade (roda toda cotação). Levanta:
      - unidade_conferir: vencedor em unidade não reconciliável c/ a venda do Gran
      - sem_custo_bi: item sem P.CUSTO no BI (não dá pra medir economia)
      - preco_suspeito: fornecedor com R$/kg > 2,5× o custo do BI (provável erro de embalagem/parse)
      - sem_ceasa: itens sem referência CEASA confiável."""
    a = {"unidade_conferir": [], "sem_custo_bi": [], "preco_suspeito": [], "sem_ceasa": 0}
    for d in resultado["decisoes"]:
        if d.get("status") != "ok":
            continue
        cod = d["cod"]; v = d.get("vencedor") or {}
        if not d.get("unid_confiavel", True):
            a["unidade_conferir"].append([cod, d.get("desc"), v.get("fornecedor"), v.get("unidade_forn")])
        if d.get("custo_sem") is None:
            a["sem_custo_bi"].append([cod, d.get("desc")])
        cu = (bi.get(cod) or {}).get("custo_unit") if bi else None
        if cu:
            for f, r in d.get("candidatos", {}).items():
                if r.get("base") == "kg" and r.get("preco_norm", 0) > 2.5 * cu:
                    a["preco_suspeito"].append([cod, d.get("desc"), f, r["preco_norm"], round(cu, 2)])
        if (d.get("ceasa") or {}).get("status") != "ok":
            a["sem_ceasa"] += 1
    return a


def carregar_exclusoes(path: str | None) -> dict:
    """CSV opcional: cod,fornecedor. Fornecedor barrado pra aquele item."""
    if not path or not Path(path).exists():
        return {}
    exc = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            exc.setdefault(int(row["cod"]), set()).add(row["fornecedor"].strip().upper())
    return exc


def salvar_historico(out_dir: Path, semana: str, resultado: dict):
    """Acumula preço por item×fornecedor×semana. Coluna corte_qualidade prevista (Fase 2)."""
    hist = out_dir.parent / "historico_precos.csv"
    novo = not hist.exists()
    with open(hist, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["semana", "cod", "desc", "fornecedor", "preco_norm",
                        "base", "canal", "corte_qualidade"])
        for d in resultado["decisoes"]:
            for forn, r in d.get("candidatos", {}).items():
                w.writerow([semana, d["cod"], d["desc"], forn, r["preco_norm"],
                            r["base"], r["canal"], ""])


def run(args):
    # O BI é a BÍBLIA do volume semanal (decisão Hugo 25/05): fica gravado em
    # <projeto>/dados/BI_Gran_atualizado.xlsx e é a base padrão da demanda. Só muda
    # quando um BI novo é enviado (substitui o arquivo). --bi explícito tem prioridade.
    bi_path = args.bi
    if not bi_path:
        _padrao = L.DADOS_DIR / "BI_Gran_atualizado.xlsx"
        if _padrao.exists():
            bi_path = str(_padrao)
    if not bi_path and not args.contagem:
        raise SystemExit("Erro: sem BI gravado e sem --bi/--contagem. Envie o BI ou informe a base.")
    out = Path(args.out)
    (out).mkdir(parents=True, exist_ok=True)

    # Validação do QUADRO FIXO (fornecedor sem parser / sem coluna no dicionário).
    for aviso in validar_fornecedores():
        print(f"[quadro-fixo] AVISO: {aviso}", file=sys.stderr)

    dic = L.carregar_dicionario()
    # Base da DEMANDA: o BI (MÉDIA FINAL × 7) é a fonte oficial (decisão 25/05).
    # O pedido semanal NÃO é mais base de demanda; quando fornecido (--contagem),
    # serve só como titular (FORNECEDOR mais atual que o do BI).
    vendas_bi = None
    bi = {}
    if bi_path:
        bi = L.carregar_bi(bi_path)
        titular_pedido = {}
        if args.contagem:
            for it in L.carregar_contagem(args.contagem, somente_a_pedir=False):
                if it.get("fornecedor_titular"):
                    titular_pedido[it["cod"]] = it["fornecedor_titular"]
        contagem, vendas_bi = L.demanda_do_bi(bi, dic, titular_pedido)
    else:
        contagem = L.carregar_contagem(args.contagem)
    tabelas = montar_tabelas(args)

    # feedback do Hugo (produto×fornecedor): 'evitar' vira exclusão/banimento
    feedback = DEC.carregar_feedback()
    excecoes_ceasa = DEC.carregar_excecoes_ceasa()
    exclusoes = carregar_exclusoes(args.exclusoes)
    for cod, fset in DEC.evitados_para_exclusoes(feedback).items():
        exclusoes.setdefault(cod, set()).update(fset)
    banir = {forn for (cod, forn), v in feedback.items() if cod is None and v["veredito"] == "evitar"}

    resultado = E.cotar(contagem, tabelas, dic, exclusoes, banir=banir)
    validades = {t["fornecedor"]: t.get("validade") for t in tabelas}

    # entregáveis
    if vendas_bi is not None:
        vendas = vendas_bi          # giro/preço/custo vêm do BI
    else:
        try:
            vendas = L.carregar_vendas()
        except Exception:
            vendas = None
    import ceasa_temporal as CT
    try:
        ceasa_atual = CT.carregar_ceasa_atual()
        ceasa_series = CT.carregar_series()
        ceasa_datas = CT.datas_trimestre()
    except Exception:
        ceasa_atual, ceasa_series, ceasa_datas = {}, {}, []

    # enriquecer: match CEASA c/ confiança, R$ em jogo, recomendação, feedback
    resultado = DEC.enriquecer(resultado, vendas=vendas, ceasa_atual=ceasa_atual,
                               ceasa_series=ceasa_series, feedback=feedback, excecoes=excecoes_ceasa)
    eventos_revisao = REV.detectar_anomalias(
        resultado["decisoes"], bi, ceasa_atual,
        historico_csv=out.parent / "historico_precos.csv",
        semana_atual=args.semana,
    )
    mapa = O.gerar_mapa_html(resultado, validades, args.semana, vendas=vendas,
                             periodo=args.periodo or "", ceasa_atual=ceasa_atual,
                             ceasa_series=ceasa_series, ceasa_datas=ceasa_datas,
                             revisao=eventos_revisao)
    (out / "mapa_decisao.html").write_text(mapa, encoding="utf-8")

    pedidos = O.gerar_pedidos_whatsapp(resultado, args.semana)
    ped_dir = out / "pedidos_whatsapp"
    ped_dir.mkdir(exist_ok=True)
    for forn, txt in pedidos.items():
        nome = forn.lower().replace(" ", "_").replace("/", "_")
        (ped_dir / f"pedido_{nome}.txt").write_text(txt, encoding="utf-8")

    salvar_historico(out, args.semana, resultado)

    # resumo de execução
    dec = resultado["decisoes"]
    ok = [d for d in dec if d["status"] == "ok"]
    resumo = {
        "semana": args.semana,
        "itens_demanda": len(dec),
        "itens_cotados": len(ok),
        "sem_cotacao": len([d for d in dec if d["status"] != "ok"]),
        "cherry_multifonte": len([d for d in ok if d["n_fontes"] >= 2]),
        "trocas_vs_titular": len([d for d in ok if d.get("troca_recomendada")]),
        # economia possível = soma das economias POSITIVAS vs custo atual do BI (onde a cotação ganha)
        "economia_estimada": round(sum(d["economia_sem"] for d in ok if (d.get("economia_sem") or 0) > 0), 2),
        "custo_atual_total": round(sum(d.get("custo_sem") or 0 for d in ok), 2),
        "custo_pos_total": round(sum(d.get("custo_pos_sem") or 0 for d in ok), 2),
        "fornecedores_acionados": sorted({d["vencedor"]["fornecedor"] for d in ok}),
        "nao_casados_por_fornecedor": {k: len(v) for k, v in resultado["nao_casados"].items()},
        "ceasa_a_confirmar": len(resultado.get("perguntar_ceasa", [])),
        "r_em_jogo_total": round(sum(d.get("r_em_jogo") or 0 for d in ok), 2),
    }
    # AUDITORIA automática de integridade (grava audit.json + resumo no stderr).
    audit = auditar(resultado, bi)
    audit_resumo = {k: (len(v) if isinstance(v, list) else v) for k, v in audit.items()}
    resumo["auditoria"] = audit_resumo
    (out / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[auditoria] unidade_conferir={audit_resumo['unidade_conferir']} "
          f"sem_custo_bi={audit_resumo['sem_custo_bi']} "
          f"preco_suspeito={audit_resumo['preco_suspeito']} "
          f"sem_ceasa={audit_resumo['sem_ceasa']}", file=sys.stderr)
    if audit["preco_suspeito"]:
        print("[auditoria] PREÇOS SUSPEITOS (R$/kg > 2,5× custo BI — conferir embalagem/parse):", file=sys.stderr)
        for cod, desc, f, p, cu in audit["preco_suspeito"][:15]:
            print(f"    COD {cod} {desc} · {f} R$ {p}/kg vs custo BI R$ {cu}", file=sys.stderr)
    # REVISÃO CRÍTICA — serializa o resultado calculado acima (decisão Hugo 28/05/2026).
    (out / "revisao.json").write_text(
        json.dumps(eventos_revisao, ensure_ascii=False, indent=2), encoding="utf-8")
    resumo["revisao_total"] = len(eventos_revisao)
    resumo["revisao_por_tipo"] = REV.resumo_por_tipo(eventos_revisao)
    if eventos_revisao:
        print(f"[revisão] {len(eventos_revisao)} item(ns) fora da banda → ver aba Alertas:", file=sys.stderr)
        for e in eventos_revisao[:8]:
            print(f"    [{e['severidade']}] {e['tipo']}: COD {e['cod']} {e['desc']} · {e['fornecedor']} "
                  f"R$ {e['preco_kg']:.2f}/kg vs {e['ref_label']} R$ {e['ref']:.2f}", file=sys.stderr)

        (out / "perguntar_ceasa.json").write_text(
        json.dumps(resultado.get("perguntar_ceasa", []), ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return resumo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semana", required=True)
    ap.add_argument("--bi", help="BI do Gran (aba APOIO PEDIDO) — base oficial da demanda (MÉDIA FINAL × 7)")
    ap.add_argument("--contagem", help="Pedido FLV — opcional; só p/ titular (FORNECEDOR). NÃO é mais base de demanda")
    ap.add_argument("--donofrio"); ap.add_argument("--shimizu")
    ap.add_argument("--docemel"); ap.add_argument("--rml")
    ap.add_argument("--hortimix"); ap.add_argument("--boacitrus")
    ap.add_argument("--igarashi")
    ap.add_argument("--entradas", help="pasta da semana com as tabelas; auto-carrega TODO o "
                    "quadro fixo (templates/fornecedores.json) cuja tabela for encontrada")
    ap.add_argument("--exclusoes")
    ap.add_argument("--periodo", default="")
    ap.add_argument("--projeto", help="pasta do projeto (dados mutáveis em <projeto>/dados)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", nargs=2, action="append", metavar=("CSV", "NOME"))
    run(ap.parse_args())


if __name__ == "__main__":
    main()
