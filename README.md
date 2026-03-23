# HealthCore

> Sistema local de suporte à saúde pessoal, com multi-agent debate, análise de exames e geração de relatórios para consultas médicas.

**Este projeto não fornece diagnósticos médicos.** Toda saída é uma hipótese clínica, sujeita à validação por profissional de saúde habilitado. Em caso de emergência, ligue **192 (SAMU)**.

---

## O que é

HealthCore é uma plataforma **local-first** que usa a API da Anthropic (Claude) para ajudar você a:

- **Entender seus exames** — análise contextualizada de laudos laboratoriais e de imagem
- **Preparar consultas médicas** — gera relatórios estruturados para levar ao médico
- **Acompanhar tendências** — histórico visual de marcadores ao longo do tempo
- **Debater hipóteses** — agente clínico e agente cético discutem cada caso antes de responder

Todos os dados pessoais ficam **exclusivamente na sua máquina**. Nenhum dado de prontuário, laudo ou exame é enviado ao GitHub.

---

## Arquitetura

```
Usuário
  │
  ▼
Check de Emergência (pré-API, sem custo)
  │
  ▼
Agente Clínico  ──────►  Agente Cético
  │                          │
  └──────────┬───────────────┘
             ▼
    Agente Genômico (se DNA referenciado)
             │
             ▼
    Orchestrator (síntese final)
             │
             ▼
    Resposta + Audit Log JSONL
```

**Stack:**
- `anthropic` SDK — motor de todos os agentes
- `streamlit` — UI local (chat, upload, histórico, relatório)
- `pdfplumber` — parsing de laudos em PDF
- `weasyprint` + `jinja2` — geração de PDF para médico
- `plotly` / `pandas` — timeline de marcadores

---

## Estrutura do Projeto

```
healthcore/
├── GUARDRAILS.md                   # Regras de segurança e guardrails
├── HEALTH_AGENT_REQUISITOS.md      # Arquitetura e requisitos detalhados
│
├── skills/                         # Skills por especialidade (público)
│   ├── endocrinology.md
│   ├── hepatology.md
│   ├── psychiatry.md
│   ├── genomics.md
│   ├── cardiology.md
│   └── lab_medicine.md
│
├── agents/                         # Agentes e system prompts
│   ├── debate.py
│   ├── clinical_agent.py
│   ├── skeptic_agent.py
│   ├── genomics_agent.py
│   └── prompts/
│
├── services/                       # Serviços core
│   ├── memory_manager.py
│   ├── pdf_parser.py
│   ├── exam_indexer.py
│   ├── report_generator.py
│   └── gdrive_sync.py              # Opcional
│
├── pages/                          # Páginas Streamlit
│   ├── 01_chat.py
│   ├── 02_upload_exam.py
│   ├── 03_exam_history.py
│   └── 04_generate_report.py
│
├── config/
│   ├── settings.py
│   └── guardrails.py
│
├── templates/
│   └── doctor_report.html.jinja2
│
├── scripts/
│   ├── setup.sh                    # First-run: inicializa prontuário e dirs
│   └── init_consent.py
│
├── PRONTUARIO.template.md          # Template público (sem dados pessoais)
├── EXAMES_HISTORICO.template.md
├── app.py
└── requirements.txt
```

**Dados pessoais (gitignored):**
```
PRONTUARIO.md           ← sua história clínica
EXAMES_HISTORICO.md     ← seus resultados
laudos/                 ← seus PDFs
logs/                   ← debates auditados
.env                    ← ANTHROPIC_API_KEY
```

---

## Instalação

### Pré-requisitos

- Python 3.11+
- [Chave de API da Anthropic](https://console.anthropic.com)

### Setup

```bash
# Clone o repositório
git clone https://github.com/murilofontes/healthcore.git
cd healthcore

# Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure o ambiente (copia templates, cria dirs, pede sua API key)
./scripts/setup.sh

# Inicie a aplicação
streamlit run app.py
```

---

## Guardrails e Segurança

O sistema opera com **guardrails em dupla camada**:

1. **Camada Python** (não bypassável) — detecta emergências antes de qualquer chamada à API, valida que o prontuário nunca encolhe (imutabilidade histórica)
2. **System prompts** — cada agente tem as regras R1-R6 embutidas, incluindo a classificação de certeza

**Classificação de certeza:**

| Label | Significado |
|-------|-------------|
| `[CONFIRMADO]` | Dado laboratorial ou clínico confirmado |
| `[SUSPEITA]` | Consistente com dados, não confirmado |
| `[HIPÓTESE]` | Inferência razoável |
| `[SUSPEITA_GENETICA]` | Variante de SNP array (não validada clinicamente) |
| `[DESCARTADO]` | Evidência de ausência |
| `[AGUARDANDO]` | Exame solicitado, resultado pendente |

**Regras absolutas:**
- **R1** — Nunca diagnóstico. Sempre "hipótese clínica"
- **R2** — Nunca prescrição. Contextualiza, médico decide
- **R3** — DNA via SNP array é sempre SUSPEITA_GENETICA
- **R4** — Incerteza explícita quando dados insuficientes
- **R5** — Emergências redirecionam imediatamente ao SAMU (192)
- **R6** — Histórico imutável. Prontuário só cresce

---

## Google Drive (Opcional)

Para sincronizar seu prontuário e laudos com o Google Drive, configure `GDRIVE_ENABLED=True` em `config/settings.py` e siga as instruções em `services/gdrive_sync.py`.

A integração usa escopo `drive.file` — o app só acessa arquivos que ele mesmo criou.

---

## Contribuindo

Este projeto nasceu de uma necessidade pessoal e é compartilhado para quem enfrenta a mesma situação: navegar um sistema de saúde complexo com muitos especialistas, muitos exames e pouca coordenação.

Contribuições são bem-vindas, especialmente:
- Novas skills de especialidade (`skills/`)
- Melhorias nos system prompts (`agents/prompts/`)
- Suporte a formatos de laudo de outros laboratórios
- Traduções e internacionalização

Abra uma issue antes de PRs grandes.

---

## Aviso Legal

Este sistema é uma ferramenta de apoio à decisão pessoal, não um dispositivo médico. Nenhuma saída deve ser interpretada como diagnóstico, prescrição ou substituição de consulta médica. O uso é de inteira responsabilidade do usuário.

---

> Gerado com [Claude Code](https://claude.ai/code) por Anthropic
>
> *"Tecnologia a serviço de quem precisa entender a própria saúde."*
