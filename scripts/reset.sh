#!/bin/bash
# HealthCore — Reset de dados pessoais
# Apaga todos os dados clínicos e restaura templates.
# Código e skills NÃO são afetados.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo -e "${RED}⚠️  RESET HEALTHCORE${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Isso irá APAGAR permanentemente:"
echo "  • PRONTUARIO.md"
echo "  • EXAMES_HISTORICO.md"
echo "  • laudos/*.pdf  ($(ls "$ROOT/laudos/"*.pdf 2>/dev/null | wc -l | tr -d ' ') arquivo(s))"
echo "  • logs/debates/*.jsonl  ($(ls "$ROOT/logs/debates/"*.jsonl 2>/dev/null | wc -l | tr -d ' ') arquivo(s))"
echo "  • logs/analyzed_labels.txt"
echo ""
echo -e "${YELLOW}Código, skills e configurações NÃO serão afetados.${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "Digite CONFIRMO para continuar: " confirm

if [ "$confirm" != "CONFIRMO" ]; then
    echo "Cancelado."
    exit 0
fi

echo ""
echo "Resetando..."

# Prontuário
cp "$ROOT/PRONTUARIO.template.md" "$ROOT/PRONTUARIO.md"
echo -e "  ${GREEN}✓${NC} PRONTUARIO.md restaurado do template"

# Histórico de exames
cp "$ROOT/EXAMES_HISTORICO.template.md" "$ROOT/EXAMES_HISTORICO.md"
echo -e "  ${GREEN}✓${NC} EXAMES_HISTORICO.md restaurado do template"

# PDFs
PDF_COUNT=$(ls "$ROOT/laudos/"*.pdf 2>/dev/null | wc -l | tr -d ' ')
if [ "$PDF_COUNT" -gt "0" ]; then
    rm -f "$ROOT/laudos/"*.pdf
    echo -e "  ${GREEN}✓${NC} $PDF_COUNT PDF(s) removido(s) de laudos/"
else
    echo -e "  ${GREEN}✓${NC} laudos/ já estava vazio"
fi

# Logs de debates
JSONL_COUNT=$(ls "$ROOT/logs/debates/"*.jsonl 2>/dev/null | wc -l | tr -d ' ')
if [ "$JSONL_COUNT" -gt "0" ]; then
    rm -f "$ROOT/logs/debates/"*.jsonl
    echo -e "  ${GREEN}✓${NC} $JSONL_COUNT log(s) de debate removido(s)"
else
    echo -e "  ${GREEN}✓${NC} logs/debates/ já estava vazio"
fi

# Rastreamento de analisados
if [ -f "$ROOT/logs/analyzed_labels.txt" ]; then
    rm -f "$ROOT/logs/analyzed_labels.txt"
    echo -e "  ${GREEN}✓${NC} analyzed_labels.txt removido"
fi

echo ""
echo -e "${GREEN}✅ Reset completo. Sistema pronto para novo usuário.${NC}"
echo ""
