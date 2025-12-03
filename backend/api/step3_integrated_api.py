# -*- coding: utf-8 -*-
"""
Step 3 통합 API 엔드포인트
추출 + 정규화 + 비교를 한 번에 처리
"""

from flask import Blueprint, request, jsonify
import os
import json
import sys
from datetime import datetime
from pathlib import Path

# 이 파일의 위치를 기준으로 프로젝트 루트 찾기
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

from logic.data_normalizer import DataNormalizer
from logic.reconciliation import ReconciliationManager

step3_integrated_bp = Blueprint('step3_integrated', __name__)
normalizer = DataNormalizer()
reconciler = ReconciliationManager()


@step3_integrated_bp.route('/api/projects/<project_id>/step3/extract-and-compare', methods=['POST'])
def extract_and_compare(project_id):
    """
    통합 API: 추출 + 정규화 + 비교 (Smart Engine 사용)
    
    Request:
        {
            "extraction_mode": "basic" or "detailed",
            "projectsDir": "D:/path/to/projects"
        }
    
    Response:
        {
            "extraction_results": {...},
            "comparison_results": [...],
            "api_usage": {...}
        }
    """
    try:
        print(f"🚀 [API] Received extraction request for project: {project_id}")
        data = request.json
        extraction_mode = data.get('extraction_mode', 'basic')  # basic or detailed
        target_ids = data.get('target_ids', None)  # List of slip IDs to process
        
        # Use absolute path for projects directory (ignore frontend relative path)
        project_root = os.path.dirname(BACKEND_DIR)
        projects_dir = os.path.join(project_root, 'Data', 'projects')
        
        project_path = os.path.join(projects_dir, project_id)
        step3_dir = os.path.join(project_path, 'step3_data_extraction')
        os.makedirs(step3_dir, exist_ok=True)
        
        print(f"[DEBUG] extract_and_compare: Saving to {step3_dir}")
        if target_ids:
            print(f"[DEBUG] Target IDs: {target_ids}")
        
        # === 1. Load Step 1 Data ===
        step1_path = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
        if not os.path.exists(step1_path):
            step1_path = os.path.join(project_path, 'step1_entry_import', 'confirmed_data.csv')
        
        if not os.path.exists(step1_path):
            return jsonify({"error": "Step 1 data not found. Please confirm Step 1 first."}), 404
        
        import pandas as pd
        df = pd.read_csv(step1_path)
        step1_data = df.to_dict('records')
        
        # === 2. Extract from PDFs using Smart Engine ===
        sys.path.append(os.path.join(BACKEND_DIR, '..', 'Modules', 'Parser'))
        from smart_extraction_engine import SmartExtractionEngine
        
        engine = SmartExtractionEngine()
        split_dir = os.path.join(project_path, 'step2_evidence_collection', 'split_documents')
        
        # 비동기 병렬 처리 (asyncio.run으로 실행)
        import asyncio
        print(f"[DEBUG] Starting async extraction for project {project_id}")
        
        try:
            # Check for existing event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            
            if loop and loop.is_running():
                print("[DEBUG] Event loop already running, using loop.run_until_complete is not possible here. Using create_task if in async context, but this is sync Flask.")
                # This is tricky in sync Flask. If we are here, it means we are in a thread with an event loop?
                # Usually Flask doesn't have one.
                # If we are in a thread with a loop, we should use it?
                # But asyncio.run() creates a NEW loop.
                # Let's try to use a new thread to run the async code if we suspect loop issues.
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    extraction_results_raw = executor.submit(asyncio.run, engine.process_project_pdfs_async(
                        project_id=project_id,
                        split_dir=split_dir,
                        extraction_mode=extraction_mode,
                        target_ids=target_ids
                    )).result()
            else:
                extraction_results_raw = asyncio.run(engine.process_project_pdfs_async(
                    project_id=project_id,
                    split_dir=split_dir,
                    extraction_mode=extraction_mode,  # basic 또는 detailed
                    target_ids=target_ids
                ))
            print(f"[DEBUG] Async extraction completed. Results count: {len(extraction_results_raw)}")
            
        except Exception as e:
            print(f"[CRITICAL ERROR] Async execution failed: {e}")
            import traceback
            traceback.print_exc()
            # Log to file to persist after crash
            with open("crash_log.txt", "a") as f:
                f.write(f"[{datetime.now()}] Crash in step3_integrated_api: {e}\n")
                f.write(traceback.format_exc())
            raise e

        
        # === 3. Transform results to comparison format ===
        extraction_results = {}
        api_usage = {}
        bl_data_map = {}  # BL 데이터 별도 저장
        
        for slip_result in extraction_results_raw:
            slip_id = slip_result.get('slip_id')
            documents = slip_result.get('documents', [])
            
            # 각 전표별로 Invoice와 BL 데이터 분리
            invoice_data = None
            bl_data = None
            total_tokens = {'input': 0, 'output': 0}
            
            for doc in documents:
                doc_type = doc.get('type')
                fields = doc.get('fields', {})
                tokens = doc.get('token_usage', {})
                
                # 토큰 누적
                total_tokens['input'] += tokens.get('input_tokens', 0)
                total_tokens['output'] += tokens.get('output_tokens', 0)
                
                field_confidences = doc.get('field_confidence', {})
                
                if doc_type == 'INVOICE':
                    # Invoice 데이터 추출
                    invoice_data = {
                        'Date': {
                            'value': fields.get('sailing_date', {}).get('value'),
                            'confidence': field_confidences.get('sailing_date', 0.0)
                        },
                        'Amount': {
                            'value': fields.get('total_amount', {}).get('value'),
                            'currency': fields.get('total_amount', {}).get('currency'),
                            'confidence': field_confidences.get('total_amount', 0.0)
                        },
                        'Quantity': {
                            'value': fields.get('total_quantity', {}).get('value'),
                            'unit': fields.get('total_quantity', {}).get('unit'),
                            'confidence': field_confidences.get('total_quantity', 0.0)
                        },
                        'Incoterms': {
                            'value': fields.get('incoterms', {}).get('value'),
                            'confidence': field_confidences.get('incoterms', 0.0)
                        }
                    }
                    
                elif doc_type == 'BL':
                    # BL 데이터 추출 (별도 저장)
                    bl_data = {
                        'bl_number': fields.get('bl_number', {}).get('value'),
                        'vessel_name': fields.get('vessel_name', {}).get('value'),
                        'port_of_loading': fields.get('port_of_loading', {}).get('value'),
                        'port_of_discharge': fields.get('port_of_discharge', {}).get('value'),
                        'on_board_date': fields.get('on_board_date', {}).get('value'),
                        'net_weight': {
                            'value': fields.get('net_weight', {}).get('value'),
                            'unit': fields.get('net_weight', {}).get('unit')
                        },
                        'gross_weight': {
                            'value': fields.get('gross_weight', {}).get('value'),
                            'unit': fields.get('gross_weight', {}).get('unit')
                        },
                        'quantity': {
                            'value': fields.get('quantity', {}).get('value'),
                            'unit': fields.get('quantity', {}).get('unit')
                        },
                        'shipper': fields.get('shipper', {}).get('value'),
                        'consignee': fields.get('consignee', {}).get('value'),
                        'freight_payment_terms': fields.get('freight_payment_terms', {}).get('value'),
                        # 신뢰도
                        'on_board_date_confidence': field_confidences.get('on_board_date', 0.0),
                        'net_weight_confidence': field_confidences.get('net_weight', 0.0),
                        'gross_weight_confidence': field_confidences.get('gross_weight', 0.0),
                        'quantity_confidence': field_confidences.get('quantity', 0.0),
                        'freight_payment_terms_confidence': field_confidences.get('freight_payment_terms', 0.0)
                    }
            
            # 결과 저장
            if invoice_data:
                extraction_results[slip_id] = invoice_data
            if bl_data:
                bl_data_map[slip_id] = bl_data
            
            api_usage[slip_id] = total_tokens
        
        # Save Invoice extraction results (병합 방식)
        invoice_results_file = os.path.join(step3_dir, 'invoice_extraction_results.json')
        
        # 기존 데이터 로드
        existing_invoice_data = {}
        if os.path.exists(invoice_results_file):
            try:
                with open(invoice_results_file, 'r', encoding='utf-8') as f:
                    existing_invoice_data = json.load(f)
                print(f"[DEBUG] 기존 Invoice 데이터 로드: {len(existing_invoice_data)}건")
            except Exception as e:
                print(f"[WARNING] 기존 Invoice 데이터 로드 실패: {e}")
        
        # 병합 (새 데이터로 덮어쓰기)
        existing_invoice_data.update(extraction_results)
        
        with open(invoice_results_file, 'w', encoding='utf-8') as f:
            json.dump(existing_invoice_data, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] Invoice 데이터 저장 완료: {len(existing_invoice_data)}건")
        
        # Save BL data separately (병합 방식)
        bl_file = os.path.join(step3_dir, 'bl_extraction_results.json')
        
        # 기존 BL 데이터 로드
        existing_bl_data = {}
        if os.path.exists(bl_file):
            try:
                with open(bl_file, 'r', encoding='utf-8') as f:
                    existing_bl_data = json.load(f)
                print(f"[DEBUG] 기존 BL 데이터 로드: {len(existing_bl_data)}건")
            except Exception as e:
                print(f"[WARNING] 기존 BL 데이터 로드 실패: {e}")
        
        # 병합
        existing_bl_data.update(bl_data_map)
        
        with open(bl_file, 'w', encoding='utf-8') as f:
            json.dump(existing_bl_data, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] BL 데이터 저장 완료: {len(existing_bl_data)}건")
        
        # Save API Usage separately (병합 방식)
        usage_file = os.path.join(step3_dir, 'api_usage.json')
        
        # 기존 Usage 데이터 로드
        existing_usage_data = {}
        if os.path.exists(usage_file):
            try:
                with open(usage_file, 'r', encoding='utf-8') as f:
                    existing_usage_data = json.load(f)
                print(f"[DEBUG] 기존 API Usage 데이터 로드: {len(existing_usage_data)}건")
            except Exception as e:
                print(f"[WARNING] 기존 API Usage 데이터 로드 실패: {e}")
        
        # 병합
        existing_usage_data.update(api_usage)
        
        with open(usage_file, 'w', encoding='utf-8') as f:
            json.dump(existing_usage_data, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] API Usage 데이터 저장 완료: {len(existing_usage_data)}건")
        
        # === 4. Normalize and Compare ===
        comparison_results = []
        
        # IMPORTANT: Use merged data for comparison, not just newly extracted data
        all_invoice_data = existing_invoice_data  # Contains both old and new data
        all_bl_data = existing_bl_data  # Contains both old and new data
        all_usage_data = existing_usage_data # Contains both old and new usage data
        
        for step1_row in step1_data:
            billing_doc = str(step1_row.get('Billing Document', '')).strip()
            if not billing_doc:

                continue
            
            step3_data = all_invoice_data.get(billing_doc, {})
            bl_data = all_bl_data.get(billing_doc, {})
            
            # Get field confidence from API response
            field_confidence = {}
            for field_name, field_value in step3_data.items():
                if isinstance(field_value, dict) and 'confidence' in field_value:
                    field_confidence[field_name] = field_value.get('confidence')
            
            # Compare using ReconciliationManager
            comparison = reconciler.compare_four_fields(step1_row, step3_data, bl_data, field_confidence)
            
            # Prepare result with BL data included
            result = {
                'billing_document': billing_doc,
                'auto_comparison': comparison,
                'api_usage': all_usage_data.get(billing_doc, {'input': 0, 'output': 0}),
                'step1_data': {
                    'date': step1_row.get('Billing Date', ''),
                    'amount': step1_row.get('Amount', ''),
                    'currency': step1_row.get('Document Currency', ''),
                    'quantity': step1_row.get('Billed Quantity', ''),
                    'unit': step1_row.get('Sales Unit', ''),
                    'incoterms': step1_row.get('Incoterms', '')
                },
                'ocr_data': {
                    # 새 필드명 우선, 없으면 구 필드명 사용 (백워드 호환성)
                    'date': (
                        step3_data.get('sailing_date', {}).get('value', '') if isinstance(step3_data.get('sailing_date'), dict) else step3_data.get('sailing_date', '')
                    ) or (
                        step3_data.get('Date', {}).get('value', '') if isinstance(step3_data.get('Date'), dict) else step3_data.get('Date', '')
                    ),
                    'amount': (
                        step3_data.get('total_amount', {}).get('value', '') if isinstance(step3_data.get('total_amount'), dict) else step3_data.get('total_amount', '')
                    ) or (
                        step3_data.get('Amount', {}).get('value', '') if isinstance(step3_data.get('Amount'), dict) else step3_data.get('Amount', '')
                    ),
                    'quantity': (
                        step3_data.get('total_quantity', {}).get('value', '') if isinstance(step3_data.get('total_quantity'), dict) else step3_data.get('total_quantity', '')
                    ) or (
                        step3_data.get('Quantity', {}).get('value', '') if isinstance(step3_data.get('Quantity'), dict) else step3_data.get('Quantity', '')
                    ),
                    'incoterms': (
                        step3_data.get('incoterms', {}).get('value', '') if isinstance(step3_data.get('incoterms'), dict) else step3_data.get('incoterms', '')
                    ) or (
                        step3_data.get('Incoterms', {}).get('value', '') if isinstance(step3_data.get('Incoterms'), dict) else step3_data.get('Incoterms', '')
                    ),
                    # 신뢰도 (새 필드명 우선)
                    'date_confidence': (
                        step3_data.get('sailing_date', {}).get('confidence', 0.0) if isinstance(step3_data.get('sailing_date'), dict) else 0.0
                    ) or (
                        step3_data.get('Date', {}).get('confidence', 0.0) if isinstance(step3_data.get('Date'), dict) else 0.0
                    ),
                    'amount_confidence': (
                        step3_data.get('total_amount', {}).get('confidence', 0.0) if isinstance(step3_data.get('total_amount'), dict) else 0.0
                    ) or (
                        step3_data.get('Amount', {}).get('confidence', 0.0) if isinstance(step3_data.get('Amount'), dict) else 0.0
                    ),
                    'quantity_confidence': (
                        step3_data.get('total_quantity', {}).get('confidence', 0.0) if isinstance(step3_data.get('total_quantity'), dict) else 0.0
                    ) or (
                        step3_data.get('Quantity', {}).get('confidence', 0.0) if isinstance(step3_data.get('Quantity'), dict) else 0.0
                    ),
                    'incoterms_confidence': (
                        step3_data.get('incoterms', {}).get('confidence', 0.0) if isinstance(step3_data.get('incoterms'), dict) else 0.0
                    ) or (
                        step3_data.get('Incoterms', {}).get('confidence', 0.0) if isinstance(step3_data.get('Incoterms'), dict) else 0.0
                    )
                },
                'bl_data': bl_data if bl_data else None
            }
            
            comparison_results.append(result)
        
        # Save auto comparison results
        auto_comparison_file = os.path.join(step3_dir, 'auto_comparison_results.json')
        with open(auto_comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_results, f, ensure_ascii=False, indent=2)
        
        # Calculate totals
        total_tokens = {
            'input': sum(usage['input'] for usage in api_usage.values()),
            'output': sum(usage['output'] for usage in api_usage.values())
        }
        
        status_summary = {
            'complete_match': sum(1 for r in comparison_results if r['auto_comparison']['status'] == 'complete_match'),
            'partial_error': sum(1 for r in comparison_results if r['auto_comparison']['status'] == 'partial_error'),
            'review_required': sum(1 for r in comparison_results if r['auto_comparison']['status'] == 'review_required')
        }
        
        # BL extraction summary
        bl_summary = {
            'total_bl_extracted': len([v for v in bl_data_map.values() if v]),
            'bl_numbers_extracted': sum(1 for v in bl_data_map.values() if v and v.get('bl_number'))
        }

        
        return jsonify({
            "status": "success",
            "extraction_results": {
                "total_documents": len(extraction_results) + len(bl_data_map),
                "invoices_extracted": len(extraction_results),
                "bls_extracted": len(bl_data_map)
            },
            "comparison_results": comparison_results,
            "api_usage": {
                "total_input_tokens": total_tokens['input'],
                "total_output_tokens": total_tokens['output'],
                "estimated_cost_krw": round((total_tokens['input'] / 1_000_000) * 0.075 * 1400 + 
                                           (total_tokens['output'] / 1_000_000) * 0.30 * 1400, 2),
                "by_document": api_usage
            },
            "summary": status_summary,
            "bl_summary": bl_summary
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@step3_integrated_bp.route('/api/projects/<project_id>/step3/update-field', methods=['POST'])
def update_field(project_id):
    """
    사용자 수기 수정 저장
    
    Request:
        {
            "billing_document": "94456995",
            "field": "amount",
            "value": 1234.56,
            "note": "OCR 오류 수정",
            "projectsDir": "Data/projects"
        }
    """
    try:
        data = request.json
        billing_doc = data.get('billing_document')
        field = data.get('field')
        value = data.get('value')
        note = data.get('note', '')
        projects_dir = data.get('projectsDir', 'Data/projects')
        
        if not all([billing_doc, field]):
            return jsonify({"error": "billing_document and field are required"}), 400
        
        project_path = os.path.join(projects_dir, project_id)
        step3_dir = os.path.join(project_path, 'step3_data_extraction')
        
        # Load auto comparison results
        auto_file = os.path.join(step3_dir, 'auto_comparison_results.json')
        if not os.path.exists(auto_file):
            return jsonify({"error": "No comparison results found"}), 404
        
        with open(auto_file, 'r', encoding='utf-8') as f:
            comparison_results = json.load(f)
        
        # Load or create final results
        final_file = os.path.join(step3_dir, 'final_comparison_results.json')
        if os.path.exists(final_file):
            with open(final_file, 'r', encoding='utf-8') as f:
                final_results = json.load(f)
        else:
            final_results = {}
        
        # Find and update the record
        for result in comparison_results:
            if result['billing_document'] == billing_doc:
                if billing_doc not in final_results:
                    final_results[billing_doc] = {
                        'auto_status': result['auto_comparison']['status'],
                        'user_corrections': {},
                        'final_status': result['auto_comparison']['status']
                    }
                
                # Add user correction
                original_value = result['ocr_data'].get(field, '')
                final_results[billing_doc]['user_corrections'][field] = {
                    'corrected_at': datetime.now().isoformat(),
                    'original_ocr': original_value,
                    'user_value': value,
                    'note': note
                }
                
                # Recalculate final status
                # Count how many fields match after correction
                # (Simplified - in production you'd rerun the comparison)
                final_results[billing_doc]['final_status'] = 'complete_match'  # Optimistic
                
                break
        
        # Save final results
        with open(final_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "status": "success",
            "message": "Field updated successfully"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@step3_integrated_bp.route('/api/projects/<project_id>/step3/send-to-dashboard', methods=['POST'])
def send_to_dashboard(project_id):
    """
    대사결과 확정하여 대시보드로 전송
    """
    try:
        data = request.json
        projects_dir = data.get('projectsDir', 'Data/projects')
        
        project_path = os.path.join(projects_dir, project_id)
        step3_dir = os.path.join(project_path, 'step3_data_extraction')
        
        # Load final comparison results (or auto if no corrections)
        final_file = os.path.join(step3_dir, 'final_comparison_results.json')
        auto_file = os.path.join(step3_dir, 'auto_comparison_results.json')
        
        if os.path.exists(final_file):
            with open(final_file, 'r', encoding='utf-8') as f:
                results_to_send = json.load(f)
        elif os.path.exists(auto_file):
            with open(auto_file, 'r', encoding='utf-8') as f:
                results_to_send = json.load(f)
        else:
            return jsonify({"error": "No comparison results found"}), 404
        
        # Save to dashboard data location
        dashboard_file = os.path.join(project_path, 'dashboard_data.json')
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            json.dump({
                'confirmed_at': datetime.now().isoformat(),
                'results': results_to_send
            }, f, ensure_ascii=False, indent=2)
        
        # Update Step 3 status to completed
        # (This would normally use StepManager, but for now just create a marker file)
        marker_file = os.path.join(step3_dir, 'step3_confirmed.json')
        with open(marker_file, 'w', encoding='utf-8') as f:
            json.dump({
                'confirmed_at': datetime.now().isoformat(),
                'status': 'completed'
            }, f, indent=2)
        
        return jsonify({
            "status": "success",
            "message": "Results sent to dashboard successfully"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@step3_integrated_bp.route('/api/projects/<project_id>/step3/extraction-data', methods=['GET'])
def get_extraction_data(project_id):
    """
    Step 3: 저장된 추출/비교 데이터 로드
    """
    try:
        # Use absolute path for projects directory
        project_root = os.path.dirname(BACKEND_DIR)
        projects_dir = os.path.join(project_root, 'Data', 'projects')
        
        project_path = os.path.join(projects_dir, project_id)
        step3_dir = os.path.join(project_path, 'step3_data_extraction')
        
        print(f"[DEBUG] get_extraction_data: Loading from {step3_dir}")
        
        # Load final comparison results (or auto if no corrections)
        final_file = os.path.join(step3_dir, 'final_comparison_results.json')
        auto_file = os.path.join(step3_dir, 'auto_comparison_results.json')
        
        results_data = {}
        if os.path.exists(final_file):
            print(f"[DEBUG] Found final_comparison_results.json")
            with open(final_file, 'r', encoding='utf-8') as f:
                results_data = json.load(f)
        elif os.path.exists(auto_file):
            print(f"[DEBUG] Found auto_comparison_results.json")
            with open(auto_file, 'r', encoding='utf-8') as f:
                results_data = json.load(f)
        else:
            print(f"[DEBUG] No results file found in {step3_dir}")

        
        response_data = []
        
        if isinstance(results_data, list):
            response_data = results_data
        elif isinstance(results_data, dict):
            # If we have final_results (dict), we need to merge it with auto_results (list).
            auto_results = []
            if os.path.exists(auto_file):
                with open(auto_file, 'r', encoding='utf-8') as f:
                    auto_results = json.load(f)
            
            # Merge
            for item in auto_results:
                billing_doc = item['billing_document']
                if billing_doc in results_data:
                    final_info = results_data[billing_doc]
                    # Update status and add corrections
                    item['auto_comparison']['status'] = final_info.get('final_status', item['auto_comparison']['status'])
                    item['user_corrections'] = final_info.get('user_corrections', {})
                response_data.append(item)
        else:
            response_data = []

        return jsonify({
            "status": "success",
            "data": response_data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
