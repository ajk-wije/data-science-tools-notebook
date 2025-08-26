from __future__ import annotations
import marimo

__generated_with = "0.14.16"
app = marimo.App(width="medium")


@app.cell
def _():
    import sys
    import os
    from pathlib import Path
    from typing import Any
    
    # Add project root to Python path for imports
    # Navigate from current working directory to project root
    current_dir = Path.cwd()
    
    # Look for the project root (where src/ directory exists)
    project_root = current_dir
    while project_root != project_root.parent:
        if (project_root / "src").exists():
            break
        project_root = project_root.parent
    
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    print(f"Project root: {project_root}")
    print(f"Python path updated: {str(project_root) in sys.path}")
    
    from src.ocr_match.core import Config, ProtocolExtractor
    from src.ocr_match.db import DatabaseManager

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
    # Debug: Check available UI components
    print("Available marimo.ui components:")
    print(dir(marimo.ui))
    
    if not initialization_success:
        ui_display = marimo.md("**Backend initialization failed. Check configuration paths.**")
        selector = None
        run_btn = None
    elif not pdf_files:
        ui_display = marimo.md("**No PDFs found. Set PDF_DIR env or update Config.**")
        selector = None
        run_btn = None
    else:
        options = [f.name for f in pdf_files]
        
        # Try different UI components based on availability
        try:
            # First try dropdown
            selector = marimo.ui.dropdown(options=options, value=options[0], label="Select PDF file:")
        except AttributeError:
            try:
                # Fallback to radio buttons
                selector = marimo.ui.radio(options=options, value=options[0], label="Select PDF file:")
            except AttributeError:
                # Final fallback - just use text and manual selection
                selector = None
                selected_file = options[0] if options else None

        if selector is not None:
            ui_display = marimo.vstack([
                marimo.md("### PDF File Selection"),
                marimo.md(f"**Available files:** {len(pdf_files)} PDFs found"),
                selector,
                marimo.md("### Precision-Focused OCR"),
                marimo.md("**Goal:** Extract 9-digit codes with high precision (exact matches only)"),
                marimo.ui.button(label="Run Precision OCR Analysis", kind="success")
            ])
            run_btn = ui_display.children[-1]
        else:
            # Fallback UI without selector
            run_btn = marimo.ui.button(label="Run Precision OCR Analysis", kind="success")
            ui_display = marimo.vstack([
                marimo.md("### PDF File Selection"),
                marimo.md(f"**Available files:** {len(pdf_files)} PDFs found"),
                marimo.md(f"**Auto-selected:** {selected_file}"),
                marimo.md("### Precision-Focused OCR"),
                marimo.md("**Goal:** Extract 9-digit codes with high precision (exact matches only)"),
                run_btn
            ])

    return ui_display, selector, run_btn


@app.cell
def _(cfg, dbm, extractor, pdf_files, run_btn, selector):
    if selector is None or run_btn is None:
        result_display = marimo.md("**UI not initialized properly**")
    elif not run_btn.value:
        result_display = marimo.md("**Click 'Run Precision OCR Analysis' to process the selected file**")
    else:
        # Get selected file
        if selector is not None:
            pdf_name = selector.value
        else:
            # Fallback to first file if no selector
            pdf_name = pdf_files[0].name if pdf_files else None
            
        if pdf_name is None:
            result_display = marimo.md("**No file available to process.**")
        else:
            pdf_path = next((p for p in pdf_files if p.name == pdf_name), None)

            if pdf_path is None:
                result_display = marimo.md("**File not found.**")
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

                        result_display = marimo.md(f"""
# {precision_status} OCR Results

**File:** {pdf_name}  
**Status:** {precision_status}  
**Protocols:** {protocols if protocols else 'None'}  
**QA Confidence:** {qa_probability:.3f}  
**Success:** {result['success']}
""")
                    else:
                        result_display = marimo.md(f"**OCR Failed:** {result.get('error_message', 'Unknown error')}")

                except Exception as e:
                    result_display = marimo.md(f"**Processing Error:** {str(e)}")

    return result_display


if __name__ == "__main__":
    app.run()
