#!/usr/bin/env python3
"""
arquivar_resposta.py — CLI de arquivamento de respostas dos fornecedores
(skill cotacao-flv-gran — comando /cotacao-arquivar).

Esta CLI cuida da PERSISTÊNCIA das respostas recebidas. A detecção visual da
resposta no WhatsApp Desktop é feita pela Claude na sessão (computer-use); este
script:

  1. LISTA fornecedores pendentes pra Claude saber em quais chats checar
  2. REGISTRA respostas detectadas (PDF, foto, texto) movendo o arquivo pro
     diretório que o /cotar consome
  3. FORNECE o template de resposta automática a áudios (pra Claude enviar)
  4. MARCA o fornecedor como recebido no manifest

Fluxo típico:

  $ python scripts/arquivar_resposta.py listar-pendentes
  # CLI retorna JSON com fornecedores que ainda não responderam

  # Claude abre cada chat via computer-use, vê se tem resposta nova,
  # se for áudio pede resposta-padrão, se for PDF/foto/texto baixa/captura

  $ python scripts/arquivar_resposta.py registrar-resposta \\
        --fornecedor HORTIMIX --formato pdf --arquivo /caminho/local/arq.pdf
  # CLI move o arquivo pra dados/cotacoes_recebidas/AAAA-MM-DD/<fornecedor>.pdf
  # e grava evento "resposta" no manifest

  $ python scripts/arquivar_resposta.py resposta-audio --alvo-tipo grupo
  # CLI retorna a string da resposta automática pra Claude enviar

  $ python scripts/arquivar_resposta.py registrar-audio --fornecedor JUNIOR_UVA
  # CLI grava evento "anti_spam_pulou" com motivo="audio_recebido" (pra status)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import envio_lib as L


# --------------------------------------------------------------------------- #
# Subcomando: listar fornecedores pendentes
# --------------------------------------------------------------------------- #

def cmd_listar_pendentes(args) -> int:
    """Retorna JSON com fornecedores que ainda não entregaram tabela nesta rodada.
    Cada item tem nome + nomes de chat (individual e grupo) pra Claude checar."""
    rodada = args.rodada or L.rodada_str()
    snap = L.agregar_manifest(rodada)
    estados = snap.get("fornecedores", {})
    fornecedores = L.carregar_fornecedores_envio()

    pendentes = []
    for f in fornecedores:
        nome = f["nome"]
        st = estados.get(nome, {})
        if st.get("status") == "recebido":
            continue  # já entregou
        # Inclui fornecedores que tiveram disparo (faz sentido checar) e os
        # que não tiveram mas estão ativos (Claude pode forçar checagem)
        pendentes.append({
            "fornecedor": nome,
            "envio_individual_nome": f.get("envio_individual_nome"),
            "envio_grupo_nome": f.get("envio_grupo_nome"),
            "envio_telefone": f.get("envio_telefone"),
            "slots_disparados": st.get("slots_disparados", []),
            "ultimo_disparo_ts": st.get("ultimo_disparo_ts"),
            "ultimo_alvo_tipo": st.get("ultimo_alvo_tipo"),
            "ultimo_alvo_nome": st.get("ultimo_alvo_nome"),
            "status_atual": st.get("status", "sem_disparo"),
        })

    print(json.dumps(pendentes, ensure_ascii=False, indent=2))
    print(f"[listar-pendentes] rodada={rodada} pendentes={len(pendentes)}", file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: registrar resposta (arquivo entregue)
# --------------------------------------------------------------------------- #

VALID_FORMATOS = {"pdf", "imagem", "texto", "jpg", "png"}


def cmd_registrar_resposta(args) -> int:
    if not args.fornecedor or not args.formato:
        print("[registrar-resposta] --fornecedor e --formato obrigatórios", file=sys.stderr)
        return 1
    formato = args.formato.lower()
    if formato not in VALID_FORMATOS:
        print(f"[registrar-resposta] --formato deve ser um de {VALID_FORMATOS}", file=sys.stderr)
        return 1

    rodada = args.rodada or L.rodada_str()
    pasta = L.rodada_dir(rodada)

    arquivo_destino = None
    if formato == "texto" and args.texto:
        # Texto colado direto via --texto, salva como .txt
        nome_seguro = _nome_arquivo_seguro(args.fornecedor)
        arquivo_destino = pasta / f"{nome_seguro}.txt"
        arquivo_destino.write_text(args.texto, encoding="utf-8")
    elif args.arquivo:
        origem = Path(args.arquivo)
        if not origem.exists():
            print(f"[registrar-resposta] arquivo não existe: {origem}", file=sys.stderr)
            return 1
        ext = origem.suffix.lower() or {"pdf": ".pdf", "imagem": ".jpg",
                                          "jpg": ".jpg", "png": ".png",
                                          "texto": ".txt"}.get(formato, ".bin")
        nome_seguro = _nome_arquivo_seguro(args.fornecedor)
        arquivo_destino = pasta / f"{nome_seguro}{ext}"
        shutil.copy2(origem, arquivo_destino)
    else:
        print("[registrar-resposta] precisa --arquivo OU (--formato texto + --texto)",
              file=sys.stderr)
        return 1

    entrada = {
        "tipo": "resposta",
        "fornecedor": args.fornecedor,
        "formato": formato,
        "arquivo": str(arquivo_destino.relative_to(L.SKILL_DIR.parent))
                    if arquivo_destino else None,
    }
    L.registrar_evento(entrada, rodada=rodada)
    L.agregar_manifest(rodada)
    print(f"[registrar-resposta] OK fornecedor={args.fornecedor} formato={formato} "
          f"arquivo={arquivo_destino.name if arquivo_destino else '-'}", file=sys.stderr)
    print(json.dumps({"ok": True, "arquivo": str(arquivo_destino)}, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: obter texto de resposta a áudio
# --------------------------------------------------------------------------- #

def cmd_resposta_audio(args) -> int:
    """Retorna o texto pra responder quando vier áudio (individual ou grupo).

    Se --texto-acompanhante for passado e a heurística reconhecer tabela nele,
    retorna decisao='dispensar' (= não precisa mandar a desculpa de áudio, já
    veio texto utilizável). Evita ruído no chat quando o fornecedor mandou
    áudio+texto e o texto já dá conta.
    """
    mensagens = L.carregar_mensagens()
    if args.alvo_tipo == "grupo":
        texto_resposta = mensagens.get("audio_response_grupo", "")
    else:
        texto_resposta = mensagens.get("audio_response_individual", "")

    decisao = "enviar"
    motivo = None
    if args.texto_acompanhante:
        if L.detectar_tabela_no_preview(args.texto_acompanhante):
            decisao = "dispensar"
            motivo = "texto_acompanhante_parece_tabela"

    out = {
        "texto": texto_resposta if decisao == "enviar" else "",
        "alvo_tipo": args.alvo_tipo,
        "decisao": decisao,
        "motivo": motivo,
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


def cmd_classificar_conteudo(args) -> int:
    """Classifica o conteúdo de uma resposta pra ajudar o agente a decidir o
    formato antes de arquivar. Lê --texto (preview / OCR / colado) e retorna:
        {"e_tabela": bool, "sugestao_formato": "texto"|"audio_only"|"so_aviso"}

    Útil quando o agente vê uma thread com áudio + texto, ou só texto curto."""
    texto = (args.texto or "").strip()
    e_tabela = L.detectar_tabela_no_preview(texto)
    if e_tabela:
        sugestao = "texto"
    elif len(texto) < 20:
        sugestao = "so_aviso"  # ex: "te mando já"
    else:
        sugestao = "indefinido"
    print(json.dumps({"e_tabela": e_tabela, "sugestao_formato": sugestao,
                       "preview": texto[:200]}, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: registrar áudio recebido (pra Claude logar)
# --------------------------------------------------------------------------- #

def cmd_registrar_audio(args) -> int:
    if not args.fornecedor:
        print("[registrar-audio] --fornecedor obrigatório", file=sys.stderr)
        return 1
    rodada = args.rodada or L.rodada_str()
    entrada = {
        "tipo": "anti_spam_pulou",
        "fornecedor": args.fornecedor,
        "motivo": "audio_recebido_resposta_solicitada",
    }
    L.registrar_evento(entrada, rodada=rodada)
    L.agregar_manifest(rodada)
    print(f"[registrar-audio] OK fornecedor={args.fornecedor}", file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- #
# Subcomando: listar arquivos da rodada (pra debug)
# --------------------------------------------------------------------------- #

def cmd_listar_arquivos(args) -> int:
    rodada = args.rodada or L.rodada_str()
    pasta = L.rodada_dir(rodada)
    arquivos = []
    for p in sorted(pasta.iterdir()):
        if p.is_file() and not p.name.startswith("_") and not p.name.startswith("manifest"):
            arquivos.append({
                "nome": p.name,
                "tamanho_bytes": p.stat().st_size,
                "modificado": p.stat().st_mtime,
            })
    print(json.dumps({"rodada": rodada, "pasta": str(pasta), "arquivos": arquivos},
                     ensure_ascii=False, indent=2))
    return 0


# --------------------------------------------------------------------------- #
# Utils
# --------------------------------------------------------------------------- #

def _nome_arquivo_seguro(s: str) -> str:
    """Converte nome de fornecedor pra slug seguro pra filesystem.
    'BOA CITRUS' -> 'boa_citrus'
    """
    import re
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="arquivar_resposta.py",
        description="Arquivamento de respostas dos fornecedores no fluxo de pedido FLV.",
    )
    sub = p.add_subparsers(dest="acao", required=True)

    p_lp = sub.add_parser("listar-pendentes", help="Lista fornecedores que não responderam")
    p_lp.add_argument("--rodada")
    p_lp.set_defaults(func=cmd_listar_pendentes)

    p_rr = sub.add_parser("registrar-resposta", help="Marca como recebido + arquiva")
    p_rr.add_argument("--fornecedor", required=True)
    p_rr.add_argument("--formato", required=True,
                      help="pdf|imagem|texto|jpg|png")
    p_rr.add_argument("--arquivo", help="Caminho do arquivo a copiar")
    p_rr.add_argument("--texto", help="Texto colado direto (use com --formato texto)")
    p_rr.add_argument("--rodada")
    p_rr.set_defaults(func=cmd_registrar_resposta)

    p_ra = sub.add_parser("resposta-audio", help="Retorna texto pra responder áudio")
    p_ra.add_argument("--alvo-tipo", choices=["individual", "grupo"], default="individual")
    p_ra.add_argument("--texto-acompanhante",
                      help="Se houver texto junto do áudio, passa aqui — se for tabela, dispensa o envio da desculpa")
    p_ra.set_defaults(func=cmd_resposta_audio)

    p_cc = sub.add_parser("classificar-conteudo",
                            help="Classifica resposta pra decidir formato (texto/áudio/aviso)")
    p_cc.add_argument("--texto", required=True)
    p_cc.set_defaults(func=cmd_classificar_conteudo)

    p_rga = sub.add_parser("registrar-audio", help="Registra que veio áudio (Claude já respondeu)")
    p_rga.add_argument("--fornecedor", required=True)
    p_rga.add_argument("--rodada")
    p_rga.set_defaults(func=cmd_registrar_audio)

    p_la = sub.add_parser("listar-arquivos", help="Lista arquivos da rodada (debug)")
    p_la.add_argument("--rodada")
    p_la.set_defaults(func=cmd_listar_arquivos)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
