import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import json
import re
from datetime import datetime
import pytesseract
from PIL import Image
import io

# ═══════════════════════════════════════════════════════════════════════
# 🔧 사용자 설정 (경로 설정)
# ═══════════════════════════════════════════════════════════════════════

# 1. [기본] 원본 PDF 입력 및 전체 결과 출력 경로
INPUT_FOLDER = r"D:\CJ\Project Manager\IDARS\로컬 모델 학습\Splitter\Input"
OUTPUT_FOLDER = r"D:\CJ\Project Manager\IDARS\로컬 모델 학습\Splitter\Output"

# 2. [Parser 학습용] 분류된 파일이 자동으로 들어갈 경로
PARSER_CI_INPUT = r"D:\CJ\Project Manager\IDARS\로컬 모델 학습\Parser\CI_Input"
PARSER_BL_INPUT = r"D:\CJ\Project Manager\IDARS\로컬 모델 학습\Parser\BL_Input"

# 3. [필수] Tesseract OCR 경로
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 4. 기타 설정
MERGE_CONSECUTIVE_SAME_TYPE = True 
OCR_THRESHOLD = 100  # 1차 필터 (이보다 적으면 바로 OCR)

# ═══════════════════════════════════════════════════════════════════════
# 🔍 패턴 정의
# ═══════════════════════════════════════════════════════════════════════

DOCUMENT_PATTERNS = {
    'Bill_of_Lading': [
        (r'BILL\s*OF\s*LADING', 100), (r'WAYBILL', 100), (r'MULTIMODAL\s*TRANSPORT', 100),
        (r'SURRENDER', 95), (r'TELEX\s*RELEASE', 95),
        (r'PORT\s*OF\s*LOADING', 60), (r'PORT\s*OF\s*DISCHARGE', 60), (r'CLEAN\s*ON\s*BOARD', 70),
        (r'FREIGHT\s*PREPAID', 60),
    ],
    'Commercial_Invoice': [
        (r'COMMERCIAL\s*INVOICE', 100), (r'TAX\s*INVOICE', 100), (r'PROFORMA\s*INVOICE', 100),
    ],
    'Packing_List': [
        (r'PACKING\s*LIST', 100), (r'DETAIL\s*OF\s*PACKING', 90),
    ],
    'Weight_List': [
        (r'WEIGHT\s*LIST', 100), (r'WEIGHT\s*CERTIFICATE', 100), (r'MEASURE\s*LIST', 90),
    ],
    'Mill_Certificate': [
        (r'MILL\s*TEST\s*CERTIFICATE', 100), (r'CHEMICAL\s*COMPOSITION', 80),
        (r'TEST\s*REPORT', 80), (r'INSPECTION\s*CERTIFICATE', 90), (r'검사\s*성적서', 100),
    ],
    'Cargo_Insurance': [
        (r'INSURANCE\s*POLICY', 100), (r'CERTIFICATE\s*OF\s*INSURANCE', 100), (r'MARINE\s*CARGO', 90),
    ],
    'Certificate_Origin': [
        (r'CERTIFICATE\s*OF\s*ORIGIN', 100), (r'COUNTRY\s*OF\s*ORIGIN', 80), (r'원산지\s*증명서', 100),
    ],
    'Customs_clearance_Letter': [
        # ★ 우선순위 최고 (한글 수출신고필증 - 띄어쓰기 선택적)
        (r'수출\s?신고\s?필증', 105),  # 띄어쓰기 있거나 없거나
        (r'수입\s?신고\s?필증', 105),
        (r'수출신고필증', 105),  # 띄어쓰기 없는 경우 명시적 추가
        (r'수입신고필증', 105),
        
        # 영문 패턴
        (r'EXPORT\s*DECLARATION', 100),
        (r'IMPORT\s*DECLARATION', 100), 
        (r'CUSTOMS\s*CLEARANCE', 100),
        
        # 추가 한글 키워드
        (r'관세청', 90),
        (r'통관고유부호', 90),
        (r'수출통관', 90),
        (r'수출\s?신고', 88),  # 더 유연하게
        (r'수입\s?신고', 88),
        (r'EP-\d+', 95),  # Export declaration number pattern
        (r'신고번호', 85),
        (r'통관', 75),  # 낮춤 (너무 일반적)
    ],
    'Delivery_Note': [
        (r'DELIVERY\s*NOTE', 100), (r'DELIVERY\s*ORDER', 100), (r'납품서', 100), (r'인수증', 100),
    ]
}

DOCUMENT_ID_PATTERNS = {
    'Commercial_Invoice': [r'BHS\d{10}', r'BHR\d{10}', r'HI[A-Z]\d{10}', r'Invoice\s*No\.?\s*[:\s]*([A-Z0-9-]+)'],
    'Bill_of_Lading': [r'B/L\s*No\.?\s*[:\s]*([A-Z0-9]+)', r'WYGSK[A-Z0-9]+', r'KYSC[A-Z0-9]+', r'SSSL[A-Z0-9]+', r'BJTL[A-Z0-9]+'],
    'Packing_List': [r'BHS\d{10}', r'BHR\d{10}'],
    'Customs_clearance_Letter': [r'신고번호\s*[:\s]*([0-9-]+)']
}

