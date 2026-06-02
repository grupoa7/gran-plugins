"""
envio_lib.py — Biblioteca compartilhada do fluxo de disparo automático de pedido de tabela
(skill cotacao-flv-gran — usada por enviar_pedido.py, arquivar_resposta.py e relatorio_rodada.py).

Responsabilidades:
  - Resolver pasta da skill + pasta de dados (compatível com host e sandbox)
  - Carregar fornecedores filtrados por envio_automatico
  - Carregar templates de mensagem (individual + grupo)
  - Calcular slot horário atual baseado em hora de Salvador (UTC-3)
  - Decidir alvo por slot (grupo vs individual)
  - Formatar mensagem (substituir {nome})
  - Ler/escrever manifest.json da rodada
  - Checks de anti-spam e auto-desativação

Princípios:
  - Sem dependências externas (só stdlib) — facilita rodar em qualquer ambiente
  - Funções puras quando possível — testáveis e reusáveis
  - Manifest é append-only no formato JSONL (uma entrada por linha) pra evitar
    corrupção em escrita concorrente; finalização agrega em manifest.json
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
from pathlib import Path

# --------------------------------------------------------------------------- #
# Constantes de path
# --------------------------------------------------------------------------- #

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"
# Dados mutáveis vivem no PROJETO (gravável); o pacote da skill é read-only quando instalado.
# Compatível com COTACAO_DADOS (usado pelo cotar.py).
DADOS_DIR = Path(os.environ.get("COTACAO_DADOS") or (SKILL_DIR / "dados"))
RODADAS_DIR = DADOS_DIR / "cotacoes_recebidas"

FORNECEDORES_JSON = TEMPLATES_DIR / "fornecedores.json"
MENSAGENS_JSON = TEMPLATES_DIR / "mensagens_pedido.json"

# Fuso de Salvador (sem DST — UTC-3 fixo)
TZ_SALVADOR = _dt.timezone(_dt.timedelta(hours=-3), name="America/Bahia")

# Janela de slots horários da rodada
SLOTS = ("03h", "04h", "05h", "06h", "07h")
SLOT_HORAS = {"03h": 3, "04h": 4, "05h": 5, "06h": 6, "07h": 7}
SLOT_LEITURA_FINAL = "08h"

# Slots que escalam pro individual mesmo se houver grupo
SLOTS_INDIVIDUAL_ONLY = ("06h", "07h")

# Dias da semana com rodada (segunda=0, quarta=2 no padrão Python weekday())
DIAS_RODADA = (0, 2)  # Segunda e Quarta

# Defaults de proteção
ANTI_SPAM_JANELA_HORAS = 4
AUTO_DESATIVAR_RODADAS_SEM_RESPOSTA = 3


# --------------------------------------------------------------------------- #
# Carregamento de configs
# --------------------------------------------------------------------------- #

def carregar_fornecedores_envio() -> list[dict]:
    """Lê fornecedores.json e filtra os com envio_automatico=true.
    Retorna lista de dicts com todos os campos do fornecedor.
    """
    try:
        data = json.loads(FORNECEDORES_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Falha ao ler {FORNECEDORES_JSON}: {e}") from e
    todos = data.get("fornecedores", [])
    return [f for f in todos if f.get("envio_automatico") is True]


def carregar_mensagens() -> dict:
    """Lê mensagens_pedido.json. Retorna o dict completo (com 'individual',
    'grupo', 'audio_response_*', '_calendario').
    """
    try:
        return json.loads(MENSAGENS_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"Falha ao ler {MENSAGENS_JSON}: {e}") from e


# --------------------------------------------------------------------------- #
# Cálculo de slot e rodada
# --------------------------------------------------------------------------- #

def agora_salvador() -> _dt.datetime:
    """Hora atual em Salvador/BA (UTC-3)."""
    return _dt.datetime.now(TZ_SALVADOR)


def slot_atual(now: _dt.datetime | None = None) -> str | None:
    """Retorna '03h'|'04h'|'05h'|'06h'|'07h'|'08h' baseado na hora atual em Salvador.
    Retorna None se estiver fora da janela 03:00-08:59.
    """
    now = now or agora_salvador()
    h = now.hour
    if h == 8:
        return SLOT_LEITURA_FINAL
    for slot, hora in SLOT_HORAS.items():
        if h == hora:
            return slot
    return None


def e_dia_de_rodada(now: _dt.datetime | None = None) -> bool:
    """Segunda ou Quarta em Salvador."""
    now = now or agora_salvador()
    return now.weekday() in DIAS_RODADA


def rodada_str(now: _dt.datetime | None = None) -> str:
    """Chave da rodada: 'AAAA-MM-DD' do dia atual em Salvador."""
    now = now or agora_salvador()
    return now.strftime("%Y-%m-%d")


def rodada_dir(rodada: str | None = None) -> Path:
    """Pasta da rodada. Cria se não existir."""
    rodada = rodada or rodada_str()
    p = RODADAS_DIR / rodada
    p.mkdir(parents=True, exist_ok=True)
    return p


# --------------------------------------------------------------------------- #
# Roteamento de alvo + formatação de mensagem
# --------------------------------------------------------------------------- #

def decidir_alvo(fornecedor: dict, slot: str) -> dict:
    """Decide pra quem mandar a msg neste slot.

    Returns:
        {
          "tipo": "individual" | "grupo",
          "nome": "[CEASA] Marcos Qualisuper" | "Doce Mel + GRAN",
          "template_categoria": "individual" | "grupo",
          "template_key": "slot_03h",
        }
    """
    if slot not in SLOTS:
        raise ValueError(f"Slot inválido: {slot}. Aceitos: {SLOTS}")

    grupo_nome = fornecedor.get("envio_grupo_nome")
    tem_grupo = bool(grupo_nome)

    # Slots 06h e 07h sempre vão pro individual (fallback)
    # Slots 03h, 04h, 05h vão pro grupo se houver, senão individual
    se_pode_grupo = tem_grupo and slot not in SLOTS_INDIVIDUAL_ONLY

    if se_pode_grupo:
        return {
            "tipo": "grupo",
            "nome": grupo_nome,
            "template_categoria": "grupo",
            "template_key": f"slot_{slot}",
        }
    return {
        "tipo": "individual",
        "nome": fornecedor.get("envio_individual_nome"),
        "template_categoria": "individual",
        "template_key": f"slot_{slot}",
    }


def formatar_mensagem(template: str, nome_chamada: str) -> str:
    """Substitui {nome} pelo nome_chamada do fornecedor."""
    return template.replace("{nome}", nome_chamada or "amigo")


def mensagem_para_disparo(fornecedor: dict, slot: str, mensagens: dict,
                          estado_fornecedor: dict | None = None) -> str:
    """Helper de alto nível: dado fornecedor + slot, retorna a string final da msg.

    Se `estado_fornecedor` for passado e `slots_disparados` estiver vazio, usa o
    template 'inicial' (com saudação + identificação) ao invés do slot_NNh — isso
    evita mensagem de retentativa indevida quando o slot 03h foi pulado e o slot
    04h vira o primeiro contato do dia.

    A categoria do template inicial segue o alvo decidido (individual vs grupo).
    """
    alvo = decidir_alvo(fornecedor, slot)
    cat = alvo["template_categoria"]
    key = alvo["template_key"]

    primeiro_disparo_da_rodada = (
        estado_fornecedor is not None
        and not (estado_fornecedor or {}).get("slots_disparados")
    )
    if primeiro_disparo_da_rodada:
        inicial = mensagens.get("inicial", {})
        template = inicial.get(cat)
        if template:
            return formatar_mensagem(template, fornecedor.get("envio_nome_chamada", "amigo"))

    template = mensagens.get(cat, {}).get(key)
    if not template:
        raise KeyError(f"Template não encontrado: {cat}.{key}")
    return formatar_mensagem(template, fornecedor.get("envio_nome_chamada", "amigo"))


def mensagem_complemento_apos_indevida(fornecedor: dict, slot: str, mensagens: dict) -> str:
    """Texto curto para corrigir um disparo de retentativa que deveria ter sido
    inicial. Usado quando o agente percebe (ou Hugo aponta) que mandou template
    de retry como primeiro contato."""
    alvo = decidir_alvo(fornecedor, slot)
    cat = alvo["template_categoria"]
    template = mensagens.get("complemento_apos_retentativa_indevida", {}).get(cat)
    if not template:
        # Fallback genérico se o JSON for de versão antiga
        return "Bom dia! Aqui é Hugo do Gran Hortifruti. A mensagem inicial pedindo a tabela ficou travada aqui."
    return formatar_mensagem(template, fornecedor.get("envio_nome_chamada", "amigo"))


# --------------------------------------------------------------------------- #
# Manifest (JSONL append-only + agregação)
# --------------------------------------------------------------------------- #

def _manifest_jsonl(rodada: str | None = None) -> Path:
    """Arquivo JSONL append-only (uma entrada por linha)."""
    return rodada_dir(rodada) / "manifest.jsonl"


def _manifest_json(rodada: str | None = None) -> Path:
    """Arquivo JSON agregado (snapshot do estado da rodada)."""
    return rodada_dir(rodada) / "manifest.json"


def registrar_evento(entrada: dict, rodada: str | None = None) -> None:
    """Append-only no manifest.jsonl. Cada evento tem campos mínimos:
        - ts: ISO-8601 (Salvador)
        - tipo: "disparo" | "resposta" | "erro" | "anti_spam_pulou" | "auto_desativado"
        - fornecedor: nome do fornecedor (ex: "QUALISUPER")
        - + campos específicos do evento
    """
    entrada.setdefault("ts", agora_salvador().isoformat())
    path = _manifest_jsonl(rodada)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def ler_eventos(rodada: str | None = None) -> list[dict]:
    """Lê todos os eventos da rodada (lista de dicts). Vazia se rodada não existe."""
    path = _manifest_jsonl(rodada)
    if not path.exists():
        return []
    eventos = []
    with path.open("r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                try:
                    eventos.append(json.loads(linha))
                except json.JSONDecodeError:
                    continue
    return eventos


def agregar_manifest(rodada: str | None = None) -> dict:
    """Snapshot do estado da rodada a partir dos eventos.
    Retorna dict no formato:
        {
          "rodada": "2026-06-01",
          "fornecedores": {
              "QUALISUPER": {
                  "slots_disparados": ["03h", "04h"],
                  "ultimo_disparo_ts": "...",
                  "ultimo_alvo_tipo": "individual",
                  "ultimo_alvo_nome": "...",
                  "status": "pendente" | "recebido" | "furou" | "erro",
                  "resposta": { "formato": "pdf", "arquivo": "...", "ts": "..." } | None,
                  "erros": [...]
              },
              ...
          }
        }
    """
    rodada = rodada or rodada_str()
    eventos = ler_eventos(rodada)
    forn_state: dict[str, dict] = {}

    for ev in eventos:
        nome = ev.get("fornecedor")
        if not nome:
            continue
        st = forn_state.setdefault(nome, {
            "slots_disparados": [],
            "ultimo_disparo_ts": None,
            "ultimo_alvo_tipo": None,
            "ultimo_alvo_nome": None,
            "status": "pendente",
            "resposta": None,
            "erros": [],
            "anti_spam_pulado": 0,
        })
        tipo = ev.get("tipo")
        if tipo == "disparo":
            slot = ev.get("slot")
            if slot and slot not in st["slots_disparados"]:
                st["slots_disparados"].append(slot)
            st["ultimo_disparo_ts"] = ev.get("ts")
            st["ultimo_alvo_tipo"] = ev.get("alvo_tipo")
            st["ultimo_alvo_nome"] = ev.get("alvo_nome")
        elif tipo == "resposta":
            st["status"] = "recebido"
            st["resposta"] = {
                "formato": ev.get("formato"),
                "arquivo": ev.get("arquivo"),
                "ts": ev.get("ts"),
            }
        elif tipo == "erro":
            st["erros"].append({
                "ts": ev.get("ts"),
                "motivo": ev.get("motivo"),
                "slot": ev.get("slot"),
            })
            if st["status"] == "pendente":
                st["status"] = "erro"
        elif tipo == "anti_spam_pulou":
            st["anti_spam_pulado"] += 1

    # Marca como "furou" quem disparou todos os 5 slots sem resposta e já passou das 08h
    agora = agora_salvador()
    if agora.hour >= 8 or agora.hour < 3:  # fora da janela (já passou ou ainda não começou)
        for nome, st in forn_state.items():
            if st["status"] == "pendente" and len(st["slots_disparados"]) >= len(SLOTS):
                st["status"] = "furou"

    snapshot = {
        "rodada": rodada,
        "fornecedores": forn_state,
    }
    # Persiste o snapshot
    path = _manifest_json(rodada)
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return snapshot


# --------------------------------------------------------------------------- #
# Anti-spam e auto-desativação
# --------------------------------------------------------------------------- #

def ja_disparou_neste_slot(estado_fornecedor: dict, slot: str) -> bool:
    """Já foi disparado pra este fornecedor neste slot na rodada atual?"""
    return slot in (estado_fornecedor or {}).get("slots_disparados", [])


def ja_recebeu_resposta(estado_fornecedor: dict) -> bool:
    """Fornecedor já entregou a tabela nesta rodada?"""
    return (estado_fornecedor or {}).get("status") == "recebido"


def anti_spam_check(estado_fornecedor: dict, agora: _dt.datetime | None = None,
                    janela_horas: int = ANTI_SPAM_JANELA_HORAS) -> tuple[bool, str | None]:
    """Verifica se é seguro disparar para este fornecedor agora.

    Returns:
        (ok, motivo_pular)
          ok=True: pode disparar
          ok=False: motivo_pular contém razão (ex: "ja_recebido", "disparo_recente")

    Limitação MVP: só olha eventos do manifest (disparos automáticos). NÃO olha
    histórico de chat do WhatsApp pra detectar msgs manuais do Hugo. Pra V2.
    """
    if not estado_fornecedor:
        return True, None
    if ja_recebeu_resposta(estado_fornecedor):
        return False, "ja_recebido"
    agora = agora or agora_salvador()
    ultimo_ts = estado_fornecedor.get("ultimo_disparo_ts")
    if ultimo_ts:
        try:
            ultimo_dt = _dt.datetime.fromisoformat(ultimo_ts)
            delta = (agora - ultimo_dt).total_seconds() / 3600.0
            if delta < janela_horas:
                return False, f"disparo_ha_{delta:.1f}h"
        except (ValueError, TypeError):
            pass
    return True, None


def slots_executados(rodada: str | None = None) -> set[str]:
    """Retorna o conjunto de slots que tiveram pelo menos 1 evento (disparo, erro
    ou anti_spam_pulou) durante a rodada. Slot sem nenhum evento = não executou
    (provavelmente Claude desktop estava fechado).
    """
    eventos = ler_eventos(rodada)
    slots = set()
    for ev in eventos:
        slot = ev.get("slot")
        if slot in SLOTS:
            slots.add(slot)
    return slots


def slots_esperados_ate_agora(now: _dt.datetime | None = None) -> set[str]:
    """Retorna o conjunto de slots que JÁ DEVIAM ter rodado neste momento, baseado
    na hora atual em Salvador. Útil pra comparar contra slots_executados e detectar
    buracos (slots que deveriam ter rodado mas não rodaram — Claude fechado).
    """
    now = now or agora_salvador()
    h = now.hour
    esperados = set()
    for slot, hora in SLOT_HORAS.items():
        if h > hora or (h == hora and now.minute >= 5):
            # Margem de 5 min: se já são 03:05, considera que o slot 03h devia ter rodado
            esperados.add(slot)
    return esperados


def slots_perdidos(rodada: str | None = None, now: _dt.datetime | None = None) -> list[str]:
    """Lista os slots que deveriam ter rodado até agora mas NÃO rodaram.
    Tipicamente = Claude desktop ficou fechado naquele horário.
    Retorna ordenado por horário (03h → 07h).
    """
    executados = slots_executados(rodada)
    esperados = slots_esperados_ate_agora(now)
    perdidos = esperados - executados
    return [s for s in SLOTS if s in perdidos]


def listar_rodadas_anteriores(n: int = 10) -> list[str]:
    """Retorna as últimas N rodadas em ordem decrescente (mais recente primeiro)."""
    if not RODADAS_DIR.exists():
        return []
    rodadas = []
    for p in RODADAS_DIR.iterdir():
        if p.is_dir() and re.match(r"^\d{4}-\d{2}-\d{2}$", p.name):
            rodadas.append(p.name)
    return sorted(rodadas, reverse=True)[:n]


def contar_rodadas_sem_resposta(fornecedor_nome: str,
                                 n_rodadas: int = AUTO_DESATIVAR_RODADAS_SEM_RESPOSTA) -> int:
    """Conta quantas das últimas N rodadas o fornecedor não respondeu.
    Considera só rodadas onde houve pelo menos 1 disparo pra ele."""
    rodadas = listar_rodadas_anteriores(n_rodadas)
    sem_resposta = 0
    for r in rodadas:
        snap = agregar_manifest(r) if (_manifest_jsonl(r)).exists() else {"fornecedores": {}}
        st = snap.get("fornecedores", {}).get(fornecedor_nome)
        if not st:
            continue  # não participou dessa rodada
        if st.get("status") != "recebido":
            sem_resposta += 1
    return sem_resposta


def deve_auto_desativar(fornecedor_nome: str) -> bool:
    """True se o fornecedor deve ser auto-desativado (sem resposta nas últimas N rodadas)."""
    return contar_rodadas_sem_resposta(fornecedor_nome) >= AUTO_DESATIVAR_RODADAS_SEM_RESPOSTA


# --------------------------------------------------------------------------- #
# Detecção de tabela já recebida fora do manifest (WhatsApp manual)
# --------------------------------------------------------------------------- #

# Padrões que sinalizam tabela de preços no preview do WhatsApp
_PADROES_TABELA = [
    re.compile(r"R\$"),                          # cifrão
    re.compile(r"\bKG\b", re.IGNORECASE),       # unidade kg
    re.compile(r"\bCX\b", re.IGNORECASE),       # caixa
    re.compile(r"\d+[\,\.]\d{2}"),            # preço X,XX ou X.XX
    re.compile(r"\btabela\b", re.IGNORECASE),
    re.compile(r"\bpreço[s]?\b", re.IGNORECASE),
]

# Padrões que CONFIRMAM ser só confirmação/ruído (ignorar)
_PADROES_RUIDO = [
    re.compile(r"^(ok|tá|valeu|opa|oi|bom dia)\.?$", re.IGNORECASE),
    re.compile(r"^te mando", re.IGNORECASE),
    re.compile(r"^já mando", re.IGNORECASE),
    re.compile(r"^perdão", re.IGNORECASE),
    re.compile(r"^perdoa", re.IGNORECASE),
    re.compile(r"^👍+$"),
    re.compile(r"^👌+$"),
]


def detectar_tabela_no_preview(texto: str) -> bool:
    """Heurística: o preview de mensagem do WhatsApp parece conter tabela de preços?

    Sinais positivos (qualquer um dispara True):
      - 2+ preços no formato X,XX ou X.XX (ex: "125,00 ... 145,00")
      - 1 preço + palavra-chave (R$, tabela, kg, cx, preço)
      - R$ + 1 número qualquer

    Sinais negativos (curto-circuito False):
      - Mensagem curta de confirmação (ok/bom dia/te mando/perdão/👍)

    Conservador: na dúvida retorna False (= deixa o ping disparar). False-negative
    é melhor que false-positive aqui — pingar um fornecedor que já mandou tabela
    é menos pior do que NÃO pingar um fornecedor que ainda não mandou.
    """
    if not texto or not texto.strip():
        return False
    texto = texto.strip()
    if len(texto) < 6:
        return False

    if len(texto) < 80:
        for pat in _PADROES_RUIDO:
            if pat.search(texto):
                return False

    preco_re = re.compile(r"\d+[\,\.]\d{2}")
    precos = preco_re.findall(texto)
    if len(precos) >= 2:
        return True

    palavra_chave_re = re.compile(
        r"\bR\$|\btabela\b|\bkg\b|\bcx\b|\bpreço[s]?\b",
        re.IGNORECASE,
    )
    tem_palavra = bool(palavra_chave_re.search(texto))

    if len(precos) >= 1 and tem_palavra:
        return True

    # R$ + qualquer número solto também conta (ex: "R$ 165")
    if re.search(r"R\$\s*\d", texto):
        return True

    return False


def registrar_tabela_externa(fornecedor: str, evidencia: str = "",
                              rodada: str | None = None) -> None:
    """Registra que o fornecedor JÁ MANDOU tabela fora do fluxo do manifest
    (ex: tabela vigente de ontem ainda válida, ou mensagem manual do Hugo).
    Marca como recebido externo — anti_spam_check vai pular este fornecedor.
    """
    registrar_evento({
        "tipo": "resposta",
        "fornecedor": fornecedor,
        "formato": "externo",
        "evidencia": evidencia,
    }, rodada=rodada)


# --------------------------------------------------------------------------- #
# Validação de número (segurança)
# --------------------------------------------------------------------------- #

_NUM_PATTERN = re.compile(r"[^\d+]")


def normalizar_telefone(s: str) -> str:
    """Reduz pra só dígitos com '+' opcional na frente.
    Ex: '+55 71 99374-5500' -> '+5571993745500'
    """
    if not s:
        return ""
    return _NUM_PATTERN.sub("", s).strip()


def telefones_batem(esperado: str, observado: str) -> bool:
    """Compara dois telefones normalizando formato. Aceita match parcial nos últimos
    9 dígitos (ignora código do país opcional).
    """
    a = normalizar_telefone(esperado)
    b = normalizar_telefone(observado)
    if not a or not b:
        return False
    if a == b:
        return True
    # Compara últimos 9 dígitos (DDD + número sem código país)
    return a[-9:] == b[-9:] and len(a) >= 9 and len(b) >= 9
