"""
registrar_pesagem.py — CLI pra adicionar pesagens reais do recebimento Gran à base
de embalagens (templates/embalagens.json), com calibração automática.

Uso:
    python registrar_pesagem.py --sku 138 --peso 17.5 --fornecedor IGARASHI
    python registrar_pesagem.py --commodity tomate_extra_primeira_salada_italiano --peso 17.5

Quando ≥2 pesagens divergem >10% do default CEASA, o sistema sugere trocar o
default pela mediana das pesagens divergentes. A troca NÃO é automática — o CLI
imprime a sugestão e pede confirmação (--aprovar pra aplicar direto).
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flv_lib as L


def main():
    ap = argparse.ArgumentParser(description="Registra pesagem real e calibra default.")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--sku", type=int, help="COD Gran do SKU pesado")
    grp.add_argument("--commodity", help="Slug da commodity (ver embalagens.json/produtos)")
    ap.add_argument("--peso", type=float, required=True, help="Peso pesado em kg")
    ap.add_argument("--fornecedor", help="Quem entregou (rastreio)")
    ap.add_argument("--data", help="ISO YYYY-MM-DD (default hoje)")
    ap.add_argument("--aprovar", action="store_true",
                    help="Se sistema sugerir troca de default, aplica direto.")
    args = ap.parse_args()

    # Resolve commodity_slug
    if args.sku:
        base = L.carregar_embalagens()
        sku = base.get("skus", {}).get(str(args.sku))
        if not sku:
            print(f"ERRO: SKU {args.sku} não encontrado no cadastro.", file=sys.stderr)
            sys.exit(1)
        slug = sku.get("commodity_slug")
        if not slug:
            print(f"ERRO: SKU {args.sku} ({sku.get('descricao_gran')}) sem commodity mapeada.",
                  file=sys.stderr)
            sys.exit(1)
        print(f"[sku {args.sku}] {sku.get('descricao_gran')}  ->  commodity: {slug}")
    else:
        slug = args.commodity

    res = L.registrar_pesagem(slug, args.peso, sku_cod=args.sku,
                              fornecedor=args.fornecedor, data=args.data)
    if not res.get("ok"):
        print(f"ERRO: {res.get('erro')}", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Pesagem registrada: {res['pesagem_registrada']}")
    print(f"  default atual (CEASA-BA): {res['default_atual']} kg")
    print(f"  total de pesagens p/ essa commodity: {res['total_pesagens']}")

    if res["sugerir_troca"]:
        sug = res["novo_default_sugerido"]
        diff_pct = abs(sug - res["default_atual"]) / res["default_atual"] * 100
        print()
        print(f"⚠ CALIBRAÇÃO SUGERIDA: trocar default de {res['default_atual']} kg "
              f"-> {sug} kg (divergência {diff_pct:.1f}%)")
        if args.aprovar:
            base = L.carregar_embalagens()
            base["produtos"][slug]["kg_por_caixa"] = sug
            base["produtos"][slug].setdefault("historico_calibracao", []).append({
                "data": args.data or __import__("datetime").date.today().isoformat(),
                "default_anterior": res["default_atual"],
                "default_novo": sug,
                "n_pesagens": res["total_pesagens"],
            })
            with open(L.EMBALAGENS_JSON, "w", encoding="utf-8") as fp:
                json.dump(base, fp, ensure_ascii=False, indent=2)
            print(f"✓ default trocado: {res['default_atual']} -> {sug} kg")
        else:
            print(f"  (rode novamente com --aprovar pra aplicar a troca)")


if __name__ == "__main__":
    main()
