# REQUISITOS — HEALTH AGENT SYSTEM
> Documento de arquitetura e requisitos | Murilo Silveira Fontes | Mar/2026

---

## 1. VISÃO GERAL

Sistema multiagente especializado em saúde individual, baseado em Claude Code, com memória persistente via prontuário versionado, debate entre agentes para validação de hipóteses, e especialidades modulares plugáveis via skills. Científico, baseado em evidências, bilíngue (técnico + acessível ao paciente).

---

## 2. ARQUITETURA DE AGENTES

### 2.1 Agente Orquestrador — `orchestrator`
**Função:** Ponto de entrada. Lê o prontuário, entende o contexto completo do paciente, decide quais agentes especialistas acionar, sintetiza os outputs e decide se atualiza o prontuário.

**Responsabilidades:**
- Carregar `PRONTUARIO.md` e `EXAMES_HISTORICO.md` antes de qualquer resposta
- Identificar qual(is) especialidade(s) são relevantes para a pergunta
- Orquestrar o debate entre Agente Clínico e Agente Cético
- Sintetizar a conclusão final
- Decidir se há dado novo que justifica atualização do prontuário
- Sinalizar quando algo exige avaliação médica presencial

**Tom:** Médico assistente pessoal — científico, direto, acessível.

---

### 2.2 Agente Clínico — `clinical`
**Função:** Formula hipóteses, interpreta dados, propõe correlações e planos de ação.

**Responsabilidades:**
- Recebe contexto do orquestrador (prontuário + dado novo)
- Formula hipótese clínica com raciocínio explícito
- Cita referências de literatura peer-reviewed quando disponível
- Propõe próximos passos (exames, consultas, ajustes)
- Distingue explicitamente: dado confirmado vs. suspeita vs. especulação

**Regra crítica:** Nunca tratar SNP array de ancestralidade (ex: Genera, 23andMe) como laudo clínico. Sempre classificar como "suspeita genética — não confirmada clinicamente".

---

### 2.3 Agente Cético — `skeptic`
**Função:** Questiona hipóteses do Agente Clínico. Seu trabalho é encontrar falhas, pedir evidências, identificar vieses e evitar conclusões precipitadas.

**Responsabilidades:**
- Recebe a hipótese do Agente Clínico
- Questiona: qual a força da evidência? é correlação ou causalidade?
- Identifica dados insuficientes para conclusão segura
- Aponta quando uma hipótese extrapola além dos dados disponíveis
- Distingue literatura robusta de estudos preliminares
- Flag obrigatório: "dado insuficiente", "hipótese não confirmada", "requer exame presencial"

**Tom:** Rigoroso, sem alarme desnecessário. Não é pessimista — é preciso.

---

### 2.4 Agente DNA — `genomics`
**Função:** Especialista em interpretação de variantes genéticas. Sim, faz sentido — com uma regra fundamental embutida.

**Responsabilidades:**
- Interpreta SNPs de arquivos brutos (CSV do Genera, 23andMe etc.)
- Correlaciona variantes com fenótipo clínico observado nos exames
- **Regra #1 — NÃO NEGOCIÁVEL:** Todo dado de SNP array é classificado como `SUSPEITA_GENETICA` — nunca como diagnóstico. Requer confirmação por teste clínico validado.
- Distingue variantes com forte evidência clínica (ex: BRCA1, MTHFR confirmado em lab) de variantes exploratórias
- Sugere confirmações laboratoriais relevantes
- Cita bases de dados: ClinVar, PharmGKB, OMIM, gnomAD

**Por que faz sentido:** DNA bruto tem ~600k SNPs — nenhum médico vai analisar isso manualmente. Um agente especializado que *já conhece as limitações do método* é genuinamente útil.

---

## 3. ESPECIALIDADES MÉDICAS (Skills Modulares)

Cada especialidade é uma skill independente — arquivo `.md` com contexto clínico, heurísticas, red flags e referências da área. Ativada pelo orquestrador conforme relevância.

### Especialidades iniciais

| Skill | Arquivo | Quando ativar |
|---|---|---|
| Endocrinologia | `skills/endocrinology.md` | Metabolismo, insulina, tireoide, obesidade, Mounjaro |
| Hepatologia | `skills/hepatology.md` | TGP/TGO/GGT, ferritina, MASLD, Fibroscan |
| Psiquiatria | `skills/psychiatry.md` | TDAH, depressão, medicamentos psicotrópicos, sono |
| Genômica | `skills/genomics.md` | SNPs, farmacogenômica, MTHFR, APOE |
| Cardiologia | `skills/cardiology.md` | Lipidograma, PA, MAV, risco cardiovascular |
| Medicina Laboratorial | `skills/lab_medicine.md` | Interpretação de exames, valores de referência, tendências |

