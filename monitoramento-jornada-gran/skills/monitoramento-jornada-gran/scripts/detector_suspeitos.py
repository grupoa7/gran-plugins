#!/usr/bin/env python3
"""detector_suspeitos.py — Skill v3.

Detecta padrões suspeitos no cartão de ponto que requerem revisão antes do relatório final.
Aplicado APÓS extração e ANTES de gerar HTML.

Heurísticas (REG-S1 a REG-S6) — ver references/heuristicas_suspeitos.md.
"""
import re

def detectar_suspeitos(nome_show, setor, dias_processar, suspenso=False):
    """Retorna lista de casos suspeitos pra esse colaborador.
    
    Cada caso inclui: nome, setor, severidade, tipo, descricao, dias_afetados,
    acao_sugerida, tratativa_rh (bool — se True, vai pra bloco separado e fora dos indicadores).
    """
    casos = []
    if suspenso: return casos

    dias_jornada = [d for d in dias_processar if d["tipo_escala"] in ("JORNADA","JORNADA_2T")]
    dias_falta_total = [d for d in dias_processar if d["tipo_escala"] in ("JORNADA","JORNADA_2T") and all(b in ("","Falta") for b in d["batidas"][:4])]

    # REG-S1/S6 — falta excessiva (>=3 dias sem batida em quem tinha jornada)
    if dias_jornada and len(dias_falta_total) >= 3:
        casos.append({
            "nome": nome_show, "setor": setor,
            "severidade": "CRITICO",
            "tipo": "FALTAS_EXCESSIVAS",
            "descricao": f"{len(dias_falta_total)}/{len(dias_jornada)} dias úteis com falta total (escalado mas zero batidas)",
            "dias_afetados": [d["data"] for d in dias_falta_total],
            "acao_sugerida": "Provável falha biométrica/cadastro. Verificar com gestor + checar histórico do mês anterior. Excluído dos indicadores agregados até decisão.",
            "tratativa_rh": True,
        })

    # REG-S2/S3 — batidas ímpares
    for d in dias_processar:
        if d["tipo_escala"] not in ("JORNADA","JORNADA_2T"): continue
        bat = d["batidas"]
        horas = [b for b in bat if b and b != "Falta" and re.match(r"^\d{1,2}:\d{2}", str(b).strip())]
        n = len(horas)
        if n == 1:
            casos.append({
                "nome": nome_show, "setor": setor,
                "severidade": "ALERTA",
                "tipo": "BATIDA_UNICA",
                "descricao": f"{d['data']}: bateu apenas 1 vez ({horas[0]})",
                "dias_afetados": [d["data"]],
                "acao_sugerida": "Confirmar trabalho com gestor + ajuste manual no RHID.",
                "tratativa_rh": False,
            })
        elif n in (3, 5):
            casos.append({
                "nome": nome_show, "setor": setor,
                "severidade": "MEDIO",
                "tipo": "BATIDAS_IMPARES",
                "descricao": f"{d['data']}: bateu {n} vezes — {' / '.join(horas)} (esqueceu 1 batida)",
                "dias_afetados": [d["data"]],
                "acao_sugerida": "Esquecimento provável. Pedir ajuste manual ('Esquecimento Marcação do Ponto') antes do fechamento.",
                "tratativa_rh": False,
            })

    # REG-S4 — trabalhou em folga
    for d in dias_processar:
        if d["tipo_escala"] in ("FOLGA","FERIAS","BH"):
            bat = d["batidas"]
            horas = [b for b in bat if b and b != "Falta" and re.match(r"^\d{1,2}:\d{2}", str(b).strip())]
            if len(horas) >= 2:
                casos.append({
                    "nome": nome_show, "setor": setor,
                    "severidade": "INFO",
                    "tipo": "TRABALHOU_EM_FOLGA",
                    "descricao": f"{d['data']}: escalado como folga/férias mas bateu ponto ({len(horas)} batidas)",
                    "dias_afetados": [d["data"]],
                    "acao_sugerida": "Verificar se foi convocação extraordinária. Pode gerar BH ou hora extra.",
                    "tratativa_rh": False,
                })

    return casos
