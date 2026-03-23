"""
Machine-readable version of GUARDRAILS.md rules.
Python-layer enforcement — not bypassable via prompt injection.
"""

# R5 — Emergency trigger strings (checked before any API call)
EMERGENCY_TRIGGERS = [
    "dor no peito",
    "dor torácica",
    "chest pain",
    "sangramento",
    "hemorragia",
    "ideação suicida",
    "quero me matar",
    "vou me matar",
    "me machucar",
    "autolesão",
    "convulsão",
    "perda de consciência",
    "desmaio",
    "avc",
    "derrame",
    "infarto",
    "falta de ar grave",
    "não consigo respirar",
    "paralisia",
    "parada cardíaca",
    "overdose",
]

EMERGENCY_RESPONSE = (
    "🔴🚨 **EMERGÊNCIA DETECTADA**\n\n"
    "Este sistema **não é adequado para emergências médicas**.\n\n"
    "**Ligue imediatamente:**\n"
    "- **SAMU: 192**\n"
    "- **Bombeiros: 193**\n"
    "- **CVV (crise emocional): 188**\n\n"
    "Vá ao pronto-socorro mais próximo ou peça ajuda a alguém ao seu redor."
)

# Certainty classification labels (Section 3 of GUARDRAILS.md)
CERTAINTY_LABELS = [
    "CONFIRMADO",
    "SUSPEITA",
    "HIPÓTESE",
    "SUSPEITA_GENETICA",
    "HIPOTESE_GENETICA",
    "CONFIRMADO_GENETICAMENTE",
    "CONFIRMADO_CLINICAMENTE",
    "DESCARTADO",
    "DESCARTADO_CLINICAMENTE",
    "AGUARDANDO",
    "DADO INSUFICIENTE",
]

# Urgency scale (Section 4 of GUARDRAILS.md)
URGENCY_LEVELS = {
    "EMERGÊNCIA": {"emoji": "🔴🚨", "description": "Risco imediato à vida"},
    "URGENTE": {"emoji": "🔴", "description": "Avaliação médica em dias"},
    "IMPORTANTE": {"emoji": "🟠", "description": "Avaliação médica em semanas"},
    "MONITORAR": {"emoji": "🟡", "description": "Acompanhar sem urgência imediata"},
    "INFORMATIVO": {"emoji": "🟢", "description": "Contexto sem ação necessária"},
}

# Skill keyword routing (triggers which skill files are loaded)
from typing import Dict, List

SKILL_KEYWORDS: Dict[str, List[str]] = {
    "endocrinology": [
        "insulina", "glicose", "homa", "hba1c", "tireoide", "tsh", "t4", "t3",
        "diabetes", "metabolismo", "obesidade", "mounjaro", "tirzepatida",
        "ozempic", "semaglutida", "resistência insulínica", "cortisol",
        "aldosterona", "adrenal",
    ],
    "hepatology": [
        "tgp", "tgo", "alt", "ast", "ggt", "fosfatase alcalina", "bilirrubina",
        "ferritina", "fígado", "hepática", "hepatite", "masld", "nash",
        "fibroscan", "fibrose", "esteatose", "cirrose",
    ],
    "cardiology": [
        "colesterol", "ldl", "hdl", "triglicérides", "lipidograma", "pressão",
        "pressão arterial", "hipertensão", "mav", "malformação arteriovenosa",
        "cardiovascular", "aterosclerose", "risco cardíaco", "apo b", "pcr",
    ],
    "psychiatry": [
        "tdah", "adhd", "depressão", "ansiedade", "sono", "insônia",
        "ritalina", "metilfenidato", "vyvanse", "lisdexanfetamina",
        "antidepressivo", "ssri", "snri", "humor", "bipolar", "toc",
    ],
    "genomics": [
        "dna", "snp", "genético", "genômica", "mthfr", "apoe", "brca",
        "genera", "23andme", "ancestrydna", "variante", "polimorfismo",
        "farmacogenômica", "pnpla3", "hfe", "hemocromatose",
    ],
    "lab_medicine": [
        "exame", "laudo", "resultado", "referência", "hemograma", "leucócitos",
        "eritrócitos", "plaquetas", "vcm", "hcm", "vitamina d", "vitamina b12",
        "folato", "zinco", "magnésio", "homocisteína", "proteína c reativa",
    ],
}

# SNP array platforms that trigger R3 guardrail
SNP_ARRAY_PLATFORMS = ["genera", "23andme", "ancestrydna", "ancestry dna", "myheritage"]

# Out-of-scope topics
OUT_OF_SCOPE_TRIGGERS = [
    "receita", "prescrição", "me prescreva", "me indique o medicamento",
    "qual dose", "posso parar de tomar", "diagnóstico definitivo",
]

OUT_OF_SCOPE_RESPONSE = (
    "Este sistema não prescreve medicamentos, ajusta doses ou emite diagnósticos definitivos (R1 e R2). "
    "Posso contextualizar mecanismos, evidências e hipóteses clínicas — a decisão é sempre do seu médico."
)
