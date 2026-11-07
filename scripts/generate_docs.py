"""
Document Generator Engine.

Generates tailored cover letters and CV variants for targeted job vacancies.
Outputs assets to generated/<company_slug>_<vacancy_id>/ and registers them in documents table.

Usage:
    python scripts/generate_docs.py --vacancy-id 138959503 [--format md,pdf] [--json]
"""

from __future__ import annotations
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.config import Config
from scripts.init_db import get_connection, init_database
from scripts.logger import log_event


CYR_TO_LAT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
}


def slugify(text: str) -> str:
    """Converts string into a clean ASCII filesystem slug with Cyrillic transliteration."""
    text_lower = text.lower()
    transliterated = "".join(CYR_TO_LAT.get(c, c) for c in text_lower)
    cleaned = re.sub(r"[^a-z0-9\s_-]", "", transliterated).strip()
    slug = re.sub(r"[-\s]+", "_", cleaned)[:40]
    return slug or "company"


def strip_yaml_frontmatter(content: str) -> str:
    """Strips YAML frontmatter delimiter (--- ... ---) from markdown text."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].lstrip()
    return content


def resolve_templates(sector: str, title: str) -> tuple[Path, Path, str, str]:
    """Resolves cover letter template and CV variant based on sector and title."""
    s_lower = f"{sector} {title}".lower()

    # Sector template
    if any(k in s_lower for k in ["банк", "финанс", "аудит", "бухгалтер", "finance"]):
        cl_template = Config.TEMPLATES_DIR / "banking_finance.md"
        hook = "Финансовая стабильность и точность аналитики — фундамент успешного развития любого масштабного бизнеса."
        achieve = "Внедрил прозрачный финансовый учет P&L и сократил постоянные расходы на 18%."
    elif any(k in s_lower for k in ["логистик", "склад", "вэд", "авиа", "logistics"]):
        cl_template = Config.TEMPLATES_DIR / "logistics_aviation.md"
        hook = "Эффективная логистика и бесперебойная цепочка поставок напрямую определяют прибыльность и масштабирование."
        achieve = "Оптимизировал регламенты обработки логистических заказов, сократив среднее время исполнения на 25%."
    elif any(k in s_lower for k in ["аналитик", "data", "it", "bi", "analytics"]):
        cl_template = Config.TEMPLATES_DIR / "it_analytics.md"
        hook = "Качественная работа с данными и автоматизация процессов позволяют компании оперативно принимать обоснованные решения."
        achieve = "Построил сквозные дашборды и обновил регламенты, снизив операционные ошибки на 22%."
    else:
        cl_template = Config.TEMPLATES_DIR / "fmcg_distribution.md"
        hook = "Операционная прозрачность и оптимизация ресурсов дают ключевое преимущество на конкурентном рынке."
        achieve = "Организовал строгий материальный учет и внедрил регламенты, исключив недостачи и снизив издержки на 18%."

    if not cl_template.exists():
        cl_template = Config.TEMPLATES_DIR / "_template_base.md"

    # CV variant
    if any(k in s_lower for k in ["финанс", "бухгалтер", "аудит", "инвест", "казначей"]):
        cv_variant = Config.VARIANTS_DIR / "financial_analyst.md"
        variant_name = "financial_analyst"
    elif any(k in s_lower for k in ["операцион", "руководит", "управляющ", "директор", "operations", "coo", "ceo"]):
        cv_variant = Config.VARIANTS_DIR / "operations_manager.md"
        variant_name = "operations_manager"
    else:
        cv_variant = Config.VARIANTS_DIR / "business_analyst.md"
        variant_name = "business_analyst"

    return cl_template, cv_variant, hook, achieve


def escape_typst(text: str) -> str:
    """Escapes special Typst markup characters (like @ for citations)."""
    return text.replace("@", "\\@")


def render_typst_to_pdf(typ_path: Path, pdf_path: Path) -> bool:
    """Renders Typst file to pristine vector PDF via standalone Typst binary."""
    typst_bin = Config.get_typst_binary()
    if not typst_bin:
        return False
    try:
        cmd = [
            str(typst_bin),
            "compile",
            str(typ_path),
            str(pdf_path),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception:
        return False


def render_html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    """Renders HTML file to PDF via headless Microsoft Edge (fallback engine)."""
    edge_bin = Config.get_edge_binary()
    if not edge_bin:
        return False
    try:
        cmd = [
            str(edge_bin),
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={pdf_path}",
            str(html_path),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        return pdf_path.exists() and pdf_path.stat().st_size > 0
    except Exception:
        return False


def convert_markdown_to_simple_html(title: str, md_text: str) -> str:
    """Lightweight stdlib markdown to styled HTML converter."""
    # Convert bold, lists, and line breaks
    html_lines = []
    for line in md_text.splitlines():
        line = line.strip()
        if not line:
            html_lines.append("<br>")
            continue
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        else:
            formatted = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            html_lines.append(f"<p>{formatted}</p>")

    body_content = "\n".join(html_lines)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    @page {{ margin: 15mm; size: A4; }}
    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      line-height: 1.5;
      color: #1e293b;
      margin: 0;
      padding: 30px;
    }}
    h1 {{ font-size: 20px; color: #0f172a; border-bottom: 2px solid #0284c7; padding-bottom: 6px; }}
    h2 {{ font-size: 16px; color: #0284c7; margin-top: 20px; }}
    h3 {{ font-size: 14px; color: #334155; margin-top: 15px; }}
    p, li {{ font-size: 13px; color: #334155; }}
    strong {{ color: #0f172a; }}
  </style>
</head>
<body>
  {body_content}
</body>
</html>"""


