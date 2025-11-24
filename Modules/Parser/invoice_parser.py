import fitz  # PyMuPDF
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import pytesseract
from PIL import Image
import io

# ═══════════════════════════════════════════════════════════════════════
# 🔧 사용자 설정
# ═══════════════════════════════════════════════════════════════════════

INPUT_FOLDER = r"D:\CJ\Project Manager\IDARS\로컬 모델 학습\Parser\CI_Input"
OUTPUT_BASE_FOLDER = r"D:\CJ\Project Manager\IDARS\로컬 모델 학습\Parser\CI_Output"
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
OCR_THRESHOLD = 100

try:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except:
    print("⚠️ Tesseract 경로 설정 오류")

# ═══════════════════════════════════════════════════════════════════════
# 🔍 파싱 패턴 (Regex)
# ═══════════════════════════════════════════════════════════════════════

class InvoicePatterns:
    # 1. Shipper
    SHIPPER_START = r"(?:Shipper|Exporter|Issued\s*by|Seller)"
    SHIPPER_END = r"(?:To\s*Applicant|Consignee|To\.|Buyer|No\.|Date|Notify|Port)"

    # 2. Applicant
    APPLICANT_START = r"(?:To\s*Applicant|Consignee|To\.|Buyer|Messrs)"
    APPLICANT_END = r"(?:Notify|Port|Vessel|Sailing|Ref|No\.|From|Remarks)"

    # 3. Invoice No
    INVOICE_NO = [
        r"(?:Invoice|Inv)\.?\s*No\.?[\s:]*([A-Z0-9\-]+)",
        r"No\.?\s*&\s*Date\s+of\s+Invoice[\s\n:]*([A-Z0-9\-]+)",
        r"Reference\s*No\.?[\s:]*([A-Z0-9\-]+)"
    ]

    # 4. Invoice Date
    INVOICE_DATE = [
        r"(?:Invoice|Inv)\.?\s*Date[:\s]*([A-Z]{3}\.?\s+\d{1,2},?\s+\d{4})",  # Added .? after month
        r"(?:Invoice|Inv)\.?\s*Date[:\s]*(\d{4}[-\./]\d{2}[-\./]\d{2})",
        r"\b([A-Z]{3}\.?\s+\d{1,2},?\s+\d{4})\b",  # Added word boundaries to avoid partial matches
        r"\b(\d{4}[-\./]\d{2}[-\./]\d{2})\b"
    ]

    # 5. On Board Date
    ON_BOARD_DATE = [
        r"(?:Sailing\s+on/?about|On\s+Board|ETD|Departure)[:\s]*\n?([A-Z0-9\s,\.]+?)(?=\n|Vessel|Port|Remar|Desc)",
        r"on/about\s+([A-Z]{3}\.?\s+\d{1,2},?\s+\d{4})",  # Added specific pattern for "on/about"
    ]

    # 6. Items
    ITEMS_KEYWORDS = [
        r"(?:PRIME\s+)?(?:HOT|COLD)\s*ROLLED\s*(?:STEEL|STAINLESS)?\s*(?:PLATE|SHEET|COIL|STRIP|PO|HGI|CR|EG)[^\n]*",
        r"WIRE\s*ROD", r"STAINLESS\s*STEEL", r"COIN\s*BLANK",
        r"GALVANIZED\s*STEEL"
    ]

    # 7. Incoterms - ADDED DAT!
    # \n이나 표 헤더(ITEM, SPEC) 만나면 중단
    # Removed \b at start to allow matches like "= DAT"
    INCOTERMS = r"(?:^|[\s=])(CIF|CIP|FOB|CFR|C\u0026F|DAP|DAT|DDP|EXW|FCA|CPT)\s+([A-Z\s,\.\-]+?)(?=\n|PRIME|HOT|COLD|ITEM|SPEC|SIZE|TOTAL|AMOUNT|GENERAL|PASIR|DESCRIPTION|=)"

    # 8. Total Quantity
    TOTAL_QUANTITY = r"(?:G\.TOTAL|GRAND\s+TOTAL|TOTAL)\s*(?:QUANTITY|Q'TY|NET\s*WEIGHT)?[:\.]?\s*([\d,]+\.?\d*)\s*(MT|KGS?|PCS|MTS)"
    GRAND_TOTAL_QUANTITY = r"(?:G\.TOTAL|GRAND\s+TOTAL|TOTAL).*?([\d,]+\.?\d*)\s*(MT|KGS?|PCS|MTS)"
    
    # NEW: Improved fallback for single-item invoices
    SINGLE_ITEM_QUANTITY = r"\b([\d,]+\.?\d+)\s*(MT|KGS?|PCS|MTS)\s+[A-Z]{3}\s*[\d,]+\.?\d+"  # quantity unit currency amount
    SINGLE_ITEM_QUANTITY_LOOSE = r"\b([\d,]+\.?\d+)\s*(MT|KGS?|PCS|MTS)\b"  # Just quantity and unit

    # 9. Total Amount
    TOTAL_AMOUNT = [
        r"(?:G\.TOTAL|GRAND\s+TOTAL|TOTAL).*?\b([A-Z]{3})\s*([\d,]+\.?\d*)",
        r"(?:G\.TOTAL|GRAND\s+TOTAL|TOTAL).*?([\d,]+\.?\d*)\s*([A-Z]{3})",
    ]
    GRAND_TOTAL_AMOUNT = [
        r"(?:G\.TOTAL|GRAND\s+TOTAL|TOTAL).*?([A-Z]{3})\s*([\d,]+\.?\d*)",
        r"(?:G\.TOTAL|GRAND\s+TOTAL|TOTAL).*?([\d,]+\.?\d*)\s*([A-Z]{3})",
    ]
    
    # NEW: Improved fallback for single-item amounts
    # Matches: Quantity Unit [Optional UnitPrice] Currency Amount
    # e.g. "336 PCS EUR 25.102 EUR 8,434.27" -> extracts 8,434.27
    # e.g. "12.00MT USD2,778.00/MT USD33,336.00" -> extracts 33,336.00
    SINGLE_ITEM_AMOUNT_CONTEXT = r"\b[\d,]+\.?\d+\s*(?:MT|KGS?|PCS|MTS)\s+(?:[A-Z]{3}\s*[\d,]+\.?\d+(?:/[A-Za-z]+)?\s+)?([A-Z]{3})\s*([\d,]+\.?\d+)"
    
    SINGLE_ITEM_AMOUNT = r"\b([A-Z]{3})\s*([\d,]+\.?\d+)"  # currency amount with word boundary

    # 10. Remark
    REMARK = r"(?:Remarks?|Note)[\s:]*([\s\S]+?)(?=\n(?:Marks|Quantity|Signed|Payment|Description)|$)"

