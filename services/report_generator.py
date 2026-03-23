"""
Report Generator — creates a structured PDF for doctor visits.
Uses WeasyPrint + Jinja2 HTML template.
Falls back to basic HTML if template not found.
"""

from datetime import date
from pathlib import Path

from config.settings import TEMPLATES_DIR


def generate_report_pdf(
    content_md: str,
    patient_name: str,
    report_date: date,
) -> bytes:
    """
    Generates a PDF from the report content.
    Returns raw PDF bytes for download.

    Args:
        content_md: Markdown content of the report.
        patient_name: Patient name for the header.
        report_date: Date for the report header.
    """
    try:
        import markdown2
        html_content = markdown2.markdown(
            content_md,
            extras=["tables", "fenced-code-blocks"],
        )
    except ImportError:
        # Basic HTML conversion without markdown2
        html_content = _basic_md_to_html(content_md)

    full_html = _build_html(html_content, patient_name, report_date)

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=full_html).write_pdf()
        return pdf_bytes
    except ImportError:
        raise ImportError(
            "WeasyPrint não instalado. Execute: pip install weasyprint"
        )


def _build_html(body_html: str, patient_name: str, report_date: date) -> str:
    """Builds the full HTML document for PDF generation."""
    date_str = report_date.strftime("%d/%m/%Y")

    # Try to load Jinja2 template
    template_path = TEMPLATES_DIR / "doctor_report.html.jinja2"
    if template_path.exists():
        try:
            from jinja2 import Template
            template = Template(template_path.read_text(encoding="utf-8"))
            return template.render(
                body_html=body_html,
                patient_name=patient_name,
                report_date=date_str,
            )
        except ImportError:
            pass

    # Fallback: inline HTML
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: "Helvetica Neue", Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #222;
            max-width: 720px;
            margin: 40px auto;
            padding: 0 20px;
        }}
        h1 {{ color: #1a5276; border-bottom: 2px solid #1a5276; padding-bottom: 8px; }}
        h2 {{ color: #1a5276; margin-top: 24px; }}
        h3 {{ color: #2e4057; }}
        blockquote {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 12px 16px;
            margin: 16px 0;
            border-radius: 4px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 12px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{ background: #1a5276; color: white; }}
        tr:nth-child(even) {{ background: #f8f9fa; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 24px 0; }}
        .footer {{
            margin-top: 40px;
            font-size: 9pt;
            color: #888;
            border-top: 1px solid #ddd;
            padding-top: 12px;
        }}
        @page {{
            margin: 2cm;
            @bottom-center {{
                content: "HealthCore — Apoio à Decisão em Saúde | Não é laudo médico";
                font-size: 8pt;
                color: #aaa;
            }}
        }}
    </style>
</head>
<body>
    {body_html}
    <div class="footer">
        <strong>HealthCore v1.0</strong> — Sistema de apoio à decisão em saúde pessoal.<br>
        Gerado por Claude Code (Anthropic). Este documento não tem valor médico-legal.<br>
        Paciente: {patient_name} | Data: {date_str}
    </div>
</body>
</html>"""


def _basic_md_to_html(md: str) -> str:
    """Very basic Markdown to HTML conversion as last resort."""
    import re

    html = md
    # Headers
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    # Bold
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    # Italic
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
    # HR
    html = re.sub(r"^---$", r"<hr>", html, flags=re.MULTILINE)
    # Paragraphs
    html = "<p>" + html.replace("\n\n", "</p><p>") + "</p>"

    return html
