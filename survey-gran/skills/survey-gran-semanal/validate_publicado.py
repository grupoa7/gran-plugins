#!/usr/bin/env python3
"""
Smoke test pós-build do Survey Gran Mesa.

Objetivo: pegar bugs como o fmtBRL ANTES de publicar — não esperar
inspeção visual em produção.

Estratégia: regex no HTML resultante para identificar chamadas a
funções `fmt*` (formatadores), e verificar se cada uma delas está
definida no próprio HTML. Não roda o JS — só análise estática.

Saída:
  exit 0 = HTML limpo, pode publicar
  exit 1 = encontrou função não definida, ABORTA publicação

Uso:
  python3 validate_publicado.py /caminho/para/Survey_Gran_Mesa_S18_2026_v2.html
  ou
  SURVEY_DATA_DIR=/data python3 validate_publicado.py  (auto-localiza)
"""

import os
import re
import sys
from pathlib import Path


def get_data_dir() -> Path:
    if env := os.environ.get('SURVEY_DATA_DIR'):
        return Path(env)
    p = Path.home() / 'Documents' / 'Claude' / 'Projects' / '[GRAN] Survey' / 'data'
    if p.exists():
        return p
    raise FileNotFoundError("Pasta data/ não encontrada.")


def find_html() -> Path:
    """Localiza o HTML mais recente em data/gran-mesa/relatorios/"""
    data_dir = get_data_dir()
    rel_dir = data_dir / 'relatorios'
    if not rel_dir.exists():
        raise FileNotFoundError(f"Pasta {rel_dir} não encontrada.")
    candidates = sorted(rel_dir.glob('Survey_Gran_S*_v12.html'),
                        key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError("Nenhum HTML Survey_Gran_S*_v12.html encontrado.")
    return candidates[0]


# Padrões "perigosos" — funções que aparecem como CHAMADAS no template
# mas que precisam estar definidas em algum lugar do HTML.
# Captura: nome_funcao(  — em qualquer contexto JS.
CALL_PATTERN = re.compile(r'\b(fmt[A-Za-z0-9_]+|format[A-Z][A-Za-z0-9_]*|render[A-Z][A-Za-z0-9_]*)\s*\(')

# Funções que sabemos que existem em libs externas (Chart.js etc.) — whitelist
KNOWN_LIBS = {
    'fmt',  # Chart.js callback shorthand às vezes
}


def validate(html_path: Path) -> int:
    print(f"📂 Validando: {html_path.name} ({html_path.stat().st_size:,} bytes)")
    src = html_path.read_text(encoding='utf-8')

    # Coleta TODAS as chamadas de função fmt*/render*/format*
    calls = set(CALL_PATTERN.findall(src))

    # Para cada chamada, verifica se há `function NOME(` ou `const NOME =`
    # ou `let NOME =` ou `var NOME =` no HTML.
    not_defined = []
    for fn in sorted(calls):
        if fn in KNOWN_LIBS:
            continue
        defined = (
            re.search(rf'\bfunction\s+{re.escape(fn)}\s*\(', src)
            or re.search(rf'\b(?:const|let|var)\s+{re.escape(fn)}\s*=', src)
            or re.search(rf'\b{re.escape(fn)}\s*=\s*function\b', src)
            or re.search(rf'\b{re.escape(fn)}\s*=\s*\(', src)  # arrow function
        )
        if not defined:
            not_defined.append(fn)

    if not_defined:
        print(f"❌ FALHA: {len(not_defined)} função(ões) chamada(s) mas NUNCA definida(s):")
        for fn in not_defined:
            # Mostra primeiro contexto onde a chamada aparece
            m = re.search(rf'.{{0,80}}\b{re.escape(fn)}\s*\(.{{0,40}}', src)
            ctx = m.group(0).strip() if m else '(contexto não encontrado)'
            print(f"   • {fn}()")
            print(f"     ↳ {ctx[:160]}")
        print()
        print("⚠️  NÃO PUBLIQUE. Corrija no source antes de fazer push.")
        return 1

    print(f"✅ OK: {len(calls)} função(ões) fmt/render/format chamada(s), todas definidas.")
    return 0


def main():
    if len(sys.argv) > 1:
        html_path = Path(sys.argv[1])
    else:
        try:
            html_path = find_html()
        except FileNotFoundError as e:
            print(f"❌ {e}")
            return 1

    if not html_path.exists():
        print(f"❌ {html_path} não existe.")
        return 1

    return validate(html_path)


if __name__ == '__main__':
    sys.exit(main())
