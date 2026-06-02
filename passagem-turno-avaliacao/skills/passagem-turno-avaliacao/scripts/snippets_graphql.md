# Snippets GraphQL — Skill Passagem de Turno

Snippets prontos pra copiar e adaptar nas execuções da skill. Endpoint: `https://app.pipefy.com/queries` (NUNCA `api.pipefy.com`).

Pattern padrão: IIFE async + CSRF do meta tag + `credentials: 'include'`. Sempre.

---

## 1. Listar cards da fase 5 (mais recentes primeiro)

Usado em `/avaliar-passagem` para identificar o card a avaliar quando Hugo não passa ID.

```javascript
(async () => {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const r = await fetch('https://app.pipefy.com/queries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    body: JSON.stringify({ query: `{
      phase(id: 340994227) {
        cards(first: 10) {
          edges { node {
            id title createdAt updated_at
            current_phase { name }
            assignees { name }
          } }
        }
      }
    }`}),
    credentials: 'include'
  });
  return JSON.stringify(await r.json(), null, 2);
})();
```

Saída: lista de cards com id, título, data de criação, atualização e responsáveis. Pegar o mais recente em `createdAt`.

---

## 2. Ler card completo (todos os campos)

Usado em `/avaliar-passagem` Passo 2 para coletar tudo que foi preenchido.

```javascript
(async () => {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const r = await fetch('https://app.pipefy.com/queries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    body: JSON.stringify({ query: `{
      card(id: CARD_ID_AQUI) {
        id title createdAt
        assignees { name }
        fields {
          name value
          field { id internal_id type label }
        }
      }
    }`}),
    credentials: 'include'
  });
  const d = await r.json();
  window._cardFull = d.data.card;
  return JSON.stringify({
    card_id: d.data.card.id,
    title: d.data.card.title,
    total_fields: d.data.card.fields.length
  }, null, 2);
})();
```

**Importante:** o resultado vai pra `window._cardFull` pra paginação. Não retornar valor bruto dos `attachment` (filtro de segurança).

Pra ler valores não-attachment em pedaços:
```javascript
(() => {
  const fields = window._cardFull.fields;
  const rest = fields.filter(f =>
    f.field &&
    f.field.type !== 'statement' &&
    f.field.type !== 'attachment'
  ).slice(0, 10).map(f => ({
    label: f.name, type: f.field.type, internal_id: f.field.internal_id, value: f.value
  }));
  return JSON.stringify(rest, null, 2);
})();
```

Mudar `.slice(0, 10)` para `.slice(10, 20)` etc., pra paginar.

---

## 3. Atualizar campo do card (4 long_texts + 3 numbers)

Usado em `/avaliar-passagem` Passo 6.

```javascript
(async () => {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const r = await fetch('https://app.pipefy.com/queries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    body: JSON.stringify({
      query: `mutation($input: UpdateCardFieldInput!) {
        updateCardField(input: $input) { success }
      }`,
      variables: {
        input: {
          card_id: CARD_ID_AQUI,
          field_id: "SLUG_DO_CAMPO",
          new_value: "valor"
        }
      }
    }),
    credentials: 'include'
  });
  return JSON.stringify(await r.json(), null, 2);
})();
```

**Slug dos campos da fase 5 (ver `templates/config.md`):**
- `coment_rio_da_l_der_de_loja_orienta_o_feedback` → Análise Abertura (long_text)
- `an_lise_encarregado_tarde_noite` → Análise Tarde/Noite (long_text)
- `sinais_de_aten_o` → Sinais de Atenção (long_text)
- `recomenda_o_ao_l_der` → Recomendação (long_text)
- `nota_encarregado_abertura_0_100` → Nota Abertura (number)
- `nota_encarregado_tarde_noite_0_100` → Nota Tarde/Noite (number)
- `pontua_o_do_dia_nil_execu_o_operacional_0_a_10` → Nota Loja (number)

Pra batchar os 7 updates, usar função wrapper:

```javascript
(async () => {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  const updateField = async (field_id, value) => {
    const r = await fetch('https://app.pipefy.com/queries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({
        query: `mutation($input: UpdateCardFieldInput!) {
          updateCardField(input: $input) { success }
        }`,
        variables: { input: { card_id: CARD_ID, field_id, new_value: value } }
      }),
      credentials: 'include'
    });
    return await r.json();
  };

  const log = [];
  log.push({step: 'Análise Abertura', res: await updateField("coment_rio_da_l_der_de_loja_orienta_o_feedback", textoAnaliseAbertura)});
  log.push({step: 'Análise Tarde/Noite', res: await updateField("an_lise_encarregado_tarde_noite", textoAnaliseTarde)});
  log.push({step: 'Sinais de Atenção', res: await updateField("sinais_de_aten_o", textoSinais)});
  log.push({step: 'Recomendação', res: await updateField("recomenda_o_ao_l_der", textoRecomendacao)});
  log.push({step: 'Nota Abertura', res: await updateField("nota_encarregado_abertura_0_100", String(notaAbertura))});
  log.push({step: 'Nota Tarde/Noite', res: await updateField("nota_encarregado_tarde_noite_0_100", String(notaTarde))});
  log.push({step: 'Nota Loja', res: await updateField("pontua_o_do_dia_nil_execu_o_operacional_0_a_10", String(notaLoja))});
  return JSON.stringify(log.map(l => ({step: l.step, ok: !!l.res.data?.updateCardField?.success})), null, 2);
})();
```

---

## 4. Listar cards finalizados (Card Pronto = marcado) para `/historico-passagem`

```javascript
(async () => {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;
  let all = [], cursor = null, hasMore = true;
  while (hasMore && all.length < 50) {
    const after = cursor ? `, after: "${cursor}"` : '';
    const r = await fetch('https://app.pipefy.com/queries', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
      body: JSON.stringify({ query: `{
        phase(id: 340994227) {
          cards(first: 20${after}) {
            pageInfo { hasNextPage endCursor }
            edges { node {
              id title createdAt
              fields { name value field { internal_id type } }
            } }
          }
        }
      }`}),
      credentials: 'include'
    });
    const d = await r.json();
    all = all.concat(d.data.phase.cards.edges.map(e => e.node));
    hasMore = d.data.phase.cards.pageInfo.hasNextPage;
    cursor = d.data.phase.cards.pageInfo.endCursor;
  }
  window._historico = all;
  return `Total: ${all.length} cards carregados em window._historico`;
})();
```

---

## 5. Bugs conhecidos (ver `references/notas_operacionais.md`)

- **Acesso negado em updatePhaseField recém-criado:** alguns campos criados via API retornam `PERMISSION_DENIED` ao tentar reordenar. Workaround: pedir Hugo arrastar manualmente na UI.
- **URLs assinadas bloqueadas no output:** filtrar `attachment` antes de retornar valor bruto.
- **Output truncado em > ~2000 chars:** usar `window._var` e paginar.