def generate_documents_for_vacancy(
    vacancy_id: str,
    doc_formats: List[str] | None = None,
    db_path: Path | None = None,
) -> Dict[str, Any]:
    """Generates tailored cover letter and CV files for a specific vacancy."""
    target_db = Path(db_path) if db_path else Config.DB_PATH
    formats = [f.strip().lower() for f in (doc_formats or ["md", "pdf"])]

    conn = get_connection(target_db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, company, sector, tier, salary_text FROM vacancies WHERE id = ?",
        (vacancy_id,),
    )
    vac = cursor.fetchone()

    if not vac:
        conn.close()
        err_msg = f"Vacancy ID '{vacancy_id}' not found in database."
        log_event("DOC_GEN_ERROR", {"error": err_msg, "vacancy_id": vacancy_id}, level="ERROR")
        return {"success": False, "error": err_msg, "code": Config.EXIT_NO_DATA}

    vid, title, company, sector, tier, salary_text = vac
    company_slug = slugify(company)
    target_dir = Config.GENERATED_DIR / f"{company_slug}_{vid}"
    target_dir.mkdir(parents=True, exist_ok=True)

    cl_tmpl_path, cv_tmpl_path, hook, achieve = resolve_templates(sector, title)

    raw_cl = cl_tmpl_path.read_text(encoding="utf-8") if cl_tmpl_path.exists() else ""
    raw_cv = cv_tmpl_path.read_text(encoding="utf-8") if cv_tmpl_path.exists() else ""

    clean_cl = strip_yaml_frontmatter(raw_cl)
    today_str = datetime.date.today().isoformat()
    now_iso = datetime.datetime.now().isoformat()

    replacements = {
        "{{company}}": company,
        "{{position}}": title,
        "{{candidate_name}}": Config.CANDIDATE_NAME,
        "{{candidate_phone}}": Config.CANDIDATE_PHONE,
        "{{candidate_email}}": Config.CANDIDATE_EMAIL,
        "{{candidate_telegram}}": Config.CANDIDATE_TELEGRAM,
        "{{salary_expectation}}": salary_text or Config.SALARY_EXPECTATION_DEFAULT,
        "{{date}}": today_str,
        "{{sector_hook}}": hook,
        "{{key_achievement}}": achieve,
    }

    # Render Cover Letter
    rendered_cl = clean_cl
    for k, v in replacements.items():
        rendered_cl = rendered_cl.replace(k, str(v))

    generated_files: Dict[str, str] = {}

    # Write Markdown
    cl_md_path = target_dir / "cover_letter.md"
    cl_md_path.write_text(rendered_cl, encoding="utf-8")
    generated_files["cover_letter_md"] = str(cl_md_path)

    cv_md_path = target_dir / "cv_tailored.md"
    cv_md_path.write_text(raw_cv, encoding="utf-8")
    generated_files["cv_md"] = str(cv_md_path)

    # HTML / PDF rendering
    if "html" in formats or "pdf" in formats:
        cl_html = convert_markdown_to_simple_html(f"Cover Letter — {company}", rendered_cl)
        cl_html_path = target_dir / "cover_letter.html"
        cl_html_path.write_text(cl_html, encoding="utf-8")
        generated_files["cover_letter_html"] = str(cl_html_path)

        cv_html = convert_markdown_to_simple_html(f"CV — {title}", raw_cv)
        cv_html_path = target_dir / "cv_tailored.html"
        cv_html_path.write_text(cv_html, encoding="utf-8")
        generated_files["cv_html"] = str(cv_html_path)

        if "pdf" in formats:
            cl_pdf_path = target_dir / "cover_letter.pdf"
            cv_pdf_path = target_dir / "cv_tailored.pdf"

            cl_typ_tmpl = cl_tmpl_path.with_suffix(".typ")
            cv_typ_tmpl = cv_tmpl_path.with_suffix(".typ")
            typst_bin = Config.get_typst_binary()

            used_typst = False
            if typst_bin and cl_typ_tmpl.exists() and cv_typ_tmpl.exists():
                # Render Typst cover letter
                cl_typ_content = cl_typ_tmpl.read_text(encoding="utf-8")
                for k, v in replacements.items():
                    cl_typ_content = cl_typ_content.replace(k, escape_typst(str(v)))
                cl_typ_path = target_dir / "cover_letter.typ"
                cl_typ_path.write_text(cl_typ_content, encoding="utf-8")
                generated_files["cover_letter_typ"] = str(cl_typ_path)

                # Render Typst CV
                cv_typ_content = cv_typ_tmpl.read_text(encoding="utf-8")
                for k, v in replacements.items():
                    cv_typ_content = cv_typ_content.replace(k, escape_typst(str(v)))
                cv_typ_path = target_dir / "cv_tailored.typ"
                cv_typ_path.write_text(cv_typ_content, encoding="utf-8")
                generated_files["cv_tailored_typ"] = str(cv_typ_path)

                # Compile with Typst
                ok_cl = render_typst_to_pdf(cl_typ_path, cl_pdf_path)
                ok_cv = render_typst_to_pdf(cv_typ_path, cv_pdf_path)
                if ok_cl and ok_cv:
                    generated_files["cover_letter_pdf"] = str(cl_pdf_path)
                    generated_files["cv_tailored_pdf"] = str(cv_pdf_path)
                    generated_files["engine_used"] = "typst"
                    used_typst = True

            if not used_typst:
                # Fallback to headless Edge
                if render_html_to_pdf(cl_html_path, cl_pdf_path):
                    generated_files["cover_letter_pdf"] = str(cl_pdf_path)
                if render_html_to_pdf(cv_html_path, cv_pdf_path):
                    generated_files["cv_tailored_pdf"] = str(cv_pdf_path)
                generated_files["engine_used"] = "edge_headless"

    # Record in documents table
    rel_cl = str(cl_md_path.relative_to(Config.PROJECT_ROOT))
    cursor.execute(
        """
        INSERT INTO documents (vacancy_id, doc_type, variant_used, file_path, generated_at)
        VALUES (?, 'cover_letter', ?, ?, ?)
    """,
        (vid, cl_tmpl_path.stem, rel_cl, now_iso),
    )

    rel_cv = str(cv_md_path.relative_to(Config.PROJECT_ROOT))
    cursor.execute(
        """
        INSERT INTO documents (vacancy_id, doc_type, variant_used, file_path, generated_at)
        VALUES (?, 'cv', ?, ?, ?)
    """,
        (vid, cv_tmpl_path.stem, rel_cv, now_iso),
    )

    conn.commit()
    conn.close()

    result = {
        "success": True,
        "code": Config.EXIT_SUCCESS,
        "vacancy_id": vid,
        "company": company,
        "title": title,
        "directory": str(target_dir),
        "files": generated_files,
        "timestamp": now_iso,
    }
    log_event("DOCS_GENERATED", result)
    return result


