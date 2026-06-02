#!/usr/bin/env python3
"""aplicar_regras.py — Motor de regras v3.2 da skill monitoramento-jornada-gran.

v3.2 (09/05/2026):
- MANOBRISTA fora dos restritos
- Janela manhã 11h-13h só vale em sábado, domingo ou feriado nacional
- Janela tarde 16h-19:30 vale em todos os dias úteis pra setores restritos
"""
import re
from datetime import date, timedelta

TOL_ATRASO_ENTRADA = 15
TOL_SAIDA = 10
INTERVALO_MIN = 60
INTERVALO_MAX = 65
JORNADA_MIN_INTERVALO_OBRIGATORIO = 6 * 60

JANELA_PROIBIDA_MANHA = (11 * 60, 13 * 60)
JANELA_PROIBIDA_TARDE = (16 * 60, 19 * 60 + 30)

# v3: MANOBRISTA SAIU dos restritos
SETORES_RESTRITOS = {"ENCARREGADOS", "OPERADOR DE LOJA", "OPERADOR DE CAIXAS"}

# v3.1: feriados nacionais 2026 (atualizar a cada virada de ano)
FERIADOS_NACIONAIS_2026 = {
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-04-21",
    "2026-05-01", "2026-06-04", "2026-09-07", "2026-10-12", "2026-11-02",
    "2026-11-15", "2026-12-25",
}

JUSTIFICATIVAS_QUE_EXCLUEM_FALTA = {
    "Atestado Médico", "Atestado de Comparecimento", "Atestado de Óbito",
    "Exame de Retorno ao Trabalho", "Férias", "Feriado",
    "Folga Domingo Trabalhado", "Folga Feriado",
    "Licença Casamento", "Licença Maternidade", "Licença Paternidade",
    "Afastamento Temporário", "Suspensão",
}

def janela_manha_aplica(data_iso):
    """v3.1: janela 11h-13h só vale em sáb/dom ou feriado nacional.
    Razão: padrão de cupons mostrou maior fluxo de manhã do que no almoço em dias úteis."""
    if data_iso in FERIADOS_NACIONAIS_2026:
        return True
    y, m, d_ = map(int, data_iso.split("-"))
    return date(y, m, d_).weekday() >= 5  # 5=sábado, 6=domingo

def parse_hhmm(s):
    if not s: return None
    s = str(s).strip()
    if s in ("Falta", "Férias", "FÉRIAS", "Folga", "Feriado", "Banco", "Rescisão", "X", "-"): return None
    s = re.sub(r"\([IPMC]\)", "", s).strip()
    m = re.match(r"^(-?)(\d{1,2}):(\d{2})$", s)
    if not m: return None
    sign = -1 if m.group(1) == "-" else 1
    return sign * (int(m.group(2)) * 60 + int(m.group(3)))

def hhmm_str(mins):
    if mins is None: return ""
    neg = "-" if mins < 0 else ""
    mins = abs(mins)
    return f"{neg}{mins // 60:02d}:{mins % 60:02d}"

def cruza_janela(ini_min, fim_min, janela):
    if ini_min is None or fim_min is None: return False
    ji, jf = janela
    return ini_min < jf and fim_min > ji

def cruza_alguma_janela_proibida(ini_min, fim_min, data_iso):
    """v3.1: janela manhã só aplica em sáb/dom/feriado."""
    if janela_manha_aplica(data_iso) and cruza_janela(ini_min, fim_min, JANELA_PROIBIDA_MANHA):
        return True
    return cruza_janela(ini_min, fim_min, JANELA_PROIBIDA_TARDE)

def janela_label(ini_min, fim_min, data_iso):
    if janela_manha_aplica(data_iso) and cruza_janela(ini_min, fim_min, JANELA_PROIBIDA_MANHA):
        return "11h-13h"
    if cruza_janela(ini_min, fim_min, JANELA_PROIBIDA_TARDE):
        return "16h-19:30"
    return ""

