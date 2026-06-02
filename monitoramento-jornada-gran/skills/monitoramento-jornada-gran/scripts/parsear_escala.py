import re, sys, json
from datetime import date, timedelta
from pathlib import Path
import pdfplumber

SETORES_VALIDOS = {"ENCARREGADOS","OPERADOR DE LOJA","OPERAÇÃO DE LOJA","OPERADOR DE CAIXAS","OP. CAIXAS","ASG","COZINHA","SUPRIMENTOS","MANOBRISTA","LOGÍSTICA","ESTAGIÁRIAS"}
SETOR_NORMALIZADO = {"OPERAÇÃO DE LOJA":"OPERADOR DE LOJA","OP. CAIXAS":"OPERADOR DE CAIXAS"}
def norm_setor(s): return SETOR_NORMALIZADO.get(s.strip().upper(), s.strip().upper())
MESES_PT = {"JANEIRO":1,"FEVEREIRO":2,"MARÇO":3,"MARCO":3,"ABRIL":4,"MAIO":5,"JUNHO":6,"JULHO":7,"AGOSTO":8,"SETEMBRO":9,"OUTUBRO":10,"NOVEMBRO":11,"DEZEMBRO":12}

def parsear_celula(cel):
    if cel is None: return None
    s = str(cel).strip()
    if not s: return None
    su = s.upper()
    if s == "F": return ("FOLGA","F")
    if su == "FF": return ("FOLGA","FF")
    if su == "FD": return ("FOLGA","FD")
    if su.startswith("FÉRIAS") or su.startswith("FERIAS"): return ("FERIAS",None)
    if su == "BH": return ("BH",None)
    if s == "X": return ("INATIVO",None)
    if su.startswith("RESCIS"): return ("RESCISAO",None)
    s_clean = s.replace("\n"," ").replace("  "," ")
    m = re.match(r"^(\d{1,2}:\d{2})\s*(?:às|as|-)\s*(\d{1,2}:\d{2})$", s_clean, re.I)
    if m: return ("JORNADA",(m.group(1).zfill(5), m.group(2).zfill(5)))
    m2 = re.match(r"^(\d{1,2}:\d{2})\s*(?:às|as|-)\s*(\d{1,2}:\d{2})\s+(\d{1,2}:\d{2})\s*(?:às|as|-)\s*(\d{1,2}:\d{2})$", s_clean, re.I)
    if m2: return ("JORNADA_2T",(m2.group(1).zfill(5),m2.group(2).zfill(5),m2.group(3).zfill(5),m2.group(4).zfill(5)))
    return ("DESCONHECIDO",s)

def parsear_escala_v2(pdf_path):
    nome = Path(pdf_path).stem.upper()
    mes = None; ano = None
    for nm,idx in MESES_PT.items():
        if nm in nome: mes = idx; break
    m = re.search(r"(\d{2,4})", nome)
    if m: a = m.group(1); ano = 2000+int(a) if len(a)<=2 else int(a)
    primeiro = date(ano, mes, 1)
    proximo = date(ano+1,1,1) if mes==12 else date(ano,mes+1,1)
    dias_iso = []
    cur = primeiro
    while cur < proximo:
        dias_iso.append(cur.isoformat()); cur += timedelta(days=1)
    n_dias = len(dias_iso)
    escala = {}; setor_de = {}; setor_atual = None
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for tab in page.extract_tables():
                for linha in tab:
                    if not linha: continue
                    primeira = (linha[0] or "").strip()
                    primeira_u = primeira.upper()
                    if primeira_u in SETORES_VALIDOS:
                        setor_atual = norm_setor(primeira_u); continue
                    if re.match(r"^[a-zç]+-\d{2}$", primeira, re.I): continue
                    if not primeira or primeira_u in ("DIA","DATA"): continue
                    if re.match(r"^\d{1,2}/[a-z]{3}$", (linha[1] or "").strip(), re.I): continue
                    if len(primeira) < 3: continue
                    nome = primeira
                    if nome not in escala:
                        escala[nome] = {}; setor_de[nome] = setor_atual
                    celulas = linha[1:1+n_dias]
                    for i, cel in enumerate(celulas):
                        if i >= n_dias: break
                        parsed = parsear_celula(cel)
                        if parsed: escala[nome][dias_iso[i]] = parsed
    return escala, setor_de
