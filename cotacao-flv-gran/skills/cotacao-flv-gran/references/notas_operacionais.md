# Notas Operacionais — aprendizados de cada rodada

Acumule aqui aprendizados técnicos de parsing, match e navegação. A cada ~8 rodadas,
consolidar padrões. Comece curto; cresça com o uso.

## Aprendizados iniciais (build 22/05/2026)
- Shimizu: preço da última coluna já é por kg/un; embalagem no nome não é divisor.
- Doce Mel: usar coluna "Preço KG"; tem código próprio (cod_fornecedor).
- D'onofrio: linhas sem "R$:" são categorias.
- RML (imagem): transcrever por visão; ofertas em amarelo são preço válido.
- CEASA-BA: pegar PDF ao vivo via Chrome (web_fetch da listagem pode vir em cache).
- Match: normalizar "20kg"=="20 kg" foi necessário pra casar Shimizu/Doce Mel.

## Cadastro Hortimix + Boa Citrus (25/05/2026)
- Hortimix PDF: o offset de colunas do `extract_tables` MUDA entre páginas. Não confiar em
  índice fixo — ancorar na célula de preço e ler à esquerda (pulando '' e 'R$' isolado, pois
  às vezes o "R$" e o número caem em células separadas, ex: BRÓCOLIS NINJA UND).
- Boa Citrus: preço por CAIXA; passar preço da caixa + "CX NNKG" e deixar o motor dividir.
  Os 6 itens parseados bateram 100% com o "/kg aproximado" que a vendedora informa.
## Base de demanda migrou para o BI (25/05/2026)
- A base de venda de cada produto agora é a **MÉDIA FINAL (col BA)** do BI (aba APOIO PEDIDO),
  média DIÁRIA ponderada. Giro semanal = BA × 7. `flv_lib.carregar_bi` + `demanda_do_bi`.
- O BI também dá custo (P.CUSTO/AN), preço (P.ATUAL/AP), curva (R) e fornecedor (AV). COD do BI
  = COD do dicionário (join direto). Universo = cadastro ∩ BI (~380; 194 com giro>0).
- `cotar.py --bi <arquivo>`. `--contagem` virou opcional e só fornece o titular (Pedido FLV,
  mais atual). `giro_semanal` aceita `giro_sem` (já semanal) vindo do BI.
- O Hugo envia o BI na conversa a cada rodada (sem caminho fixo).

- **Risco do `_match_fallback` (contenção):** termo genérico do fornecedor casa com variedade
  específica do Gran quando uma string contém a outra e a razão de tamanho ≥0,5. Ex.: Hortimix
  "LARANJA" (R$2,50) casou errado com "LARANJA LIMA KG" e, por ser mais barato, sobrescreveria
  o R$10 da laranja lima real. Mitigação atual: os genéricos cítricos (laranja/lima/limão/pocan)
  ficam fora do dicionário até a compradora definir a variedade — aí o match vira exato e o
  fallback não dispara. Se reincidir com outros fornecedores, avaliar subir o threshold do
  fallback p/ a direção "nd contido na chave" (mexe em todos os fornecedores — testar antes).

## Igarashi (canal ENTREGA) — onboarding 2026-05-25
- Tabela texto/RTF "Nome - preço", preço POR CAIXA/SACA. Pesos NÃO vêm na tabela (item-específico) → ficam no parser `_ig_peso_familia`: alho 10kg(CX), batata 25kg(SC)*, cebola/cenoura 20kg(SACO), repolho 19kg(CX), tomate 21kg(CX), maçã 18kg(CX) / linha MI-070 12,5kg (peso inline). Pesos triangulados: spec Hugo × R$/kg do CARDÁPIO DEFAULT × CEASA-BA 22/05 — todos batem.
- Preço = último número pt-BR de 2 casas (`\d+,\d{2}`); a linha MI-070 traz "12,5" (1 casa) = PESO, não casa no regex de preço de propósito.
- Maçã = cherry-pick por calibre: mapeei só a linha do DEFAULT do cardápio (CAT1 CAL120 Gala) ao COD 45; demais calibres/CAT/Fuji/Belgala vão a nao_casados. Senão a CAT3/calibre miúdo (mais barato) venceria escondido — exatamente a fruta que Hugo não quer a granel.
- ⚠ ARMADILHA do `_match_fallback`: marcador MI/PREMIUM tem que vir ANTES do calibre no desc canônico ("MACA GALA MI CAT1 CAL120"), senão o desc do default ("...CAT1 CAL120") é substring da variação MI e o fallback por contenção casa a MI (mais barata) ao mesmo COD. Bug pego no teste e corrigido.
- (*) Batata: 25kg dá 9,40/kg (logo acima do CEASA esp 7,80); 50kg daria 4,70/kg (abaixo do atacado, impossível) → 25kg confere. Confirmar verbal mesmo assim.
- ASSUNÇÃO em aberto: Tomate Saladete→COD139 (salada redondo). Se for tipo italiano/roma, mover p/ COD138. Igarashi venceu tomate 139 a 5,00 vs Shimizu 8,80 — economia depende dessa identidade.
- W21: Igarashi vence alho(14,50), repolho(5,00), tomate salada(5,00); empata cebola branca c/ RML(4,50). Batata(108) e maçã(45) cadastrados mas SEM demanda na contagem W21.

