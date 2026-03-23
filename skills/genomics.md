# Skill: Genômica Clínica
> Version: 1.0 | Last Updated: Mar/2026
> Guidelines: ACMG 2023, CPIC Guidelines, PharmGKB, ClinVar

## Escopo

Ativar quando a pergunta envolver: SNPs, variantes genéticas, farmacogenômica, MTHFR, APOE, PNPLA3, HFE, ancestralidade genética, dados Genera/23andMe/AncestryDNA.

---

## REGRA FUNDAMENTAL (R3 — ABSOLUTA)

**Todo dado de SNP array é `[SUSPEITA_GENETICA]`. Nunca diagnóstico.**

Plataformas como Genera, 23andMe e AncestryDNA:
- Foram desenvolvidas para ancestralidade, não diagnóstico clínico
- Não têm validação clínico-laboratorial para uso médico no Brasil
- O médico não pode prescrever ou decidir conduta baseado nelas sozinho
- Sempre indicar confirmação por teste laboratorial específico

---

## Variantes de Alta Relevância Clínica

### MTHFR

| Variante | Impacto | Frequência | Confirmação |
|----------|---------|-----------|-------------|
| C677T (rs1801133) TT | Redução ~70% atividade MTHFR | ~10–15% população | PCR + homocisteína sérica |
| C677T CT | Redução ~35% | ~40% | PCR |
| A1298C (rs1801131) CC | Impacto menor isolado | ~10% | PCR |
| C677T TT + A1298C AC (composto) | Redução moderada-grave | Raro | Dosagem enzimática |

**Relevância clínica:**
- Metabolismo de folato e metilação (ciclo do metil)
- Homocisteína: cada aumento de 5 µmol/L → ~10% aumento risco cardiovascular (meta-análise)
- Sensibilidade ao metotrexato, 5-FU (farmacogenômica)

**Confirmação recomendada:** PCR alelo-específico (Fleury, DASA) + dosagem de homocisteína + folato sérico.

### APOE

| Genótipo | Risco Alzheimer | Risco Cardiovascular |
|----------|----------------|---------------------|
| ε2/ε2 | Menor | Neutro-protetor |
| ε3/ε3 | Basal | Basal |
| ε3/ε4 | ~3-4x | Aumentado |
| ε4/ε4 | ~12-15x | Alto |

**Limitações:**
- ε4 aumenta risco mas não determina diagnóstico de Alzheimer
- Penetrância < 100% — maioria dos ε4 não desenvolve Alzheimer
- Aconselhamento genético recomendado antes de revelar resultado

### PNPLA3 rs738409

| Genótipo | Risco MASLD | Risco Fibrose |
|----------|-----------|---------------|
| GG (homozigoto normal) | Basal | Basal |
| CG (heterozigoto) | Moderado | Moderado |
| CC (homozigoto risco) | Alto | Alto |

**ClinVar:** Pathogenic/likely pathogenic para MASLD em CC homozigoto.
**Mecanismo:** PNPLA3 I148M reduz lipólise hepática → acúmulo de triglicérides.

### HFE — Hemocromatose Hereditária

| Variante | Penetrância | Interpretação |
|----------|------------|---------------|
| C282Y/C282Y | 25% H, <1% M | Alto risco — investigar ferritina + saturação transferrina |
| C282Y/H63D | 5–10% | Risco moderado |
| H63D/H63D | Baixo | Risco leve; maioria não desenvolve sobrecarga de ferro clínica |

---

## Farmacogenômica — Variantes com Nível CPIC 1A/1B

| Gene | Variante | Medicamento | Impacto |
|------|----------|-------------|---------|
| CYP2C19 | *2, *3 (poor metabolizer) | Clopidogrel | Redução ativação — menor eficácia antiagregante |
| CYP2C19 | *17 (ultra-rapid) | IBPs (omeprazol) | Metabolização acelerada — pode necessitar dose maior |
| SLCO1B1 | *5 (rs4149056) | Sinvastatina, outros | Risco aumentado de miopatia com estatinas |
| CYP2D6 | *4, *5, *6 (poor) | Codeína, antidepressivos | Toxicidade ou falta de efeito |
| DPYD | *2A | 5-FU, capecitabina | Risco toxicidade severa — oncologia |
| TPMT/NUDT15 | variantes | Azatioprina, 6-MP | Mielotoxicidade |

---

## Guardrails Específicos

- SNP array → sempre `[SUSPEITA_GENETICA]`
- APOE ε4 não é diagnóstico de Alzheimer — aconselhamento genético recomendado
- Farmacogenômica informa — não prescrevemos ajustes de dose
- Confirmar com fontes: ClinVar (pathogenic), PharmGKB (level 1A/1B)

---

## Diretrizes de Referência

- ACMG Standards and Guidelines 2023
- CPIC Guidelines — cpicpgx.org
- PharmGKB — pharmgkb.org (Level 1A/1B apenas)
- ClinVar — ncbi.nlm.nih.gov/clinvar
- gnomAD — gnomad.broadinstitute.org (frequências populacionais)