def compile_master_resume(output_pdf: Path | None = None) -> Dict[str, Any]:
    """Compiles the master resume into a standalone PDF via Typst."""
    target_out = output_pdf or (Config.MASTER_DIR / "resume.pdf")
    typ_path = Config.MASTER_DIR / "resume.typ"

    if not typ_path.exists():
        return {"success": False, "error": f"Master resume template not found at {typ_path}"}

    # Prepare replacements
    content = typ_path.read_text(encoding="utf-8")
    replacements = {
        "{{candidate_name}}": Config.CANDIDATE_NAME,
        "{{candidate_phone}}": Config.CANDIDATE_PHONE,
        "{{candidate_email}}": escape_typst(Config.CANDIDATE_EMAIL),
        "{{candidate_telegram}}": escape_typst(Config.CANDIDATE_TELEGRAM),
    }
    for k, v in replacements.items():
        content = content.replace(k, str(v))

    tmp_typ = Config.MASTER_DIR / "resume_compiled.typ"
    tmp_typ.write_text(content, encoding="utf-8")
    try:
        ok = render_typst_to_pdf(tmp_typ, target_out)
        if not ok:
            # Fallback to HTML
            html_path = Config.MASTER_DIR / "resume.html"
            ok = render_html_to_pdf(html_path, target_out)
        return {"success": ok, "pdf_path": str(target_out), "engine": "typst" if ok else "failed"}
    finally:
        if tmp_typ.exists():
            tmp_typ.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate tailored Cover Letter and CV for vacancy")
    parser.add_argument("--vacancy-id", type=str, default=None, help="Target vacancy ID")
    parser.add_argument("--all-applied", action="store_true", help="Generate docs for all applied vacancies")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], default=None, help="Generate docs for all vacancies in tier")
    parser.add_argument("--compile-master", action="store_true", help="Compile master resume.pdf")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of vacancies processed")
    parser.add_argument("--format", type=str, default="md,pdf", help="Output formats comma-separated (md,html,pdf)")
    parser.add_argument("--db-path", type=str, default=None, help="Custom DB path")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    args = parser.parse_args()
    db_target = Path(args.db_path) if args.db_path else Config.DB_PATH
    formats = [f.strip().lower() for f in args.format.split(",") if f.strip()]

    # If --compile-master requested
    if args.compile_master:
        res_m = compile_master_resume()
        if args.json:
            print(json.dumps(res_m, indent=2, ensure_ascii=False))
        else:
            print(f"[OK] Master resume compiled: {res_m.get('pdf_path')}")
        return Config.EXIT_SUCCESS if res_m["success"] else Config.EXIT_ERROR

    # Determine target vacancy IDs
    vacancy_ids: List[str] = []
    if args.vacancy_id:
        vacancy_ids.append(args.vacancy_id)
    elif args.all_applied:
        conn = get_connection(db_target)
        c = conn.cursor()
        query = "SELECT DISTINCT vacancy_id FROM applications ORDER BY last_updated DESC"
        if args.limit:
            query += f" LIMIT {args.limit}"
        vacancy_ids = [r[0] for r in c.execute(query).fetchall()]
        conn.close()
    elif args.tier:
        conn = get_connection(db_target)
        c = conn.cursor()
        query = f"SELECT id FROM vacancies WHERE tier = {args.tier} ORDER BY id ASC"
        if args.limit:
            query += f" LIMIT {args.limit}"
        vacancy_ids = [r[0] for r in c.execute(query).fetchall()]
        conn.close()
    else:
        parser.print_help()
        return Config.EXIT_ERROR

    if not vacancy_ids:
        err = {"success": False, "error": "No matching vacancies found", "code": Config.EXIT_NO_DATA}
        if args.json:
            print(json.dumps(err, indent=2, ensure_ascii=False))
        else:
            print("[WARN] No vacancies found matching query", file=sys.stderr)
        return Config.EXIT_NO_DATA

    results = []
    for vid in vacancy_ids:
        r = generate_documents_for_vacancy(
            vacancy_id=vid,
            doc_formats=formats,
            db_path=db_target,
        )
        results.append(r)

    if args.json:
        if args.vacancy_id and len(results) == 1:
            out = results[0]
        else:
            out = {
                "success": True,
                "total_processed": len(results),
                "engine": "typst",
                "results": results,
            }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"[OK] Successfully generated {len(results)} tailored document sets via Typst:")
        for r in results:
            if r["success"]:
                print(f"     [{r['vacancy_id']}] {r['company']} — {r['title']}")
                print(f"       -> {r['directory']}")

    return Config.EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
