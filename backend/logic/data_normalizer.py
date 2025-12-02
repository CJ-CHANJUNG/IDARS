# -*- coding: utf-8 -*-
"""
Data Normalizer - 데이터 정규화 및 검증
Gemini API 응답 후 값과 단위를 표준화하고 검증합니다.
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime


class DataNormalizer:
    """
    Gemini 응답 후 데이터 정규화 및 검증
    """
    
    # 통화 표준화 매핑
    CURRENCY_MAP = {
        'USD': 'USD', 'US$': 'USD', 'DOLLAR': 'USD', 'DOLLARS': 'USD',
        'JPY': 'JPY', 'YEN': 'JPY', '¥': 'JPY',
        'KRW': 'KRW', 'WON': 'KRW', '₩': 'KRW',
        'EUR': 'EUR', '€': 'EUR', 'EURO': 'EUR', 'EUROS': 'EUR',
        'GBP': 'GBP', '£': 'GBP', 'POUND': 'GBP', 'POUNDS': 'GBP'
    }
    
    # 단위 표준화 매핑
    UNIT_MAP = {
        'MT': 'MT', 'TON': 'MT', 'TONS': 'MT', 'M/T': 'MT', 'METRIC TON': 'MT', 'METRIC TONS': 'MT',
        'KG': 'KG', 'KILOGRAM': 'KG', 'KILOGRAMS': 'KG', 'KILO': 'KG', 'KILOS': 'KG',
        'PCS': 'PCS', 'PIECE': 'PCS', 'PIECES': 'PCS', 'EA': 'PCS', 'EACH': 'PCS',
        'M': 'M', 'METER': 'M', 'METERS': 'M', 'METRE': 'M', 'METRES': 'M',
        'L': 'L', 'LITER': 'L', 'LITERS': 'L', 'LITRE': 'L', 'LITRES': 'L'
    }
    
    # 인코텀즈 표준화 매핑
    INCOTERMS_MAP = {
        'FOB': ['FOB', 'F.O.B', 'F.O.B.', 'F O B'],
        'CIF': ['CIF', 'C.I.F', 'C.I.F.', 'C I F'],
        'CFR': ['CFR', 'C&F', 'C.F.R', 'C F R', 'C AND F'],
        'EXW': ['EXW', 'EX WORKS', 'EX-WORKS'],
        'FCA': ['FCA', 'F.C.A', 'FREE CARRIER'],
        'CPT': ['CPT', 'C.P.T', 'CARRIAGE PAID'],
        'CIP': ['CIP', 'C.I.P', 'CARRIAGE AND INSURANCE PAID'],
        'DAP': ['DAP', 'D.A.P', 'DELIVERED AT PLACE'],
        'DPU': ['DPU', 'D.P.U', 'DELIVERED AT PLACE UNLOADED'],
        'DDP': ['DDP', 'D.D.P', 'DELIVERED DUTY PAID'],
        'FAS': ['FAS', 'F.A.S', 'FREE ALONGSIDE SHIP']
    }
    
    @staticmethod
    def parse_quantity_with_unit(ocr_text: str) -> Dict[str, Any]:
        """
        OCR 텍스트에서 수량과 단위 분리
        
        지원 패턴:
        1. "100 KG" (공백 있음)
        2. "100KG" (공백 없음) 
        3. "100.5MT" (소수점 포함)
        4. "1,000 TONS" (천단위 구분)
        
        Returns:
            {"quantity": 100, "unit": "KG", "raw": "100 KG"}
        """
        if not ocr_text:
            return {"quantity": None, "unit": None, "raw": ocr_text}
        
        text = str(ocr_text).strip().upper()
        
        # 패턴: 숫자 + 선택적 공백 + 단위
        pattern = r'([\d,\.]+)\s*([A-Z/]+)?'
        match = re.search(pattern, text)
        
        if match:
            quantity_str = match.group(1)
            unit = match.group(2) or ''
            
            try:
                clean_quantity = float(quantity_str.replace(',', ''))
            except:
                clean_quantity = None
            
            # 단위 표준화
            clean_unit = DataNormalizer.UNIT_MAP.get(unit.strip(), unit) if unit else None
            
            return {
                "quantity": clean_quantity,
                "unit": clean_unit,
                "raw": text
            }
        
        return {"quantity": None, "unit": None, "raw": text}
    
    @staticmethod
    def normalize_quantity(raw_value: Any) -> Dict[str, Any]:
        """
        수량 정규화
        입력: {"value": 1000, "unit": "MT"} 또는 "1,000 MT"
        출력: {"value": 1000.0, "unit": "MT", \"formatted": "1,000.00 MT"}
        """
        if isinstance(raw_value, dict):
            value = raw_value.get('value') or raw_value.get('quantity')
            unit = raw_value.get('unit', '')
        else:
            # 문자열인 경우 파싱
            parsed = DataNormalizer.parse_quantity_with_unit(raw_value)
            value = parsed['quantity']
            unit = parsed['unit']
        
        # 숫자 정리
        try:
            clean_value = float(str(value).replace(',', '')) if value else None
        except:
            clean_value = None
        
        # 단위 표준화
        if unit:
            clean_unit = DataNormalizer.UNIT_MAP.get(str(unit).upper().strip(), unit)
        else:
            clean_unit = None
        
        # 포맷된 문자열 생성
        if clean_value is not None:
            formatted = f"{clean_value:,.2f} {clean_unit}" if clean_unit else f"{clean_value:,.2f}"
        else:
            formatted = ""
        
        return {
            "value": clean_value,
            "unit": clean_unit,
            "formatted": formatted
        }
    
    @staticmethod
    def parse_amount_with_currency(ocr_text: str) -> Dict[str, Any]:
        """
        OCR 텍스트에서 금액과 통화 분리
        
        지원 패턴:
        1. "USD 1,234.56" (통화 앞, 공백)
        2. "1,234.56 USD" (통화 뒤, 공백)
        3. "USD1,234.56" (통화 앞, 공백 없음)
        4. "1,234.56USD" (통화 뒤, 공백 없음)
        5. "$ 1,234.56" (기호, 공백)
        6. "$1,234.56" (기호, 공백 없음)
        7. "US$ 1,234.56" (달러 변형)
        
        Returns:
            {"currency": "USD", "amount": 1234.56, "raw": "USD 1,234.56"}
        """
        if not ocr_text:
            return {"currency": None, "amount": None, "raw": ocr_text}
        
        text = str(ocr_text).strip()
        
        # 다양한 패턴 시도 (우선순위 순)
        patterns = [
            # 패턴 1: 3자 통화 코드 + 숫자 (예: "USD 1,234.56" 또는 "USD1,234.56")
            r'([A-Z]{3})\s*([\d,\.]+)',
            # 패턴 2: 숫자 + 3자 통화 코드 (예: "1,234.56 USD" 또는 "1,234.56USD")
            r'([\d,\.]+)\s*([A-Z]{3})',
            # 패턴 3: 달러 변형 + 숫자 (예: "US$ 1,234.56" 또는 "US$1,234.56")
            r'(US\$|US \$)\s*([\d,\.]+)',
            # 패턴 4: 기호 + 숫자 (예: "$ 1,234.56" 또는 "$1,234.56")
            r'([$¥₩€£])\s*([\d,\.]+)',
            # 패턴 5: 숫자 + 기호 (예: "1,234.56$")
            r'([\d,\.]+)\s*([$¥₩€£])',
        ]
        
        currency = None
        amount_str = None
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                # 첫 번째 그룹이 숫자인지 확인
                if re.match(r'[\d,\.]+', groups[0]):
                    amount_str = groups[0]
                    currency = groups[1] if len(groups) > 1 else None
                else:
                    currency = groups[0]
                    amount_str = groups[1] if len(groups) > 1 else None
                break
        
        # 숫자 파싱
        try:
            clean_amount = float(amount_str.replace(',', '')) if amount_str else None
        except:
            clean_amount = None
        
        # 통화 표준화
        if currency:
            currency = currency.upper().strip()
            currency = DataNormalizer.CURRENCY_MAP.get(currency, currency)
        
        return {
            "currency": currency,
            "amount": clean_amount,
            "raw": text
        }
    
    @staticmethod
    def normalize_amount(raw_value: Any) -> Dict[str, Any]:
        """
        금액 정규화
        입력: {"value": 50000, "currency": "USD"} 또는 "USD 50,000" 또는 OCR 텍스트
        출력: {"value": 50000.0, "currency": "USD", "formatted": "50,000.00 USD"}
        """
        if isinstance(raw_value, dict):
            # 이미 구조화된 데이터
            value = raw_value.get('value') or raw_value.get('amount')
            currency = raw_value.get('currency', '')
        else:
            # 문자열인 경우 파싱
            parsed = DataNormalizer.parse_amount_with_currency(raw_value)
            value = parsed['amount']
            currency = parsed['currency']
        
        # 숫자 정리
        try:
            clean_value = float(str(value).replace(',', '')) if value else None
        except:
            clean_value = None
        
        # 통화 표준화 (이미 parse_amount_with_currency에서 했지만 재확인)
        if currency:
            clean_currency = DataNormalizer.CURRENCY_MAP.get(str(currency).upper().strip(), currency)
        else:
            clean_currency = None
        
        # 포맷된 문자열 생성
        if clean_value is not None:
            formatted = f"{clean_value:,.2f} {clean_currency}" if clean_currency else f"{clean_value:,.2f}"
        else:
            formatted = ""
        
        return {
            "value": clean_value,
            "currency": clean_currency,
            "formatted": formatted
        }
    
    @staticmethod
    def normalize_date(raw_value: Any) -> Dict[str, Any]:
        """
        날짜 정규화
        입력: "2025-06-30" 또는 "JUN 30 2025" 또는 "30/06/2025"
        출력: {"value": "2025-06-30", "formatted": "2025-06-30"}
        """
        if isinstance(raw_value, dict):
            value = raw_value.get('value')
        else:
            value = str(raw_value)
        
        # 빈 값 처리
        if not value or value.strip() == '':
            return {"value": None, "formatted": ""}
        
        try:
            # dateutil로 파싱 시도
            from dateutil import parser as date_parser
            parsed = date_parser.parse(value)
            normalized = parsed.strftime("%Y-%m-%d")
        except:
            # 파싱 실패 시 원본 유지
            normalized = value
        
        return {
            "value": normalized,
            "formatted": normalized
        }
    
    @staticmethod
    def normalize_incoterms(raw_value: Any) -> Dict[str, Any]:
        """
        인코텀즈 표준화
        입력: "F.O.B" 또는 "fob" 또는 "C.I.F Hamburg"
        출력: {"value": "FOB", "formatted": "FOB"}
        """
        if isinstance(raw_value, dict):
            value = raw_value.get('value')
        else:
            value = str(raw_value)
        
        if not value or value.strip() == '':
            return {"value": None, "formatted": ""}
        
        # 대문자로 변환 및 공백 제거
        clean_value = value.upper().strip().replace('.', '').replace(' ', '')
        
        # 표준화 매핑에서 찾기
        for standard, variants in DataNormalizer.INCOTERMS_MAP.items():
            for variant in variants:
                variant_clean = variant.replace('.', '').replace(' ', '')
                if clean_value.startswith(variant_clean):
                    return {"value": standard, "formatted": standard}
        
        # 매핑에 없으면 처음 3자만 대문자로
        normalized = clean_value[:3] if len(clean_value) >= 3 else clean_value
        
        return {
            "value": normalized,
            "formatted": normalized
        }
    
    @classmethod
    def normalize_extraction_result(cls, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        전체 추출 결과 정규화
        """
        fields = raw_result.get('fields', {})
        normalized = {}
        
        # 각 필드 타입별 정규화
        for field_name, field_value in fields.items():
            field_lower = field_name.lower()
            
            if 'quantity' in field_lower or 'qty' in field_lower:
                normalized[field_name] = cls.normalize_quantity(field_value)
            elif 'amount' in field_lower or 'price' in field_lower:
                normalized[field_name] = cls.normalize_amount(field_value)
            elif 'date' in field_lower:
                normalized[field_name] = cls.normalize_date(field_value)
            elif 'incoterms' in field_lower:
                normalized[field_name] = cls.normalize_incoterms(field_value)
            else:
                # 텍스트 필드는 그대로
                if isinstance(field_value, dict) and 'value' in field_value:
                    normalized[field_name] = field_value
                else:
                    normalized[field_name] = {
                        "value": field_value,
                        "formatted": str(field_value) if field_value is not None else ""
                    }
        
        return {
            "fields": normalized,
            "confidence": raw_result.get('confidence', {}),
            "field_confidence": raw_result.get('field_confidence', {}),
            "document_type": raw_result.get('document_type'),
            "raw_fields": fields  # 원본 데이터 보존 (디버깅용)
        }


