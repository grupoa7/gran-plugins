#!/usr/bin/env python3
"""
enviar_pedido.py — CLI de disparo de pedido de tabela via WhatsApp Desktop
(skill cotacao-flv-gran — comando /cotacao-disparar).

Esta CLI NÃO controla o WhatsApp diretamente (computer-use fica com Claude na
sessão agendada). O papel desta CLI é:

  1. CALCULAR o que precisa ser disparado neste slot (lista JSON estruturada)
  2. REGISTRAR o resultado de cada disparo (sucesso, erro, anti-spam pulado)
  3. RECOMENDAR fornecedores pra auto-desativação (após N rodadas sem resposta)

Fluxo típico na sessão Claude agendada:

  $ python scripts/enviar_pedido.py --listar
  # CLI retorna JSON: [{fornecedor, slot, alvo_tipo, alvo_nome, mensagem, ...}, ...]
  # Claude itera, executa cliques no WhatsApp via computer-use pra cada item

  $ python scripts/enviar_pedido.py --registrar-disparo --fornecedor QUALISUPER \\
        --slot 03h --alvo-tipo individual --alvo-nome "[CEASA] Marcos Qualisuper"
  # CLI grava evento "disparo" no manifest.jsonl

  $ python scripts/enviar_pedido.py --registrar-erro --fornecedor HORTIMIX \\
        --slot 03h --motivo "favorito_nao_encontrado"
  # CLI grava evento "erro"

  $ python scripts/enviar_pedido.py --status
  # CLI retorna snapshot agregado da rodada (manifest.json)

Modo dry-run:
  $ python scripts/enviar_pedido.py --listar --dry-run
  # Mostra o que seria disparado sem checar manifest existente

Filtros:
  --slot SLOT          força um slot específico (default: auto-detect pela hora)
  --rodada AAAA-MM-DD  força uma rodada específica (default: hoje em Salvador)
  --fornecedor NOME    opera apenas no fornecedor especificado
  --fornecedores A,B,C múltiplos fornecedores
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Permite importar envio_lib mesmo quando rodado de outro cwd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import envio_lib as L


# --------------------------------------------------------------------------- #
# Subcomando: listar disparos pendentes do slot atual
# --------------------------------------------------------------------------- #

def cmd_listar(args) -> int:
    """Calcula a lista de disparos que devem acontecer neste slot.

    Output (stdout): JSON com array de objetos. Cada objeto:
      {
        "fornecedor": "QUALISUPER",
        "slot": "03h",
        "alvo_tipo": "individual",
        "alvo_nome": "[CEASA] Marcos Qualisuper",
        "envio_telefone": "+55 71 99374-5500",  // pra Claude validar
        "envio_nome_chamada": "Marcos",
        "mensagem": "Bom dia, meu amigo!...",
        "pulou_anti_spam": false,
        "motivo_pulo": null
      }

    Saída (stderr): logs informativos.
    Exit code: 0 sempre (mesmo se não houver nada a disparar).
    """
    rodada = args.rodada or L.rodada_str()
    slot = args.slot or L.slot_atual()
    if not slot:
        print(f"[listar] Fora da janela 03h-08h em Salvador. Slot atual: None", file=sys.stderr)
        print("[]", file=sys.stdout)
        return 0
    if slot == L.SLOT_LEITURA_FINAL:
        print(f"[listar] Slot {slot} é só leitura final (sem disparo).", file=sys.stderr)
        print("[]", file=sys.stdout)
        return 0

    # Checa dia da semana (Seg/Qua) — ignora se --force-dia
    agora = L.agora_salvador()
    if not args.force_dia and not L.e_dia_de_rodada(agora):
        nome_dia = agora.strftime("%A")
        print(f"[listar] {rodada} é {nome_dia}, não é dia de rodada (Seg/Qua). Use --force-dia.",
              file=sys.stderr)
        print("[]", file=sys.stdout)
        return 0

    fornecedores = L.carregar_fornecedores_envio()
    mensagens = L.carregar_mensagens()

    # Filtro por nome
    nomes_filtro = _parse_nomes_filtro(args)
    if nomes_filtro:
        fornecedores = [f for f in fornecedores if f["nome"] in nomes_filtro]

    # Snapshot atual da rodada (pra checar anti-spam + já-recebidos)
    snapshot = L.agregar_manifest(rodada) if not args.dry_run else {"fornecedores": {}}
    estado_por_forn = snapshot.get("fornecedores", {})

    saida = []
    for f in fornecedores:
        nome = f["nome"]
        estado = estado_por_forn.get(nome, {})

        # Anti-spam: já recebeu OU disparou recentemente?
        ok, motivo_pulo = L.anti_spam_check(estado, agora=agora) if not args.dry_run else (True, None)
        if not ok:
            saida.append({
                "fornecedor": nome,
                "slot": slot,
                "pulou_anti_spam": True,
                "motivo_pulo": motivo_pulo,
            })
            print(f"[listar] {nome}: PULADO ({motivo_pulo})", file=sys.stderr)
            continue

        # Já disparou neste slot? (sem ser anti-spam — pode ter sido este script
        # rodando 2x acidentalmente)
        if not args.dry_run and L.ja_disparou_neste_slot(estado, slot):
            saida.append({
                "fornecedor": nome,
                "slot": slot,
                "pulou_anti_spam": True,
                "motivo_pulo": "ja_disparou_neste_slot",
            })
            print(f"[listar] {nome}: PULADO (já disparou no slot {slot})", file=sys.stderr)
            continue

        alvo = L.decidir_alvo(f, slot)
        primeiro_disparo = not bool(estado.get("slots_disparados"))
        try:
            msg = L.mensagem_para_disparo(f, slot, mensagens, estado_fornecedor=estado)
        except KeyError as e:
            saida.append({
                "fornecedor": nome,
                "slot": slot,
                "erro": f"template_ausente: {e}",
            })
            continue

        saida.append({
            "fornecedor": nome,
            "slot": slot,
            "alvo_tipo": alvo["tipo"],
            "alvo_nome": alvo["nome"],
            "envio_telefone": f.get("envio_telefone"),
            "envio_nome_chamada": f.get("envio_nome_chamada"),
            "mensagem": msg,
            "mensagem_tipo": "inicial" if primeiro_disparo else "retentativa",
            "pulou_anti_spam": False,
            "motivo_pulo": None,
        })

    print(json.dumps(saida, ensure_ascii=False, indent=2), file=sys.stdout)
    n_disparos = sum(1 for s in saida if not s.get("pulou_anti_spam") and not s.get("erro"))
    n_pulados = sum(1 for s in saida if s.get("pulou_anti_spam"))
    print(f"[listar] slot={slot} rodada={rodada} disparos_a_executar={n_disparos} pulados={n_pulados}",
          file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: registrar disparo bem-sucedido
# --------------------------------------------------------------------------- #

def cmd_registrar_disparo(args) -> int:
    if not args.fornecedor or not args.slot:
        print("[registrar-disparo] --fornecedor e --slot são obrigatórios", file=sys.stderr)
        return 1
    rodada = args.rodada or L.rodada_str()
    entrada = {
        "tipo": "disparo",
        "fornecedor": args.fornecedor,
        "slot": args.slot,
        "alvo_tipo": args.alvo_tipo,
        "alvo_nome": args.alvo_nome,
    }
    L.registrar_evento(entrada, rodada=rodada)
    L.agregar_manifest(rodada)
    print(f"[registrar-disparo] OK fornecedor={args.fornecedor} slot={args.slot} alvo={args.alvo_tipo}",
          file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: registrar erro
# --------------------------------------------------------------------------- #

def cmd_registrar_erro(args) -> int:
    if not args.fornecedor or not args.motivo:
        print("[registrar-erro] --fornecedor e --motivo são obrigatórios", file=sys.stderr)
        return 1
    rodada = args.rodada or L.rodada_str()
    entrada = {
        "tipo": "erro",
        "fornecedor": args.fornecedor,
        "slot": args.slot,
        "motivo": args.motivo,
    }
    L.registrar_evento(entrada, rodada=rodada)
    L.agregar_manifest(rodada)
    print(f"[registrar-erro] OK fornecedor={args.fornecedor} motivo={args.motivo}", file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: registrar anti-spam pulado (msg manual detectada)
# --------------------------------------------------------------------------- #

def cmd_registrar_anti_spam(args) -> int:
    if not args.fornecedor or not args.motivo:
        print("[registrar-anti-spam] --fornecedor e --motivo são obrigatórios", file=sys.stderr)
        return 1
    rodada = args.rodada or L.rodada_str()
    entrada = {
        "tipo": "anti_spam_pulou",
        "fornecedor": args.fornecedor,
        "slot": args.slot,
        "motivo": args.motivo,
    }
    L.registrar_evento(entrada, rodada=rodada)
    L.agregar_manifest(rodada)
    print(f"[registrar-anti-spam] OK fornecedor={args.fornecedor}", file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: status (snapshot da rodada)
# --------------------------------------------------------------------------- #

def cmd_status(args) -> int:
    rodada = args.rodada or L.rodada_str()
    snap = L.agregar_manifest(rodada)
    print(json.dumps(snap, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: candidatos a auto-desativar
# --------------------------------------------------------------------------- #

def cmd_candidatos_desativar(args) -> int:
    """Lista fornecedores que não responderam nas últimas N rodadas.
    NÃO mexe no fornecedores.json — só recomenda. Hugo aprova manualmente."""
    fornecedores = L.carregar_fornecedores_envio()
    candidatos = []
    for f in fornecedores:
        n_sem = L.contar_rodadas_sem_resposta(f["nome"])
        if n_sem >= L.AUTO_DESATIVAR_RODADAS_SEM_RESPOSTA:
            candidatos.append({
                "fornecedor": f["nome"],
                "rodadas_sem_resposta": n_sem,
                "telefone": f.get("envio_telefone"),
                "individual_nome": f.get("envio_individual_nome"),
            })
    print(json.dumps(candidatos, ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: marcar fornecedor como já-recebido fora do manifest
# --------------------------------------------------------------------------- #

def cmd_marcar_tabela_externa(args) -> int:
    """Marca que o fornecedor JÁ TEM tabela vigente no chat (vista pelo agente
    Claude durante a varredura, ANTES de disparar). Anti-spam passa a pular ele.

    Uso típico: agente abre WhatsApp, busca o contato, vê preview com preços ou
    tabela aberta no chat, e roda este comando antes de disparar."""
    if not args.fornecedor:
        print("[marcar-tabela-externa] --fornecedor é obrigatório", file=sys.stderr)
        return 1
    rodada = args.rodada or L.rodada_str()
    L.registrar_tabela_externa(args.fornecedor, evidencia=args.evidencia or "", rodada=rodada)
    L.agregar_manifest(rodada)
    print(f"[marcar-tabela-externa] OK fornecedor={args.fornecedor}", file=sys.stderr)
    return 0


def cmd_checar_preview(args) -> int:
    """Roda a heurística de detecção sobre um texto de preview e retorna JSON
    {"e_tabela": bool, "evidencia": texto}. Útil pro agente decidir se chama
    marcar-tabela-externa ou não."""
    texto = args.texto or sys.stdin.read()
    e_tabela = L.detectar_tabela_no_preview(texto)
    print(json.dumps({"e_tabela": e_tabela, "evidencia": texto.strip()[:200]},
                     ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- #
# Utils
# --------------------------------------------------------------------------- #

def _parse_nomes_filtro(args) -> set[str] | None:
    if args.fornecedor:
        return {args.fornecedor.upper()}
    if args.fornecedores:
        return {n.strip().upper() for n in args.fornecedores.split(",") if n.strip()}
    return None


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="enviar_pedido.py",
        description="Orquestrador do disparo automático de pedido de tabela FLV.",
    )
    sub = p.add_subparsers(dest="acao", required=True)

    p_listar = sub.add_parser("listar", help="Lista disparos a executar neste slot")
    p_listar.add_argument("--slot", choices=list(L.SLOTS), help="Slot específico (default: auto)")
    p_listar.add_argument("--rodada", help="Rodada AAAA-MM-DD (default: hoje)")
    p_listar.add_argument("--fornecedor", help="Filtra um fornecedor")
    p_listar.add_argument("--fornecedores", help="Lista CSV de fornecedores")
    p_listar.add_argument("--force-dia", action="store_true",
                          help="Ignora check de Seg/Qua (pra testes)")
    p_listar.add_argument("--dry-run", action="store_true",
                          help="Não checa manifest, mostra tudo")
    p_listar.set_defaults(func=cmd_listar)

    p_disp = sub.add_parser("registrar-disparo", help="Registra disparo bem-sucedido")
    p_disp.add_argument("--fornecedor", required=True)
    p_disp.add_argument("--slot", required=True, choices=list(L.SLOTS))
    p_disp.add_argument("--alvo-tipo", required=True, choices=["individual", "grupo"])
    p_disp.add_argument("--alvo-nome", required=True)
    p_disp.add_argument("--rodada", help="Rodada AAAA-MM-DD (default: hoje)")
    p_disp.set_defaults(func=cmd_registrar_disparo)

    p_err = sub.add_parser("registrar-erro", help="Registra erro de disparo")
    p_err.add_argument("--fornecedor", required=True)
    p_err.add_argument("--motivo", required=True)
    p_err.add_argument("--slot", choices=list(L.SLOTS))
    p_err.add_argument("--rodada")
    p_err.set_defaults(func=cmd_registrar_erro)

    p_spam = sub.add_parser("registrar-anti-spam", help="Registra anti-spam pulado")
    p_spam.add_argument("--fornecedor", required=True)
    p_spam.add_argument("--motivo", required=True)
    p_spam.add_argument("--slot", choices=list(L.SLOTS))
    p_spam.add_argument("--rodada")
    p_spam.set_defaults(func=cmd_registrar_anti_spam)

    p_status = sub.add_parser("status", help="Snapshot agregado da rodada")
    p_status.add_argument("--rodada")
    p_status.set_defaults(func=cmd_status)

    p_desat = sub.add_parser("candidatos-desativar",
                              help="Lista fornecedores com 3+ rodadas sem resposta")
    p_desat.set_defaults(func=cmd_candidatos_desativar)

    p_ext = sub.add_parser("marcar-tabela-externa",
                            help="Marca fornecedor como já tendo tabela vigente (anti-spam pula)")
    p_ext.add_argument("--fornecedor", required=True)
    p_ext.add_argument("--evidencia", help="Texto/snippet da mensagem que comprova")
    p_ext.add_argument("--rodada")
    p_ext.set_defaults(func=cmd_marcar_tabela_externa)

    p_chk = sub.add_parser("checar-preview",
                            help="Heurística: texto de preview parece tabela de preços?")
    p_chk.add_argument("--texto", help="Texto a checar (se omitir, lê de stdin)")
    p_chk.set_defaults(func=cmd_checar_preview)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
