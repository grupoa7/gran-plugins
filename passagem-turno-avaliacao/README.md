# passagem-turno-avaliacao

Plugin Cowork pro Gran Hortifruti. Avalia cards de Passagem de Turno (Pipefy), aplica rubrica v2 (escala foto 0-3, regra ouro de ruptura) e dispara mensagens privadas + resumo semanal de lideranca.

## Setup obrigatorio antes do primeiro uso

Esta skill precisa de um arquivo `config.md` LOCAL com dados sensiveis (telefones de funcionarios). Esses dados NAO entram no repo Git.

**1. Copie o template e preencha os dados reais:**

```bash
cd <pasta-da-skill>/skills/passagem-turno-avaliacao/templates
cp config.template.md config.md
```

**2. Edite `config.md`** preenchendo os placeholders:
- `{TELEFONE_SILVIO}` -> numero real do encarregado (formato +5571XXXXXXXXX)
- `{TELEFONE_ALYNE}` -> numero real da encarregada

**3. Confirme que `config.md` esta no `.gitignore` raiz do repo** (ja esta por default).

## Dependencias

- Chrome MCP conectado (Pipefy + WhatsApp Web logados)
- Sessao Pipefy: `hugo@grupoa7.com.br`
- Sessao WhatsApp: sessao da Fran (onde Silvio e Alyne estao na agenda)
- Python 3 + openpyxl (`pip install openpyxl --break-system-packages`) pra `adicionar_excel.py`

## Comandos

| Comando | O que faz |
|---|---|
| `/avaliar-passagem [card_id]` | Avalia card manual ou ultimo da fase 5 |
| `/ritual-diario` | Rodada automatica seg-sab 13h20 |
| `/ritual-semanal` | Rodada automatica quarta 13h35 |
| `/calibrar` | Registra discordancia / aprendizado no doc CRITERIOS |
| `/historico-passagem` | Mostra historico + padroes cruzados |

## Scheduled tasks recomendados

```
ritual-diario:  seg-sab 13h20 (America/Bahia)
ritual-semanal: quarta 13h35 (America/Bahia)
```

## Cuidado importante

A skill grava no Pipefy E dispara WhatsApp pra encarregados. Tom errado quebra adesao. Antes de migrar pra producao 24/7, rodar 1 semana em paralelo com revisao humana de cada rodada (politica de "Cenario C nao envia automatico" ja vigente desde 25/05/2026).