if __name__ == "__main__":
    # 테스트 코드
    normalizer = DataNormalizer()
    
    # 수량 테스트
    print("=== Quantity Normalization ===")
    print(normalizer.normalize_quantity({"value": 1000, "unit": "MT"}))
    print(normalizer.normalize_quantity("1,500 TONS"))
    print(normalizer.normalize_quantity("100KG"))  # 공백 없음
    
    # 금액 테스트
    print("\n=== Amount Normalization ===")
    print(normalizer.normalize_amount({"value": 50000, "currency": "USD"}))
    print(normalizer.normalize_amount("USD 1,234,567.89"))
    print(normalizer.normalize_amount("1,234.56USD"))  # 공백 없음, 통화 뒤
    print(normalizer.normalize_amount("US$ 1,000"))  # 달러 변형
    print(normalizer.normalize_amount("$1,234.56"))  # 기호, 공백 없음
    print(normalizer.normalize_amount("¥ 500,000"))
    
    # 날짜 테스트
    print("\n=== Date Normalization ===")
    print(normalizer.normalize_date("JUN 30 2025"))
    print(normalizer.normalize_date("30/06/2025"))
    print(normalizer.normalize_date("2025-06-30"))
    
    # 인코텀즈 테스트
    print("\n=== Incoterms Normalization ===")
    print(normalizer.normalize_incoterms("F.O.B"))
    print(normalizer.normalize_incoterms("fob"))
    print(normalizer.normalize_incoterms("C.I.F Hamburg"))

