import re
from datetime import datetime
import pandas as pd
from logic.data_normalizer import DataNormalizer


class ReconciliationManager:
    """
    Step 1 (전표) vs Step 3 (OCR) 비교 엔진
    """
    
    def __init__(self):
        self.normalizer = DataNormalizer()
    
    def _normalize_amount(self, value):
        """
        LEGACY: 하위 호환성을 위해 유지
        """
        if not value:
            return None
        try:
            clean_val = re.sub(r'[^\d.]', '', str(value).replace(',', ''))
            if clean_val:
                return float(clean_val)
        except:
            pass
        return None
    
    def _normalize_quantity(self, value):
        """
        LEGACY: 하위 호환성을 위해 유지
        """
        if not value:
            return None
        try:
            clean_val = re.sub(r'[^\d.]', '', str(value).replace(',', ''))
            if clean_val:
                return float(clean_val)
        except:
            pass
        return None
    
    def _normalize_incoterms(self, value):
        """
        LEGACY: 하위 호환성을 위해 유지
        """
        if not value:
            return ""
        return str(value).strip()[:3].upper()
    
    def _normalize_date(self, value):
        """
        LEGACY: 하위 호환성을 위해 유지
        """
        if not value:
            return ""
        
        val_str = str(value).strip()
        formats = ['%Y-%m-%d', '%Y.%m.%d', '%Y/%m/%d', '%Y%m%d', '%b. %d, %Y', '%B %d, %Y', '%d-%b-%y']
        
        for fmt in formats:
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return val_str
    
    def compare_four_fields(self, step1_row: dict, step3_data: dict, field_confidence: dict = None) -> dict:
        """
        4가지 필드 비교: 날짜, 금액, 수량, 인코텀즈
        
        Returns:
            {
                "status": "complete_match" | "partial_error" | "review_required",
                "field_results": {...},
                "mismatch_count": int
            }
        """
        field_confidence = field_confidence or {}
        results = {}
        
        # 날짜 비교
        step1_date = step1_row.get('Billing Date', '') or step1_row.get('날짜', '')
        step3_date = step3_data.get('Date', {})
        if not isinstance(step3_date, dict):
            step3_date = {'value': step3_date}
        
        step1_date_norm = self.normalizer.normalize_date(step1_date)
        step3_date_norm = self.normalizer.normalize_date(step3_date.get('value', ''))
        
        results['date'] = {
            'match': step1_date_norm['value'] == step3_date_norm['value'],
            'step1_value': step1_date_norm['value'],
            'step3_value': step3_date_norm['value'],
            'confidence': field_confidence.get('Date', field_confidence.get('date', None))
        }
        
        # 금액 비교
        step1_amount = step1_row.get('Amount', '')
        step1_currency = step1_row.get('Document Currency', '')
        step3_amount_data = step3_data.get('Amount', {})
        if not isinstance(step3_amount_data, dict):
            step3_amount_data = {'value': step3_amount_data}
        
        step1_amount_norm = self.normalizer.normalize_amount(step1_amount)
        step3_amount_norm = self.normalizer.normalize_amount(step3_amount_data.get('value', ''))
        
        amount_match = False
        if step1_amount_norm['value'] is not None and step3_amount_norm['value'] is not None:
            diff = abs(step1_amount_norm['value'] - step3_amount_norm['value'])
            amount_match = diff < 0.01
        
        currency_match = True
        if step1_currency or step3_amount_norm['currency']:
            step1_currency_std = self.normalizer.CURRENCY_MAP.get(step1_currency.upper(), step1_currency) if step1_currency else None
            currency_match = step1_currency_std == step3_amount_norm['currency']
        
        results['amount'] = {
            'match': amount_match and currency_match,
            'step1_value': step1_amount_norm['value'],
            'step3_value': step3_amount_norm['value'],
            'step1_currency': step1_currency,
            'step3_currency': step3_amount_norm['currency'],
            'currency_match': currency_match,
            'confidence': field_confidence.get('Amount', None)
        }
        
        # 수량 비교
        step1_qty = step1_row.get('Billed Quantity', '')
        step1_unit = step1_row.get('Sales Unit', '')
        step3_qty_data = step3_data.get('Quantity', {})
        if not isinstance(step3_qty_data, dict):
            step3_qty_data = {'value': step3_qty_data}
        
        step1_qty_norm = self.normalizer.normalize_quantity(step1_qty)
        step3_qty_norm = self.normalizer.normalize_quantity(step3_qty_data.get('value', ''))
        
        qty_match = False
        if step1_qty_norm['value'] is not None and step3_qty_norm['value'] is not None:
            diff = abs(step1_qty_norm['value'] - step3_qty_norm['value'])
            qty_match = diff < 0.01
        
        unit_match = True
        if step1_unit or step3_qty_norm['unit']:
            step1_unit_std = self.normalizer.UNIT_MAP.get(step1_unit.upper(), step1_unit) if step1_unit else None
            unit_match = step1_unit_std == step3_qty_norm['unit']
        
        results['quantity'] = {
            'match': qty_match and unit_match,
            'step1_value': step1_qty_norm['value'],
            'step3_value': step3_qty_norm['value'],
            'step1_unit': step1_unit,
            'step3_unit': step3_qty_norm['unit'],
            'unit_match': unit_match,
            'confidence': field_confidence.get('Quantity', None)
        }
        
        # 인코텀즈 비교
        step1_inco = step1_row.get('Incoterms', '')
        step3_inco_data = step3_data.get('Incoterms', {})
        if not isinstance(step3_inco_data, dict):
            step3_inco_data = {'value': step3_inco_data}
        
        step1_inco_norm = self.normalizer.normalize_incoterms(step1_inco)
        step3_inco_norm = self.normalizer.normalize_incoterms(step3_inco_data.get('value', ''))
        
        results['incoterms'] = {
            'match': step1_inco_norm['value'] == step3_inco_norm['value'],
            'step1_value': step1_inco_norm['value'],
            'step3_value': step3_inco_norm['value'],
            'confidence': field_confidence.get('Incoterms', None)
        }
        
        # 전체 상태 판단
        mismatch_count = sum(1 for r in results.values() if not r['match'])
        
        if mismatch_count == 0:
            status = 'complete_match'
        elif mismatch_count <= 2:
            status = 'partial_error'
        else:
            status = 'review_required'
        
        return {
            'status': status,
            'field_results': results,
            'mismatch_count': mismatch_count
        }
    
    def compare_data(self, step1_data, step3_data):
        """
        LEGACY: 기존 함수 보존 - 하위 호환성
        """
        print(f"[DEBUG] compare_data called. Step 1: {len(step1_data)}, Step 3: {len(step3_data)}")
        results = []
        
        billing_col = 'Billing Document'
        if step1_data and 'Billing Document' not in step1_data[0]:
            if '전표번호' in step1_data[0]:
                billing_col = '전표번호'
            elif 'billing_document' in step1_data[0]:
                billing_col = 'billing_document'

        for row in step1_data:
            doc_id = str(row.get(billing_col, '')).strip()
            if not doc_id:
                continue
                
            ledger_amount = row.get('Amount', '')
            ledger_qty = row.get('Billed Quantity', '')
            ledger_inco = row.get('Incoterms', '')
            ledger_date = row.get('Billing Date', '')
            
            extracted = step3_data.get(doc_id, {})
            ext_amount = extracted.get('Extracted Amount', '')
            ext_qty = extracted.get('Extracted Quantity', '')
            ext_inco = extracted.get('Extracted Incoterms', '')
            ext_date = extracted.get('Extracted Date', '')
            
            norm_l_amt = self._normalize_amount(ledger_amount)
            norm_e_amt = self._normalize_amount(ext_amount)
            norm_l_qty = self._normalize_quantity(ledger_qty)
            norm_e_qty = self._normalize_quantity(ext_qty)
            norm_l_inco = self._normalize_incoterms(ledger_inco)
            norm_e_inco = self._normalize_incoterms(ext_inco)
            norm_l_date = self._normalize_date(ledger_date)
            norm_e_date = self._normalize_date(ext_date)
            
            discrepancies = []
            
            if norm_l_amt != norm_e_amt:
                if not (norm_l_amt is None and norm_e_amt is None):
                    discrepancies.append('Amount')

            if norm_l_qty != norm_e_qty:
                if not (norm_l_qty is None and norm_e_qty is None):
                    discrepancies.append('Quantity')
            
            if norm_l_inco != norm_e_inco:
                discrepancies.append('Incoterms')
            
            if norm_l_date != norm_e_date:
                if norm_l_date or norm_e_date:
                    discrepancies.append('Date')
            
            status = 'MATCH' if not discrepancies else 'MISMATCH'
            if not extracted:
                status = 'MISSING_EVIDENCE'
            
            results.append({
                'Billing Document': doc_id,
                'Status': status,
                'Discrepancies': discrepancies,
                'Ledger Amount': ledger_amount,
                'Extracted Amount': ext_amount,
                'Amount Match': 'Amount' not in discrepancies,
                'Ledger Quantity': ledger_qty,
                'Extracted Quantity': ext_qty,
                'Quantity Match': 'Quantity' not in discrepancies,
                'Ledger Incoterms': ledger_inco,
                'Extracted Incoterms': ext_inco,
                'Incoterms Match': 'Incoterms' not in discrepancies,
                'Ledger Date': ledger_date,
                'Extracted Date': ext_date,
                'Date Match': 'Date' not in discrepancies
            })
            
        return results