CONTINUATION_MARKERS = ['to be continued', 'continuation page', 'page:', 'total', 'last item', 'sub total']

try:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except:
    print("⚠️ Tesseract 설정 오류")

# ═══════════════════════════════════════════════════════════════════════
# 메인 클래스
# ═══════════════════════════════════════════════════════════════════════

class PDFSplitter:
    def __init__(self, input_path: str, output_dir: str):
        self.pdf_path = Path(input_path)
        self.output_dir = Path(output_dir)
        self.doc = None
        try:
            self.slip_no = self.pdf_path.name.split('_')[0]
        except:
            self.slip_no = "UnknownSlip"

    def __enter__(self):
        self.doc = fitz.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()

    def _perform_ocr(self, page, high_res=False) -> str:
        """강제 OCR 수행 함수 - 한글 인식 최적화 (적응형 해상도)"""
        try:
            # ★ 적응형 해상도 (기본 3x3, 필요시 4x4)
            matrix = fitz.Matrix(3, 3) if not high_res else fitz.Matrix(4, 4)
            pix = page.get_pixmap(matrix=matrix)
            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))
            
            # 한글 우선 인식 (kor+eng 순서로 변경)
            ocr_text = pytesseract.image_to_string(image, lang='kor+eng')
            
            # ★ 결과가 너무 적으면 고해상도로 재시도
            if len(ocr_text.strip()) < 20 and not high_res:
                print(f"    🔁 Low OCR result, retrying with high resolution...")
                return self._perform_ocr(page, high_res=True)
            
            # 디버그: OCR 결과 일부 출력
            preview = ocr_text.strip()[:100] if ocr_text else "(empty)"
            res_label = "High-Res" if high_res else "Normal"
            print(f"    [OCR {res_label}] {preview}")
            
            return ocr_text
        except Exception as e:
            print(f"    [OCR Error] {str(e)}")
            return ""

    def _get_text_hybrid(self, page, page_num) -> str:
        """1차 텍스트 추출 (글자수 적으면 OCR)"""
        text = page.get_text()
        if len(text.strip()) < OCR_THRESHOLD:
            print(f"  [OCR] P.{page_num+1} Scanning (Low Text)...")
            return self._perform_ocr(page)
        return text

    def _classify_page(self, text: str) -> Tuple[Optional[str], float, str]:
        text_upper = text.upper()
        best_type = None
        best_conf = 0.0
        best_method = 'unknown'
        scores = {}  # 모든 점수 추적

        for doc_type, patterns in DOCUMENT_PATTERNS.items():
            max_score = 0
            for pattern, score in patterns:
                if re.search(pattern, text_upper):
                    if score > max_score:
                        max_score = score
            scores[doc_type] = max_score
            
            if max_score > best_conf:
                best_conf = max_score
                best_type = doc_type
                best_method = 'header_match' if max_score >= 90 else 'content_keyword'
        
        # ★ 신뢰도 임계값 상향 (50 → 80)
        if best_conf < 80:
            return None, 0.0, 'low_confidence'
        
        # ★ 점수 차이 확인 (애매한 경우 감지)
        sorted_scores = sorted(scores.values(), reverse=True)
        second_best = sorted_scores[1] if len(sorted_scores) > 1 else 0
        
        if best_conf - second_best < 15:  # 점수 차이 15점 미만
            print(f"    ⚠️ Uncertain classification: {best_type}({best_conf}) vs 2nd({second_best})")
            return None, 0.0, 'uncertain'
        
        return best_type, best_conf, best_method

    def _extract_id(self, text: str, doc_type: str) -> Optional[str]:
        if not doc_type or doc_type not in DOCUMENT_ID_PATTERNS: return None
        for pattern in DOCUMENT_ID_PATTERNS[doc_type]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val = match.group(1) if match.groups() else match.group(0)
                return re.sub(r'[^A-Z0-9-]', '', val)
        return None


    def group_pages(self) -> List[Dict]:
        analyses = []
        for i in range(len(self.doc)):
            page = self.doc[i]
            
            # 1. 먼저 일반 텍스트만 추출 (OCR 없이, 빠름)
            text = page.get_text()
            doc_type, conf, method = self._classify_page(text)
            
            # 🚨 [RESCUE LOGIC] 분류 실패 시 OCR 시도 (느리지만 정확) 🚨
            if doc_type is None:
                print(f"  [RESCUE] P.{i+1} Text-based classification failed. Trying OCR...")
                text = self._perform_ocr(page)  # 이제 OCR 실행
                doc_type, conf, method = self._classify_page(text)  # OCR 텍스트로 재분류
                if doc_type:
                    print(f"    ✅ Rescued! Detected: {doc_type}")
                else:
                    # 🔥 [FILENAME FALLBACK] OCR도 실패 시 파일명 기반 분류
                    filename = str(self.pdf_path.name).upper()
                    if 'EP-' in filename or 'EXPORT' in filename or 'DECLARATION' in filename:
                        doc_type = 'Customs_clearance_Letter'
                        conf = 80
                        method = 'filename_fallback'
                        print(f"    🔥 Rescued by filename! Detected: {doc_type}")
                    else:
                        print(f"    ❌ OCR also failed. Marking as Etc.")

            doc_id = self._extract_id(text, doc_type)
            analyses.append({'page': i, 'type': doc_type, 'id': doc_id, 'conf': conf, 'method': method, 'text': text})
            
            # DEBUG: Print classification result for each page
            print(f"  📄 Page {i+1}: Type={doc_type}, ID={doc_id}, Conf={conf}, Method={method}")

        # DEBUG: Print all analyses
        print(f"\n  [DEBUG] Total pages analyzed: {len(analyses)}")
        for idx, item in enumerate(analyses):
            print(f"    P.{idx+1}: {item['type']} | ID: {item['id']}")

        groups = []
        current = None

        for item in analyses:
            start_new = False
            if current is None:
                start_new = True
            else:
                if item['type'] is not None and item['type'] != current['type']:
                    start_new = True
                elif item['type'] is not None and item['type'] == current['type']:
                    if item['id'] and current['id'] and item['id'] != current['id']:
                        start_new = True
                    else:
                        if item['type'] in ['Weight_List', 'Packing_List', 'Mill_Certificate']:
                            start_new = False
                        else:
                            start_new = False
                elif item['type'] is None:
                    if current['type'] in ['Bill_of_Lading', 'Mill_Certificate', 'Weight_List']:
                        start_new = False
                    else:
                        start_new = False

            if start_new:
                if current: groups.append(current)
                current = {
                    'type': item['type'] or 'Etc', 'pages': [item['page']], 'id': item['id'],
                    'log': {'doc_type': item['type'], 'confidence': item['conf'], 'method': item['method']}
                }
            else:
                current['pages'].append(item['page'])
                if not current['id'] and item['id']: current['id'] = item['id']
                if current['type'] == 'Etc' and item['type']:
                    current['type'] = item['type']
                    current['log'] = {'doc_type': item['type'], 'confidence': item['conf'], 'method': item['method']}

        if current: groups.append(current)
        
        # DEBUG: Print grouping results
        print(f"\n  [DEBUG] Created {len(groups)} groups:")
        for idx, grp in enumerate(groups):
            page_range = f"P.{grp['pages'][0]+1}-{grp['pages'][-1]+1}" if len(grp['pages']) > 1 else f"P.{grp['pages'][0]+1}"
            print(f"    Group {idx+1}: {grp['type']} | {page_range} | ID: {grp['id']}")
        
        return groups

    def process(self) -> List[Dict]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        groups = self.group_pages()
        saved_files = []
        
        # Parser 폴더 생성
        Path(PARSER_CI_INPUT).mkdir(parents=True, exist_ok=True)
        Path(PARSER_BL_INPUT).mkdir(parents=True, exist_ok=True)
        
        for grp in groups:
            doc_type = grp['type']
            pages = grp['pages']
            start, end = pages[0]+1, pages[-1]+1
            
            out_pdf = fitz.open()
            out_pdf.insert_pdf(self.doc, from_page=pages[0], to_page=pages[-1])
            
            page_str = f"{start}p" if start == end else f"{start}-{end}p"
            id_str = f"_{grp['id']}" if grp['id'] else ""
            filename = f"{self.slip_no}_{doc_type}{id_str}_{page_str}.pdf"
            if len(filename) > 100: filename = f"{self.slip_no}_{doc_type}_{page_str}.pdf"
            
            # 1. Output 저장
            save_path = self.output_dir / filename
            out_pdf.save(str(save_path))
            
            # 2. Parser 폴더 복사
            if doc_type == 'Commercial_Invoice':
                out_pdf.save(str(Path(PARSER_CI_INPUT) / filename))
            elif doc_type == 'Bill_of_Lading':
                out_pdf.save(str(Path(PARSER_BL_INPUT) / filename))
            
            out_pdf.close()
            
            saved_files.append({
                "file_name": filename, "slip_no": self.slip_no, "document_type": doc_type,
                "page_range": [start, end], "document_id": grp['id'], "classification_log": grp['log']
            })
            print(f" ✅ Saved: {filename}")
            
        return saved_files

def main():
    input_path = Path(INPUT_FOLDER)
    timestamp = datetime.now().strftime("%Y%m%d%H%M")
    output_path = Path(OUTPUT_FOLDER) / timestamp
    
    if not input_path.exists(): return
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 Input: {input_path}")
    print(f"📂 Output: {output_path}\n")
    
    all_results = []
    for pdf in list(input_path.glob("*.pdf")):
        print(f"\n📄 Processing {pdf.name}...")
        try:
            with PDFSplitter(str(pdf), str(output_path)) as splitter:
                all_results.extend(splitter.process())
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

    with open(output_path / "processing_result.json", 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()