# -*- coding: utf-8 -*-
"""
Tesseract 좌표 추출 테스트
스캔 PDF에서 OCR + 좌표를 추출하여 page.search_for()와 비교
"""

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# Tesseract 경로
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def test_pdf_type(pdf_path):
    """PDF가 텍스트 기반인지 스캔 기반인지 확인"""
    doc = fitz.open(pdf_path)
    page = doc[0]
    text = page.get_text()
    doc.close()

    if len(text.strip()) < 100:
        return "SCAN", len(text.strip())
    else:
        return "TEXT", len(text.strip())

def test_pymupdf_search(pdf_path, search_terms):
    """PyMuPDF page.search_for() 테스트"""
    print(f"\n[PyMuPDF search_for() 테스트]")
    doc = fitz.open(pdf_path)
    page = doc[0]

    results = {}
    for term in search_terms:
        rects = page.search_for(str(term))
        if rects:
            rect = rects[0]
            width = page.rect.width
            height = page.rect.height
            coords = [
                int((rect.y0 / height) * 1000),
                int((rect.x0 / width) * 1000),
                int((rect.y1 / height) * 1000),
                int((rect.x1 / width) * 1000)
            ]
            results[term] = coords
            print(f"   OK '{term}' -> {coords}")
        else:
            results[term] = [0, 0, 0, 0]
            print(f"   FAIL '{term}' -> NOT FOUND")

    doc.close()
    return results

def test_tesseract_coordinates(pdf_path, search_terms):
    """Tesseract image_to_data() 좌표 추출 테스트"""
    print(f"\n[Tesseract image_to_data() 테스트]")

    doc = fitz.open(pdf_path)
    page = doc[0]

    # 고해상도 이미지 생성
    pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # OCR + 좌표 추출
    ocr_data = pytesseract.image_to_data(img, lang='eng+kor', output_type=pytesseract.Output.DICT)

    # 데이터 정제
    n = len(ocr_data['text'])
    ocr_items = []
    for i in range(n):
        if ocr_data['conf'][i] != -1 and ocr_data['text'][i].strip():
            ocr_items.append({
                'text': ocr_data['text'][i].strip(),
                'left': ocr_data['left'][i],
                'top': ocr_data['top'][i],
                'width': ocr_data['width'][i],
                'height': ocr_data['height'][i],
                'conf': ocr_data['conf'][i]
            })

    print(f"   [총 {len(ocr_items)}개 텍스트 블록 검출]")

    # OCR 결과 샘플 출력 (처음 30개)
    print(f"\n   [OCR 결과 샘플 - 처음 30개]")
    for i, item in enumerate(ocr_items[:30]):
        print(f"   {i+1}. '{item['text']}' (conf: {item['conf']})")

    if len(ocr_items) > 30:
        print(f"   ... (이하 {len(ocr_items)-30}개 생략)\n")

    # 검색어 매칭
    results = {}
    width = page.rect.width
    height = page.rect.height
    img_width = pix.width
    img_height = pix.height

    for term in search_terms:
        term_str = str(term).replace(',', '').strip()  # 숫자 정규화
        found = False

        for item in ocr_items:
            ocr_text = item['text'].replace(',', '').strip()

            # 완전 일치 또는 포함 관계
            if term_str in ocr_text or ocr_text in term_str:
                # 이미지 좌표 → PDF 좌표 변환
                x = item['left']
                y = item['top']
                w = item['width']
                h = item['height']

                # 정규화 (0~1000)
                coords = [
                    int((y / img_height) * 1000),
                    int((x / img_width) * 1000),
                    int(((y + h) / img_height) * 1000),
                    int(((x + w) / img_width) * 1000)
                ]

                results[term] = coords
                print(f"   OK '{term}' (match: '{item['text']}', conf: {item['conf']}) -> {coords}")
                found = True
                break

        if not found:
            results[term] = [0, 0, 0, 0]
            print(f"   FAIL '{term}' -> NOT FOUND")

    doc.close()
    return results

def main():
    # 테스트 대상 PDF
    test_cases = [
        {
            "slip_id": "94527880",
            "pdf": r"d:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\샘플2_20251231_072311\step2_evidence_collection\split_documents\94527880\extraction_targets\94527880_Commercial_Invoice_20251118_HELI_SPINDO_1266678_F_1p.pdf",
            "search_terms": ["183196.48", "183,196.48", "329.380", "CFR"]  # 실제 값들
        },
        {
            "slip_id": "94526443",
            "pdf": r"d:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\샘플2_20251231_072311\step2_evidence_collection\split_documents\94526443\extraction_targets\94526443_Commercial_Invoice_1264695_1p.pdf",
            "search_terms": ["13200.00", "1100", "FOB", "2024-11-13"]  # 예상 값들
        }
    ]

    for case in test_cases:
        print(f"\n{'='*60}")
        print(f"[전표] {case['slip_id']}")
        print(f"{'='*60}")

        pdf_type, char_count = test_pdf_type(case['pdf'])
        print(f"[PDF 타입] {pdf_type} (텍스트 {char_count}자)")

        # PyMuPDF 방식
        pymupdf_results = test_pymupdf_search(case['pdf'], case['search_terms'])

        # Tesseract 방식
        tesseract_results = test_tesseract_coordinates(case['pdf'], case['search_terms'])

        # 비교
        print(f"\n[결과 비교]")
        for term in case['search_terms']:
            pym = pymupdf_results.get(term, [0,0,0,0])
            tess = tesseract_results.get(term, [0,0,0,0])

            pym_ok = pym != [0,0,0,0]
            tess_ok = tess != [0,0,0,0]

            if pym_ok and tess_ok:
                print(f"   [OK] '{term}': 둘 다 성공")
            elif tess_ok:
                print(f"   [TESS ONLY] '{term}': Tesseract만 성공 (하이브리드 필요!)")
            elif pym_ok:
                print(f"   [PYM ONLY] '{term}': PyMuPDF만 성공")
            else:
                print(f"   [FAIL] '{term}': 둘 다 실패")

if __name__ == '__main__':
    main()