def avaliar_dia(batidas, escala_dia, setor, data_iso, regime_estagio=False, justificativa=None):
    """Avalia 1 dia. data_iso é necessário pra regra de janela manhã condicional."""
    alertas = []
    tipo_escala, valor_escala = escala_dia
    batidas = (list(batidas) + [""] * 6)[:6]

    if tipo_escala in ("FOLGA", "FERIAS", "BH", "INATIVO"):
        bateu_algo = any(b not in ("", "Falta", "Folga", "Férias", "Banco", "Feriado", "Rescisão", "X", "-") for b in batidas[:4])
        if bateu_algo and tipo_escala == "FERIAS":
            alertas.append({"tipo":"TRABALHOU_EM_FERIAS","severidade":"alert","descricao":"Bateu ponto durante férias previstas","evidencia":" · ".join([b for b in batidas[:4] if b])})
        return alertas, "folga"

    prev_ini_str, prev_fim_str = valor_escala
    prev_ini = parse_hhmm(prev_ini_str); prev_fim = parse_hhmm(prev_fim_str)

    todas_falta = all(b in ("Falta", "") for b in batidas[:4])
    if todas_falta:
        if justificativa and justificativa in JUSTIFICATIVAS_QUE_EXCLUEM_FALTA:
            sev = "alert" if justificativa == "Suspensão" else "info"
            alertas.append({"tipo":"FALTA_JUSTIFICADA","severidade":sev,"descricao":f"Ausência justificada: {justificativa}","evidencia":f"Previsto: {prev_ini_str} → {prev_fim_str}"})
            return alertas, "ok" if sev == "info" else "alert"
        alertas.append({"tipo":"FALTA_SECA","severidade":"crit","descricao":"Falta sem justificativa registrada","evidencia":f"Previsto: {prev_ini_str} → {prev_fim_str}"})
        return alertas, "falta"

    e1 = parse_hhmm(batidas[0]); s1 = parse_hhmm(batidas[1])
    e2 = parse_hhmm(batidas[2]); s2 = parse_hhmm(batidas[3])
    e3 = parse_hhmm(batidas[4]); s3 = parse_hhmm(batidas[5])
    todas = [b for b in [e1, s1, e2, s2, e3, s3] if b is not None]

    seq_ok = all(todas[i] <= todas[i+1] for i in range(len(todas)-1)) if todas else True
    if not seq_ok:
        alertas.append({"tipo":"MARCACOES_INCOERENTES","severidade":"alert","descricao":"Sequência de batidas fora de ordem — VERIFICAR MANUALMENTE","evidencia":" / ".join([b for b in batidas[:6] if b])})

    if e1 is not None and prev_ini is not None:
        diff = e1 - prev_ini
        if diff > TOL_ATRASO_ENTRADA:
            alertas.append({"tipo":"ATRASO_ENTRADA","severidade":"alert","descricao":f"Atraso de {diff} min na entrada","evidencia":f"Bateu {hhmm_str(e1)} · previsto {hhmm_str(prev_ini)}"})

    ultimas = [b for b in [s3, s2, s1] if b is not None]
    if ultimas and prev_fim is not None:
        ultima = ultimas[0]
        diff = ultima - prev_fim
        if diff < -TOL_SAIDA:
            alertas.append({"tipo":"SAIDA_ANTECIPADA","severidade":"alert","descricao":f"Saiu {-diff} min antes do previsto","evidencia":f"Bateu {hhmm_str(ultima)} · previsto {hhmm_str(prev_fim)}"})
        elif diff > TOL_SAIDA:
            alertas.append({"tipo":"HORA_EXTRA","severidade":"info","descricao":f"Hora extra de {diff} min após o previsto","evidencia":f"Bateu {hhmm_str(ultima)} · previsto {hhmm_str(prev_fim)}"})

    intervalos = []
    if s1 is not None and e2 is not None: intervalos.append(("INT1", s1, e2))
    if s2 is not None and e3 is not None: intervalos.append(("INT2", s2, e3))
    setor_restrito = setor in SETORES_RESTRITOS

    if not regime_estagio:
        for nm, ini, fim in intervalos:
            dur = fim - ini
            if dur < INTERVALO_MIN:
                alertas.append({"tipo":"INTERVALO_CURTO","severidade":"alert","descricao":f"Intervalo de {dur} min (abaixo de 1h)","evidencia":f"{hhmm_str(ini)} → {hhmm_str(fim)}"})
            elif dur > INTERVALO_MAX:
                alertas.append({"tipo":"INTERVALO_LONGO","severidade":"alert","descricao":f"Intervalo de {hhmm_str(dur)} (acima de 1h05)","evidencia":f"{hhmm_str(ini)} → {hhmm_str(fim)}"})
            if setor_restrito and cruza_alguma_janela_proibida(ini, fim, data_iso):
                alertas.append({"tipo":"JANELA_PROIBIDA","severidade":"crit","descricao":f"Descanso em janela proibida ({janela_label(ini, fim, data_iso)}) — setor restrito","evidencia":f"{hhmm_str(ini)} → {hhmm_str(fim)}"})
        if e1 is not None and ultimas and not intervalos:
            total = ultimas[0] - e1
            if total > JORNADA_MIN_INTERVALO_OBRIGATORIO:
                alertas.append({"tipo":"PULOU_INTERVALO","severidade":"crit","descricao":f"Trabalhou {hhmm_str(total)} sem intervalo registrado (limite CLT 6h)","evidencia":f"Entrou {hhmm_str(e1)} · saiu {hhmm_str(ultimas[0])}"})

    if any(a["severidade"] == "crit" for a in alertas): status = "crit"
    elif any(a["severidade"] == "alert" for a in alertas): status = "alert"
    else: status = "ok"
    return alertas, status

