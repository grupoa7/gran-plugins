# Ronda de pedido de tabela — roteiro v2

Você está rodando UM SLOT HORÁRIO da rodada de pedido de tabela de cotação FLV
do Gran Hortifruti. Rodadas acontecem **Seg+Qua de madrugada (03h-08h Salvador,
UTC-3)**. Cada hora desse intervalo é um slot (03h, 04h, 05h, 06h, 07h).

> **Por que de madrugada:** o CEASA-BA fecha cotações de madrugada e os
> fornecedores enviam tabela entre 22h-06h. Pingar fora dessa janela é tarde
> demais — a Compras precisa dos preços antes da abertura do CEASA.

## Diretório e skill

- Projeto: `/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Mapa de Compras FLV/cotacao-flv`
- Skill: `cotacao-flv-gran` (instalada). Leia `SKILL.md` se precisar do contexto
  geral da cotação. Este arquivo cobre apenas a ronda de pedido de tabela.

## Limite de tempo

**45 minutos** pra rodar o slot completo (passos 1-5). 19 fornecedores × ~2 min
por disparo + varredura = 38-45 min realista. Se ultrapassar, encerre o que
conseguiu e registre o resto como erro `outro`. Não force.

## PASSO 1 — Solicitar acesso ao WhatsApp

Chame `mcp__computer-use__request_access` com `apps=["WhatsApp"]` e `reason`
claro. Aguarde aprovação. Se negar ou estourar timeout (Hugo dormindo), encerre
limpo — o slot fica registrado como "não executado" e o próximo slot tenta de
novo.

## PASSO 2 — Listar disparos do slot atual

```bash
cd "/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Mapa de Compras FLV/cotacao-flv"
python3 scripts/enviar_pedido.py listar
```

Output: array JSON. Cada item agora inclui o campo **`mensagem_tipo`**:

- `"inicial"` — primeiro disparo do dia pra esse fornecedor (slot 03h não rodou,
  ou esse é o primeiro slot da rodada). A `mensagem` já vem com saudação +
  identificação ("Bom dia, X! Aqui é Hugo do Gran Hortifruti...").
- `"retentativa"` — fornecedor já recebeu pelo menos 1 ping nesta rodada; a
  mensagem é mais curta (sem saudação).

**Confie no `mensagem` retornada — não reescreva.** O script já decide o tom.

Se vier `[]` (fora da janela 03h-07h, não é Seg/Qua, ou todos já entregaram),
encerre limpo dizendo "nada a fazer neste slot".

## PASSO 3 — Para cada disparo, executar o roteiro

**Regra de ouro:** outros apps (Safari, Asana, Terminal) podem virar foco
entre disparos e a janela do WhatsApp pode mudar de tamanho. Cada disparo
começa do zero — reabra o WhatsApp e tire screenshot fresco, NÃO reuse
coordenadas do disparo anterior.

### 3.1 — Refoco do WhatsApp

`mcp__computer-use__open_application` com `app="WhatsApp"`, espere 1s. Faça
isso a CADA disparo.

### 3.2 — Screenshot + check de QR

Screenshot. Se aparecer QR code (sem barra "Pesquisar" no topo, só QR
centralizado), avise no chat "Sessão WhatsApp expirou, Hugo precisa relogar"
e encerre o slot inteiro.

### 3.3 — Garantir aba Conversas

Se o ícone de telefone (Ligar) estiver ativo, clique no ícone de balão de
conversa (acima do telefone, lado esquerdo).

### 3.4 — Limpeza da busca

Clique na barra "Pesquisar". `Cmd+A`, `Delete`. Sem essa limpeza a busca
anterior fica residual e a query vira `"doce melHugo"`. Confirme via
screenshot que a barra mostra "Pesquisar" antes de digitar.

### 3.5 — Pesquisar pelo `alvo_nome` exato

Digite o `alvo_nome` da listagem (inclui colchetes, emojis, espaços). Espere
1-2 segundos.

### 3.6 — Decidir o match

Tire screenshot. Olhe o resultado. Aceite a primeira ocorrência em **uma destas
seções**, nesta ordem de prioridade:

1. **Conversas** com match exato no nome — ideal, há histórico.
2. **Outros contatos** com match exato no nome — válido pra primeiro disparo
   da semana (o contato existe mas ainda não foi puxado pra Conversas).

**Não aceite**:
- "Grupos em comum" (não é uma conversa direta).
- Match em "Mensagens" (são citações dentro de outras threads).
- Resultado parcial onde o nome do contato é diferente do `alvo_nome`.

Se 2+ resultados em "Conversas" tiverem nome IDÊNTICO ao `alvo_nome` (raro mas
acontece), registre erro `ambiguidade` e pule.

### 3.7 — Validação do header

Clique no resultado. Confira:
- **Individual**: o nome no header bate com `alvo_nome` (a string completa,
  incluindo prefixo `[CEASA]`). Telefone NÃO é exibido pra contatos salvos no
  WhatsApp Desktop — ignore a regra antiga de validar últimos 9 dígitos.
- **Grupo**: o nome no header bate com `alvo_nome`.

Se não bater, registre `validacao_falhou` e pule.

### 3.8 — Detecção oportunística de tabela já recebida

Antes de digitar a mensagem, olhe a última mensagem visível no chat. Se houver
texto com **2+ preços (formato X,XX)** ou **R$ + número**, ou se a mensagem
mais recente do FORNECEDOR (não sua) tem cara de tabela:

