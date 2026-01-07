
import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
PROJECT_ROOT = r"d:\CJ\Project Manager\IDARS\IDARS PJT"
sys.path.insert(0, PROJECT_ROOT)

from Modules.Parser.dterm_extraction_engine import DtermExtractionEngine

async def analyze_samples():
    try:
        engine = DtermExtractionEngine()
        
        sample_dir = r"d:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\D조건_251001~251231_20260105_110824\step2_evidence_collection\dterm_downloads"
        
        files = [f for f in os.listdir(sample_dir) if f.lower().endswith(('.pdf', '.png'))]
        print(f"Found {len(files)} sample files.")
        
        for filename in files:
            file_path = os.path.join(sample_dir, filename)
            print(f"\n\n{'='*50}")
            print(f"Analyzing: {filename}")
            print(f"{'='*50}")
            
            # 1. OCR Raw Text Snippet
            raw_text = ""
            try:
                # Use engine's OCR method if possible, or simple fallback
                if filename.endswith('.png'):
                    full_text = engine.high_quality_ocr(file_path, 0)
                    raw_text = full_text
                else:
                    import fitz
                    doc = fitz.open(file_path)
                    for i in range(min(len(doc), 2)):
                        raw_text += doc[i].get_text()
                    doc.close()
            except Exception as e:
                raw_text = f"OCR Error: {e}"

            print(f"[Raw Text Snippet]:\n{raw_text[:800]}") # Show more chars
            
            # 2. Gemini Extraction
            print("\n[Running Gemini Extraction...]")
            result = await engine.process_single_pdf_async(file_path, "TEST_SLIP_ID")
            print(f"Result: {result}")
            
    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    # Redirect stdout to file
    with open("analysis_result.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        asyncio.run(analyze_samples())
