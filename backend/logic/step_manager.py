import os
import json
import shutil
from datetime import datetime
import pandas as pd

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
            # Step 2 should technically be locked or pending? 
            # If Step 1 is pending, Step 2 cannot be worked on? 
            # Usually Step 2 depends on Step 1. So Step 2 should be locked or reset.
            # But user might want to just edit Step 1 and re-confirm.
            # Let's keep Step 2 as is, but maybe 'locked' if strict dependency.
            # For now, just set Step 1 to pending.
            
        elif step_number == 2:
            # Step 2 Unconfirm
            if metadata['steps']['step3']['status'] == 'completed':
                raise Exception("Step 3가 확정된 상태에서는 Step 2 확정을 취소할 수 없습니다.")
                
            metadata['steps']['step2']['status'] = 'pending'
            metadata['steps']['step2']['completed_at'] = None
            # Optional: Remove evidence_mapping.json? No, keep it as draft.
            
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
        metadata = self.load_metadata(project_id)
        
        summary = {
            "project": metadata,
            "step1_summary": None,
            "step2_summary": None,
            "step3_summary": None,
            "step4_summary": None
        }
        
        # Calculate summaries if steps are completed
        if metadata['steps']['step1']['status'] == 'completed':
            _, confirmed_data = self.get_step1_data(project_id)
            summary['step1_summary'] = {
                "count": len(confirmed_data),
                # Add more stats like total amount if column known
            }
            
        # Add logic for other steps as they are implemented
        
        return summary
