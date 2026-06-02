#!/usr/bin/env python3
"""DEPRECATED — não usar. v3.2 não tem orquestrador Python centralizado.

A skill v3.2 instrui o Claude a executar o fluxo passo-a-passo seguindo SKILL.md.
Os scripts auxiliares (parsear_escala, aplicar_regras, detector_suspeitos, gerar_html)
são chamados pelo Claude conforme necessário durante a rodada.

Se chamado, abortar.
"""
import sys
print("ERRO: run_jornada_semana.py é DEPRECATED. Siga o fluxo em SKILL.md.", file=sys.stderr)
sys.exit(1)