## Atualização CEASA-BA via Chrome MCP (28/05/2026)
- `web_fetch` da listagem retorna HTML cliente-renderizado/sem links — não dá pra extrair os PDFs.
  Usar Chrome MCP: `tabs_context_mcp(createIfEmpty=true)` → `navigate(url)` →
  `read_page(contentType="links")`. O href dos PDFs aparece como `/sde/sites/site-sde/files/AAAA-MM/DD-MM-AAAA.pdf`.
- Baixar via `curl -sSL <url>` no sandbox direto pra `dados/ceasa_historico/ceasa_AAAA-MM-DD.pdf`.
- Parsear com `parse_ceasa.parse_boletim_pdf(path)`, montar row como `["<unidade> <produto>", "<comum>", "<sit>"]`,
  anexar em `dados/ceasa_historico/ceasa_trimestre.json` e podar pra janela de 13 boletins.
- A coluna de preço "MAIS COMUM" no boletim NOVO (≥abril/2026) é a 4ª (MIN COMUM MAX SIT após PRODUTO/UNIDADE/PROCEDÊNCIA);
  formatos antigos invertiam a ordem mas o regex em `parse_ceasa._RE_LINHA` lida com os dois.

## Publicação Cloudflare Pages roda do sandbox (28/05/2026)
- O `.env` com `CLOUDFLARE_API_TOKEN` (escopo Pages:Edit) está em `dados/.env` e o `publicar.py`
  carrega via `carregar_env(raiz)`. O wrangler é puxado por `npx wrangler` sob demanda (Node 22+
  já instalado no sandbox). NÃO precisa mais rodar no Mac do Hugo.
- Endereço fixo: `https://cotacao-flv-gran.pages.dev`. Cada deploy também recebe URL única.
- Após `cotar.py`, basta `python3 publicar.py --semana 2026-Www` na raiz do projeto.

## Camada de revisão crítica de preços (28/05/2026)
- `scripts/revisao.py` detecta 5 tipos de anomalia (todos R$/kg, só decisões `ok`):
  `VENCEDOR_VS_BI` (>2× custo BI), `VENCEDOR_BAIXO_DEMAIS` (<½ custo BI — suspeita unidade trocada
  OU BI velho), `VENCEDOR_VS_CEASA` (>1,5× CEASA), `FORNECEDOR_OUTLIER` (>2× mediana dos demais),
  `SALTO_VS_SEMANA` (|Δ| >30% vs semana anterior do mesmo fornecedor — usa historico_precos.csv).
- Resultado serializado em `cotacoes/semana-AAAA-Www/revisao.json` + bloco no topo da aba Alertas
  do mapa HTML (`_panel_alertas` recebe `revisao=`).
- NÃO bloqueia decisão. Só sinaliza. Preço fora da banda PODE ser realidade (Shimizu premium
  cota chuchu a 2× mediana — é Shimizu sendo Shimizu, não bug).
- Parâmetros calibrados (FATOR_BI=2.0, FATOR_CEASA=1.5, FATOR_OUTLIER=2.0, FATOR_SALTO=0.30) ficam
  no topo de `revisao.py`. Ajustar se virar barulho.

## JUNIOR_UVA — 4 colunas no XLSX + guard defensivo (28/05/2026)
- Roster (`templates/fornecedores.json`) tinha JUNIOR_UVA em col_dict=53 mas o dicionário XLSX
  só ia até a col 52 (JUAN) → `IndexError` em `carregar_dicionario`.
