# Regras de Negócio — Cotação FLV

Leia antes de rodar. Estas regras são a alma da skill; o código em `scripts/` as implementa.

## 1. Cherry-picking por item
Aloca cada item ao fornecedor mais barato (em R$/kg ou R$/un normalizado), quebrando
o "pacote" do fornecedor. Por quê: ataca os dois problemas de uma vez — nunca refém de
uma fonte (disponibilidade) e nunca engole item de margem ruim só porque o resto era bom.

## 2. Exclusão por item (defesa de disponibilidade)
Um fornecedor pode ser ótimo em tomate e péssimo em uva. Se um fornecedor não é confiável
para um item (qualidade ou corte de entrega), ele **não vence aquele item, mesmo mais barato**.
Mantido em `dados/exclusoes.csv` (colunas `cod,fornecedor`). Hugo edita conforme aprende —
captura por exceção, sustentável. O score automático de corte/qualidade é Fase 2.

## 3. Canais de compra
- **Busca (CEASA, via Micael):** só **Micael e RML**. Existe mais por disponibilidade que
  por preço — itens diferenciados que o fornecedor de entrega corta se não formos buscar.
  Os fornecedores novos que Hugo cadastrar entram aqui.
- **Entrega:** todos os demais. Pedido até 10h do dia útil anterior.
- A comparação de preço é **cross-canal** — o canal é só atributo de logística.

## 4. Âncoras de preço (para expor preço inflado)
Em ordem de uso:
1. **Mediana entre fornecedores da semana** — sempre fresca. Base do desvio.
2. **CEASA-BA** (boletim oficial, KVIs de maior giro) — âncora externa independente.
3. **Último custo do BI** — banda de sanidade: pega erro de embalagem (saca 25 vs 50kg)
   e preço absurdo (> 2x ou < 1/2x do último custo → alerta `CONFERIR PREÇO/UNIDADE`).

## 5. Creep e desvio (a partir da 2ª rodada)
- **Creep:** item×fornecedor subindo N semanas seguidas, sobretudo com poucas fontes →
  resposta: rotacionar. O simples fato de medir já disciplina o fornecedor.
- **Desvio:** fornecedor muito acima da mediana ou do CEASA-BA para o item.
Ligam quando o `historico_precos.csv` tiver ≥2 semanas.

## 6. Especialistas / fonte única
Item com só 1 fornecedor não gera comparação (alerta `FONTE ÚNICA`). Especialistas
(ovos/Mix Bahia, cogumelos, folhagem/Mac Ramos, morango) são seedados pelo custo do BI
até a tabela real chegar; aparecem no pedido e começam a ser monitorados para creep.

## 7. Dado real ou nada
Preço **0,00 ou vazio = NÃO COTADO** — nunca entra, nunca vence. Estimativas, quando
inevitáveis, são marcadas e registradas. Nunca inventar preço.

## 8. Priorização
Itens de maior giro / curva A primeiro (o Mapa já ordena por curva). O peso de
priorização e a base de venda vêm da **MÉDIA FINAL (col BA) do BI** — média DIÁRIA
ponderada (exclui outliers). Giro semanal = MÉDIA FINAL × 7 (Gran abre todo dia).

## 9. A skill NÃO prevê demanda — usa a média do BI
A base de venda de cada produto é a **MÉDIA FINAL (col BA) do BI do Gran** (decisão
25/05/2026). O pedido semanal (Pedido FLV) **não** é mais a base de demanda — foi um
erro inicial. O Pedido FLV, quando fornecido, serve só como **titular** (coluna
FORNECEDOR, mais atual que a do BI). A skill decide **de quem** comprar; não prevê demanda.

## 10. Regras fixas
- **Micael**: core do canal de busca, nunca remover.
- **RML**: canal de busca (apesar de estar no dicionário com os de entrega).
- **RLS**: inativo — tratar à parte. Não confundir com RML.

## 11. Conversão caixa→kg (base de embalagens CEASA-BA)
Quando o fornecedor cota **"caixa R$ X" sem declarar peso** (HR, Igarashi, Boa Citrus,
Qualisuper, Potência fazem isso em parte ou no todo), a skill consulta a base mestre
`templates/embalagens.json` pra puxar o peso default da praça Salvador.

**Fluxo**:
1. Parser do fornecedor mapeia a descrição → COD Gran via `dicionario_equivalencia_oficial.xlsx`.
2. Se a unidade traz peso (ex.: "CX 20KG"), `flv_lib.peso_kg_da_unidade()` resolve direto.
3. **Senão**, chama `flv_lib.peso_caixa_por_sku(cod)` → retorna `(peso_kg, nao_padrao, motivo, slug)`.
4. Se `nao_padrao=True`, **bloqueia conversão automática** e marca alerta amarelo
   `PESO ASSUMIDO [CEASA] — confirmar` no Mapa de Decisão. Hugo decide se confirma ou
   pede peso ao fornecedor.

**Fonte da base**: `Tabela_Conversao_Caixas_FLV_Gran.xlsx` (boletim CEASA-BA 22/05/2026 +
cartilhas CEAGESP "A medida das frutas/hortaliças" 2017). 79 commodities, 386 SKUs Gran.

**Exceções marcadas `nao_padrao=true` no MVP** (forçam fornecedor a cotar kg):
- **Banana Prata** (CX 45 kg na BA vs 20 kg em SP — regionalismo forte).
- **Banana Nanica/Maçã/Ouro** ([est.] 20 kg — confirmar com fornecedor).
- **Banana da Terra** (vendida por KG ou CENTO — não tem caixa).
- **Abacaxi** (CENTO = 100 frutas em Salvador, não kg).
- **Folhosa em maru / Alface Americana** (CX 10 kg — caixa baixa diferente da padrão CEASA).
- Tudo que tem peso `<15 kg` ou `>30 kg` (foge da caixa universal CEASA 46-52L preta ~22 kg).
- Tudo com regionalismo `⚠⚠` no boletim (Goiaba, Manga, Uva, Pinha, Acerola na BA têm caixa grande; em SP é papelão pequeno).

## 12. Calibração com pesagem real
Quando o Gran pesar uma caixa no recebimento e o peso divergir do default CEASA-BA,
registrar via CLI:
```
python scripts/registrar_pesagem.py --sku 138 --peso 17.5 --fornecedor IGARASHI
```
A pesagem entra em `produtos[slug].pesagens` do `embalagens.json`. **Quando ≥2 pesagens
divergirem >10% do default**, o sistema sugere trocar o default pela mediana das pesagens
divergentes. Troca **não é automática** — Hugo aprova com `--aprovar`. Histórico das
trocas fica em `produtos[slug].historico_calibracao`.
