#!/usr/bin/env python3
"""
relatorio_rodada.py — Status consolidado da rodada de pedido de tabela
(skill cotacao-flv-gran — comando /cotacao-status).

Lê o manifest da rodada e produz um relatório agregando:
  - Quem entregou (com formato e tempo de resposta)
  - Quem está pendente (com último slot disparado)
  - Quem furou (todos os slots disparados sem resposta após 08h)
  - Quem teve erro técnico (favorito não encontrado, app travou, etc)
  - Métricas: taxa de entrega, tempo médio de resposta, slots mais eficientes

Formatos de saída:
  - texto: relatório compacto pra notificar Hugo no chat
  - json: dump completo do snapshot
  - html: relatório visual (futuro — fica como TODO)

Fluxo típico:

  $ python scripts/relatorio_rodada.py texto
  # Imprime relatório compacto:
  #   📊 Rodada 2026-06-01 (Seg) — 03h-08h
  #   ✅ Entregaram: 16/19 (84%)
  #      Tempo médio de resposta: 42 min
  #   ⚠️ Furaram: 2 (HORTIMIX, ALINE)
  #   ❌ Erros: 1 (BRAS_IMPORT: favorito_nao_encontrado)
  #
  #   Por slot:
  #   03h: 8 entregas (mais eficiente)
  #   04h: 5 entregas
  #   05h: 2 entregas
  #   06h: 1 entrega
  #   07h: 0 entregas

  $ python scripts/relatorio_rodada.py json --rodada 2026-06-01
  # Dump completo do snapshot
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import envio_lib as L


# --------------------------------------------------------------------------- #
# Análise do snapshot
# --------------------------------------------------------------------------- #

def analisar_rodada(rodada: str) -> dict:
    """Calcula métricas agregadas a partir do snapshot."""
    snap = L.agregar_manifest(rodada)
    estados = snap.get("fornecedores", {})

    entregaram = []
    pendentes = []
    furaram = []
    com_erro = []

    tempos_resposta_min = []
    slot_to_entregas: dict[str, int] = {s: 0 for s in L.SLOTS}

    for nome, st in estados.items():
        status = st.get("status")
        if status == "recebido":
            resp = st.get("resposta") or {}
            t_disparo = st.get("ultimo_disparo_ts")
            t_resp = resp.get("ts")
            tempo_min = None
            if t_disparo and t_resp:
                try:
                    dt_disp = _dt.datetime.fromisoformat(t_disparo)
                    dt_resp = _dt.datetime.fromisoformat(t_resp)
                    tempo_min = (dt_resp - dt_disp).total_seconds() / 60.0
                    if tempo_min >= 0:
                        tempos_resposta_min.append(tempo_min)
                except (ValueError, TypeError):
                    pass
            slots_disp = st.get("slots_disparados", [])
            slot_origem = slots_disp[0] if slots_disp else "?"
            if slot_origem in slot_to_entregas:
                slot_to_entregas[slot_origem] += 1
            entregaram.append({
                "fornecedor": nome,
                "formato": resp.get("formato"),
                "tempo_resposta_min": round(tempo_min, 1) if tempo_min is not None else None,
                "slot_disparo": slot_origem,
                "alvo_tipo": st.get("ultimo_alvo_tipo"),
            })
        elif status == "furou":
            furaram.append({
                "fornecedor": nome,
                "slots_disparados": st.get("slots_disparados", []),
                "ultimo_alvo_tipo": st.get("ultimo_alvo_tipo"),
            })
        elif status == "erro":
            com_erro.append({
                "fornecedor": nome,
                "erros": st.get("erros", []),
            })
        else:  # pendente ou sem_disparo
            pendentes.append({
                "fornecedor": nome,
                "slots_disparados": st.get("slots_disparados", []),
                "ultimo_disparo_ts": st.get("ultimo_disparo_ts"),
            })

    total_ativos = sum(1 for _ in L.carregar_fornecedores_envio())
    tempo_medio = (sum(tempos_resposta_min) / len(tempos_resposta_min)) if tempos_resposta_min else None
    taxa_entrega = (len(entregaram) / total_ativos) if total_ativos else 0.0

    # Detecta slots que deviam ter rodado mas não rodaram (Claude desktop
    # provavelmente estava fechado naquele horário)
    perdidos = L.slots_perdidos(rodada)

    return {
        "rodada": rodada,
        "total_ativos": total_ativos,
        "entregaram": entregaram,
        "pendentes": pendentes,
        "furaram": furaram,
        "com_erro": com_erro,
        "taxa_entrega": taxa_entrega,
        "tempo_medio_resposta_min": round(tempo_medio, 1) if tempo_medio is not None else None,
        "slot_to_entregas": slot_to_entregas,
        "slots_perdidos": perdidos,
    }


# --------------------------------------------------------------------------- #
# Renderizadores
# --------------------------------------------------------------------------- #

def render_texto(analise: dict) -> str:
    rodada = analise["rodada"]
    try:
        dt_rodada = _dt.datetime.strptime(rodada, "%Y-%m-%d")
        dia_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"][dt_rodada.weekday()]
        rodada_str = f"{rodada} ({dia_semana})"
    except (ValueError, TypeError):
        rodada_str = rodada

    n_entregaram = len(analise["entregaram"])
    total = analise["total_ativos"]
    pct = analise["taxa_entrega"] * 100
    tempo_med = analise["tempo_medio_resposta_min"]

    linhas = [
        f"📊 Rodada {rodada_str} — janela 03h-08h",
        "",
        f"✅ Entregaram: {n_entregaram}/{total} ({pct:.0f}%)",
    ]
    if tempo_med is not None:
        linhas.append(f"   Tempo médio de resposta: {tempo_med:.0f} min")

    # Alerta de slots perdidos (Claude desktop fechado naquele horário)
    perdidos = analise.get("slots_perdidos", [])
    if perdidos:
        linhas.append("")
        linhas.append(f"🚨 Slots NÃO executados ({len(perdidos)}): {', '.join(perdidos)}")
        linhas.append("   Provavelmente Claude desktop estava fechado nesse horário.")
        linhas.append("   Cobertura perdida — fornecedores receberam menos lembretes.")

    if analise["furaram"]:
        nomes = ", ".join(f["fornecedor"] for f in analise["furaram"])
        linhas.append("")
        linhas.append(f"⚠️ Furaram ({len(analise['furaram'])}): {nomes}")

    if analise["com_erro"]:
        linhas.append("")
        linhas.append(f"❌ Erros ({len(analise['com_erro'])}):")
        for e in analise["com_erro"]:
            motivos = ", ".join(er.get("motivo", "?") for er in e["erros"])
            linhas.append(f"   - {e['fornecedor']}: {motivos}")

    if analise["pendentes"]:
        linhas.append("")
        linhas.append(f"⏳ Pendentes ({len(analise['pendentes'])}):")
        for p in analise["pendentes"][:5]:
            slots = ",".join(p["slots_disparados"]) or "nenhum disparo"
            linhas.append(f"   - {p['fornecedor']} (slots: {slots})")
        if len(analise["pendentes"]) > 5:
            linhas.append(f"   ... e mais {len(analise['pendentes']) - 5}")

    linhas.append("")
    linhas.append("Por slot (entregas que vieram de cada slot inicial):")
    for slot in L.SLOTS:
        n = analise["slot_to_entregas"].get(slot, 0)
        linhas.append(f"   {slot}: {n} entregas")

    return "\n".join(linhas)


def render_json(analise: dict) -> str:
    return json.dumps(analise, ensure_ascii=False, indent=2)


def render_markdown(analise: dict) -> str:
    """Markdown pra Hugo abrir como nota."""
    rodada = analise["rodada"]
    n_e = len(analise["entregaram"])
    total = analise["total_ativos"]
    pct = analise["taxa_entrega"] * 100

    out = [f"# Rodada {rodada}", ""]
    out.append(f"**Taxa de entrega:** {n_e}/{total} ({pct:.0f}%)")
    if analise["tempo_medio_resposta_min"]:
        out.append(f"**Tempo médio de resposta:** {analise['tempo_medio_resposta_min']:.0f} min")
    out.append("")

    # Alerta de slots perdidos
    perdidos = analise.get("slots_perdidos", [])
    if perdidos:
        out.append(f"> 🚨 **Slots NÃO executados:** {', '.join(perdidos)} — provavelmente "
                   f"Claude desktop estava fechado naquele horário. Cobertura perdida.")
        out.append("")

    if analise["entregaram"]:
        out.append("## ✅ Entregaram")
        out.append("")
        out.append("| Fornecedor | Formato | Tempo (min) | Slot | Canal |")
        out.append("|---|---|---|---|---|")
        for e in analise["entregaram"]:
            tempo = e["tempo_resposta_min"] or "-"
            out.append(f"| {e['fornecedor']} | {e['formato'] or '-'} | {tempo} | "
                       f"{e['slot_disparo']} | {e['alvo_tipo'] or '-'} |")
        out.append("")

    if analise["furaram"]:
        out.append("## ⚠️ Furaram")
        out.append("")
        for f in analise["furaram"]:
            out.append(f"- **{f['fornecedor']}** — slots disparados: "
                       f"{', '.join(f['slots_disparados'])}")
        out.append("")

    if analise["com_erro"]:
        out.append("## ❌ Erros técnicos")
        out.append("")
        for e in analise["com_erro"]:
            out.append(f"- **{e['fornecedor']}**:")
            for er in e["erros"]:
                out.append(f"  - {er.get('ts', '?')}: {er.get('motivo', '?')}")
        out.append("")

    if analise["pendentes"]:
        out.append("## ⏳ Pendentes")
        out.append("")
        for p in analise["pendentes"]:
            slots = ", ".join(p["slots_disparados"]) or "(sem disparo)"
            out.append(f"- **{p['fornecedor']}** — slots: {slots}")
        out.append("")

    out.append("## Distribuição por slot")
    out.append("")
    for slot in L.SLOTS:
        n = analise["slot_to_entregas"].get(slot, 0)
        out.append(f"- **{slot}:** {n} entregas")

    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Subcomandos
# --------------------------------------------------------------------------- #

def cmd_texto(args) -> int:
    rodada = args.rodada or L.rodada_str()
    analise = analisar_rodada(rodada)
    print(render_texto(analise))
    return 0


def cmd_json(args) -> int:
    rodada = args.rodada or L.rodada_str()
    analise = analisar_rodada(rodada)
    print(render_json(analise))
    return 0


def cmd_markdown(args) -> int:
    rodada = args.rodada or L.rodada_str()
    analise = analisar_rodada(rodada)
    out = render_markdown(analise)
    if args.salvar:
        path = L.rodada_dir(rodada) / "relatorio.md"
        path.write_text(out, encoding="utf-8")
        print(f"[markdown] salvo em {path}", file=sys.stderr)
    print(out)
    return 0


def cmd_listar_rodadas(args) -> int:
    rodadas = L.listar_rodadas_anteriores(n=args.n)
    print(json.dumps({"rodadas": rodadas}, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="relatorio_rodada.py",
        description="Status consolidado da rodada de pedido de tabela FLV.",
    )
    sub = p.add_subparsers(dest="acao", required=True)

    p_t = sub.add_parser("texto", help="Relatório compacto em texto")
    p_t.add_argument("--rodada", help="Rodada AAAA-MM-DD (default: hoje)")
    p_t.set_defaults(func=cmd_texto)

    p_j = sub.add_parser("json", help="Dump JSON completo")
    p_j.add_argument("--rodada")
    p_j.set_defaults(func=cmd_json)

    p_m = sub.add_parser("markdown", help="Relatório Markdown formatado")
    p_m.add_argument("--rodada")
    p_m.add_argument("--salvar", action="store_true",
                     help="Salva como relatorio.md na pasta da rodada")
    p_m.set_defaults(func=cmd_markdown)

    p_lr = sub.add_parser("listar-rodadas", help="Lista últimas N rodadas")
    p_lr.add_argument("-n", type=int, default=10)
    p_lr.set_defaults(func=cmd_listar_rodadas)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
