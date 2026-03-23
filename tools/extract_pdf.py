#!/usr/bin/env python3
"""
Extrai texto de PDF(s) sem usar a API da Anthropic.
Use para preparar laudos para colar no Claude Code.

Uso:
    python3 tools/extract_pdf.py laudos/meu-laudo.pdf
    python3 tools/extract_pdf.py laudos/          # extrai todos os PDFs da pasta
    python3 tools/extract_pdf.py arquivo.zip       # extrai todos os PDFs do ZIP
"""

import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def extract_one(pdf_path: Path) -> str:
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            if row:
                                pages.append(" | ".join(str(c or "") for c in row))
                else:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
        return "\n".join(pages)
    except Exception:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        except Exception as e:
            return f"[ERRO: {e}]"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    target = Path(sys.argv[1])

    # ZIP
    if target.suffix.lower() == ".zip":
        zf = zipfile.ZipFile(target)
        pdfs = [n for n in zf.namelist() if n.lower().endswith(".pdf") and not n.startswith("__")]
        print(f"\n{'='*60}")
        print(f"ZIP: {target.name} — {len(pdfs)} PDF(s)")
        print(f"{'='*60}\n")
        for pdf_name in pdfs:
            pdf_bytes = zf.read(pdf_name)
            tmp = Path("/tmp") / Path(pdf_name).name
            tmp.write_bytes(pdf_bytes)
            text = extract_one(tmp)
            print(f"\n--- {Path(pdf_name).name} ---\n")
            print(text[:4000])
            if len(text) > 4000:
                print(f"\n[... +{len(text)-4000} caracteres — use o Streamlit para o texto completo]")
        zf.close()

    # Diretório
    elif target.is_dir():
        pdfs = sorted(target.glob("*.pdf"))
        if not pdfs:
            print(f"Nenhum PDF encontrado em {target}")
            sys.exit(1)
        print(f"\n{'='*60}")
        print(f"Pasta: {target} — {len(pdfs)} PDF(s)")
        print(f"{'='*60}")
        for pdf_path in pdfs:
            text = extract_one(pdf_path)
            print(f"\n--- {pdf_path.name} ---\n")
            print(text[:3000])
            if len(text) > 3000:
                print(f"\n[... +{len(text)-3000} caracteres]")

    # Arquivo único
    elif target.exists() and target.suffix.lower() == ".pdf":
        text = extract_one(target)
        print(f"\n--- {target.name} ---\n")
        print(text)

    else:
        print(f"Arquivo não encontrado: {target}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("Cole o texto acima no Claude Code para análise.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
