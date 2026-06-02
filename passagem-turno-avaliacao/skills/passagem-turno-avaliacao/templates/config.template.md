# Configuração — Skill Passagem de Turno

**⚠ ESTE É O TEMPLATE PÚBLICO.** Copie para `config.md` (gitignored) e preencha os placeholders com dados reais antes de usar a skill.

```bash
cp config.template.md config.md
```

Parâmetros operacionais. Editar `config.md` (não este arquivo) em vez de hardcoded nos workflows.

## Pipe e fases

| Atributo | Valor |
|---|---|
| Pipe ID | `306798124` |
| Pipe URL | `https://app.pipefy.com/pipes/306798124` |
| Fase 1 (Painel 11h) | `340994226` |
| Fase 2 (Passagem) | `340994228` |
| Fase 3 (Painel 16h) | `340994229` |
| Fase 4 (Fechamento) | `340994230` |
| Fase 5 (Avaliação Líder) | `340994227` |

## Internal IDs dos campos da fase 5

| Campo | Slug (id) | Internal ID |
|---|---|---|
| Conferi com Paineis | `conferi_se_os_dados_batem_com_os_paineis_de_guerra_11h_e_16h` | `421632658` |
| Análise — Encarregado Abertura | `coment_rio_da_l_der_de_loja_orienta_o_feedback` | `421632739` |
| Análise — Encarregado Tarde/Noite | `an_lise_encarregado_tarde_noite` | `429243738` |
| Sinais de Atenção | `sinais_de_aten_o` | `429243739` |
| Recomendação ao Líder | `recomenda_o_ao_l_der` | `429243740` |
| Nota Encarregado Abertura | `nota_encarregado_abertura_0_100` | `429239947` |
| Nota Encarregado Tarde/Noite | `nota_encarregado_tarde_noite_0_100` | `429239950` |
| Nota Loja | `pontua_o_do_dia_nil_execu_o_operacional_0_a_10` | `421632866` |
| Card Pronto | `card_pronto_para_encerramento` | `421632888` |

## Campos a ler (fases 1-4) — para coleta de dados

A skill lê todos os 70+ campos via GraphQL query (`{ card(id: X) { fields { name value field { id internal_id type label }}}}`). Não precisa enumerar aqui.

## Caminhos

| Item | Path |
|---|---|
| Workspace do projeto | `/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Passagem de Turno/` |
| Doc CRITERIOS (canônico) | `{workspace}/CRITERIOS_AVALIACAO_FASE5.md` |
| Manual técnico do pipe | `{workspace}/MANUAL_PIPEFY_RELATORIO_PASSAGEM_TURNO.md` |
| XLSX acumulativo do Super Gran | `{workspace}/passagem-turno-superGran.xlsx` |
| Log de calibrações | `{workspace}/calibracoes-passagem-turno.md` |

## Painel de Guerra

| Item | Valor |
|---|---|
| URL base | `https://grupoa7.github.io/painel-guerra-gran/` |
| Pattern Painel 11h | `BIv10_{YYYYMMDD}_p11h.html` |
| Pattern Painel 16h | `BIv10_{YYYYMMDD}_p16h.html` |

## Parâmetros de avaliação

| Parâmetro | Valor |
|---|---|
| Faixa nota verde (✓) | ≥ 80% |
| Faixa nota amarela (→) | 50% – 79% |
| Faixa nota vermelha (!) | < 50% |
| Máximo de Sinais de Atenção por avaliação | 5 |
| Limite de cards no `/historico-passagem` | últimos 30 |

## Chrome MCP

A skill opera via Chrome MCP. Hugo deve estar logado em Pipefy com `hugo@grupoa7.com.br`. Endpoint GraphQL: `https://app.pipefy.com/queries` (NUNCA `api.pipefy.com`).

## Contatos WhatsApp — Ritual Diário e Semanal

**Sessão Chrome MCP a usar:** sessão da Fran (WhatsApp Web logado, contatos Sílvio e Alyne na agenda dela).

> ⚠ Preencher números reais APENAS no `config.md` local (não versionado). Templates abaixo usam placeholders.

| Contato | Nome agenda | Número |
|---|---|---|
| Encarregado Sílvio | `[GRAN] Silvio Rouzan` | `{TELEFONE_SILVIO}` |
| Encarregada Alyne | `[GRAN] Alyne Bittencourt` | `{TELEFONE_ALYNE}` |
| Grupo Liderança | `[LIDERANÇA] Gran` | (grupo — usado no Passo 7.5 do ritual diário) |

**Forma de buscar no WhatsApp Web:** preferir busca pelo nome salvo (mais robusto que número), com o nome exato `[GRAN] Silvio Rouzan` ou `[GRAN] Alyne Bittencourt`. Caso falhe, usar o número internacional como fallback.

## Thresholds dos cenários de mensagem privada

| Cenário | Condição | Template |
|---|---|---|
| A — Normal | (média_individual − 5pp) ≤ nota_dia ≤ (média_individual + 5pp) | `whatsapp_privado_cenario_a_normal.md` |
| B — Excelente | nota_dia > média_individual + 5pp | `whatsapp_privado_cenario_b_excelente.md` |
| C — Difícil | nota_dia < média_individual − 5pp | `whatsapp_privado_cenario_c_dificil.md` |
| C — Reincidência | 3+ dias consecutivos em Cenário C | C + adendo no parágrafo final |
| Pingar Hugo antes | nota_dia < média_individual − 15pp | Não disparar automático, perguntar antes |

**Janela de média individual:** mínimo 3 avaliações, máximo 7. Se < 3, usar Cenário A sempre (sem média confiável).

## Ritual diário

| Atributo | Valor |
|---|---|
| Cadência | seg-sáb 13h20 (local Salvador BRT) |
| Card avaliado | Dia anterior |
| Comando | `/ritual-diario` |
| Workflow | `references/ritual_diario.md` |
| Log de envios | `data/log_envios_whatsapp.csv` |

## Ritual semanal

| Atributo | Valor |
|---|---|
| Cadência | quarta 13h35 (local Salvador BRT) |
| Janela | qua-anterior → terça (mesmo padrão monitoramento-jornada-gran) |
| Comando | `/ritual-semanal` |
| Workflow | `references/ritual_semanal.md` |
| Log de resumos | `data/log_resumos_semanais.csv` |

## Loop de melhoria contínua

Ver `references/loop_melhoria_continua.md`. Sweet spots:
- Taxa de aceitação de candidatos: 30-60%
- Distribuição de cenários: 70% A · 15% B · 15% C
- Tempo total ritual diário: < 10 min
- Revisão de saúde da skill: a cada 10 rodadas