### Especialidades adicionadas conforme necessidade

O orquestrador detecta quando uma pergunta requer especialidade não disponível e sinaliza: `"Skill não encontrada para [área] — considere criar skills/[area].md"`.

---

## 4. SISTEMA DE MEMÓRIA

### 4.1 Estrutura de arquivos

```
~/saude/
├── CLAUDE.md                        # contexto do agente — lido automaticamente
├── PRONTUARIO.md                    # fonte da verdade clínica — nunca deletar histórico
├── EXAMES_HISTORICO.md              # todas as tabelas laboratoriais consolidadas
├── laudos/                          # PDFs brutos — input para o agente
│   └── YYYY-MM-DD_laboratorio.pdf
├── skills/
│   ├── endocrinology.md
│   ├── hepatology.md
│   ├── psychiatry.md
│   ├── genomics.md
│   ├── cardiology.md
│   ├── lab_medicine.md
│   ├── skeptic.md                   # instruções do agente cético
│   └── clinical.md                  # instruções do agente clínico
├── agents/
│   ├── orchestrator.md              # lógica do orquestrador
│   ├── debate.py                    # script de debate entre agentes via API
│   └── update_prontuario.py         # atualização automática do prontuário
└── README.md
```

### 4.2 Regras de atualização do prontuário

- **Nunca deletar** dados históricos — apenas adicionar
- **Sempre datar** cada entrada nova
- **Trigger de atualização:** novo exame, novo medicamento, nova bioimpedância, nova consulta, novo sintoma relevante, nova hipótese confirmada ou refutada
- **Tabela de exames:** sempre append — nova linha, nunca sobrescrever linha existente
- **Classificação de certeza** em cada entrada: `CONFIRMADO` | `SUSPEITA` | `DESCARTADO` | `AGUARDANDO`

### 4.3 Tabela consolidada de exames

O `EXAMES_HISTORICO.md` é o documento dedicado a todas as tabelas laboratoriais seriadas. Separado do prontuário narrativo para facilitar leitura rápida de tendências. Estrutura:

```markdown
## Marcador X
| Data | Valor | Ref. | Status | Contexto |
|------|-------|------|--------|----------|
| ...  | ...   | ...  | ✅/↑/↓  | ...      |
```

---

## 5. MODELO DE ESCRITA — PADRÃO CLÍNICO

### 5.1 Referência: SOAP + narrativa integrativa

O padrão recomendado na medicina para prontuários é o **SOAP** (Subjective, Objective, Assessment, Plan), adaptado para prontuário longitudinal:

- **S — Subjetivo:** o que o paciente relata (sintomas, queixas, hábitos)
- **O — Objetivo:** dados mensuráveis (exames, bioimpedância, sinais vitais)
- **A — Avaliação:** interpretação clínica, hipóteses, diagnósticos ativos
- **P — Plano:** próximas ações, pendências, ajustes

Para o sistema de agentes, o formato de resposta segue:

```
[AVALIAÇÃO]
Interpretação clínica em linguagem técnica com termos explicados inline.
Ex: "HOMA-IR 8,35 — índice de resistência insulínica (dificuldade do corpo
de usar glicose) — significativamente acima do limite de 2,7."

[CORRELAÇÃO COM HISTÓRICO]
Como este dado se relaciona com exames e diagnósticos anteriores.

[EVIDÊNCIA]
Referência à literatura quando relevante.
Ex: "Conforme Eslam et al. (2020, Journal of Hepatology), a presença de
PNPLA3 rs738409 está associada a..."

[PLANO / PRÓXIMOS PASSOS]
Lista clara de ações recomendadas com prioridade.

[INCERTEZAS]
O que ainda não se sabe. O que precisa de confirmação. O que o Agente
Cético apontou como insuficiente.
```

### 5.2 Tom e linguagem

- Termos técnicos sempre explicados na mesma frase: `"TGP elevada — enzima que indica lesão das células do fígado"`
- Nunca alarmar desnecessariamente — nem minimizar
- Citações sutis de evidência: `"estudos de coorte mostram que..."`, `"conforme diretriz da SBH (2023)..."`
- Distinguir sempre: **confirmado** vs. **suspeita** vs. **hipótese de trabalho**
- Sinalizar explicitamente quando avaliação médica presencial é necessária

### 5.3 Fontes preferenciais

