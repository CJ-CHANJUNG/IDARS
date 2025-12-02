import os
import json
import shutil
import asyncio
from datetime import datetime
import pandas as pd
from Modules.Parser.smart_extraction_engine import SmartExtractionEngine

class StepManager:
    def __init__(self, projects_dir):
        self.projects_dir = projects_dir

    def get_project_path(self, project_id):
        return os.path.join(self.projects_dir, project_id)

    def get_metadata_path(self, project_id):
        return os.path.join(self.get_project_path(project_id), 'metadata.json')

    def load_metadata(self, project_id):
        path = self.get_metadata_path(project_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Metadata not found for project {project_id}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_metadata(self, project_id, metadata):
        path = self.get_metadata_path(project_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def initialize_project_structure(self, project_id, name):
        project_path = self.get_project_path(project_id)
        os.makedirs(project_path, exist_ok=True)
        
        # Create step directories
        steps_dirs = [
            'step1_invoice_confirmation',
            'step2_evidence_collection',
            'step3_data_extraction',
            'step4_reconciliation'
        ]
        
        for step_dir in steps_dirs:
            os.makedirs(os.path.join(project_path, step_dir), exist_ok=True)
            
        # Initialize metadata
        metadata = {
            "id": project_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "current_step": 0,
            "status": "new",
            "steps": {
                "step1": {
                    "status": "pending", # pending, in_progress, completed
                    "started_at": None,
                    "completed_at": None,
                    "data_path": "step1_invoice_confirmation/confirmed_invoices.csv"
                },
                "step2": {
                    "status": "locked", # locked until prev step done
                    "started_at": None,
                    "completed_at": None,
                    "data_path": "step2_evidence_collection/evidence_metadata.json"
                },
                "step3": {
                    "status": "locked",
                    "started_at": None,
                    "completed_at": None,
                    "data_path": "step3_data_extraction/extracted_data.json"
                },
                "step4": {
                    "status": "locked",
                    "started_at": None,
                    "completed_at": None,
                    "data_path": "step4_reconciliation/reconciliation_results.json"
                }
            }
        }
        self.save_metadata(project_id, metadata)
        return metadata

    def save_step1_draft(self, project_id, data, visible_columns=None):
        """Save working draft for Step 1"""
        metadata = self.load_metadata(project_id)
        
        # Check if Step 2 is already completed (Locking)
        if metadata['steps']['step2']['status'] == 'completed':
            raise Exception("Step 2가 이미 확정되었습니다. Step 1을 수정하려면 Step 2 확정을 취소해야 합니다.")
            
        project_path = self.get_project_path(project_id)
        draft_path = os.path.join(project_path, 'step1_invoice_confirmation', 'ledger.csv')
        
        if data:
            df = pd.DataFrame(data)
            df.to_csv(draft_path, index=False, encoding='utf-8-sig')
            
        metadata = self.load_metadata(project_id)
        metadata['updated_at'] = datetime.now().isoformat()
        if metadata['steps']['step1']['status'] == 'pending':
            metadata['steps']['step1']['status'] = 'in_progress'
            metadata['steps']['step1']['started_at'] = datetime.now().isoformat()
            
        if visible_columns:
            metadata['visibleColumns'] = visible_columns
            
        self.save_metadata(project_id, metadata)
        return metadata

    def confirm_step1(self, project_id, data, visible_columns=None):
        """Confirm Step 1 Data"""
        metadata = self.load_metadata(project_id)
        
        # Check if Step 2 is already completed (Locking)
        if metadata['steps']['step2']['status'] == 'completed':
            raise Exception("Step 2가 이미 확정되었습니다. Step 1을 수정하려면 Step 2 확정을 취소해야 합니다.")
            
        project_path = self.get_project_path(project_id)
        confirmed_path = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
        
        # Save confirmed data
        if data:
            df = pd.DataFrame(data)
            df.to_csv(confirmed_path, index=False, encoding='utf-8-sig')
            
        # Update Metadata
        metadata['updated_at'] = datetime.now().isoformat()
        
        # Step 1 Complete
        metadata['steps']['step1']['status'] = 'completed'
        metadata['steps']['step1']['completed_at'] = datetime.now().isoformat()
        
        # Step 2 Unlock (if not already)
        if metadata['steps']['step2']['status'] == 'locked':
            metadata['steps']['step2']['status'] = 'pending'
        
        metadata['current_step'] = 1
        if visible_columns:
            metadata['visibleColumns'] = visible_columns
            
        self.save_metadata(project_id, metadata)
        return metadata
    
    def confirm_step2(self, project_id, evidence_data):
        """Confirm Step 2 Evidence Collection"""
        metadata = self.load_metadata(project_id)
        
        # Check if Step 3 is already completed (Future Locking)
        if metadata['steps']['step3']['status'] == 'completed':
            raise Exception("Step 3가 이미 확정되었습니다. Step 2를 수정하려면 Step 3 확정을 취소해야 합니다.")

        project_path = self.get_project_path(project_id)
        evidence_path = os.path.join(project_path, 'step2_evidence_collection', 'evidence_mapping.json')
        
        # Save evidence mapping
        with open(evidence_path, 'w', encoding='utf-8') as f:
            json.dump(evidence_data, f, ensure_ascii=False, indent=2)
        
        # Update Metadata
        metadata['updated_at'] = datetime.now().isoformat()
        
        # Step 2 Complete
        metadata['steps']['step2']['status'] = 'completed'
        metadata['steps']['step2']['completed_at'] = datetime.now().isoformat()
        
        # Step 3 Unlock
        if metadata['steps']['step3']['status'] == 'locked':
            metadata['steps']['step3']['status'] = 'pending'
        
        metadata['current_step'] = 2
        
        self.save_metadata(project_id, metadata)
        return metadata

    def confirm_step3(self, project_id, extraction_data):
        """Confirm Step 3 Data Extraction"""
        metadata = self.load_metadata(project_id)
        
        # Check if Step 4 is already completed (Future Locking)
        if metadata['steps']['step4']['status'] == 'completed':
            raise Exception("Step 4가 이미 확정되었습니다. Step 3를 수정하려면 Step 4 확정을 취소해야 합니다.")

        project_path = self.get_project_path(project_id)
        # Save confirmed data to the path defined in metadata
        confirmed_path = os.path.join(project_path, 'step3_data_extraction', 'extracted_data.json')
        
        # Save extraction data
        with open(confirmed_path, 'w', encoding='utf-8') as f:
            json.dump(extraction_data, f, ensure_ascii=False, indent=2)
        
        # Update Metadata
        metadata['updated_at'] = datetime.now().isoformat()
        
        # Step 3 Complete
        metadata['steps']['step3']['status'] = 'completed'
        metadata['steps']['step3']['completed_at'] = datetime.now().isoformat()
        
        # Step 4 Unlock
        if metadata['steps']['step4']['status'] == 'locked':
            metadata['steps']['step4']['status'] = 'pending'
        
        metadata['current_step'] = 3
        
        self.save_metadata(project_id, metadata)
        return metadata

    def confirm_step4(self, project_id, reconciliation_data):
        """Confirm Step 4 Reconciliation Results"""
        metadata = self.load_metadata(project_id)
        
        project_path = self.get_project_path(project_id)
        confirmed_path = os.path.join(project_path, 'step4_reconciliation', 'reconciliation_results.json')
        
        # Save reconciliation results
        with open(confirmed_path, 'w', encoding='utf-8') as f:
            json.dump(reconciliation_data, f, ensure_ascii=False, indent=2)
        
        # Update Metadata
        metadata['updated_at'] = datetime.now().isoformat()
        
        # Step 4 Complete
        metadata['steps']['step4']['status'] = 'completed'
        metadata['steps']['step4']['completed_at'] = datetime.now().isoformat()
        
        # Mark project as completed
        metadata['current_step'] = 4
        metadata['status'] = 'completed'
        
        self.save_metadata(project_id, metadata)
        return metadata

    def unconfirm_step(self, project_id, step_number):
        """Unconfirm a step (Cancel Confirmation)"""
        metadata = self.load_metadata(project_id)
        
        if step_number == 1:
            # Step 1 Unconfirm
            # Check if Step 2 is completed
            if metadata['steps']['step2']['status'] == 'completed':
                raise Exception("Step 2가 확정된 상태에서는 Step 1 확정을 취소할 수 없습니다. 먼저 Step 2 확정을 취소하세요.")
            
            metadata['steps']['step1']['status'] = 'pending'
            metadata['steps']['step1']['completed_at'] = None
            metadata['current_step'] = 0
            
        elif step_number == 2:
            # Step 2 Unconfirm
            if metadata['steps']['step3']['status'] == 'completed':
                raise Exception("Step 3가 확정된 상태에서는 Step 2 확정을 취소할 수 없습니다. 먼저 Step 3 확정을 취소하세요.")
                
            metadata['steps']['step2']['status'] = 'pending'
            metadata['steps']['step2']['completed_at'] = None
            metadata['current_step'] = 1
            # Optional: Remove evidence_mapping.json? No, keep it as draft.
            
        elif step_number == 3:
            # Step 3 Unconfirm
            if metadata['steps']['step4']['status'] == 'completed':
                raise Exception("Step 4가 확정된 상태에서는 Step 3 확정을 취소할 수 없습니다. 먼저 Step 4 확정을 취소하세요.")
                
            metadata['steps']['step3']['status'] = 'pending'
            metadata['steps']['step3']['completed_at'] = None
            metadata['current_step'] = 2
            # Keep extracted_data.json as draft
            
        elif step_number == 4:
            # Step 4 Unconfirm (No dependency check needed - it's the last step)
            metadata['steps']['step4']['status'] = 'pending'
            metadata['steps']['step4']['completed_at'] = None
            metadata['current_step'] = 3
            # Keep reconciliation_results.json as draft
            
        metadata['updated_at'] = datetime.now().isoformat()
        self.save_metadata(project_id, metadata)
        return metadata

    def update_step2_status(self, project_id, status_updates):
        """Update Step 2 Evidence Status (e.g., after download)"""
        project_path = self.get_project_path(project_id)
        status_path = os.path.join(project_path, 'step2_evidence_collection', 'evidence_status.json')
        
        current_status = {}
        if os.path.exists(status_path):
            try:
                with open(status_path, 'r', encoding='utf-8') as f:
                    current_status = json.load(f)
            except:
                pass
        
        # Update status
        for doc_num, info in status_updates.items():
            current_status[doc_num] = info
            
        # Save status
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(current_status, f, ensure_ascii=False, indent=2)
            
        return current_status

    def _sync_evidence_status(self, project_id):
        """Sync evidence status with actual files in DMS folder"""
        project_path = self.get_project_path(project_id)
        status_path = os.path.join(project_path, 'step2_evidence_collection', 'evidence_status.json')
        dms_dir = os.path.join(project_path, 'step2_evidence_collection', 'DMS_Downloads', 'Billing')
        
        current_status = {}
        if os.path.exists(status_path):
            try:
                with open(status_path, 'r', encoding='utf-8') as f:
                    current_status = json.load(f)
            except:
                pass
        
        updated = False
        
        # 1. 실제 파일 스캔하여 추가
        if os.path.exists(dms_dir):
            for filename in os.listdir(dms_dir):
                if filename.lower().endswith('.pdf'):
                    # 파일명 형식: {doc_number}_{original_name}
                    parts = filename.split('_', 1)
                    if len(parts) >= 1:
                        doc_num = parts[0]
                        if doc_num not in current_status:
                            current_status[doc_num] = {
                                "status": "collected",
                                "downloaded_at": datetime.now().isoformat(), # Approximate
                                "files": [filename]
                            }
                            updated = True
                        else:
                            # 이미 존재하지만 파일 목록에 없으면 추가
                            if 'files' not in current_status[doc_num]:
                                current_status[doc_num]['files'] = []
                            if filename not in current_status[doc_num]['files']:
                                current_status[doc_num]['files'].append(filename)
                                updated = True
        
        # 2. JSON에는 있지만 실제 파일이 없는 경우 제거 (동기화)
        docs_to_remove = []
        for doc_num, info in current_status.items():
            files = info.get('files', [])
            if not files:
                docs_to_remove.append(doc_num)
                continue
                
            # 파일들이 실제로 존재하는지 확인
            existing_files = []
            for f_name in files:
                if os.path.exists(os.path.join(dms_dir, f_name)):
                    existing_files.append(f_name)
            
            if not existing_files:
                docs_to_remove.append(doc_num)
            elif len(existing_files) != len(files):
                current_status[doc_num]['files'] = existing_files
                updated = True
        
        for doc_num in docs_to_remove:
            del current_status[doc_num]
            updated = True
        
        if updated:
            with open(status_path, 'w', encoding='utf-8') as f:
                json.dump(current_status, f, ensure_ascii=False, indent=2)
                
        return current_status

    def get_step1_data(self, project_id):
        project_path = self.get_project_path(project_id)
        draft_path = os.path.join(project_path, 'step1_invoice_confirmation', 'ledger.csv')
        confirmed_path = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
        
        draft_data = []
        confirmed_data = []
        
        if os.path.exists(draft_path):
            df = pd.read_csv(draft_path)
            df = df.fillna('')
            draft_data = df.to_dict(orient='records')
            
        if os.path.exists(confirmed_path):
            df = pd.read_csv(confirmed_path)
            df = df.fillna('')
            confirmed_data = df.to_dict(orient='records')
            
            # Sync and merge evidence status
            evidence_status = self._sync_evidence_status(project_id)
            
            # Find billing column
            billing_col = None
            if confirmed_data:
                first_row = confirmed_data[0]
                priority_names = ['Billing Document', 'BillingDocument', '전표번호', 'Document Number', 'Invoice Number']
                for name in priority_names:
                    if name in first_row:
                        billing_col = name
                        break
                if not billing_col:
                    for col in first_row.keys():
                        lower_col = col.lower()
                        if 'billing' in lower_col and 'date' not in lower_col and '일자' not in lower_col:
                            billing_col = col
                            break
            
            if billing_col:
                for row in confirmed_data:
                    doc_num = str(row.get(billing_col, '')).strip()
                    if doc_num in evidence_status:
                        row['evidence_status'] = evidence_status[doc_num]
                    else:
                        row['evidence_status'] = {'status': 'pending'}
            
        return draft_data, confirmed_data

    def get_mother_workspace_data(self, project_id):
        """Get comprehensive mother workspace data with summaries for all steps"""
        metadata = self.load_metadata(project_id)
        
        summary = {
            "project": metadata,
            "step1_summary": None,
            "step2_summary": None,
            "step3_summary": None,
            "step4_summary": None
        }
        
        project_path = self.get_project_path(project_id)
        
        # Step 1 Summary: Invoice/Ledger Data
        if metadata['steps']['step1']['status'] == 'completed':
            try:
                _, confirmed_data = self.get_step1_data(project_id)
                total_amount = 0
                
                # Try to find amount column
                if confirmed_data:
                    first_row = confirmed_data[0]
                    amount_col = None
                    for col in ['Net Value', 'Amount', 'Total Amount', '금액', 'Net amount']:
                        if col in first_row:
                            amount_col = col
                            break
                    
                    if amount_col:
                        for row in confirmed_data:
                            try:
                                val = str(row.get(amount_col, '0')).replace(',', '').strip()
                                if val and val != '':
                                    total_amount += float(val)
                            except (ValueError, TypeError):
                                pass
                
                summary['step1_summary'] = {
                    "invoice_count": len(confirmed_data),
                    "total_amount": total_amount
                }
            except Exception as e:
                print(f"Error calculating Step 1 summary: {e}")
                summary['step1_summary'] = {"invoice_count": 0, "total_amount": 0}
        
        # Step 2 Summary: Evidence Collection
        if metadata['steps']['step2']['status'] == 'completed':
            try:
                evidence_dir = os.path.join(project_path, 'step2_evidence_collection')
                split_dir = os.path.join(evidence_dir, 'split_documents')
                
                total_docs = 0
                collected_docs = 0
                doc_types = {}
                
                if os.path.exists(split_dir):
                    for billing_doc in os.listdir(split_dir):
                        doc_path = os.path.join(split_dir, billing_doc)
                        if os.path.isdir(doc_path):
                            total_docs += 1
                            
                            # Check for files in new structure (extraction_targets, others) or old structure
                            has_files = False
                            for subfolder in ['extraction_targets', 'others']:
                                subfolder_path = os.path.join(doc_path, subfolder)
                                if os.path.exists(subfolder_path):
                                    files = [f for f in os.listdir(subfolder_path) if f.lower().endswith('.pdf')]
                                    if files:
                                        has_files = True
                                        for f in files:
                                            # Count document types
                                            doc_type = self._get_doc_type_from_filename(f)
                                            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                            
                            # Fallback to old structure
                            if not has_files:
                                files = [f for f in os.listdir(doc_path) if f.lower().endswith('.pdf')]
                                if files:
                                    has_files = True
                                    for f in files:
                                        doc_type = self._get_doc_type_from_filename(f)
                                        doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                            
                            if has_files:
                                collected_docs += 1
                
                collection_rate = (collected_docs / total_docs * 100) if total_docs > 0 else 0
                
                summary['step2_summary'] = {
                    "total_documents": total_docs,
                    "collected_documents": collected_docs,
                    "collection_rate": round(collection_rate, 1),
                    "document_types": doc_types
                }
            except Exception as e:
                print(f"Error calculating Step 2 summary: {e}")
                summary['step2_summary'] = {"total_documents": 0, "collected_documents": 0, "collection_rate": 0}
        
        # Step 3 Summary: Data Extraction
        if metadata['steps']['step3']['status'] == 'completed':
            try:
                extraction_data = self.get_step3_extraction_data(project_id)
                
                total_fields = 0
                high_confidence_fields = 0
                
                if isinstance(extraction_data, list):
                    for doc in extraction_data:
                        if 'extracted_fields' in doc:
                            for field_name, field_data in doc['extracted_fields'].items():
                                total_fields += 1
                                confidence = field_data.get('confidence', 0)
                                if confidence >= 0.8:
                                    high_confidence_fields += 1
                
                avg_accuracy = (high_confidence_fields / total_fields * 100) if total_fields > 0 else 0
                low_confidence_count = total_fields - high_confidence_fields
                
                summary['step3_summary'] = {
                    "extracted_documents": len(extraction_data) if isinstance(extraction_data, list) else 0,
                    "total_fields": total_fields,
                    "avg_accuracy": round(avg_accuracy, 1),
                    "low_confidence_count": low_confidence_count
                }
            except Exception as e:
                print(f"Error calculating Step 3 summary: {e}")
                summary['step3_summary'] = {"extracted_documents": 0, "avg_accuracy": 0}
        
        # Step 4 Summary: Reconciliation
        if metadata['steps']['step4']['status'] == 'completed':
            try:
                recon_path = os.path.join(project_path, 'step4_reconciliation', 'reconciliation_results.json')
                if os.path.exists(recon_path):
                    with open(recon_path, 'r', encoding='utf-8') as f:
                        recon_data = json.load(f)
                    
                    matched = recon_data.get('matched', 0)
                    unmatched = recon_data.get('unmatched', 0)
                    needs_review = recon_data.get('needs_review', 0)
                    total = matched + unmatched + needs_review
                    
                    match_rate = (matched / total * 100) if total > 0 else 0
                    
                    summary['step4_summary'] = {
                        "total_items": total,
                        "matched": matched,
                        "unmatched": unmatched,
                        "needs_review": needs_review,
                        "match_rate": round(match_rate, 1)
                    }
            except Exception as e:
                print(f"Error calculating Step 4 summary: {e}")
                summary['step4_summary'] = {"total_items": 0, "match_rate": 0}
        
        return summary
    
    def _get_doc_type_from_filename(self, filename):
        """Helper to extract document type from filename"""
        lower_name = filename.lower()
        
        if 'bill_of_lading' in lower_name or 'b_l' in lower_name:
            return 'Bill of Lading'
        if 'commercial_invoice' in lower_name or 'invoice' in lower_name:
            return 'Invoice'
        if 'packing_list' in lower_name or 'packing' in lower_name:
            return 'Packing List'
        if 'certificate_origin' in lower_name:
            return 'Certificate of Origin'
        if 'weight' in lower_name:
            return 'Weight List'
        if 'mill' in lower_name:
            return 'Mill Certificate'
        
        return 'Other'

    def run_step3_extraction(self, project_id, selected_fields=None):
        """
        Run Step 3: Smart Extraction Engine
        """
        print(f"🚀 Step 3 Extraction Started: {project_id}")
        metadata = self.load_metadata(project_id)
        
        # Check prerequisites (Step 2 completed?)
        # if metadata['steps']['step2']['status'] != 'completed':
        #     raise Exception("Step 2가 완료되지 않았습니다.")
            
        project_path = self.get_project_path(project_id)
        split_dir = os.path.join(project_path, 'step2_evidence_collection', 'split_documents')
        output_dir = os.path.join(project_path, 'step3_data_extraction')
        os.makedirs(output_dir, exist_ok=True)
        
        # Update status to in_progress
        metadata['steps']['step3']['status'] = 'in_progress'
        metadata['steps']['step3']['started_at'] = datetime.now().isoformat()
        self.save_metadata(project_id, metadata)
        
        try:
            # Initialize Engine
            engine = SmartExtractionEngine()
            
            # Run Async Extraction (Synchronously wait for it in this thread)
            # In production, this should be offloaded to a background worker (Celery/Redis Queue)
            results = asyncio.run(engine.process_project_pdfs_async(project_id, split_dir, selected_fields))
            
            # Save Results
            output_file = os.path.join(output_dir, 'extracted_data.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            # Update Metadata to Completed
            metadata['steps']['step3']['status'] = 'completed'
            metadata['steps']['step3']['completed_at'] = datetime.now().isoformat()
            
            # Unlock Step 4
            if metadata['steps']['step4']['status'] == 'locked':
                metadata['steps']['step4']['status'] = 'pending'
                
            self.save_metadata(project_id, metadata)
            
            return "task_completed"
            
        except Exception as e:
            print(f"❌ Extraction Failed: {e}")
            metadata['steps']['step3']['status'] = 'failed'
            self.save_metadata(project_id, metadata)
            raise e

    def get_step3_extraction_data(self, project_id):
        """
        Get Step 3 Extracted Data
        """
        project_path = self.get_project_path(project_id)
        data_path = os.path.join(project_path, 'step3_data_extraction', 'extracted_data.json')
        
        if not os.path.exists(data_path):
            return []
            
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
