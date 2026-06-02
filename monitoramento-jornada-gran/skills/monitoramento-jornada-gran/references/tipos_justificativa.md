# Tipos de Justificativa — Skill Monitoramento de Jornada

20 tipos cadastrados no RHID em `/v2/#/list/justificationtype`. Classificação pra a skill:

---

## Tipos que **excluem** falta seca

Quando o RHID marca "Falta" no dia mas existe uma dessas justificativas associada → **NÃO conta como falta seca** no relatório.

| Tipo no RHID | Classe |
|---|---|
| Atestado Médico | ATESTADO |
| Atestado de Comparecimento | ATESTADO |
| Atestado de Óbito | ATESTADO |
| Exame de Retorno ao Trabalho | ATESTADO |
| Férias | FÉRIAS |
| Feriado | FERIADO |
| Folga Domingo Trabalhado | FOLGA |
| Folga Feriado | FOLGA |
| Licença Casamento | LICENÇA |
| Licença Maternidade | LICENÇA |
| Licença Paternidade | LICENÇA |
| Afastamento Temporário | AFASTAMENTO |
| Suspensão | SUSPENSÃO ⚠️ |

⚠️ **Suspensão** exclui falta mas é punitivo — sinalizar separado em "Observações" do relatório.

---

## Tipos que **NÃO** excluem (são ajustes ou genéricos)

| Tipo no RHID | Classe | Observação |
|---|---|---|
| Abonar ausência no período | ABONO_GENÉRICO | Aceito mas registrar na obs |
| Abonar quantidade de horas | ABONO_GENÉRICO | Aceito mas registrar na obs |
| Ajuste Banco | BH | Não é falta — é compensação |
| Ajuste quantidade de horas | BH | Idem |
| Banco | BH | Idem |
| Não Banco | BH | Idem |
| Redução Aviso Trabalhado | AVISO | Caso específico, revisão manual |

---

## Como recuperar justificativas no fluxo

A skill consulta o **Relatório de Afastamentos** (`/v2/#/relatorio_afastamentos`) ou **Ocorrências** (`/v2/#/relatorio_ocorrencias`) com:

```
Empresa: vazio
Funcionários: Ativos
Data Início: <quarta_anterior>
Data Término: <terça>
Tipos de Justificativa: vazio (puxa todos)
Mostrar Ausência por Justificativa: Sim
Formato: HTML
```

Resultado: tabela de `(funcionario, data, tipo_justificativa)`.

Match na skill:
1. Pra cada dia marcado "Falta" no Cartão de Ponto
2. Verifica se há entrada correspondente no Relatório de Afastamentos pra `(nome, data)`
3. Se sim e o tipo está na tabela "exclui falta seca" acima → não conta

---

## Atualização

Se o RH cadastrar **novo Tipo de Justificativa** no RHID, atualizar este arquivo:
1. Adicionar o nome novo na tabela correspondente (exclui ou não exclui)
2. Definir a Classe
3. Documentar a decisão na nota operacional

**Sem aprovação do Hugo, novo tipo cai automaticamente em "NÃO exclui" (conservador).**
