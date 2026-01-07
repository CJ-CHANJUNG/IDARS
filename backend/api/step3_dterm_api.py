# -*- coding: utf-8 -*-
"""
D-Term Step 3 전용 API 엔드포인트
기존 sales_evidence 워크플로우와 완전히 분리된 독립 파일
"""

from flask import Blueprint, request, jsonify, current_app
import os
import json
import sys
from datetime import datetime
from pathlib import Path

# 이 파일의 위치를 기준으로 프로젝트 루트 찾기
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, BACKEND_DIR)

step3_dterm_bp = Blueprint('step3_dterm', __name__)

@step3_dterm_bp.route('/api/projects/<project_id>/step3/dterm/extract', methods=['POST'])
def extract_dterm_evidence(project_id):
    """
    D-Term 증빙 도착일 추출 및 검증 API
    """
    try:
        print(f"⚓ [D-TERM API] Received extraction request for project: {project_id}")
        data = request.json
        target_ids = data.get('target_ids', None)  # List of slip IDs to process
        
        project_root = os.path.dirname(BACKEND_DIR)
        projects_dir = os.path.join(project_root, 'Data', 'projects')
        project_path = os.path.join(projects_dir, project_id)
        step3_dir = os.path.join(project_path, 'step3_data_extraction')
        os.makedirs(step3_dir, exist_ok=True)
        
        # === 1. Load Step 1 Data (Robust Master List) ===
        step1_path = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
        if not os.path.exists(step1_path):
            step1_path = os.path.join(project_path, 'step1_entry_import', 'confirmed_data.csv')
        
        if not os.path.exists(step1_path):
            return jsonify({"error": "Step 1 data not found. Please confirm Step 1 first."}), 404
        
        import pandas as pd
        df = pd.read_csv(step1_path)
        step1_data = df.to_dict('records')
        
        # --- Robust Column Mapping (Same as GET endpoint) ---
        cols = df.columns.tolist()
        def find_col(keywords):
            for col in cols:
                for kw in keywords:
                    if kw.lower() in col.lower():
                        return col
            return None

        col_billing = find_col(['Billing No', 'Billing Document', 'Billing Doc', '전표번호']) or 'Billing Document'
        col_ata = find_col(['ATA Date', 'Actual Arrival Date', 'ATA', 'Arrival Date']) or 'ATA Date'
        col_eta = find_col(['ETA Date', 'ETA']) or 'ETA Date'
        col_billing_date = find_col(['Billing Date', '매출일']) or 'Billing Date'
        col_amount = find_col(['Amount', 'Net Value', '매출액', '금액']) or 'Amount'
        col_customer = find_col(['Customer Desc', 'Customer Name', 'Customer']) or 'Customer Desc.'
        
        col_curr = find_col(['Curr', 'Currency']) or 'Curr'
        col_amount_loc = find_col(['매출액(Loc)', 'Amount(Loc)', 'Local Amount']) or '매출액(Loc)'
        col_curr_loc = find_col(['Curr(Loc)', 'Local Curr']) or 'Curr(Loc)'

        # SAP Data Map 생성
        sap_data_map = {}
        for row in step1_data:
            sid = str(row.get(col_billing, ''))
            if not sid or sid == 'nan': continue
            
            def safe_str(val):
                if pd.isna(val) or str(val).lower() == 'nan': return ''
                return str(val)

            sap_data_map[sid] = {
                'ata_date': safe_str(row.get(col_ata, '')),
                'eta_date': safe_str(row.get(col_eta, '')),
                'billing_date': safe_str(row.get(col_billing_date, '')),
                'amount': safe_str(row.get(col_amount, '')),
                'curr': safe_str(row.get(col_curr, '')),
                'amount_loc': safe_str(row.get(col_amount_loc, '')),
                'curr_loc': safe_str(row.get(col_curr_loc, '')),
                
                'tc': safe_str(row.get('TC', '')),
                'so': safe_str(row.get('SO', '')),
                'invoice': safe_str(row.get('Invoice', '')),
                'customer_desc': safe_str(row.get(col_customer, '')),
                'hq': safe_str(row.get('본부', '')),
                'office': safe_str(row.get('실', '')),
                'group': safe_str(row.get('그룹', '')),
                'profit_center': safe_str(row.get('Profit Center', '')),
                'sales_person': safe_str(row.get('sales_person', row.get('Sales Person', ''))),
                'registrant': safe_str(row.get('등록자', ''))
            }
            
        print(f"[DEBUG] Loaded SAP data for {len(sap_data_map)} slips.")

        # === 2. Load Existing Results (Merge Base) ===
        result_file = os.path.join(step3_dir, 'dterm_comparison_results.json')
        existing_results_map = {}
        if os.path.exists(result_file):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    saved_results = json.load(f)
                    for r in saved_results:
                        existing_results_map[r['billing_document']] = r
                print(f"[DEBUG] Loaded {len(existing_results_map)} existing results for merging.")
            except Exception as e:
                print(f"[WARN] Failed to load existing results: {e}")

        # === 3. D-Term Extraction Engine Setup ===
        sys.path.append(os.path.join(BACKEND_DIR, '..', 'Modules', 'Parser'))
        from dterm_extraction_engine import DtermExtractionEngine
        
        engine = DtermExtractionEngine()
        
        # Evidence directory
        split_dir = os.path.join(project_path, 'step2_evidence_collection', 'dterm_downloads')
        if not os.path.exists(split_dir) or not os.listdir(split_dir):
            split_dir = os.path.join(project_path, 'step2_evidence_collection', 'split_documents')
            
        # Progress Tracking
        if 'extraction_progress' not in current_app.config:
            current_app.config['extraction_progress'] = {}
            
        current_app.config['extraction_progress'][project_id] = {
            "status": "running",
            "current": 0,
            "total": len(target_ids) if target_ids else 0,
            "message": "D-Term 추출 시작...",
            "doc_number": ""
        }

        def update_progress(current, total, doc_number, message):
            current_app.config['extraction_progress'][project_id].update({
                "current": current,
                "total": total,
                "doc_number": doc_number,
                "message": message
            })
            print(f"[D-TERM PROGRESS] {current}/{total} - {doc_number}: {message}")

        # === 4. Run Extraction (Async) ===
        import asyncio
        print(f"[DEBUG] Starting async D-Term extraction for {project_id}")
        
        try:
             # Pass generic map (engine might use it for context, though engine usually focuses on file)
             # Note: Engine's context map expects basic keys. Our sap_data_map is robust now.
             new_extraction_results = asyncio.run(engine.process_project_dterm_async(
                project_id, split_dir, target_ids, progress_callback=update_progress, context_map=sap_data_map
            ))
        except Exception as e:
            current_app.config['extraction_progress'][project_id]["status"] = "error"
            current_app.config['extraction_progress'][project_id]["message"] = str(e)
            raise e

        # === 5. Compare & Format & Merge Results ===
        
        for res in new_extraction_results:
            sid = res.get('slip_id')
            sap_info = sap_data_map.get(sid, {})
            
            sap_ata = sap_info.get('ata_date')
            evidence_arrival = res.get('arrival_date')
            
            status = 'review_required'
            diff_days = None
            
            # Date Comparison Logic
            if sap_ata and evidence_arrival:
                try:
                    def parse_date(d_str):
                        for fmt in ['%Y-%m-%d', '%Y.%m.%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S']:
                            try:
                                return datetime.strptime(str(d_str)[:10], fmt)
                            except:
                                pass
                        return None

                    d1 = parse_date(sap_ata)
                    d2 = parse_date(evidence_arrival)
                    
                    if d1 and d2:
                        diff = (d2 - d1).days
                        diff_days = diff
                        if diff == 0: status = 'match'
                        elif abs(diff) <= 3: status = 'review_required'
                        else: status = 'review_required'
                except Exception as e:
                    print(f"Date parsing error: {e}")
            
            # Construct Full Item Result
            merged_item = {
                'billing_document': sid,
                'file_name': res.get('file_name'),
                'document_type': res.get('document_type'),
                'arrival_date': evidence_arrival, 
                
                'verification_status': res.get('verification_status', 'Unidentified'),
                'matched_identifiers': res.get('matched_identifiers', []),
                'date_confidence': res.get('date_confidence', 0.0),
                
                # SAP Data (Preserved from Robust Map)
                'sap_ata_date': sap_info.get('ata_date'),          
                'sap_eta_date': sap_info.get('eta_date'),          
                'sap_billing_date': sap_info.get('billing_date'),  
                'sap_amount': sap_info.get('amount'),
                'sap_curr': sap_info.get('curr'),
                'sap_amount_loc': sap_info.get('amount_loc'),
                'sap_curr_loc': sap_info.get('curr_loc'),
                
                'tc': sap_info.get('tc'),
                'so': sap_info.get('so'),
                'customer_desc': sap_info.get('customer_desc'),
                'invoice': sap_info.get('invoice'),
                'hq': sap_info.get('hq'),
                'office': sap_info.get('office'),
                'group': sap_info.get('group'),
                'profit_center': sap_info.get('profit_center'),
                'sales_person': sap_info.get('sales_person'),
                'registrant': sap_info.get('registrant'),

                'diff_days': diff_days,
                'reasoning': res.get('reasoning'),
                'status': status,
                'evidence_text': res.get('evidence_text')
            }
            
            # Update Existing Map
            existing_results_map[sid] = merged_item
            
        # Convert Map back to List
        final_results_list = list(existing_results_map.values())

        # Save Merged Results
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(final_results_list, f, ensure_ascii=False, indent=2)
            
        # Complete
        current_app.config['extraction_progress'][project_id]["status"] = "completed"
        current_app.config['extraction_progress'][project_id]["message"] = "D-Term 검증 완료"
        
        return jsonify({
            "status": "success",
            "comparison_results": final_results_list,
            "summary": {
                "total": len(final_results_list),
                "match": sum(1 for r in final_results_list if r.get('status') == 'match')
            }
        })

    except Exception as e:
        print(f"[CRITICAL ERROR] D-Term extraction failed: {e}")
        return jsonify({"error": str(e)}), 500

