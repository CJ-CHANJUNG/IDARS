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
        """
        coordinates = None
        if isinstance(raw_value, dict):
            value = raw_value.get('value') or raw_value.get('quantity')
            unit = raw_value.get('unit', '')
            coordinates = raw_value.get('coordinates')
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
            "formatted": formatted,
            "coordinates": coordinates
        }

    @staticmethod
    def normalize_amount(raw_value: Any) -> Dict[str, Any]:
        """
        금액 정규화
        """
        coordinates = None
        if isinstance(raw_value, dict):
            # 이미 구조화된 데이터
            value = raw_value.get('value') or raw_value.get('amount')
            currency = raw_value.get('currency', '')
            coordinates = raw_value.get('coordinates')
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
        
        # 통화 표준화
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
            "formatted": formatted,
            "coordinates": coordinates
        }
    
    @staticmethod
    def normalize_date(raw_value: Any) -> Dict[str, Any]:
        """
        날짜 정규화
        """
        coordinates = None
        if isinstance(raw_value, dict):
            value = raw_value.get('value')
            coordinates = raw_value.get('coordinates')
        else:
            value = str(raw_value)
        
        # 빈 값 처리
        if not value or value.strip() == '':
            return {"value": None, "formatted": "", "coordinates": coordinates}
        
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
            "formatted": normalized,
            "coordinates": coordinates
        }
    
    @staticmethod
    def normalize_incoterms(raw_value: Any) -> Dict[str, Any]:
        """
        인코텀즈 표준화
        """
        coordinates = None
        if isinstance(raw_value, dict):
            value = raw_value.get('value')
            coordinates = raw_value.get('coordinates')
        else:
            value = str(raw_value)
        
        if not value or value.strip() == '':
            return {"value": None, "formatted": "", "coordinates": coordinates}
        
        # 대문자로 변환 및 공백 제거
        clean_value = value.upper().strip().replace('.', '').replace(' ', '')
        
        # 표준화 매핑에서 찾기
        for standard, variants in DataNormalizer.INCOTERMS_MAP.items():
            for variant in variants:
                variant_clean = variant.replace('.', '').replace(' ', '')
                if clean_value.startswith(variant_clean):
                    return {"value": standard, "formatted": standard, "coordinates": coordinates}
        
        # 매핑에 없으면 처음 3자만 대문자로
        normalized = clean_value[:3] if len(clean_value) >= 3 else clean_value
        
        return {
            "value": normalized,
            "formatted": normalized,
            "coordinates": coordinates
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
            "evidence": raw_result.get('evidence'),
            "notes": raw_result.get('notes'),
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

