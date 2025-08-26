from __future__ import annotations
import marimo

__generated_with = "0.14.16"
app = marimo.App(width="medium")


@app.cell
def _():
    from pathlib import Path
    from typing import Any
    from src.ocr_match.core import Config, ProtocolExtractor
    from src.ocr_match.db import DatabaseManager
    import marimo as mo

    try:
        cfg = Config()
        extractor = ProtocolExtractor(cfg)
        dbm = DatabaseManager(cfg)

        pdf_dir_exists = cfg.PDF_DIR.exists()
        db_file_exists = cfg.DATABASE_PATH.exists()

        if pdf_dir_exists:
            pdf_files = sorted(cfg.PDF_DIR.glob("*.pdf"))
        else:
            pdf_files = []

        print("OCR App Configuration:")
        print(f"  PDF Directory: {cfg.PDF_DIR} {'EXISTS' if pdf_dir_exists else 'NOT FOUND'}")
        print(f"  Database File: {cfg.DATABASE_PATH} {'EXISTS' if db_file_exists else 'NOT FOUND'}")
        print(f"  PDF files found: {len(pdf_files)}")

        initialization_success = True

    except Exception as e:
        print(f"Initialization error: {e}")
        cfg = None
        extractor = None
        dbm = None
        pdf_files = []
        initialization_success = False

    return cfg, dbm, extractor, pdf_files, initialization_success


@app.cell
def _(cfg, dbm, extractor, pdf_files, initialization_success):
    import marimo as mo
    
    if not initialization_success:
        ui_display = mo.md("**Backend initialization failed. Check configuration paths.**")
        selector = None
        run_btn = None
    elif not pdf_files:
        ui_display = mo.md("**No PDFs found. Set PDF_DIR env or update Config.**")
        selector = None
        run_btn = None
    else:
        options = [f.name for f in pdf_files]
        selector = mo.ui.select(options=options, value=options[0], label="Select PDF file:")
        run_btn = mo.ui.button(label="Run Precision OCR Analysis", kind="success")

        ui_display = mo.vstack([
            mo.md("### PDF File Selection"),
            mo.md(f"**Available files:** {len(pdf_files)} PDFs found"),
            selector,
            mo.md("### Precision-Focused OCR"),
            mo.md("**Goal:** Extract 9-digit codes with high precision (exact matches only)"),
            run_btn
        ])

    return ui_display, selector, run_btn


@app.cell  
def _(cfg, dbm, extractor, pdf_files, run_btn, selector):
    import marimo as mo
    
    if selector is None or run_btn is None:
        result_display = mo.md("**UI not initialized properly**")
    elif not run_btn.value:
        result_display = mo.md("**Click 'Run Precision OCR Analysis' to process the selected file**")
    else:
        pdf_name = selector.value
        pdf_path = next((p for p in pdf_files if p.name == pdf_name), None)

        if pdf_path is None:
            result_display = mo.md("**File not found.**")
        else:
            try:
                print(f"Processing: {pdf_name}")
                result = extractor.process_pdf(pdf_path)

                if result['success']:
                    protocols = result['protocols']
                    extraction_details = result.get('extraction_details', {})
                    qa_probability = extraction_details.get('qa_probability', 0.0)
                    
                    if len(protocols) == 1 and qa_probability >= 0.85:
                        precision_status = "HIGH PRECISION"
                    elif len(protocols) > 0:
                        precision_status = "MEDIUM PRECISION"
                    else:
                        precision_status = "NO DETECTION"

                    result_display = mo.md(f"""
# {precision_status} OCR Results

**File:** {pdf_name}  
**Status:** {precision_status}  
**Protocols:** {protocols if protocols else 'None'}  
**QA Confidence:** {qa_probability:.3f}  
**Success:** {result['success']}
""")
                else:
                    result_display = mo.md(f"**OCR Failed:** {result.get('error_message', 'Unknown error')}")

            except Exception as e:
                result_display = mo.md(f"**Processing Error:** {str(e)}")

    return result_display


if __name__ == "__main__":
    app.run()
