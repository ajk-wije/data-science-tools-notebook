"""
Precision-Focused OCR App

Select a PDF from Config.PDF_DIR, run hybrid OCR (PaddleOCR + Textract fallback),
with QA gate decisions and precision-focused analysis.
"""
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

        # Check if paths exist
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
    """File selection UI with error handling"""
    import marimo as mo
    
    if not initialization_success:
        return mo.md("**Backend initialization failed. Check configuration paths.**"), None, None
    elif not pdf_files:
        return mo.md("**No PDFs found. Set PDF_DIR env or update Config.**"), None, None
    else:
        options = [f.name for f in pdf_files]
        selector = mo.ui.select(options=options, value=options[0], label="Select PDF file:")

        file_selection_ui = mo.vstack([
            mo.md("### PDF File Selection"),
            mo.md(f"**Available files:** {len(pdf_files)} PDFs found"),
            selector
        ])

        run_btn = mo.ui.button(label="Run Precision OCR Analysis", kind="success")

        ocr_ui = mo.vstack([
            mo.md("### Precision-Focused OCR"),
            mo.md("**Goal:** Extract 9-digit codes with high precision (exact matches only)"),
            run_btn
        ])

        return mo.vstack([file_selection_ui, ocr_ui]), selector, run_btn


@app.cell
def _(cfg, dbm, extractor, pdf_files, run_btn, selector):
    """Precision-focused OCR processing with detailed results"""
    from pathlib import Path
    import marimo as mo
    
    if selector is None or run_btn is None:
        return mo.md("**UI not initialized properly**")

    if not run_btn.value:
        return mo.md("**Click 'Run Precision OCR Analysis' to process the selected file**")

    pdf_name = selector.value
    pdf_path = next((p for p in pdf_files if p.name == pdf_name), None)

    if pdf_path is None:
        return mo.md("**File not found.**")

    try:
        print(f"Processing: {pdf_name}")
        print("=" * 50)

        # Process PDF with precision-focused approach
        result = extractor.process_pdf(pdf_path)

        # Display precision-focused results
        if result['success']:
            protocols = result['protocols']
            extraction_details = result.get('extraction_details', {})
            qa_probability = extraction_details.get('qa_probability', 0.0)
            qa_action = extraction_details.get('qa_action', 'unknown')
            source = extraction_details.get('source', 'unknown')

            # Determine precision status
            if len(protocols) == 1 and qa_probability >= 0.85:
                precision_status = "HIGH PRECISION"
            elif len(protocols) > 0:
                precision_status = "MEDIUM PRECISION"
            else:
                precision_status = "NO DETECTION"

            result_md = f"""
## {precision_status} Precision OCR Results for `{pdf_name}`

### Processing Summary
- **Status:** {precision_status}
- **Success:** {result['success']}
- **Processing Time:** {result['processing_time']:.2f}s
- **OCR Source:** {source}

### Precision Metrics
- **Protocols Detected:** {len(protocols)}
- **QA Confidence:** {qa_probability:.3f}
- **QA Decision:** {qa_action}
- **Protocols:** `{protocols if protocols else 'None'}`

### Quality Assessment
"""

            if protocols:
                result_md += f"""
- **Single Detection:** {'EXACT' if len(protocols) == 1 else 'NOT EXACT'} (Preferred for precision)
- **High Confidence:** {'HIGH' if qa_probability >= 0.85 else 'LOWER THAN 0.85'} (Target: >0.85)
- **QA Approved:** {'APPROVED' if qa_action == 'accept' else 'NOT APPROVED'} (QA gate decision)
"""
            else:
                result_md += """
- **No Detection:** (Better than wrong detection for precision)
- **QA Decision:** No protocols to evaluate
"""

            result_md += f"""

### Cache Performance
"""

            cache_perf = result.get('cache_performance', {})
            if cache_perf:
                result_md += f"""
- **Cache Hits:** {cache_perf.get('cache_hits', 0)}
- **API Calls:** {cache_perf.get('api_calls', 0)}
- **Hit Rate:** {cache_perf.get('cache_hit_rate', 0):.1f}%
- **Estimated Cost:** ${cache_perf.get('estimated_cost', 0):.3f}
"""
            else:
                result_md += "- **Cache Info:** Not available"

            # Database matching section
            db_match_md = ""
            if result['protocols'] and dbm:
                try:
                    top_protocol = result['protocols'][0]
                    wi_stem = Path(pdf_name).stem
                    match = dbm.lookup_protocol(wi_stem, top_protocol)

                    db_match_md = "\n### Database Matching\n"

                    if match['status'] == 'success':
                        db_match_md += f"""
**Database Match Found**
- **Input Protocol:** `{match['input_protocol']}`
- **Matched Protocol:** `{match['matched_protocol']}`
- **Match Type:** {match['match_type']}
- **Confidence Score:** {match['match_score']:.3f}
"""
                    else:
                        db_match_md += f"""
**No Database Match**
- **Input Protocol:** `{match['input_protocol']}`
- **Status:** {match['status']}
- **Error:** {match.get('error_message', 'No match found')}
"""

                except Exception as e:
                    db_match_md = f"\n### Database Matching\n**Database matching error:** {e}"

            return mo.md(result_md + db_match_md)

        else:
            # Handle failure case
            error_msg = result.get('error_message', 'Unknown error')
            return mo.md(f"""
## OCR Processing Failed

**File:** `{pdf_name}`
**Error:** {error_msg}
**Processing Time:** {result['processing_time']:.2f}s

**Troubleshooting:**
- Check if PDF contains clear 9-digit handwritten codes
- Verify handwriting is legible
- Consider if protocol might be at unusual angle
- Review OCR cache for this file
""")

    except Exception as e:
        print(f"Processing error: {e}")
        return mo.md(f"""
## Processing Error

**File:** `{pdf_name}`
**Error:** {str(e)}

**Check:**
- Backend initialization
- File accessibility
- AWS credentials (if using Textract)
- System resources
""")


if __name__ == "__main__":
    app.run()