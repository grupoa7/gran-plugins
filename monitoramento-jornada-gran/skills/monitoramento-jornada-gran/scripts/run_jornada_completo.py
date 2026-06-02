#!/usr/bin/env python3
"""
run_jornada_completo.py — Orquestrador v3.3 do pipeline de Monitoramento de Jornada.

Roda do passo 2 ao 8 da skill em sequência. O passo 1 (EXTRAÇÃO via Chrome MCP)
fica fora — Claude faz via tools de navegação e entrega o JSON do Cartão de Ponto
em `cartao_ponto_S{N}_2026.json` na pasta do projeto.

Uso:
    python3 run_jornada_completo.py \\
        --projeto "/path/[GRAN RH] Monitoramento de jornada" \\
        --cartao cartao_ponto_S20_2026.json \\
        --escala "escalas/ESCALA GRAN_MAIO26_REV001.pdf" \\
        --semana-id S20 \\
        --periodo-ini 2026-05-06 \\
        --periodo-fim 2026-05-12 \\
        [--no-publish]

Etapas (cada uma idempotente):
  2. Parsear escala mensal (PDF)
  3. Match RHID ↔ Escala (token-based)
  4. Aplicar regras + detector REG-S1..S6
  5. Persistir histórico (JSON semana + CSV cumulativo)
  6. Gerar HTML v3.2 → relatorios/
  7. Copiar staging → repo_publico_pra_subir/
  8. Git push origin/main (a menos que --no-publish)

Requer .env na pasta do projeto com:
  GITHUB_PAT=github_pat_...
  GITHUB_REPO=grupoa7/gran-rh-monitoramento
"""
import argparse, json, os, sys, re, csv, subprocess, shutil, unicodedata
from datetime import datetime
from pathlib import Path


def log(msg, level="INFO"):
    sym = {"INFO": "·", "OK": "✓", "WARN": "⚠", "ERR": "✗", "STEP": "▶"}.get(level, "·")
    print(f"  {sym} {msg}", file=sys.stderr)


def carregar_env(projeto):
    env_path = Path(projeto) / ".env"
    if not env_path.exists():
        return {}
    env = {}
    for line in env_path.read_text().splitlines():
        if line.strip() and not line.strip().startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def norm_token(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z\s]", " ", s)
    return [t for t in s.split() if len(t) > 1]


def match_rhid_escala(nomes_rhid, nomes_escala):
    """Match por primeiro nome com prefix-5 + interseção de tokens."""
    mapping = {}
    for nr in nomes_rhid:
        tr = norm_token(nr)
        if not tr: continue
        primeiro_r = tr[0]
        candidatos = []
        for ne in nomes_escala:
            te = norm_token(ne)
            if not te: continue
            primeiro_e = te[0]
            if primeiro_r == primeiro_e or (len(primeiro_r) > 4 and len(primeiro_e) > 4 and primeiro_r[:5] == primeiro_e[:5]):
                inter = set(tr) & set(te)
                candidatos.append((ne, len(inter)))
        if candidatos:
            candidatos.sort(key=lambda x: -x[1])
            mapping[nr] = candidatos[0][0]
    return mapping