def processar_colaborador(nome, setor, dias, justificativas=None, regime_estagio=False):
    """Cada dia em `dias` deve ter: data, tipo_escala, valor_escala, batidas."""
    just = justificativas or {}
    res_dias = []
    contadores = {"falta_seca":0,"falta_justificada":0,"atraso":0,"saida_fora":0,"hora_extra":0,"interv_curto":0,"interv_longo":0,"janela_proib":0,"pulou_interv":0,"incoerente":0,"trabalhou_ferias":0}
    for dia in dias:
        esc = (dia["tipo_escala"], dia["valor_escala"])
        alertas, st = avaliar_dia(dia["batidas"], esc, setor, dia["data"], regime_estagio, just.get(dia["data"]))
        res_dias.append({"data":dia["data"],"tipo_escala":dia["tipo_escala"],"valor_escala":dia["valor_escala"],"batidas":dia["batidas"],"alertas":alertas,"status":st})
        for a in alertas:
            mp = {"FALTA_SECA":"falta_seca","FALTA_JUSTIFICADA":"falta_justificada","ATRASO_ENTRADA":"atraso","SAIDA_ANTECIPADA":"saida_fora","HORA_EXTRA":"hora_extra","INTERVALO_CURTO":"interv_curto","INTERVALO_LONGO":"interv_longo","JANELA_PROIBIDA":"janela_proib","PULOU_INTERVALO":"pulou_interv","MARCACOES_INCOERENTES":"incoerente","TRABALHOU_EM_FERIAS":"trabalhou_ferias"}
            k = mp.get(a["tipo"])
            if k: contadores[k] += 1
    if contadores["falta_seca"] >= 1 or contadores["janela_proib"] >= 1 or contadores["pulou_interv"] >= 1: status = "crit"
    elif sum(contadores.values()) > 0: status = "alert"
    else: status = "ok"
    return {"setor":setor,"restrito":setor in SETORES_RESTRITOS,"dias":res_dias,"contadores":contadores,"status":status}
