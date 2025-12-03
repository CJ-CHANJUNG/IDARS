import re
from datetime import datetime
import pandas as pd
from logic.data_normalizer import DataNormalizer

class IntegratedCrossVerifier:
    def __init__(self):
        self.report = {"status": "PASS", "details": [], "scores": {}}

    # [유틸리티] 데이터 정규화
    def to_float(self, value):
        try:
            if isinstance(value, dict) and 'value' in value:
                value = value['value']
            return float(str(value).replace(',', '').strip())
        except:
            return 0.0
    
    def normalize_date(self, date_str):
        if isinstance(date_str, dict) and 'value' in date_str:
            date_str = date_str['value']
        
        if not date_str: return None
        # YYYY-MM-DD 형식으로 정규화 (단순 문자열 처리)
        try:
            # 이미 YYYY-MM-DD 형식이면 그대로 반환
            if re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_str)):
                return str(date_str)
            
            # 간단한 변환 시도 (YYYY.MM.DD -> YYYY-MM-DD)
            return str(date_str).strip().replace('.', '-').replace('/', '-')
        except:
            return str(date_str)

    # [핵심] 검증 로직
    def verify(self, slip_row, invoice_doc, bl_doc):
        """
        slip_row: 전표 데이터 (ERP)
        invoice_doc: Invoice extraction results ({'Date': {'value': ..., 'confidence': ...}})
        bl_doc: BL extraction results
        """
        self.report = {"status": "PASS", "details": [], "scores": {}}
        
        # 1. 금액 검증 (전표 Amount vs Invoice Amount)
        # 허용 오차: 0 (정확히 일치)
        erp_amt = self.to_float(slip_row.get('Amount'))
        inv_amt = self.to_float(invoice_doc.get('Amount'))  # Already formatted with 'value' key
        
        # 정확히 일치해야 함 (float 부동소수점 고려하여 아주 작은 엡실론만 허용)
        is_amt_match = abs(erp_amt - inv_amt) < 0.000001
        
        if not is_amt_match:
            self.fail(f"금액 불일치: ERP({erp_amt:,.2f}) vs Invoice({inv_amt:,.2f})")
        else:
            self.log(f"금액 일치 ({erp_amt:,.2f})")

        # 2. 날짜 검증 (3자 대사: ERP vs Invoice vs BL)
        date_erp = self.normalize_date(slip_row.get('Billing Date'))
        date_inv = self.normalize_date(invoice_doc.get('Date'))
        date_bl = self.normalize_date(bl_doc.get('on_board_date')) if bl_doc else None
        
        # 3자 대사 로직
        dates_to_compare = [d for d in [date_erp, date_inv, date_bl] if d]
        
        if len(dates_to_compare) < 2:
             self.warn("날짜 정보 부족으로 검증 불가")
        else:
            # 모든 날짜가 동일한지 확인
            if all(x == dates_to_compare[0] for x in dates_to_compare):
                if len(dates_to_compare) == 3:
                    self.log(f"3자 날짜 일치 ({date_erp})")
                else:
                    self.log(f"2자 날짜 일치 ({date_erp}) - BL 날짜 누락")
            else:
                self.fail(f"날짜 불일치: ERP({date_erp}) vs Invoice({date_inv}) vs BL({date_bl})")

        # 3. 수량 검증 (Quantity Verification)
        # Primary: ERP == Invoice
        erp_qty = self.to_float(slip_row.get('Billed Quantity'))
        inv_qty = self.to_float(invoice_doc.get('Quantity'))
        
        # Secondary: BL Net Weight와 비교 (참고용)
        bl_net_wgt = self.to_float(bl_doc.get('net_weight')) if bl_doc else 0.0
        
        is_qty_match = abs(erp_qty - inv_qty) < 0.01  # 오차 0.01 허용 (부동소수점)
        
        if not is_qty_match:
            self.fail(f"수량 불일치: ERP({erp_qty:.2f}) vs Invoice({inv_qty:.2f})")
        else:
            self.log(f"수량 일치 ({erp_qty:.2f})")
            
        # BL Net Weight 참고 검증
        if bl_net_wgt > 0:
            bl_diff = abs(erp_qty - bl_net_wgt)
            if bl_diff > 0.01:
                self.warn(f"BL Net Weight 상이: ERP({erp_qty:.2f}) vs BL({bl_net_wgt:.2f}), 차이={bl_diff:.2f}")

        # 4. Incoterms 검증
        # Primary: ERP vs Invoice (정확히 일치)
        erp_inco = str(slip_row.get('Incoterms', '')).strip().upper()
        
        # Extract value from dict if needed
        inv_inco_raw = invoice_doc.get('Incoterms', '')
        if isinstance(inv_inco_raw, dict):
            inv_inco = str(inv_inco_raw.get('value', '')).strip().upper()
        else:
            inv_inco = str(inv_inco_raw).strip().upper()
        
        # Extract just the incoterm code (first 3 letters)
        erp_code = erp_inco[:3] if len(erp_inco) >= 3 else erp_inco
        inv_code = inv_inco[:3] if len(inv_inco) >= 3 else inv_inco
        
        is_inco_match = (erp_code == inv_code)
        
        if not is_inco_match:
            self.fail(f"인코텀즈 불일치: ERP({erp_code}) vs Invoice({inv_code})")
        else:
            self.log(f"인코텀즈 일치 ({erp_code})")
        
        # Secondary: BL Freight Terms 논리 검증
        if bl_doc:
            bl_freight = str(bl_doc.get('freight_payment_terms', '')).strip().upper()
            
            if bl_freight:
                # C/D 그룹: CIF, CFR, CPT, CIP, DAT, DAP, DDP -> Prepaid
                # E/F 그룹: EXW, FOB, FCA, FAS -> Collect
                cd_group = ['CIF', 'CFR', 'CPT', 'CIP', 'DAT', 'DAP', 'DDP']
                ef_group = ['EXW', 'FOB', 'FCA', 'FAS']
                
                if erp_code in cd_group:
                    if 'PREPAID' not in bl_freight:
                        self.warn(f"BL Freight 불일치: {erp_code}는 Prepaid여야 함, 실제: {bl_freight}")
                elif erp_code in ef_group:
                    if 'COLLECT' not in bl_freight:
                        self.warn(f"BL Freight 불일치: {erp_code}는 Collect여야 함, 실제: {bl_freight}")
        
        return self.report

    def fail(self, msg):
        self.report['status'] = "FAIL"
        self.report['details'].append(f"❌ {msg}")
    
    def warn(self, msg):
        # FAIL 상태가 아닐 때만 WARNING으로 변경 (FAIL이 더 심각하므로)
        if self.report['status'] != "FAIL": 
            self.report['status'] = "WARNING"
        self.report['details'].append(f"⚠️ {msg}")
    
    def log(self, msg):
        self.report['details'].append(f"✅ {msg}")