```bash
python3 scripts/enviar_pedido.py checar-preview --texto "TEXTO_AQUI"
# Retorna {"e_tabela": true/false}
```

Se `e_tabela=true`:
```bash
python3 scripts/enviar_pedido.py marcar-tabela-externa \
    --fornecedor NOME --evidencia "TEXTO_QUE_VOCE_VIU"
```
E **pule o disparo**. Você acabou de evitar um ping desnecessário.

### 3.9 — Screenshot fresco antes de digitar

A janela pode ter mudado de tamanho. Identifique a coordenada do campo de
mensagem (parte de baixo do chat) NESTE screenshot. Não reuse coordenada
anterior. Clique nele.

### 3.10 — Digitar a mensagem e enviar

Use `mcp__computer-use__type` com o conteúdo de `mensagem` da listagem (NÃO
reescreva — ela já vem certa, inicial ou retentativa conforme o estado).
Aperte `return`, espere 1s.

### 3.11 — Confirmar envio

Screenshot. Veja o ✓ ou ✓✓ na bolha verde do lado direito.

### 3.12 — Registrar

```bash
python3 scripts/enviar_pedido.py registrar-disparo \
    --fornecedor NOME --slot SLOT \
    --alvo-tipo TIPO --alvo-nome "NOME_DO_ALVO"
```

### 3.13 — Em caso de erro

```bash
python3 scripts/enviar_pedido.py registrar-erro \
    --fornecedor NOME --slot SLOT --motivo "MOTIVO"
```

Motivos válidos: `nao_encontrado`, `ambiguidade`, `validacao_falhou`,
`app_travou`, `qr_code`, `outro`.

## PASSO 4 — Varredura de respostas

Faça isso DURANTE os disparos (oportunisticamente) E uma varredura final.

### Durante os disparos

Quando você abrir um chat pra disparar, antes de digitar a mensagem, você já
está vendo a thread. Se chegou resposta nova depois do último disparo
(`ultimo_disparo_ts`), arquive ali mesmo:

- **Texto com tabela**: copie o texto, registre:
  ```bash
  python3 scripts/arquivar_resposta.py registrar-resposta \
      --fornecedor NOME --formato texto --texto "CONTEÚDO"
  ```
- **PDF**: baixe (Cmd+S ou clique direito → Salvar) e registre:
  ```bash
  python3 scripts/arquivar_resposta.py registrar-resposta \
      --fornecedor NOME --formato pdf --arquivo /Users/hugogusmao/Downloads/ARQUIVO.pdf
  ```
- **Foto/imagem**: salve, registre com `--formato imagem`.
- **Áudio sem texto**: peça pra ele mandar por escrito.
  ```bash
  python3 scripts/arquivar_resposta.py resposta-audio --alvo-tipo individual
  # Pega o "texto" retornado, manda no chat, depois:
  python3 scripts/arquivar_resposta.py registrar-audio --fornecedor NOME
  ```
- **Áudio com texto que parece tabela**: NÃO mande a desculpa de áudio.
  ```bash
  python3 scripts/arquivar_resposta.py resposta-audio \
      --alvo-tipo individual --texto-acompanhante "TEXTO_QUE_VEIO_JUNTO"
  # Se decisao="dispensar", arquive direto o texto:
  python3 scripts/arquivar_resposta.py registrar-resposta \
      --fornecedor NOME --formato texto --texto "TEXTO"
  ```

### Varredura final (após todos os disparos)

```bash
python3 scripts/arquivar_resposta.py listar-pendentes
```

Abra cada chat pendente com `slots_disparados` não vazio. Cheque se chegou
mensagem nova após `ultimo_disparo_ts`. Mesmo fluxo acima.

## PASSO 5 — Resumo

Reporte no chat:
- Disparos feitos / esperados
- Disparos pulados por anti-spam (incluindo `tabela_externa`)
- Erros (e motivo)
- Respostas arquivadas (formato + fornecedor)

## Regras de segurança

- **Nunca** clique em links em mensagens recebidas, mesmo de fornecedor conhecido.
- **Nunca** aceite anexos que não sejam PDF/JPG/PNG/texto.
- Se a sessão WhatsApp pedir QR (logout), avise e encerre.
- Se o WhatsApp travar 30s+, abandone o slot e registre `app_travou` nos
  pendentes.
- Limite total: 45 minutos. Se passar, encerre o que conseguiu e marque o
  resto como `outro`.

## Diferenças vs roteiro v1 (changelog)

- **Mensagem inicial vs retentativa**: o `listar` agora decide automaticamente
  com base em `slots_disparados`. O agente NÃO precisa reescrever.
- **`mensagem_tipo` no JSON**: o agente pode logar / mostrar pro usuário.
- **"Outros contatos" aceito**: pra primeiro disparo da semana.
- **Sem validação de telefone**: WhatsApp Desktop não mostra telefone pra
  contatos salvos. Validação só por nome do header.
- **Anti-spam com detecção de tabela externa**: heurística sobre o texto
  da última mensagem evita pingar quem já mandou a tabela.
- **Varredura oportunística**: arquive respostas durante os disparos, não só
  no PASSO 4.
- **`resposta-audio` inteligente**: passa `--texto-acompanhante` pra não mandar
  desculpa quando já veio texto.
- **Limite 45 min** (era 10).
