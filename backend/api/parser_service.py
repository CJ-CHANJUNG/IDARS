import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from Parser.invoice_parser import CoordinateInvoiceParser

def parse_invoice(pdf_path):
    """
    Parses a single invoice PDF.
    """
    try:
        parser = CoordinateInvoiceParser(Path(pdf_path))
        if parser.extract_text(force_ocr=False):
            data = parser.parse()
            if data == "RETRY":
                parser.extract_text(force_ocr=True)
                data = parser.parse()
            
            if isinstance(data, dict):
                return data
            else:
                return {"error": "Failed to parse"}
        else:
            return {"error": "Failed to extract text"}
    except Exception as e:
        return {"error": str(e)}
