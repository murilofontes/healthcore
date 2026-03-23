#!/bin/bash
# HealthCore — First-run setup script
# Creates personal data files from templates and configures the environment.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     HealthCore — Setup Inicial       ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Create directories
echo "→ Criando estrutura de diretórios..."
mkdir -p "$PROJECT_DIR/laudos"
mkdir -p "$PROJECT_DIR/logs/debates"
mkdir -p "$PROJECT_DIR/skills"
mkdir -p "$PROJECT_DIR/agents/prompts"
mkdir -p "$PROJECT_DIR/services"
mkdir -p "$PROJECT_DIR/config"
mkdir -p "$PROJECT_DIR/templates"
mkdir -p "$PROJECT_DIR/pages"
echo "  ✓ Diretórios criados"

# Create PRONTUARIO.md from template
if [ ! -f "$PROJECT_DIR/PRONTUARIO.md" ]; then
    echo ""
    echo "→ Configurando seu prontuário..."
    read -p "  Seu nome completo: " NOME_PACIENTE
    read -p "  Data de nascimento (DD/MM/AAAA): " DATA_NASCIMENTO
    read -p "  Médico principal (opcional): " MEDICO_PRINCIPAL

    DATA_CRIACAO=$(date +"%d/%m/%Y")

    sed \
        -e "s/{{NOME_PACIENTE}}/$NOME_PACIENTE/g" \
        -e "s/{{DATA_CRIACAO}}/$DATA_CRIACAO/g" \
        -e "s/{{DATA_NASCIMENTO}}/$DATA_NASCIMENTO/g" \
        -e "s/{{MEDICO_PRINCIPAL}}/$MEDICO_PRINCIPAL/g" \
        -e "s/{{SEXO_BIOLOGICO}}/não informado/g" \
        -e "s/{{PLANO_SAUDE}}/não informado/g" \
        "$PROJECT_DIR/PRONTUARIO.template.md" > "$PROJECT_DIR/PRONTUARIO.md"

    echo "  ✓ PRONTUARIO.md criado (gitignored)"
else
    echo "  ✓ PRONTUARIO.md já existe — mantido"
fi

# Create EXAMES_HISTORICO.md from template
if [ ! -f "$PROJECT_DIR/EXAMES_HISTORICO.md" ]; then
    NOME_FOR_EXAMES="${NOME_PACIENTE:-Paciente}"
    sed \
        -e "s/{{NOME_PACIENTE}}/$NOME_FOR_EXAMES/g" \
        -e "s/{{DATA}}/$(date +%Y-%m)/g" \
        -e "s/{{VALOR}}/preencher/g" \
        -e "s/{{CONTEXTO}}/primeiro registro/g" \
        "$PROJECT_DIR/EXAMES_HISTORICO.template.md" > "$PROJECT_DIR/EXAMES_HISTORICO.md"
    echo "  ✓ EXAMES_HISTORICO.md criado (gitignored)"
else
    echo "  ✓ EXAMES_HISTORICO.md já existe — mantido"
fi

# Configure .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo ""
    echo "→ Configurando API key da Anthropic..."
    read -p "  ANTHROPIC_API_KEY (sk-ant-...): " API_KEY

    cat > "$PROJECT_DIR/.env" << EOF
ANTHROPIC_API_KEY=$API_KEY
HEALTHCORE_MODEL=claude-sonnet-4-6
GDRIVE_ENABLED=false
EOF
    echo "  ✓ .env criado (gitignored)"
else
    echo "  ✓ .env já existe — mantido"
fi

# Install Python dependencies
echo ""
echo "→ Instalando dependências Python..."
if command -v pip3 &> /dev/null; then
    pip3 install -r "$PROJECT_DIR/requirements.txt" -q
    echo "  ✓ Dependências instaladas"
elif command -v pip &> /dev/null; then
    pip install -r "$PROJECT_DIR/requirements.txt" -q
    echo "  ✓ Dependências instaladas"
else
    echo "  ⚠ pip não encontrado — instale manualmente:"
    echo "    pip install -r requirements.txt"
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║         Setup concluído! ✓           ║"
echo "╠══════════════════════════════════════╣"
echo "║  Para iniciar:                       ║"
echo "║    streamlit run app.py              ║"
echo "╚══════════════════════════════════════╝"
echo ""