# ═══════════════════════════════════════════════════════════════════════
# 🛠️ 파서 클래스 (Layout-Aware)
# ═══════════════════════════════════════════════════════════════════════

class CoordinateInvoiceParser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = None
        self.full_text = ""
        self.ocr_data = [] 
        self.is_ocr_mode = False
        
        self.data = {
            "CI_01_Shipper": None, "CI_02_Applicant": None, "CI_03_Invoice_No": None,
            "CI_04_Invoice_Date": None, "CI_05_On_Board_Date": None, "CI_06_Items": None,
            "CI_07_Incoterms": None, "CI_08_Total_Quantity": None, "CI_09_Total_Amount": None,
            "CI_10_Remark": None,
            "CI_11_Grand_Total_Quantity": None, "CI_12_Grand_Total_Amount": None
        }

    def _perform_ocr_with_data(self, page, page_num):
        """OCR 수행 및 좌표 데이터 추출 (Line 단위 재구성)"""
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # HOCR 데이터 추출
            data = pytesseract.image_to_data(image, lang='eng+kor', output_type=pytesseract.Output.DICT)
            
            scale_factor = 1/3
            n_boxes = len(data['text'])
            
            # 1. 단어 단위 수집
            words = []
            for i in range(n_boxes):
                if int(data['conf'][i]) > 0:
                    text = data['text'][i].strip()
                    if text:
                        words.append({
                            'text': text,
                            'page': page_num + 1,
                            'x': data['left'][i] * scale_factor,
                            'y': data['top'][i] * scale_factor,
                            'w': data['width'][i] * scale_factor,
                            'h': data['height'][i] * scale_factor
                        })
            
            # 2. 라인(Line) 단위로 재구성 (Y좌표가 비슷하면 같은 줄)
            lines = []
            current_line = []
            last_y = -100
            
            # Y좌표 정렬
            words.sort(key=lambda w: w['y'])
            
            for w in words:
                if abs(w['y'] - last_y) > 10: # 줄바꿈 기준 (10px)
                    if current_line:
                        # X좌표 정렬 후 합치기
                        current_line.sort(key=lambda w: w['x'])
                        line_text = " ".join([cw['text'] for cw in current_line])
                        # 라인의 BBox 계산
                        min_x = min(cw['x'] for cw in current_line)
                        min_y = min(cw['y'] for cw in current_line)
                        max_x = max(cw['x'] + cw['w'] for cw in current_line)
                        max_y = max(cw['y'] + cw['h'] for cw in current_line)
                        
                        lines.append({
                            'text': line_text,
                            'page': page_num + 1,
                            'bbox': [min_x, min_y, max_x, max_y]
                        })
                        current_line = []
                    last_y = w['y']
                current_line.append(w)
                
            # 마지막 라인 처리
            if current_line:
                current_line.sort(key=lambda w: w['x'])
                line_text = " ".join([cw['text'] for cw in current_line])
                min_x = min(cw['x'] for cw in current_line)
                min_y = min(cw['y'] for cw in current_line)
                max_x = max(cw['x'] + cw['w'] for cw in current_line)
                max_y = max(cw['y'] + cw['h'] for cw in current_line)
                lines.append({
                    'text': line_text,
                    'page': page_num + 1,
                    'bbox': [min_x, min_y, max_x, max_y]
                })
            
            self.ocr_data.extend(lines)
            return "\n".join([l['text'] for l in lines])
            
        except Exception as e:
            print(f"   [OCR Error] {e}")
            return ""

    def extract_text(self, force_ocr=False):
        try:
            if self.doc: self.doc.close()
            self.doc = fitz.open(self.pdf_path)
            text_pages = []
            self.ocr_data = [] 
            self.is_ocr_mode = force_ocr
            
            for i in range(min(2, len(self.doc))):
                page = self.doc[i]
                text = page.get_text()
                
                if force_ocr or len(text.strip()) < OCR_THRESHOLD:
                    if not self.is_ocr_mode: print(f"   ⚠️ P.{i+1} Auto-OCR triggered...")
                    self.is_ocr_mode = True
                    text = self._perform_ocr_with_data(page, i)
                
                text_pages.append(text)
            
            self.full_text = "\n".join(text_pages)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def _find_coordinates(self, text_to_find: str) -> dict:
        if not text_to_find: return None
        search_term = text_to_find.strip()
        if len(search_term) < 2: return None
        
        # OCR 데이터(라인 단위)에서 검색
        target_words = search_term.split()
        if not target_words: return None
        first_word = target_words[0] # 첫 단어 기준 검색 (근사치)
        
        for item in self.ocr_data:
            if first_word in item['text']:
                return {"page": item['page'], "bbox": item['bbox']}
        
        # OCR 모드가 아니면 PDF 내부 검색
        if not self.is_ocr_mode:
            for i in range(min(2, len(self.doc))):
                page = self.doc[i]
                quads = page.search_for(search_term[:30]) # 앞부분만 검색
                if quads:
                    rect = quads[0]
                    return {"page": i + 1, "bbox": [rect.x0, rect.y0, rect.x1, rect.y1]}
                    
        return None

    def _format_result(self, value: str) -> dict:
        if not value: return None
        clean_val = re.sub(r'\s+', ' ', value).strip(" :.,")
        loc = self._find_coordinates(clean_val)
        return {"value": clean_val, "location": loc}

    def _extract_block(self, start_pattern, end_pattern):
        # [개선] 좌우 분할 로직 (Shipper는 보통 왼쪽 상단)
        # 정규식으로 찾되, 너무 긴 텍스트는 좌표를 확인하여 왼쪽/오른쪽 구분 가능하면 좋음
        # 일단은 정규식 강화로 처리
        pattern = f"({start_pattern})(.*?)({end_pattern})"
        match = re.search(pattern, self.full_text, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(2).strip()
            if len(content) > 500: return None
            return self._format_result(content)
        return None

    def parse(self):
        text = self.full_text
        
        # 1. Shipper & Applicant
        self.data["CI_01_Shipper"] = self._extract_block(InvoicePatterns.SHIPPER_START, InvoicePatterns.SHIPPER_END)
        self.data["CI_02_Applicant"] = self._extract_block(InvoicePatterns.APPLICANT_START, InvoicePatterns.APPLICANT_END)

        # 3. Invoice No
        for pattern in InvoicePatterns.INVOICE_NO:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if any(c.isdigit() for c in val):
                    self.data["CI_03_Invoice_No"] = self._format_result(val)
                    break

        # 4. Invoice Date
        for pattern in InvoicePatterns.INVOICE_DATE:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                # Check for "Due" in surrounding context (before and in the matched text)
                context_before = text[max(0, match.start()-30):match.start()]
                context_after = text[match.end():min(len(text), match.end()+20)]
                
                # Skip if "Due" or "Maturity" appears nearby
                if "Due" not in context_before and "Due" not in val and "Maturity" not in context_before:
                    self.data["CI_04_Invoice_Date"] = self._format_result(val)
                    break
        
        # 5. On Board Date
        for pattern in InvoicePatterns.ON_BOARD_DATE:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                self.data["CI_05_On_Board_Date"] = self._format_result(match.group(1))
                break

        # 6. Items
        found_items = []
        for pattern in InvoicePatterns.ITEMS_KEYWORDS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_items.extend(matches)
        if found_items:
            longest_item = max(found_items, key=len)
            self.data["CI_06_Items"] = self._format_result(longest_item[:150])

        # 7. Incoterms
        match = re.search(InvoicePatterns.INCOTERMS, text, re.IGNORECASE)
        if match:
            val = f"{match.group(1)} {match.group(2).strip()}"
            self.data["CI_07_Incoterms"] = self._format_result(val)

        # 8. Total Quantity
        match = re.search(InvoicePatterns.TOTAL_QUANTITY, text, re.IGNORECASE)
        if match:
            val = f"{match.group(1)} {match.group(2)}"
            self.data["CI_08_Total_Quantity"] = self._format_result(val)
        else:
            # Fallback: try single-item pattern
            match = re.search(InvoicePatterns.SINGLE_ITEM_QUANTITY, text, re.IGNORECASE)
            if match:
                val = f"{match.group(1)} {match.group(2)}"
                self.data["CI_08_Total_Quantity"] = self._format_result(val)
            else:
                # Fallback 2: try loose single-item pattern
                match = re.search(InvoicePatterns.SINGLE_ITEM_QUANTITY_LOOSE, text, re.IGNORECASE)
                if match:
                    val = f"{match.group(1)} {match.group(2)}"
                    self.data["CI_08_Total_Quantity"] = self._format_result(val)

        # 9. Total Amount
        for pattern in InvoicePatterns.TOTAL_AMOUNT:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                g1, g2 = match.groups()
                if g1 and re.match(r'[A-Z]{3}', g1): val = f"{g1} {g2}"
                else: val = f"{g2} {g1}" if g1 else g2
                self.data["CI_09_Total_Amount"] = self._format_result(val)
                break
        
        # Fallback: try single-item pattern if no TOTAL found
        if not self.data["CI_09_Total_Amount"]:
            # Try context-aware pattern first (Quantity ... Amount)
            match = re.search(InvoicePatterns.SINGLE_ITEM_AMOUNT_CONTEXT, text, re.IGNORECASE)
            if match:
                val = f"{match.group(1)} {match.group(2)}"
                self.data["CI_09_Total_Amount"] = self._format_result(val)
            else:
                # Look for pattern: "EUR 8,434.27" in the AMOUNT column area
                amount_matches = re.findall(InvoicePatterns.SINGLE_ITEM_AMOUNT, text, re.IGNORECASE)
                # Filter for likely amounts (has comma or decimal, reasonable size)
                for match in amount_matches:
                    curr, amt = match
                    if ',' in amt or '.' in amt:  # likely an amount
                        val = f"{curr} {amt}"
                        self.data["CI_09_Total_Amount"] = self._format_result(val)
                        break

        # [NEW] 11. Grand Total Quantity
        match = re.search(InvoicePatterns.GRAND_TOTAL_QUANTITY, text, re.IGNORECASE)
        if match:
            val = f"{match.group(1)} {match.group(2)}"
            self.data["CI_11_Grand_Total_Quantity"] = self._format_result(val)

        # [NEW] 12. Grand Total Amount
        for pattern in InvoicePatterns.GRAND_TOTAL_AMOUNT:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                g1, g2 = match.groups()
                if g1 and re.match(r'[A-Z]{3}', g1): val = f"{g1} {g2}"
                else: val = f"{g2} {g1}" if g1 else g2
                self.data["CI_12_Grand_Total_Amount"] = self._format_result(val)
                break

        # 10. Remark
        match = re.search(InvoicePatterns.REMARK, text, re.IGNORECASE | re.DOTALL)
        if match:
            content = match.group(1).strip()[:300]
            self.data["CI_10_Remark"] = self._format_result(content)
            
        if not self.data["CI_03_Invoice_No"] and not self.is_ocr_mode:
            return "RETRY"

        return self.data

# ═══════════════════════════════════════════════════════════════════════
# 🚀 실행부
# ═══════════════════════════════════════════════════════════════════════

def main():
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    output_dir = Path(OUTPUT_BASE_FOLDER) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Invoice Parser v5 (Layout-Aware)")
    
    input_path = Path(INPUT_FOLDER)
    pdf_files = list(input_path.glob("*.pdf"))
    results = []

    for pdf in pdf_files:
        print(f"📄 Parsing {pdf.name}...", end=" ")
        try:
            parser = CoordinateInvoiceParser(pdf)
            if parser.extract_text(force_ocr=False):
                data = parser.parse()
                
                if data == "RETRY":
                    print(" 🔄 Retry with OCR...", end=" ")
                    parser.extract_text(force_ocr=True)
                    data = parser.parse()
                
                if isinstance(data, dict):
                    data["_file_name"] = pdf.name
                    results.append(data)
                    print("✅ Done")
                else:
                    print("❌ Failed")
            else:
                print("❌ Failed to extract")
        except Exception as e:
            print(f"❌ Error: {e}")

    output_file = output_dir / "invoice_extraction_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"\n🎉 Complete! Results saved to: {output_file}")

if __name__ == "__main__":
    main()