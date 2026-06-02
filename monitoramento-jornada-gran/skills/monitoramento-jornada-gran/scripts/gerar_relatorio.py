#!/usr/bin/env python3
"""DEPRECATED — não usar. v3.2 usa gerar_html.py em vez deste arquivo.

Este arquivo era o orquestrador da v1 (com bug — assumia que template era S19 hardcoded).
Em v2 deveria ter sido removido mas ficou aqui por compatibilidade.
Em v3.2: o gerador correto é gerar_html.py.

Se chamado, abortar.
"""
import sys
print("ERRO: gerar_relatorio.py é DEPRECATED. Use scripts/gerar_html.py (v3.2).", file=sys.stderr)
sys.exit(1)