- Adicionadas DESCRICAO/UNIDADE/CONFIANCA/OBSERVACOES JUNIOR_UVA nas colunas 54-57 (1-indexed).
  Backup em `dados/dicionario_equivalencia_oficial.BACKUP-pre-JUNIOR_UVA-AAAAMMDDhhmmss.xlsx`.
- Guard em `flv_lib.carregar_dicionario`: se `di + 1 >= len(r)`, pula o fornecedor (não quebra).
  Cobre o caso "novo no roster, ainda sem mapeamento no XLSX". Vira `nao_casados`.

## Protocolo de auto-revisão antes de publicar (rodada 2026-W23 — 01/06/2026)
**Princípio**: o `revisao.json` produzido pelo `scripts/revisao.py` é só um DETECTOR.
Antes de entregar o mapa pro Hugo, rodar **double-check em cada alerta ALTA** —
caso contrário a saída fica recheada de falsos positivos vindos de BI defasado, o que
mina a confiança no processo.

Protocolo (gravado em `cotacoes/semana-AAAA-Www/auto_revisao.md` a cada rodada):
1. Pegar cada item de `revisao.json` com `severidade=='alta'`.
2. Pra cada um, 3 cross-checks:
   a. **Conta na tabela bruta** — abrir a linha original do fornecedor e validar
      `preco_unitário ÷ peso_da_embalagem`.
   b. **CEASA-BA** — comparar com o `comum_kg` do parser `parse_ceasa`. Faixa ±30%.
   c. **Mediana entre fornecedores** — vencedor está dentro da banda dos outros candidatos?
3. Classificar:
   - **REAL** (3/3 ok) → falso positivo do BI inflado, aceitar.
   - **ERRO confirmado** (≥2/3 discordam) → corrigir na origem e re-rodar.
   - **SUSPEITO** (1 incoerência só) → reportar ao Hugo decidir.
4. Documentar tudo em `auto_revisao.md` da semana com veredictos.

**Casos resolvidos na rodada W23 (3 erros, 7 reais):**
- ❌ COD 113 CENOURA HORTIMIX R$ 1,15/kg → bug do `_match_fallback` casou
  "CENOURA RAMA · MÇO · R$ 23" como COD 113 e aplicou peso da saca de cenoura
  (20kg). Corrigido via exclusão `113,HORTIMIX` em `dados/exclusoes.csv`.
- ❌ COD 130 PIMENTÃO AMARELO RML R$ 1,90 / COD 3642 PIMENTÃO VERMELHO RML R$ 1,90
  → erro de transcrição na imagem RML W22: `P AMARELO CX 10KG, R$ 19,00` quando
  W21 (mesma linha) cotava R$ 160,00. Corrigido pra R$ 160 (referência W21) no
  `rml_transcrito.csv` da semana.
- ✅ 7 alertas REAL (Tangerina IMP RML, Laranja Pera Boa Citrus, Melancia RML,
  Pepino HR, Vagem Donofrio, Tangerina Murcote Donofrio, Abacate Avocado RML):
  preço de atacado abaixo do "custo BI" (que reflete varejo). Bate com CEASA-BA
  na faixa esperada. Aceitar e atualizar histórico pra próxima rodada não
  realertar.

**Dívidas técnicas pendentes (precisam virar fix da skill):**
- `_match_fallback` em `engine.py` precisa de **filtro de variante** — quando a
  desc do fornecedor tem token marcador ("RAMA", "BABY", "MINI", "PREMIUM",
  "ROXA") ausente da chave do dicionário, NÃO casar. Senão a variante errada
  vence dentro do mesmo fornecedor pelo menor preço_norm.
- `cotar.py::carregar_exclusoes` quebra com linhas começando por `#` (`ValueError:
  invalid literal for int()`). Adicionar skip de linhas comentadas.
- `VENCEDOR_BAIXO_DEMAIS` (em `revisao.py`) deveria exigir CONFIRMAÇÃO CRUZADA
  (preço também < 50% de CEASA OU < 50% mediana entre fornecedores) antes de
  marcar ALTA. Hoje só compara com custo BI, que é varejo defasado → 70%+ dos
  alertas ALTA viram falso positivo.
- `arquivar_resposta.py` salva texto bruto do WhatsApp (com markdown `*`, sem
  estrutura CSV, imagem PNG). Os parsers especializados esperam formatos
  canônicos do upload manual. Etapa de normalização automática pós-WhatsApp
  é o caminho — senão cada rodada vai exigir 8 normalizações manuais.