def parsear_alteracoes_rhid(alts):
    JUST_MAP = {
        "atestado de comparecimento": "Atestado de Comparecimento",
        "atestado médico": "Atestado Médico",
        "férias": "Férias",
        "folga habilitada": "Folga",
        "folga": "Folga",
        "feriado": "Feriado",
        "folga feriado": "Folga Feriado",
        "folga domingo": "Folga Domingo Trabalhado",
        "licença maternidade": "Licença Maternidade",
        "licença paternidade": "Licença Paternidade",
        "suspensão": "Suspensão",
    }
    just = {}
    for a in alts:
        s = a.lower()
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})", a)
        if not m: continue
        d, mn, y = m.groups()
        iso = f"{y}-{mn}-{d}"
        for k, v in JUST_MAP.items():
            if k in s:
                just[iso] = v
                break
        else:
            if "habilitada" in s:
                just[iso] = "Folga"
    return just


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projeto", required=True, help="Pasta raiz do projeto Monitoramento de Jornada")
    ap.add_argument("--cartao", required=True, help="JSON do Cartão de Ponto (nome do arquivo dentro de --projeto)")
    ap.add_argument("--escala", required=True, help="PDF da escala mensal (path relativo a --projeto)")
    ap.add_argument("--semana-id", required=True, help="Ex: S20")
    ap.add_argument("--periodo-ini", required=True, help="YYYY-MM-DD")
    ap.add_argument("--periodo-fim", required=True, help="YYYY-MM-DD")
    ap.add_argument("--no-publish", action="store_true", help="Pular git push no final")
    ap.add_argument("--suspensos", default="", help="Nomes separados por vírgula (escala mas não monitorar)")
    args = ap.parse_args()

    projeto = Path(args.projeto).resolve()
    if not projeto.is_dir():
        log(f"Projeto inexistente: {projeto}", "ERR"); sys.exit(1)

    scripts_dir = projeto / ".claude/skills/monitoramento-jornada-gran/scripts"
    sys.path.insert(0, str(scripts_dir))
    from parsear_escala import parsear_escala_v2
    from aplicar_regras import processar_colaborador
    from detector_suspeitos import detectar_suspeitos

    env = carregar_env(projeto)
    out_dir = projeto / f"outputs_{args.semana_id.lower()}"
    out_dir.mkdir(exist_ok=True)

    suspensos = [s.strip() for s in args.suspensos.split(",") if s.strip()]

    # ===== Passo 2: Parsear escala =====
    log(f"Passo 2 — Parseando escala {args.escala}", "STEP")
    escala_raw, setor_de = parsear_escala_v2(str(projeto / args.escala))
    log(f"Escala: {len(escala_raw)} colaboradores, {len(set(setor_de.values()))} setores", "OK")

    # ===== Passo 3: Carregar Cartão e fazer matching =====
    log(f"Passo 3 — Carregando Cartão {args.cartao} + match RHID↔Escala", "STEP")
    cartao = json.load(open(projeto / args.cartao))
    nomes_rhid = sorted(set(v["nome"] for v in cartao.values()))
    nomes_escala = sorted(escala_raw.keys())
    mapping = match_rhid_escala(nomes_rhid, nomes_escala)
    nao_no_rhid = [n for n in nomes_escala if n not in set(mapping.values()) and n not in suspensos]
    log(f"Match: {len(mapping)}/{len(nomes_rhid)} RHID. Escala sem RHID: {nao_no_rhid}", "OK" if len(mapping) == len(nomes_rhid) else "WARN")

    # ===== Passo 4: Aplicar regras + detector =====
    log("Passo 4 — Aplicando regras + detector REG-S1..S6", "STEP")
    resultados = {}
    suspeitos_total = []
    for k, c in cartao.items():
        nome_rhid = c["nome"]
        nome_esc = mapping.get(nome_rhid)
        if not nome_esc:
            log(f"Ignorando {nome_rhid} (sem match)", "WARN")
            continue
        setor = setor_de.get(nome_esc, "?")
        dias_proc = []
        for d in c["dias"]:
            data_br = d["dia"].split(" - ")[0]
            dd, mm, yy = data_br.split("/")
            iso = f"{yy}-{mm}-{dd}"
            esc_dia = escala_raw.get(nome_esc, {}).get(iso)
            if not esc_dia:
                tipo, val = "DESCONHECIDO", None
            else:
                tipo = esc_dia[0]
                val = tuple(esc_dia[1]) if isinstance(esc_dia[1], (list, tuple)) else esc_dia[1]
            batidas = [d.get("ent1", ""), d.get("sai1", ""), d.get("ent2", ""), d.get("sai2", ""), d.get("ent3", ""), d.get("sai3", "")]
            dias_proc.append({"data": iso, "tipo_escala": tipo, "valor_escala": val, "batidas": batidas})

        just = parsear_alteracoes_rhid(c.get("alteracoes", []))
        regime_estagio = (nome_esc.lower() == "alana")
        r = processar_colaborador(nome_esc, setor, dias_proc, just, regime_estagio)
        r["nome"] = nome_esc; r["nome_rhid"] = nome_rhid
        r["alteracoes"] = c.get("alteracoes", [])
        r["suspeitos"] = detectar_suspeitos(nome_esc, setor, dias_proc)
        suspeitos_total.extend(r["suspeitos"])
        resultados[nome_esc] = r

    crit = sum(1 for r in resultados.values() if r["status"] == "crit")
    alert = sum(1 for r in resultados.values() if r["status"] == "alert")
    ok = sum(1 for r in resultados.values() if r["status"] == "ok")
    log(f"Status: {crit} CRIT · {alert} ALERT · {ok} OK · {len(resultados)} total", "OK")

    # ===== Passo 5: Persistir histórico =====
    log("Passo 5 — Persistindo JSON + CSV cumulativo", "STEP")
    kpis = {
        "total_ativos_indicador": len(resultados),
        "criticos": crit, "alerta": alert, "ok": ok,
        "falta_seca_dias": sum(r["contadores"]["falta_seca"] for r in resultados.values()),
        "atrasos": sum(r["contadores"]["atraso"] for r in resultados.values()),
        "saida_fora": sum(r["contadores"]["saida_fora"] for r in resultados.values()),
        "hora_extra": sum(r["contadores"]["hora_extra"] for r in resultados.values()),
        "janela_proibida": sum(r["contadores"]["janela_proib"] for r in resultados.values()),
        "pulou_intervalo": sum(r["contadores"]["pulou_interv"] for r in resultados.values()),
        "intervalo_curto": sum(r["contadores"]["interv_curto"] for r in resultados.values()),
        "intervalo_longo": sum(r["contadores"]["interv_longo"] for r in resultados.values()),
        "incoerente": sum(r["contadores"]["incoerente"] for r in resultados.values()),
    }
    colabs_ind = [{
        "nome": n, "setor": r["setor"], "status": r["status"].upper(),
        "contadores": r["contadores"], "alteracoes": r.get("alteracoes", []),
    } for n, r in resultados.items()]

    hist = {
        "semana": f"{args.semana_id}/2026",
        "periodo": f"{args.periodo_ini[8:10]}/{args.periodo_ini[5:7]}/{args.periodo_ini[0:4]} a {args.periodo_fim[8:10]}/{args.periodo_fim[5:7]}/{args.periodo_fim[0:4]}",
        "periodo_iso": {"ini": args.periodo_ini, "fim": args.periodo_fim},
        "gerado_em": datetime.now().isoformat(),
        "skill_versao": "v3.3",
        "rodada": 1,
        "kpis_indicador": kpis,
        "tratativa_rh_resumo": {"total_casos": len([s for s in suspeitos_total if s.get("tratativa_rh")]), "por_severidade": {"CRITICO": 0, "MEDIO": 0, "ALERTA": 0, "INFO": 0}},
        "colaboradores_indicador": colabs_ind,
        "casos_tratativa_rh": [s for s in suspeitos_total if s.get("tratativa_rh")],
        "suspensos": suspensos,
        "excluidos_rhid": [n for n in nao_no_rhid if n not in suspensos],
    }
    hist_path = projeto / "historico" / f"{args.periodo_ini}_a_{args.periodo_fim}.json"
    hist_path.parent.mkdir(exist_ok=True)
    hist_path.write_text(json.dumps(hist, ensure_ascii=False, indent=2))
    log(f"JSON salvo: {hist_path.name}", "OK")

    # CSV cumulativo
    csv_path = projeto / "historico" / "historico_jornada.csv"
    fields = ["semana", "periodo", "nome", "setor", "status", "falta_seca", "falta_justificada", "atraso", "saida_fora", "hora_extra", "interv_curto", "interv_longo", "janela_proib", "pulou_interv", "incoerente", "trabalhou_ferias"]
    existing = []
    if csv_path.exists():
        with csv_path.open() as f:
            existing = [row for row in csv.DictReader(f) if row.get("semana") != hist["semana"]]
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in existing:
            w.writerow({k: row.get(k, "") for k in fields})
        for n, r in resultados.items():
            w.writerow({"semana": hist["semana"], "periodo": hist["periodo"], "nome": n, "setor": r["setor"], "status": r["status"].upper(), **r["contadores"]})
    log(f"CSV atualizado: {csv_path.name}", "OK")

    # ===== Passo 6: Gerar HTML =====
    log("Passo 6 — Gerando HTML v3.2/v3.3", "STEP")
    # Salvar resultados_v31 com nome_display
    arr = []
    for n, r in resultados.items():
        parts = n.split()
        r["nome_display"] = f"{parts[0]} {parts[-1]}" if len(parts) >= 2 else n
        r["nome_show"] = n
        r["restrito"] = r["setor"] in {"ENCARREGADOS", "OPERADOR DE LOJA", "OPERADOR DE CAIXAS"}
        r["suspenso"] = False
        r["tratativa_rh"] = False
        r["casos_suspeitos"] = r.pop("suspeitos", [])
        # status pra lowercase nos dias
        for d in r.get("dias", []):
            if "status" in d: d["status"] = d["status"].lower()
        arr.append(r)
    resultados_doc = {
        "skill_versao": "v3.3", "rodada": 1,
        "periodo_iso": {"ini": args.periodo_ini, "fim": args.periodo_fim},
        "periodo_ini": f"{args.periodo_ini[8:10]}/{args.periodo_ini[5:7]}/{args.periodo_ini[0:4]}",
        "periodo_fim": f"{args.periodo_fim[8:10]}/{args.periodo_fim[5:7]}/{args.periodo_fim[0:4]}",
        "resultados": arr,
    }
    res_path = out_dir / "resultados_v31.json"
    res_path.write_text(json.dumps(resultados_doc, ensure_ascii=False, indent=2))

    # Rodar gerar_html via env vars
    rel_path = projeto / "relatorios" / f"Relatorio_Jornada_Semanal_{args.semana_id}_2026.html"
    rel_path.parent.mkdir(exist_ok=True)
    env_html = {**os.environ,
                "JORNADA_PROJECT_DIR": str(projeto),
                "JORNADA_HIST_DIR": str(projeto / "historico"),
                "JORNADA_SEMANA_ARQUIVO": hist_path.name,
                "JORNADA_RESULTADOS_FILE": str(res_path)}
    with rel_path.open("w") as fh:
        ret = subprocess.run(["python3", str(scripts_dir / "gerar_html.py")], stdout=fh, env=env_html)
    if ret.returncode != 0:
        log(f"gerar_html.py falhou: exit {ret.returncode}", "ERR"); sys.exit(2)
    log(f"HTML salvo: {rel_path.name} ({rel_path.stat().st_size} bytes)", "OK")

    # ===== Passo 7: Atualizar staging =====
    log("Passo 7 — Atualizando staging repo_publico_pra_subir/", "STEP")
    staging = projeto / "repo_publico_pra_subir"
    staging.mkdir(exist_ok=True)
    shutil.copy(rel_path, staging / f"relatorio_{args.semana_id}_2026.html")
    shutil.copy(rel_path, staging / "index.html")
    # README — patchar referências da semana
    readme = staging / "README.md"
    if readme.exists():
        txt = readme.read_text()
        txt = re.sub(r"S\d+/2026", f"{args.semana_id}/2026", txt)
        # Atualizar próxima rodada (+7 dias)
        prox = datetime.strptime(args.periodo_fim, "%Y-%m-%d")
        from datetime import timedelta as _td
        prox = prox + _td(days=8)
        txt = re.sub(r"Próxima rodada:\s*\d{2}/\d{2}/2026", f"Próxima rodada: {prox.strftime('%d/%m/%Y')}", txt)
        readme.write_text(txt)
    log("Staging OK", "OK")

    # ===== Passo 8: Git push =====
    if args.no_publish:
        log("Passo 8 — pulando push (--no-publish)", "WARN")
        return

    log("Passo 8 — Publicando no GitHub Pages", "STEP")
    pat = env.get("GITHUB_PAT")
    repo = env.get("GITHUB_REPO", "grupoa7/gran-rh-monitoramento")
    if not pat:
        log("GITHUB_PAT não está em .env — pulando push", "ERR"); sys.exit(3)

    tmpdir = Path(f"/tmp/grm_publish_{args.semana_id.lower()}")
    if tmpdir.exists(): shutil.rmtree(tmpdir)
    url = f"https://x-access-token:{pat}@github.com/{repo}.git"
    subprocess.run(["git", "clone", url, str(tmpdir)], check=True, capture_output=True)

    # Copiar arquivos
    for fname in ["index.html", "README.md", f"relatorio_{args.semana_id}_2026.html"]:
        src = staging / fname
        if src.exists():
            shutil.copy(src, tmpdir / fname)

    subprocess.run(["git", "-C", str(tmpdir), "config", "user.email", "hugo@grupoa7.com.br"], check=True)
    subprocess.run(["git", "-C", str(tmpdir), "config", "user.name", "Hugo Gusmao (via Claude/Cowork)"], check=True)
    subprocess.run(["git", "-C", str(tmpdir), "add", "-A"], check=True)
    diff = subprocess.run(["git", "-C", str(tmpdir), "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        log("Nada a publicar (sem mudanças)", "WARN")
    else:
        commit_msg = f"{args.semana_id}/2026 — Monitoramento de Jornada {hist['periodo']}\n\nGerado via Cowork/Claude. Status: {crit} CRIT · {alert} ALERT · {ok} OK · {len(resultados)} total."
        subprocess.run(["git", "-C", str(tmpdir), "commit", "-m", commit_msg], check=True)
        push = subprocess.run(["git", "-C", str(tmpdir), "push", "origin", "main"], capture_output=True, text=True)
        if push.returncode != 0:
            log(f"Push falhou: {push.stderr}", "ERR"); sys.exit(4)
        log(f"Publicado! Aguarde ~30-60s e checar https://grupoa7.github.io/gran-rh-monitoramento/", "OK")

    shutil.rmtree(tmpdir, ignore_errors=True)
    log("Pipeline concluído.", "OK")


if __name__ == "__main__":
    main()