@step3_dterm_bp.route('/api/projects/<project_id>/step3/dterm/results', methods=['GET'])
def get_dterm_results(project_id):
    """결과 조회 API (결과 없으면 Step 1 데이터 기반 초기 목록 반환)"""
    try:
        project_root = os.path.dirname(BACKEND_DIR)
        projects_dir = os.path.join(project_root, 'Data', 'projects')
        project_path = os.path.join(projects_dir, project_id)
        step3_dir = os.path.join(project_path, 'step3_data_extraction')
        result_file = os.path.join(step3_dir, 'dterm_comparison_results.json')
        
        # 1. Load existing extraction results (Map by Billing Document)
        extracted_map = {}
        if os.path.exists(result_file):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    saved_results = json.load(f)
                    for r in saved_results:
                        extracted_map[r['billing_document']] = r
                print(f"[DEBUG] Loaded {len(extracted_map)} existing extraction results")
            except Exception as e:
                print(f"[ERROR] Failed to load results file: {e}")

        # 2. Load Step 1 Confirmed Data (Master List)
        step1_path = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
        if not os.path.exists(step1_path):
            step1_path = os.path.join(project_path, 'step1_entry_import', 'confirmed_data.csv')
            
        final_results = []
        
        if os.path.exists(step1_path):
            import pandas as pd
            df = pd.read_csv(step1_path)
            step1_data = df.to_dict('records')
            
            # Prepare File List for Matching
            evidence_subpath = 'dterm_downloads'
            evidence_dir = os.path.join(project_path, 'step2_evidence_collection', evidence_subpath)
            if not os.path.exists(evidence_dir) or not os.listdir(evidence_dir):
                evidence_subpath = 'split_documents'
                evidence_dir = os.path.join(project_path, 'step2_evidence_collection', evidence_subpath)
            
            available_files = {}
            if os.path.exists(evidence_dir):
                for f in os.listdir(evidence_dir):
                    if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                        available_files[f] = f

                # SAP Data Map
                sap_map = {}
                
                # Dynamic Column finding
                cols = df.columns.tolist()
                print(f"[DEBUG] CSV Columns: {cols}")
                
                def find_col(keywords):
                    for col in cols:
                        for kw in keywords:
                            if kw.lower() in col.lower():
                                return col
                    return None

                col_billing = find_col(['Billing No', 'Billing Document', 'Billing Doc', '전표번호']) or 'Billing Document'
                col_ata = find_col(['ATA Date', 'Actual Arrival Date', 'ATA', 'Arrival Date']) or 'ATA Date'
                col_eta = find_col(['ETA Date', 'ETA']) or 'ETA Date'
                col_billing_date = find_col(['Billing Date', '매출일']) or 'Billing Date'
                col_amount = find_col(['Amount', 'Net Value', '매출액', '금액']) or 'Amount'
                col_customer = find_col(['Customer Desc', 'Customer Name', 'Customer']) or 'Customer Desc.'
                
                col_curr = find_col(['Curr', 'Currency']) or 'Curr'
                col_amount_loc = find_col(['매출액(Loc)', 'Amount(Loc)', 'Local Amount']) or '매출액(Loc)'
                col_curr_loc = find_col(['Curr(Loc)', 'Local Curr']) or 'Curr(Loc)'

                print(f"[DEBUG] Mapped Columns: Billing={col_billing}, Amount={col_amount}({col_curr}), LocAmount={col_amount_loc}({col_curr_loc})")

                # Iterate ALL Step 1 Items
                for row in step1_data:
                    # Billing No. Identification
                    sid = str(row.get(col_billing, ''))
                    if not sid or sid == 'nan': continue
                    
                    # Helper to safely get string value or empty string, handling NaN
                    def safe_str(val):
                        if pd.isna(val) or str(val).lower() == 'nan':
                            return ''
                        return str(val)

                    # Base Info from SAP (Step 1)
                    sap_info = {
                        'ata': safe_str(row.get(col_ata, '')),
                        'eta': safe_str(row.get(col_eta, '')),
                        'billing': safe_str(row.get(col_billing_date, '')),
                        
                        'amount': safe_str(row.get(col_amount, '')),
                        'curr': safe_str(row.get(col_curr, '')),
                        'amount_loc': safe_str(row.get(col_amount_loc, '')),
                        'curr_loc': safe_str(row.get(col_curr_loc, '')),
                        
                        'tc': safe_str(row.get('TC', '')),
                        'so': safe_str(row.get('SO', '')),
                        'invoice': safe_str(row.get('Invoice', '')),
                        'delivery': safe_str(row.get('Delivery', '')),
                        'customer_desc': safe_str(row.get(col_customer, '')),
                        'hq': safe_str(row.get('본부', '')),
                        'office': safe_str(row.get('실', '')),
                        'group': safe_str(row.get('그룹', '')),
                        'profit_center': safe_str(row.get('Profit Center', '')),
                        'sales_person': safe_str(row.get('sales_person', row.get('Sales Person', ''))),
                        'registrant': safe_str(row.get('등록자', ''))
                    }

                    # Construct Item Data
                    item = {
                        'billing_document': sid,
                        'sap_ata_date': sap_info['ata'] or None,
                        'sap_eta_date': sap_info['eta'] or None,
                        'sap_billing_date': sap_info['billing'] or None,
                        
                        'sap_amount': sap_info['amount'] or None,
                        'sap_curr': sap_info['curr'] or None,
                        'sap_amount_loc': sap_info['amount_loc'] or None,
                        'sap_curr_loc': sap_info['curr_loc'] or None,
                        
                        'tc': sap_info['tc'],
                        'so': sap_info['so'],
                        'customer_desc': sap_info['customer_desc'],
                        'invoice': sap_info['invoice'],
                        'hq': sap_info['hq'],
                        'office': sap_info['office'],
                        'group': sap_info['group'],
                        'profit_center': sap_info['profit_center'],
                        'sales_person': sap_info['sales_person'],
                        'registrant': sap_info['registrant'],
                    }


                    # Merge with Extracted Results OR File Info
                    if sid in extracted_map:
                        # Already Extracted
                        extracted = extracted_map[sid]
                        
                        fname = extracted.get('file_name')
                        fpath = None
                        if fname and fname in available_files:
                             fpath = f"step2_evidence_collection/{evidence_subpath}/{fname}"
                        
                        item.update({
                            'file_name': fname,
                            'file_path': fpath,
                            'document_type': extracted.get('document_type'),
                            'arrival_date': extracted.get('arrival_date'),
                            'verification_status': extracted.get('verification_status'),
                            'matched_identifiers': extracted.get('matched_identifiers', []),
                            'date_confidence': extracted.get('date_confidence', 0.0),
                            'diff_days': extracted.get('diff_days'),
                            'reasoning': extracted.get('reasoning'),
                            'status': extracted.get('status', 'match'), # Legacy status
                            'evidence_text': extracted.get('evidence_text')
                        })
                    else:
                        # Not Extracted Yet - Check for File
                        # Simple matching: check if SID matches any file start
                        # (Note: This simple check mimics the previous logic. The Engine does context matching, 
                        # but for initial display, we rely on filename or just show "File Missing")
                        matched_file = None
                        for f_name in available_files:
                            if sid in f_name:
                                matched_file = f_name
                                break
                        
                        if matched_file:
                            item.update({
                                'file_name': matched_file,
                                'file_path': f"step2_evidence_collection/{evidence_subpath}/{matched_file}",
                                'status': 'pending', # Ready for extraction
                                'verification_status': 'Ready',
                                'arrival_date': None,
                                'document_type': 'Unknown'
                            })
                        else:
                            item.update({
                                'file_name': '-',
                                'file_path': None,
                                'status': 'no_evidence',
                                'verification_status': 'No Evidence',
                                'arrival_date': None,
                                'document_type': '-'
                            })
                    
                    final_results.append(item)

        return jsonify({"results": final_results})
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