| Área | Fontes prioritárias |
|---|---|
| Geral | PubMed, UpToDate, BMJ, NEJM, Lancet |
| Hepatologia | Journal of Hepatology, EASL Guidelines |
| Endocrinologia | Diabetes Care, AACE Guidelines, SBD |
| Genômica | ClinVar, PharmGKB, OMIM, gnomAD, Nature Genetics |
| Farmacogenômica | PharmGKB, CPIC Guidelines |
| Laboratorial | SBPC/ML, AACC |

---

## 6. FLUXO DE DEBATE ENTRE AGENTES

```
Input do usuário
      ↓
Orquestrador lê prontuário + identifica especialidades relevantes
      ↓
Agente Clínico formula hipótese
      ↓
Agente Cético questiona hipótese
      ↓
[se necessário] Agente DNA / Especialidade específica adiciona camada
      ↓
Orquestrador sintetiza: confirma, refuta ou mantém como hipótese aberta
      ↓
Resposta ao usuário (técnica + acessível)
      ↓
[se dado novo] Atualiza prontuário automaticamente
```

---

## 7. REGRAS NÃO NEGOCIÁVEIS DO SISTEMA

1. **DNA como hipótese:** Dados de SNP array (Genera, 23andMe etc.) são sempre `SUSPEITA_GENETICA`. Nunca diagnóstico. Sempre sugerir confirmação laboratorial.
2. **Histórico imutável:** Nenhuma linha de exame histórico é deletada ou sobrescrita — apenas novas linhas são adicionadas.
3. **Incerteza explícita:** Quando dados são insuficientes para conclusão segura, o sistema diz explicitamente o que falta.
4. **Avaliação presencial:** O sistema nunca substitui avaliação médica. Quando algo excede o escopo seguro de análise remota, sinaliza ativamente.
5. **Fontes peer-reviewed:** Afirmações clínicas relevantes devem ter referência ou ser marcadas como `[sem referência disponível]`.
6. **Separação dado/interpretação:** Exame bruto vs. interpretação clínica são sempre apresentados separadamente.

---

## 8. REPOSITÓRIO PÚBLICO (GitHub)

### O que vai para o repo público
```
skills/                    # todas as skills — sem dado pessoal
agents/                    # scripts de debate e atualização
CLAUDE.md.template         # template com variáveis {{nome}}, {{diagnósticos}}
PRONTUARIO.template.md     # prontuário vazio para novos usuários
EXAMES_HISTORICO.template.md
README.md                  # como usar, como configurar
```

### O que fica local (nunca comitar)
```
PRONTUARIO.md              # dados pessoais
EXAMES_HISTORICO.md        # dados pessoais
laudos/                    # PDFs com dados médicos
.env                       # ANTHROPIC_API_KEY
```

### `.gitignore`
```
PRONTUARIO.md
EXAMES_HISTORICO.md
laudos/
.env
*.pdf
```

---

## 9. STACK TÉCNICA SUGERIDA

| Componente | Tecnologia |
|---|---|
| Agente principal | Claude Code |
| Debate entre agentes | Python + Anthropic SDK (`anthropic`) |
| Parsing de PDF | `pypdf` ou `pdfplumber` |
| Versionamento do prontuário | Git local |
| Skills | Markdown files (`.md`) |
| Memória persistente | Arquivos locais — sem banco de dados |
| API key | `.env` + `python-dotenv` |

---

## 10. MVP — O QUE IMPLEMENTAR PRIMEIRO

**Fase 1 — Fundação**
- [ ] Estrutura de pastas
- [ ] `CLAUDE.md` com contexto clínico completo
- [ ] `PRONTUARIO.md` migrado do projeto claude.ai
- [ ] `EXAMES_HISTORICO.md` migrado

**Fase 2 — Skills básicas**
- [ ] `skills/skeptic.md`
- [ ] `skills/clinical.md`
- [ ] `skills/genomics.md` (com regra SNP array embutida)
- [ ] `skills/lab_medicine.md`

**Fase 3 — Especialidades**
- [ ] `skills/endocrinology.md`
- [ ] `skills/hepatology.md`
- [ ] `skills/psychiatry.md`

**Fase 4 — Debate automatizado**
- [ ] `agents/debate.py` — implementa o loop clínico ↔ cético via API
- [ ] `agents/update_prontuario.py` — atualização automática pós-debate

**Fase 5 — GitHub**
- [ ] Templates públicos
- [ ] README com instruções de setup
- [ ] `.gitignore` configurado

---

*Requisitos v1.0 — Mar/2026 | Próximo passo: implementação Fase 1*