class ReconciliationManager:
    """
    Step 1 (전표) vs Step 3 (OCR) 비교 엔진
    IntegratedCrossVerifier를 사용하여 검증 수행
    """
    
    def __init__(self):
        self.verifier = IntegratedCrossVerifier()
        self.normalizer = DataNormalizer()
    
    def compare_four_fields(self, step1_row: dict, step3_data: dict, bl_data: dict = None, field_confidence: dict = None) -> dict:
        """
        통합 검증 실행
        """
        # IntegratedCrossVerifier 실행
        report = self.verifier.verify(step1_row, step3_data, bl_data)
        
        # 기존 포맷으로 변환 (프론트엔드 호환성 유지)
        status_map = {
            "PASS": "complete_match",
            "FAIL": "partial_error",
            "WARNING": "review_required"
        }
        
        final_status = status_map.get(report['status'], "review_required")
        
        # 상세 결과 매핑 (기존 UI 호환)
        details = str(report['details'])
        
        # Invoice 필드 비교 결과
        results = {
            'date': {
                'match': "날짜 불일치" not in details, 
                'step1_value': step1_row.get('Billing Date'), 
                'step3_value': step3_data.get('Date'),
                'confidence': field_confidence.get('Date', 0.0) if field_confidence else 0.0
            },
            'amount': {
                'match': "금액 불일치" not in details, 
                'step1_value': step1_row.get('Amount'), 
                'step3_value': step3_data.get('Amount'),
                'confidence': field_confidence.get('Amount', 0.0) if field_confidence else 0.0
            },
            'quantity': {
                'match': "수량 불일치" not in details, 
                'step1_value': step1_row.get('Billed Quantity'), 
                'step3_value': step3_data.get('Quantity'),
                'confidence': field_confidence.get('Quantity', 0.0) if field_confidence else 0.0
            },
            'incoterms': {
                'match': "인코텀즈 불일치" not in details, 
                'step1_value': step1_row.get('Incoterms'), 
                'step3_value': step3_data.get('Incoterms'),
                'confidence': field_confidence.get('Incoterms', 0.0) if field_confidence else 0.0
            }
        }
        
        # BL 필드 비교 결과 추가 (참고용, WARNING 상태 표시)
        bl_results = {}
        if bl_data:
            # BL Net Weight vs ERP Quantity 비교 (참고)
            bl_results['bl_net_weight'] = {
                'match': "BL Net Weight 상이" not in details,
                'bl_value': bl_data.get('net_weight'),
                'step1_value': step1_row.get('Billed Quantity')
            }
            # BL On Board Date vs ERP/Invoice Date 비교
            bl_results['bl_on_board_date'] = {
                'match': "날짜 불일치" not in details,  # 3자 대사에 포함됨
                'bl_value': bl_data.get('on_board_date'),
                'step1_value': step1_row.get('Billing Date')
            }
            # BL Freight Terms vs ERP Incoterms 논리 검증 (참고)
            bl_results['bl_freight_terms'] = {
                'match': "Prepaid여야 함" not in details and "Collect여야 함" not in details,
                'bl_value': bl_data.get('freight_payment_terms'),
                'step1_value': step1_row.get('Incoterms')
            }
        
        return {
            "status": final_status,
            "field_results": results,
            "bl_results": bl_results,  # BL 비교 결과 추가
            "mismatch_count": 1 if final_status == "partial_error" else 0,
            "verifier_report": report # 상세 리포트 포함
        }
