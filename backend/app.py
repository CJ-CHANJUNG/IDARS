from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path
from flask_cors import CORS
from threading import Timer
import webbrowser
import pandas as pd
from datetime import datetime
import re
import shutil
import json
import os
import sys

# Add project root to sys.path to allow importing Modules
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

from logic.step_manager import StepManager
from logic.reconciliation import ReconciliationManager

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')

app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path='')
CORS(app)

# Register API blueprints (AFTER app creation)
from api.step3_integrated_api import step3_integrated_bp
app.register_blueprint(step3_integrated_bp)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'Data', 'raw')
# Ensure DATA_DIR exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

# Project Data Directory
PROJECTS_DIR = os.path.join(BASE_DIR, 'Data', 'projects')
if not os.path.exists(PROJECTS_DIR):
    os.makedirs(PROJECTS_DIR, exist_ok=True)

# Initialize StepManager
step_manager = StepManager(PROJECTS_DIR)
reconciliation_manager = ReconciliationManager()

# Global storage for async operation progress
download_progress = {}
split_progress = {}
extraction_progress = {}  # Step 3 추출 진행률

@app.route('/')
def serve():
    return app.send_static_file('index.html')

@app.errorhandler(404)
def not_found(e):
    return app.send_static_file('index.html')

def sanitize_filename(name):
    # Remove invalid characters for filenames
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")

@app.route('/api/projects', methods=['GET'])
def get_projects():
    projects = []
    if os.path.exists(PROJECTS_DIR):
        for dirname in os.listdir(PROJECTS_DIR):
            meta_path = os.path.join(PROJECTS_DIR, dirname, 'metadata.json')
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                        # Ensure ID matches dirname (for legacy or manual changes)
                        if meta.get('id') != dirname:
                            meta['id'] = dirname
                        projects.append(meta)
                except:
                    continue
    # Sort by created_at desc
    projects.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    name = data.get('name', 'Untitled Project')
    
    # Generate ID: Name_YYYYMMDD_HHMMSS
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sanitized_name = sanitize_filename(name)
    project_id = f"{sanitized_name}_{timestamp}"
    
    try:
        metadata = step_manager.initialize_project_structure(project_id, name)
        return jsonify(metadata)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/save', methods=['POST'])
def save_project(project_id):
    try:
        data = request.json
        ledger_data = data.get('ledgerData', [])
        visible_columns = data.get('visibleColumns')
        
        # Currently only supporting saving to Step 1 draft
        metadata = step_manager.save_step1_draft(project_id, ledger_data, visible_columns)
        
        return jsonify({"status": "success", "message": "Project saved", "metadata": metadata})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/confirm', methods=['POST'])
def confirm_project(project_id):
    try:
        data = request.json
        ledger_data = data.get('ledgerData', [])
        visible_columns = data.get('visibleColumns')
        
        # Currently only supporting confirming Step 1
        metadata = step_manager.confirm_step1(project_id, ledger_data, visible_columns)
        
        return jsonify({"status": "success", "message": "Project confirmed", "metadata": metadata})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/unconfirm', methods=['POST'])
def unconfirm_project(project_id):
    try:
        data = request.json
        step_number = data.get('step')
        
        if not step_number:
            return jsonify({"error": "Step number required"}), 400
            
        metadata = step_manager.unconfirm_step(project_id, int(step_number))
        
        return jsonify({"status": "success", "message": f"Step {step_number} unconfirmed", "metadata": metadata})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/load', methods=['GET'])
def load_project(project_id):
    try:
        metadata = step_manager.load_metadata(project_id)
        ledger_data, confirmed_data = step_manager.get_step1_data(project_id)
            
        return jsonify({
            "metadata": metadata, 
            "ledgerData": ledger_data, 
            "confirmedData": confirmed_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/mother-workspace', methods=['GET'])
def get_mother_workspace(project_id):
    try:
        summary = step_manager.get_mother_workspace_data(project_id)
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    
    if not os.path.exists(project_dir):
        return jsonify({"error": "Project not found"}), 404
    
    try:
        shutil.rmtree(project_dir)
        return jsonify({"status": "success", "message": "Project deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    project_id = request.form.get('projectId')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        try:
            # Read the file directly into pandas with encoding detection for CSV
            filename = file.filename.lower()
            if filename.endswith('.csv'):
                try:
                    df = pd.read_csv(file, encoding='utf-8')
                except UnicodeDecodeError:
                    file.seek(0)
                    try:
                        df = pd.read_csv(file, encoding='cp949')
                    except UnicodeDecodeError:
                        file.seek(0)
                        df = pd.read_csv(file, encoding='euc-kr')
            elif filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                return jsonify({"error": "Unsupported file type"}), 400
            
            # Replace NaN with empty string to avoid JSON serialization errors (NaN)
            df = df.fillna('')
            data = df.to_dict(orient='records')

            # Save to project directory if projectId is provided
            if project_id:
                # Use StepManager to save draft
                step_manager.save_step1_draft(project_id, data)

            return jsonify(data)
        except Exception as e:
            print(f"Upload error: {str(e)}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/sap/download', methods=['POST'])
def run_sap_downloader():
    data = request.json
    project_id = data.get('projectId')
    date_from = data.get('dateFrom')
    date_to = data.get('dateTo')

    print(f"Received SAP download request: Project={project_id}, From={date_from}, To={date_to}")

    if not project_id or not date_from or not date_to:
        return jsonify({"error": "Missing parameters"}), 400

    project_dir = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "Project not found"}), 404

    # Format dates for the script (YYYY.MM.DD)
    try:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').strftime('%Y.%m.%d')
        end_date = datetime.strptime(date_to, '%Y-%m-%d').strftime('%Y.%m.%d')
    except ValueError:
         return jsonify({"error": "Invalid date format"}), 400

    script_path = os.path.join(BASE_DIR, 'Modules', 'List_Downloader', 'zsdr0580_downloader.py')
    
    # Run the script
    cmd = [sys.executable, script_path, '--start_date', start_date, '--end_date', end_date, '--output_dir', project_dir]
    print(f"Executing command: {cmd}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
        if result.returncode != 0:
             return jsonify({"error": f"Script failed: {result.stderr}"}), 500
            
        # Check if file was created (logic to find file in project_dir)
        # Note: The script likely outputs to project_dir. We need to find it and move/save it as ledger.csv in step1
        
        # Find the latest file in project_dir that matches pattern
        # For simplicity, let's assume the script outputs to project_dir root, and we move it to step1
        
        start_short = start_date[2:4] + start_date[5:7] + start_date[8:10]
        end_short = end_date[2:4] + end_date[5:7] + end_date[8:10]
        expected_filename_xlsx = f"Billing List_{start_short}~{end_short}.XLSX"
        expected_path_xlsx = os.path.join(project_dir, expected_filename_xlsx)
        
        expected_filename_csv = f"Billing List_{start_short}~{end_short}.csv"
        expected_path_csv = os.path.join(project_dir, expected_filename_csv)
        
        df = None

        if os.path.exists(expected_path_xlsx):
            df = pd.read_excel(expected_path_xlsx)
        elif os.path.exists(expected_path_csv):
            df = pd.read_csv(expected_path_csv)
        
        if df is not None:
            df = df.fillna('')
            data = df.to_dict(orient='records')
            # Save using StepManager
            step_manager.save_step1_draft(project_id, data)
            return jsonify(data)
        else:
             return jsonify({"error": "Output file not found"}), 500

    except Exception as e:
        return jsonify({"error": f"Execution failed: {str(e)}"}), 500

@app.route('/api/projects/<project_id>/dms-download', methods=['POST'])
def download_dms_documents(project_id):
    """DMS 증빙 다운로드"""
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    if not os.path.exists(project_dir):
        return jsonify({"error": "Project not found"}), 404
    
    # Use StepManager to get confirmed data path
    # Or just use the known path
    confirmed_path = os.path.join(project_dir, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
    
    if not os.path.exists(confirmed_path):
        return jsonify({"error": "Confirmed data not found. Please confirm data first."}), 404
    
    try:
        # Confirmed data 로드
        df = pd.read_csv(confirmed_path)
        print(f"[DMS] Loaded confirmed data: {len(df)} rows")
        
        # Check for target documents and force redownload option
        data = request.json or {}
        target_documents = data.get('targetDocuments')
        force_redownload = data.get('forceRedownload', False)  # Default to False (skip existing)
        
        print(f"[DMS] Received request - targetDocuments: {target_documents}, forceRedownload: {force_redownload}")
        
        doc_numbers = []
        
        if target_documents:
            doc_numbers = [str(d).strip() for d in target_documents]
            print(f"[DMS] Target download for {len(doc_numbers)} documents")
        else:
            # Billing Document 컬럼 찾기 (우선순위 적용)
            billing_col = None
            
            # 1. 정확한 이름 매칭 시도
            priority_names = ['Billing Document', 'BillingDocument', '전표번호', 'Document Number', 'Invoice Number']
            for name in priority_names:
                if name in df.columns:
                    billing_col = name
                    break
            
            # 2. 부분 일치 시도 (Date 제외)
        dms_dir = os.path.join(project_dir, 'step2_evidence_collection', 'DMS_Downloads')
        os.makedirs(dms_dir, exist_ok=True)
        
        # 백그라운드 스레드에서 다운로드 실행
        import threading
        
        # Initialize progress
        download_progress[project_id] = {
            "status": "running",
            "current": 0,
            "total": len(doc_numbers),
            "message": "Starting download...",
            "results": []
        }
        
        def download_task():
            try:
                # DMS 다운로더 import
                sys.path.insert(0, os.path.join(BASE_DIR, 'Modules', 'DMS_Downloader'))
                from dms_downloader_module import DMSDownloader
                
                print(f"[DMS] Starting download for {len(doc_numbers)} documents...")
                
                def progress_callback(current, total, doc_number, message):
                    download_progress[project_id].update({
                        "current": current,
                        "total": total,
                        "message": f"[{doc_number}] {message}" if doc_number else message
                    })
                
                # 다운로더 실행
                downloader = DMSDownloader(dms_dir, progress_callback)
                results = downloader.download_documents(doc_numbers, force_redownload=force_redownload)
                
                print(f"✓ DMS 다운로드 완료: {results}")
                
                # Update Step 2 Status (Evidence Collected)
                status_updates = {}
                if 'results' in results:
                    for res in results['results']:
                        # Process each result if needed (currently no operation)
                        pass
                
                # Mark as completed
                download_progress[project_id].update({
                    "status": "completed",
                    "current": len(doc_numbers),
                    "total": len(doc_numbers),
                    "message": f"Download complete. Success: {results.get('success', 0)}, Failed: {results.get('failed', 0)}",
                    "results": results
                })
                
            except Exception as e:
                import traceback
                error_msg = f"API Error: {str(e)}\n{traceback.format_exc()}"
                traceback.print_exc()
                try:
                    with open("dms_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [API_ERROR] {error_msg}\n")
                except:
                    pass
                
                # Mark as error
                download_progress[project_id].update({
                    "status": "error",
                    "message": str(e)
                })

        
        # Start the background thread
        thread = threading.Thread(target=download_task, daemon=True)
        thread.start()
        
        return jsonify({
            "status": "started",
            "message": "Download started in background",
            "project_id": project_id
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/dms/progress/<project_id>', methods=['GET'])
def get_dms_progress(project_id):
    """Get DMS download progress"""
    progress = download_progress.get(project_id)
    if not progress:
        return jsonify({"status": "not_found"}), 404
    return jsonify(progress)

@app.route('/api/dms/select-folder', methods=['POST'])
def select_download_folder():
    """Windows 탐색기로 폴더 선택"""
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))
        from folder_dialog import select_folder_dialog
        folder_path = select_folder_dialog()
        
        if folder_path:
            return jsonify({"status": "success", "folder_path": folder_path})
        else:
            return jsonify({"status": "cancelled"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dms/manual-download', methods=['POST'])
def manual_dms_download():
    """수동 전표번호 입력 DMS 다운로드"""
    data = request.json
    doc_numbers = data.get('docNumbers', [])
    custom_folder = data.get('customFolder')
    
    if not doc_numbers:
        return jsonify({"error": "No document numbers provided"}), 400
    
    try:
        # 저장 경로 결정
        if custom_folder:
            dms_dir = custom_folder
        else:
            dms_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'DMS_Downloads')
        
        os.makedirs(dms_dir, exist_ok=True)
        
        # DMS 다운로더 import
        sys.path.insert(0, os.path.join(BASE_DIR, 'Modules', 'DMS_Downloader'))
        from dms_downloader_module import DMSDownloader
        
        # 다운로더 실행
        downloader = DMSDownloader(dms_dir)
        results = downloader.download_documents(doc_numbers)
        
        return jsonify({
            "status": "success",
            "results": results,
            "download_path": dms_dir
        })
        
    except Exception as e:
        import traceback
        error_msg = f"Manual Download Error: {str(e)}\n{traceback.format_exc()}"
        traceback.print_exc()
        try:
            with open("dms_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] [MANUAL_ERROR] {error_msg}\n")
        except:
            pass
        return jsonify({"error": str(e)}), 500

@app.route('/api/pipeline/parse', methods=['POST'])
def run_parser():
    data = request.json
    return jsonify({"status": "started", "message": "Parsing started"})

@app.route('/api/projects/<project_id>/split-evidence', methods=['POST'])
def split_evidence(project_id):
    """Split PDFs in DMS_Downloads folder"""
    try:
        data = request.json or {}
        target_documents = data.get('targetDocuments')  # Optional list
        
        # Initialize progress
        split_progress[project_id] = {
            "status": "running",
            "current": 0,
            "total": 0,
            "message": "Starting split...",
            "results": []
        }
        
        # Run splitter in background thread
        import threading
        
        def split_task():
            try:
                from logic.pdf_splitter_api import split_evidence_pdfs
                
                print(f"[SPLIT] Starting PDF split for project {project_id}")
                if target_documents:
                    print(f"[SPLIT] Target documents: {target_documents}")
                
                # Progress callback to update split_progress dict
                def progress_callback(current, total, doc_number, message):
                    split_progress[project_id].update({
                        "current": current,
                        "total": total,
                        "message": f"[{doc_number}] {message}" if doc_number else message
                    })
                
                # Run the splitter (this will take time)
                result = split_evidence_pdfs(project_id, PROJECTS_DIR, target_documents, progress_callback)
                
                if 'error' in result:
                    split_progress[project_id].update({
                        "status": "error",
                        "message": result['error']
                    })
                else:
                    split_progress[project_id].update({
                        "status": "completed",
                        "message": "Split completed successfully",
                        "results": result
                    })
                    print(f"[SPLIT] ✅ Split completed: {result.get('files_processed', 0)} files processed")
                    
            except Exception as e:
                import traceback
                error_msg = f"Split error: {str(e)}\n{traceback.format_exc()}"
                print(error_msg)
                traceback.print_exc()
                split_progress[project_id].update({
                    "status": "error",
                    "message": str(e)
                })
        
        # Start background thread
        split_thread = threading.Thread(target=split_task, daemon=True)
        split_thread.start()
        
        return jsonify({
            "status": "started",
            "message": "PDF split started in background",
            "project_id": project_id
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/split/progress/<project_id>', methods=['GET'])
def get_split_progress(project_id):
    """Get PDF split progress"""
    progress = split_progress.get(project_id)
    if not progress:
        return jsonify({"status": "not_found"}), 404
    return jsonify(progress)



@app.route('/api/projects/<project_id>/confirm-step2', methods=['POST'])
def confirm_step2(project_id):
    """Confirm Step 2 evidence collection and move to Step 3"""
    try:
        data = request.json
        evidence_data = data.get('evidenceData', [])
        
        # Save evidence data and confirm Step 2
        metadata = step_manager.confirm_step2(project_id, evidence_data)
        
        return jsonify({
            "status": "success",
            "message": "Step 2 confirmed",
            "metadata": metadata
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/confirm-step4', methods=['POST'])
def confirm_step4(project_id):
    """Confirm Step 4 reconciliation results and complete project"""
    try:
        data = request.json
        reconciliation_data = data.get('reconciliationData', {})
        
        # Save reconciliation results and confirm Step 4
        metadata = step_manager.confirm_step4(project_id, reconciliation_data)
        
        return jsonify({
            "status": "success",
            "message": "Step 4 confirmed - Project completed!",
            "metadata": metadata
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/files/list', methods=['GET'])
def list_project_files(project_id):
    """List files in a specific project subdirectory"""
    subpath = request.args.get('path', '')
    try:
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        target_dir = os.path.join(project_dir, subpath)
        
        if not os.path.exists(target_dir):
            return jsonify([])
            
        files = []
        for f in os.listdir(target_dir):
            full_path = os.path.join(target_dir, f)
            if os.path.isfile(full_path):
                files.append(f)
                
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/evidence/search', methods=['GET'])
def search_evidence(project_id):
    """Search for evidence files for a specific billing document"""
    billing_doc = request.args.get('billingDocument')
    if not billing_doc:
        return jsonify({"error": "Billing document required"}), 400
        
    try:
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        evidence_dir = os.path.join(project_dir, 'step2_evidence_collection')
        
        results = []
        
        # 1. Check split_documents (Priority) - Support new folder structure
        split_dir = os.path.join(evidence_dir, 'split_documents', billing_doc)
        if os.path.exists(split_dir):
            # Check new subfolder structure first
            has_subfolders = False
            for subfolder in ['extraction_targets', 'others']:
                subfolder_path = os.path.join(split_dir, subfolder)
                if os.path.exists(subfolder_path) and os.path.isdir(subfolder_path):
                    has_subfolders = True
                    for f in os.listdir(subfolder_path):
                        if f.lower().endswith('.pdf'):
                            results.append({
                                "type": "split",
                                "filename": f,
                                "path": f"step2_evidence_collection/split_documents/{billing_doc}/{subfolder}/{f}"
                            })
            
            # Fallback: Check root folder for backward compatibility
            if not has_subfolders:
                for f in os.listdir(split_dir):
                    if f.lower().endswith('.pdf'):
                        results.append({
                            "type": "split",
                            "filename": f,
                            "path": f"step2_evidence_collection/split_documents/{billing_doc}/{f}"
                        })
        
        # 2. Check DMS_Downloads (Fallback) if no split files found (or always?)
        # User might want to see originals even if split exists. Let's return both.
        dms_dir = os.path.join(evidence_dir, 'DMS_Downloads')
        if os.path.exists(dms_dir):
            # Recursive search in DMS_Downloads for files starting with billing_doc
            for root, dirs, files in os.walk(dms_dir):
                for f in files:
                    if f.startswith(billing_doc) and f.lower().endswith('.pdf'):
                        # Calculate relative path from project root
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, project_dir)
                        # Ensure forward slashes for URL
                        rel_path = rel_path.replace('\\', '/')
                        results.append({
                            "type": "original",
                            "filename": f,
                            "path": rel_path
                        })
                        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/evidence/delete', methods=['DELETE'])
def delete_evidence(project_id):
    """Delete a specific evidence file"""
    try:
        data = request.json
        filepath = data.get('filepath')
        
        if not filepath:
            return jsonify({"error": "Filepath required"}), 400
            
        # Security check: Ensure path is within project directory
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        full_path = os.path.join(project_dir, filepath)
        
        # Normalize paths to check common prefix
        project_dir_abs = os.path.abspath(project_dir)
        full_path_abs = os.path.abspath(full_path)
        
        if not full_path_abs.startswith(project_dir_abs):
            return jsonify({"error": "Invalid file path"}), 403
            
        if os.path.exists(full_path_abs):
            os.remove(full_path_abs)
            return jsonify({"status": "success", "message": "File deleted"})
        else:
            return jsonify({"error": "File not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/evidence/status', methods=['GET'])
def get_evidence_status(project_id):
    """Get evidence status for all billing documents in the project"""
    try:
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        evidence_dir = os.path.join(project_dir, 'step2_evidence_collection')
        
        status_map = {}
        
        # Helper to map filename to type
        def get_doc_type(filename):
            lower_name = filename.lower()
            
            # Mapping based on pdf_splitter.py output conventions
            if 'bill_of_lading' in lower_name: return 'Bill_of_Lading'
            if 'commercial_invoice' in lower_name: return 'Commercial_Invoice'
            if 'packing_list' in lower_name: return 'Packing_List'
            if 'weight_list' in lower_name: return 'Weight_List'
            if 'mill_certificate' in lower_name: return 'Mill_Certificate'
            if 'cargo_insurance' in lower_name: return 'Cargo_Insurance'
            if 'certificate_origin' in lower_name: return 'Certificate_Origin'
            if 'customs_clearance_letter' in lower_name: return 'Customs_clearance_Letter'
            if 'delivery_note' in lower_name: return 'Delivery_Note'
            
            # Fallbacks for manual uploads or variations
            if 'b_l' in lower_name: return 'Bill_of_Lading'
            if 'invoice' in lower_name: return 'Commercial_Invoice'
            if 'packing' in lower_name: return 'Packing_List'
            
            return 'Other'

        # 1. Scan Split Documents - Support new folder structure
        # New structure: split_documents/{billing_doc}/extraction_targets/ and /others/
        # Old structure: split_documents/{billing_doc}/*.pdf (backward compatibility)
        split_base = os.path.join(evidence_dir, 'split_documents')
        if os.path.exists(split_base):
            for billing_doc in os.listdir(split_base):
                doc_path = os.path.join(split_base, billing_doc)
                if os.path.isdir(doc_path):
                    status_map[billing_doc] = status_map.get(billing_doc, {'split': False, 'original': False, 'types': []})
                    
                    # Check new subfolder structure first
                    has_subfolders = False
                    for subfolder in ['extraction_targets', 'others']:
                        subfolder_path = os.path.join(doc_path, subfolder)
                        if os.path.exists(subfolder_path) and os.path.isdir(subfolder_path):
                            has_subfolders = True
                            files = [f for f in os.listdir(subfolder_path) if f.lower().endswith('.pdf')]
                            if files:
                                status_map[billing_doc]['split'] = True
                                for f in files:
                                    doc_type = get_doc_type(f)
                                    if doc_type not in status_map[billing_doc]['types']:
                                        status_map[billing_doc]['types'].append(doc_type)
                                        print(f"[DEBUG] Found {doc_type} for {billing_doc}: {subfolder}/{f}")
                    
                    # Fallback: Check root folder for backward compatibility (old structure)
                    if not has_subfolders:
                        files = [f for f in os.listdir(doc_path) if f.lower().endswith('.pdf')]
                        if files:
                            status_map[billing_doc]['split'] = True
                            for f in files:
                                doc_type = get_doc_type(f)
                                if doc_type not in status_map[billing_doc]['types']:
                                    status_map[billing_doc]['types'].append(doc_type)
                                    print(f"[DEBUG] Found {doc_type} for {billing_doc}: {f} (old structure)")

        # 2. Scan DMS Downloads (Originals) - DO NOT classify types
        # Original files are just evidence existence indicators
        # Type classification happens ONLY after split
        dms_base = os.path.join(evidence_dir, 'DMS_Downloads')
        if os.path.exists(dms_base):
            print(f"[DEBUG] Scanning DMS directory: {dms_base}")
            for root, dirs, files in os.walk(dms_base):
                for f in files:
                    if f.lower().endswith('.pdf'):
                        # Try to extract billing document number from filename
                        # Common patterns: "94459275.pdf", "94459275_Document.pdf", "Billing/94459275.pdf"
                        billing_doc = None
                        
                        # Method 1: Split by _ and take first part
                        parts = f.replace('.pdf', '').split('_')
                        if parts and parts[0].isdigit():
                            billing_doc = parts[0]
                        # Method 2: Just the filename without extension if it's all digits
                        elif f.replace('.pdf', '').replace('.PDF', '').isdigit():
                            billing_doc = f.replace('.pdf', '').replace('.PDF', '')
                        
                        if billing_doc:
                            status_map[billing_doc] = status_map.get(billing_doc, {'split': False, 'original': False, 'types': []})
                            status_map[billing_doc]['original'] = True
                            # ✅ DO NOT classify doc type for originals - only for split files
                            print(f"[DEBUG] Found DMS file for {billing_doc}: {f}")
        
        print(f"[DEBUG] Evidence status for {len(status_map)} documents")
        return jsonify(status_map)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/files/<path:filepath>', methods=['GET'])
def serve_project_file(project_id, filepath):
    """Serve files from the project directory, optionally with highlighting"""
    try:
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        full_path = os.path.join(project_dir, filepath)
        
        if not os.path.exists(full_path):
            return jsonify({"error": "File not found"}), 404

        # Check for highlight query param: ?highlight=ymin,xmin,ymax,xmax
        highlight_param = request.args.get('highlight')
        
        if highlight_param and filepath.lower().endswith('.pdf'):
            try:
                import fitz  # PyMuPDF
                
                # Parse coordinates
                # Format: ymin,xmin,ymax,xmax (normalized 0-1000)
                coords = [float(x) for x in highlight_param.split(',')]
                if len(coords) == 4:
                    ymin, xmin, ymax, xmax = coords
                    
                    # Open PDF
                    doc = fitz.open(full_path)
                    page = doc[0]  # Assume first page for now, or pass page param
                    
                    # Get page dimensions
                    rect = page.rect
                    width = rect.width
                    height = rect.height
                    
                    # Convert normalized coordinates to PDF points
                    # Note: PDF coordinates usually start from bottom-left, but fitz uses top-left (0,0)
                    # Normalized 0-1000 usually assumes top-left origin (0,0) to bottom-right (1000,1000)
                    
                    x0 = (xmin / 1000) * width
                    y0 = (ymin / 1000) * height
                    x1 = (xmax / 1000) * width
                    y1 = (ymax / 1000) * height
                    
                    # Draw rectangle
                    # Set color to red (1, 0, 0), fill opacity 0.3
                    shape = page.new_shape()
                    shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
                    shape.finish(color=(1, 0, 0), fill=(1, 1, 0), fill_opacity=0.3, width=2)
                    shape.commit()
                    
                    # Stream modified PDF
                    pdf_bytes = doc.tobytes()
                    doc.close()
                    
                    from io import BytesIO
                    return send_file(
                        BytesIO(pdf_bytes),
                        mimetype='application/pdf',
                        as_attachment=False,
                        download_name=os.path.basename(filepath)
                    )
            except Exception as e:
                print(f"Highlighting failed: {e}")
                # Fallback to original file if highlighting fails
                pass

        return send_from_directory(project_dir, filepath)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/api/projects/<project_id>/evidence/upload', methods=['POST'])
def upload_evidence(project_id):
    """Manual evidence upload for a specific billing document"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    billing_doc = request.form.get('billingDocument')
    
    if not billing_doc:
        return jsonify({"error": "Billing document number required"}), 400
        
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    try:
        # Define output directory: step2_evidence_collection/DMS_Downloads/
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        output_dir = os.path.join(project_dir, 'step2_evidence_collection', 'DMS_Downloads')
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename: <billing_doc>_<original_filename>
        # This preserves keywords for get_doc_type (e.g. "Invoice", "Packing List")
        # and ensures association with billing_doc
        safe_original_name = sanitize_filename(file.filename)
        filename = f"{billing_doc}_{safe_original_name}"
        save_path = os.path.join(output_dir, filename)
        
        file.save(save_path)
        
        # Generate thumbnail (Optional, but good for UI if it supports originals)
        # Note: ProjectPDFSplitter might expect files in split_documents for thumbnails, 
        # but we'll try to generate it anyway if the method supports paths.
        try:
            sys.path.insert(0, os.path.join(BASE_DIR, 'backend'))
            from logic.pdf_splitter_api import ProjectPDFSplitter
            splitter = ProjectPDFSplitter(project_id, PROJECTS_DIR)
            # We pass the save_path. The type "manual" might need to be adjusted or kept.
            splitter._generate_thumbnail(Path(save_path), billing_doc, "manual")
        except Exception as e:
            print(f"Thumbnail generation failed: {e}")
            
        return jsonify({
            "status": "success",
            "message": "File uploaded successfully as Original",
            "filepath": f"step2_evidence_collection/DMS_Downloads/{filename}"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def open_browser():
    webbrowser.open_new("http://localhost:5000")

# @app.route('/api/projects/<project_id>/step3/extraction-data', methods=['GET'])
def get_step3_extraction_data_deprecated(project_id):
    """Load Step 1 confirmed data merged with Step 3 extraction results in structured format"""
    try:
        # Load Step 1 confirmed data (Source A - Ledger)
        step1_confirmed_path = os.path.join(PROJECTS_DIR, project_id, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
        
        if not os.path.exists(step1_confirmed_path):
            alt_path = os.path.join(PROJECTS_DIR, project_id, 'step1_entry_import', 'confirmed_data.csv')
            if os.path.exists(alt_path):
                step1_confirmed_path = alt_path
            else:
                return jsonify({"error": "No confirmed data found. Please confirm Step 1 first."}), 404
        
        # Read Step 1 confirmed data
        df = pd.read_csv(step1_confirmed_path)
        df = df.fillna('')
        
        # Normalize column names
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower == 'sales unit':
                column_mapping[col] = 'Sales Unit'
            elif col_lower == 'billing document':
                column_mapping[col] = 'Billing Document'
            elif col == '전표번호':
                column_mapping[col] = 'Billing Document'
            elif col_lower in ['billing date', '청구일']:
                column_mapping[col] = 'Billing Date'
            elif col_lower == 'incoterms':
                column_mapping[col] = 'Incoterms'
            elif col_lower in ['billed quantity', '청구수량']:
                column_mapping[col] = 'Billed Quantity'
            elif col_lower in ['amount', '금액']:
                column_mapping[col] = 'Amount'
            elif col_lower in ['document currency', '통화']:
                column_mapping[col] = 'Document Currency'
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
            print(f"[STEP3] Normalized columns: {column_mapping}")
        
        # Load extraction results (Source B - Invoice, Source C - B/L)
        # Try new filename first, fallback to old for backward compatibility
        step3_results_path = os.path.join(PROJECTS_DIR, project_id, 'step3_data_extraction', 'invoice_extraction_results.json')
        if not os.path.exists(step3_results_path):
            # Fallback to old filename
            step3_results_path = os.path.join(PROJECTS_DIR, project_id, 'step3_data_extraction', 'extraction_results.json')
        
        extraction_results = {}
        
        if os.path.exists(step3_results_path):
            try:
                with open(step3_results_path, 'r', encoding='utf-8') as f:
                    extraction_results = json.load(f)
                print(f"[STEP3] Loaded extraction results for {len(extraction_results)} documents")
            except Exception as e:
                print(f"[STEP3] Error loading extraction results: {e}")
        
        # Find billing document column
        billing_col = 'Billing Document'
        if billing_col not in df.columns:
            # Try to find it
            for col in df.columns:
                if col.lower() in ['billing document', 'billingdocument', '전표번호']:
                    billing_col = col
                    break
        
        if billing_col not in df.columns:
            return jsonify({"error": "Billing Document column not found in Step 1 data"}), 400
        
        # Helper function to extract value from dict or return as-is
        def get_val(val):
            if isinstance(val, dict) and 'value' in val:
                return val['value']
            return val if val else ''
        
        # Build structured comparison data
        data = []
        for _, row in df.iterrows():
            billing_doc = str(row.get(billing_col, '')).strip()
            
            # Source A - Ledger data
            sourceA = {
                'Date': str(row.get('Billing Date', '')),
                'Incoterms': str(row.get('Incoterms', '')),
                'Quantity': str(row.get('Billed Quantity', '')),
                'Sales Unit': str(row.get('Sales Unit', '')),
                'Amount': str(row.get('Amount', '')),
                'Currency': str(row.get('Document Currency', ''))
            }
            
            # Source B - Invoice extraction
            sourceB = {
                'Date': '',  # On Board Date
                'Incoterms': '',
                'Quantity': '',
                'Amount': '',
                'Currency': ''
            }
            
            # Source C - B/L extraction
            sourceC = {
                'Date': '',  # B/L Date
                'Incoterms': '',
                'Quantity': ''
            }
            
            # Populate from extraction results if available
            if billing_doc in extraction_results:
                extracted = extraction_results[billing_doc]
                
                # For now, we only have Invoice extraction (sourceB)
                # Assuming extraction_results contains Invoice data
                sourceB['Date'] = get_val(extracted.get('Extracted Date', ''))  # On Board Date
                sourceB['Incoterms'] = get_val(extracted.get('Extracted Incoterms', ''))
                sourceB['Quantity'] = get_val(extracted.get('Extracted Quantity', ''))
                sourceB['Amount'] = get_val(extracted.get('Extracted Amount', ''))
                sourceB['Currency'] = get_val(extracted.get('Extracted Currency', ''))
                
                # TODO: Add B/L extraction when available
                # sourceC would be populated from B/L extraction results
            
            data.append({
                'Billing Document': billing_doc,
                'sourceA': sourceA,
                'sourceB': sourceB,
                'sourceC': sourceC
            })
        
        return jsonify({
            "status": "success",
            "data": data,
            "total_records": len(data),
            "extracted_count": len(extraction_results)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/step3/extract', methods=['POST'])
def extract_step3_data(project_id):
    """Run invoice extraction for selected documents"""
    try:
        data = request.json
        selected_ids = data.get('selectedIds', [])
        
        if not selected_ids:
            return jsonify({"error": "No documents selected"}), 400
        
        # Convert all IDs to strings for consistency
        selected_ids = [str(id).strip() for id in selected_ids]
        
        # Setup logging to file
        step3_dir = os.path.join(PROJECTS_DIR, project_id, 'step3_data_extraction')
        os.makedirs(step3_dir, exist_ok=True)
        log_file = os.path.join(step3_dir, 'extraction_debug.log')
        
        def log(msg):
            """Log to both console and file"""
            print(msg)
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
            except:
                pass
        
        log(f"\n{'='*80}")
        log(f"[EXTRACT] Starting extraction session for project {project_id}")
        log(f"[EXTRACT] Selected {len(selected_ids)} documents: {selected_ids}")
        log(f"[EXTRACT] Log file: {log_file}")
        log(f"{'='*80}\n")
        
        # Import parser
        sys.path.append(os.path.join(BASE_DIR, 'Modules', 'Parser'))
        from invoice_parser import CoordinateInvoiceParser
        
        # Load existing extraction results if they exist
        step3_dir = os.path.join(PROJECTS_DIR, project_id, 'step3_data_extraction')
        os.makedirs(step3_dir, exist_ok=True)
        
        # Try new filename first, fallback to old for backward compatibility
        results_file = os.path.join(step3_dir, 'invoice_extraction_results.json')
        if not os.path.exists(results_file):
            results_file = os.path.join(step3_dir, 'extraction_results.json')
        
        # Load existing results
        if os.path.exists(results_file):
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                log(f"[EXTRACT] Loaded {len(results)} existing extraction results")
            except Exception as e:
                log(f"[EXTRACT] Error loading existing results: {e}")
                results = {}
        else:
            results = {}
        
        split_dir = os.path.join(PROJECTS_DIR, project_id, 'step2_evidence_collection', 'split_documents')
        
        newly_extracted = 0  # Track only newly extracted items
        
        for doc_id in selected_ids:
            # doc_id is already a string from the conversion above
            # PDFs are in the extraction_targets subfolder
            doc_dir = os.path.join(split_dir, doc_id, 'extraction_targets')
            log(f"\n[EXTRACT] ====== Processing {doc_id} ======")
            log(f"[EXTRACT] Looking in directory: {doc_dir}")
            
            if not os.path.exists(doc_dir):
                log(f"[EXTRACT] ❌ Document directory not found: {doc_dir}")
                continue
            
            # List all files in the directory
            try:
                all_files = os.listdir(doc_dir)
                log(f"[EXTRACT] Found {len(all_files)} files in directory:")
                for f in all_files:
                    log(f"[EXTRACT]   - {f}")
            except Exception as e:
                log(f"[EXTRACT] ❌ Error listing directory: {e}")
                continue
                
            # Find Invoice PDF
            invoice_pdf = None
            for file in all_files:
                if file.lower().endswith('.pdf') and ('invoice' in file.lower() or 'inv' in file.lower()):
                    invoice_pdf = os.path.join(doc_dir, file)
                    log(f"[EXTRACT] ✓ Found invoice PDF: {file}")
                    break
            
            if not invoice_pdf:
                # Fallback: try any PDF if only one exists
                pdfs = [f for f in all_files if f.lower().endswith('.pdf')]
                log(f"[EXTRACT] No invoice-specific PDF found. Total PDFs: {len(pdfs)}")
                if len(pdfs) == 1:
                    invoice_pdf = os.path.join(doc_dir, pdfs[0])
                    log(f"[EXTRACT] Using single PDF: {pdfs[0]}")
                elif len(pdfs) > 1:
                    log(f"[EXTRACT] ⚠️ Multiple PDFs found but no invoice-specific match:")
                    for pdf in pdfs:
                        log(f"[EXTRACT]     - {pdf}")
            
            if invoice_pdf:
                log(f"[EXTRACT] 📄 Parsing: {invoice_pdf}")
                try:
                    parser = CoordinateInvoiceParser(invoice_pdf)
                    log(f"[EXTRACT] Parser created successfully")
                    
                    if parser.extract_text(force_ocr=False):
                        log(f"[EXTRACT] Text extraction successful (mode: {'OCR' if parser.is_ocr_mode else 'native'})")
                        
                        # Log extracted text to file for debugging
                        try:
                            text_preview = parser.full_text[:500] if len(parser.full_text) > 500 else parser.full_text
                            log(f"[EXTRACT] Text preview (first 500 chars):\n{text_preview}\n---")
                            
                            # Save full text to separate file for detailed debugging
                            debug_text_file = os.path.join(step3_dir, f'extracted_text_{doc_id}.txt')
                            with open(debug_text_file, 'w', encoding='utf-8') as f:
                                f.write(parser.full_text)
                            log(f"[EXTRACT] Full extracted text saved to: {debug_text_file}")
                        except Exception as e:
                            log(f"[EXTRACT] Warning: Could not save text preview: {e}")
                        
                        parsed_data = parser.parse()
                        
                        # Retry with OCR if needed
                        if parsed_data == "RETRY":
                            log(f"[EXTRACT] 🔄 Retrying with OCR for {doc_id}")
                            parser.extract_text(force_ocr=True)
                            parsed_data = parser.parse()
                        
                        if isinstance(parsed_data, dict):
                            log(f"[EXTRACT] Parse successful. Fields found:")
                            for key, value in parsed_data.items():
                                if value:
                                    val_preview = str(value.get('value', ''))[:50] if isinstance(value, dict) else str(value)[:50]
                                    log(f"[EXTRACT]   {key}: {val_preview}")
                            
                            # Map fields
                            extracted_item = {
                                "Extracted Incoterms": parsed_data.get("CI_07_Incoterms", {}).get("value") if parsed_data.get("CI_07_Incoterms") else "",
                                "Extracted Quantity": parsed_data.get("CI_08_Total_Quantity", {}).get("value") if parsed_data.get("CI_08_Total_Quantity") else "",
                                "Extracted Amount": parsed_data.get("CI_09_Total_Amount", {}).get("value") if parsed_data.get("CI_09_Total_Amount") else "",
                                "Extracted Date": parsed_data.get("CI_05_On_Board_Date", {}).get("value") if parsed_data.get("CI_05_On_Board_Date") else ""
                            }
                            results[doc_id] = extracted_item
                            newly_extracted += 1  # Count newly extracted item
                            log(f"[EXTRACT] ✅ Successfully extracted {doc_id}")
                        else:
                            log(f"[EXTRACT] ❌ Parse returned non-dict: {type(parsed_data)}")
                    else:
                        log(f"[EXTRACT] ❌ Text extraction failed")
                except Exception as e:
                    import traceback
                    log(f"[EXTRACT] ❌ Exception during parsing: {str(e)}")
                    log(f"[EXTRACT] Traceback:")
                    traceback.print_exc()
                    # Also log traceback to file
                    try:
                        with open(log_file, 'a', encoding='utf-8') as f:
                            traceback.print_exc(file=f)
                    except:
                        pass
            else:
                log(f"[EXTRACT] ❌ No invoice PDF found for {doc_id}")
        
        # Save extraction results to JSON file
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        log(f"\n[EXTRACT] Saved {len(results)} total results to {results_file}")
        log(f"[EXTRACT] Session complete: {newly_extracted} newly extracted, {len(results)} total accumulated\n")
            
        return jsonify({
            "status": "success",
            "results": results,
            "total_processed": len(selected_ids),
            "total_success": newly_extracted,  # Return only newly extracted count
            "total_accumulated": len(results)  # Also return total accumulated
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/confirm-step3', methods=['POST'])
def confirm_step3(project_id):
    print(f"[DEBUG] confirm_step3 called for project {project_id}")
    try:
        data = request.json
        print(f"[DEBUG] Payload received: {len(data.get('extractionData', []))} items")
        extraction_data = data.get('extractionData', [])
        metadata = step_manager.confirm_step3(project_id, extraction_data)
        print(f"[DEBUG] Step 3 confirmed. Metadata updated.")
        return jsonify({
            "status": "success",
            "message": "Step 3 confirmed",
            "metadata": metadata
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/step3/save-draft', methods=['POST'])
def save_step3_draft(project_id):
    """Save Step 3 intermediate results (draft)"""
    try:
        data = request.json
        judgments = data.get('judgments', {})
        
        step3_dir = os.path.join(PROJECTS_DIR, project_id, 'step3_data_extraction')
        os.makedirs(step3_dir, exist_ok=True)
        final_file = os.path.join(step3_dir, 'final_comparison_results.json')
        
        current_data = {}
        if os.path.exists(final_file):
            with open(final_file, 'r', encoding='utf-8') as f:
                current_data = json.load(f)
        
        # If current_data is not a dict (e.g. list from auto results), reset it to dict for corrections
        if not isinstance(current_data, dict):
            current_data = {} 
        
        for doc_id, status in judgments.items():
            if doc_id not in current_data:
                current_data[doc_id] = {}
            current_data[doc_id]['final_status'] = status
            
        with open(final_file, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            "status": "success",
            "message": "Draft saved successfully"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/step4/run', methods=['GET'])
def run_step4_reconciliation(project_id):
    print(f"[DEBUG] run_step4_reconciliation called for {project_id}")
    try:
        # 1. Load Step 1 Data (Confirmed Ledger)
        project_path = os.path.join(PROJECTS_DIR, project_id)
        step1_file = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
        
        step1_data = []
        if os.path.exists(step1_file):
             try:
                df = pd.read_csv(step1_file)
                # Replace NaN with None to ensure valid JSON output
                step1_data = df.where(pd.notnull(df), None).to_dict('records')
             except Exception as e:
                 print(f"[ERROR] Failed to read Step 1 CSV: {e}")
        
        print(f"[DEBUG] Loaded Step 1 Data: {len(step1_data)} items")
        
        # 2. Load Step 3 Data (Prioritize Dashboard Data > Final > Auto)
        dashboard_file = os.path.join(project_path, 'dashboard_data.json')
        final_file = os.path.join(project_path, 'step3_data_extraction', 'final_comparison_results.json')
        auto_file = os.path.join(project_path, 'step3_data_extraction', 'auto_comparison_results.json')
        
        step3_results = []
        
        # Load Auto Results first as base (always needed if final is partial)
        auto_results = []
        if os.path.exists(auto_file):
            with open(auto_file, 'r', encoding='utf-8') as f:
                auto_results = json.load(f)
        
        if os.path.exists(dashboard_file):
            print(f"[DEBUG] Loading from dashboard_data.json")
            with open(dashboard_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                step3_results = data.get('results', [])
        elif os.path.exists(final_file):
            print(f"[DEBUG] Loading from final_comparison_results.json")
            with open(final_file, 'r', encoding='utf-8') as f:
                final_data = json.load(f)
                
            # If final_data is a dict (user corrections), merge it with auto_results
            if isinstance(final_data, dict):
                step3_results = []
                for item in auto_results:
                    doc_id = item.get('billing_document')
                    if doc_id and doc_id in final_data:
                        # Merge correction
                        correction = final_data[doc_id]
                        # Create a copy to modify
                        merged_item = item.copy()
                        # Update status
                        if 'final_status' in correction:
                            merged_item['auto_comparison']['status'] = correction['final_status']
                        # Update fields if needed (optional for dashboard status, but good for details)
                        # ...
                        step3_results.append(merged_item)
                    else:
                        step3_results.append(item)
            else:
                step3_results = final_data
        else:
            step3_results = auto_results

        print(f"[DEBUG] Loaded Step 3 Results: {len(step3_results)} items")
        
        # 3. Merge Data
        # Create a map of Step 3 results by Billing Document for easy lookup
        step3_map = {}
        for item in step3_results:
            # Try to find a key. The structure from step3_integrated_api.py seems to be:
            # { 'billing_document': ..., 'auto_comparison': { ... }, ... }
            key = item.get('billing_document')
            if key:
                step3_map[str(key)] = item
        
        merged_results = []
        
        # Iterate through Step 1 data (Master)
        for row in step1_data:
            # Find matching Step 3 result
            # Assuming 'Billing Document' is the key in Step 1 CSV
            doc_id = str(row.get('Billing Document', '')).strip()
            if not doc_id:
                 # Try other common keys if 'Billing Document' is missing
                 doc_id = str(row.get('Invoice No', '')).strip()
            
            match_data = step3_map.get(doc_id)
            
            # Construct the dashboard row
            dashboard_row = {
                # --- Reconciliation Status (Fixed Columns) ---
                'final_judgment': match_data['auto_comparison']['status'] if match_data else 'MISSING',
                'date_status': '일치' if match_data and match_data['auto_comparison']['field_results']['date']['match'] else '불일치' if match_data else 'PASS',
                'amount_status': '일치' if match_data and match_data['auto_comparison']['field_results']['amount']['match'] else '불일치' if match_data else 'PASS',
                'incoterms_status': '일치' if match_data and match_data['auto_comparison']['field_results']['incoterms']['match'] else '불일치' if match_data else 'PASS',
                'quantity_status': '일치' if match_data and match_data['auto_comparison']['field_results']['quantity']['match'] else '불일치' if match_data else 'PASS',
                
                # --- Original Step 1 Data (All Columns) ---
                **row # Spread all Step 1 columns
            }
            
            # Add extracted values for reference (Optional, but good for debugging/detailed view if needed later)
            if match_data:
                dashboard_row['_extracted_date'] = match_data['auto_comparison']['field_results']['date']['step3_value']
                dashboard_row['_extracted_amount'] = match_data['auto_comparison']['field_results']['amount']['step3_value']
                dashboard_row['_extracted_incoterms'] = match_data['auto_comparison']['field_results']['incoterms']['step3_value']
                dashboard_row['_extracted_quantity'] = match_data['auto_comparison']['field_results']['quantity']['step3_value']

            merged_results.append(dashboard_row)
            
        # Calculate Summary
        summary = {
            "total": len(merged_results),
            "matched": sum(1 for r in merged_results if r['final_judgment'] == 'complete_match'),
            "mismatched": sum(1 for r in merged_results if r['final_judgment'] == 'partial_error'),
            "missing": sum(1 for r in merged_results if r['final_judgment'] == 'MISSING' or r['final_judgment'] == 'review_required'), # Group review_required with missing/warn for now or separate? Design said PASS/FAIL/WARN.
            # Let's map strictly to design:
            # PASS (Green) -> complete_match
            # FAIL (Red) -> partial_error
            # WARN (Yellow) -> review_required
            # MISSING (Gray) -> MISSING (Not in step 3 results)
        }
        
        # Helper to sanitize data for JSON
        def sanitize_for_json(obj):
            if isinstance(obj, float):
                if pd.isna(obj) or obj == float('inf') or obj == float('-inf'):
                    return None
            elif isinstance(obj, dict):
                return {k: sanitize_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_for_json(v) for v in obj]
            return obj

        # Sanitize results and summary
        sanitized_results = sanitize_for_json(merged_results)
        sanitized_summary = sanitize_for_json(summary)
        
        return jsonify({
            "status": "success",
            "results": sanitized_results,
            "summary": sanitized_summary
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/projects/<project_id>/step4/export', methods=['GET'])
def export_step4_results(project_id):
    try:
        # Reuse the logic to get merged results
        # (In a real app, refactor this into a logic function. For now, calling the logic directly or duplicating slightly is safer to avoid breaking existing code structure too much)
        
        # ... (Duplicate logic for safety and speed, or better: refactor. Let's refactor slightly by extracting the merge logic if possible, but given the constraints, I'll just implement the export logic here reading the same files)
        
        project_path = os.path.join(PROJECTS_DIR, project_id)
        step1_file = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
        step3_file = os.path.join(project_path, 'step3_data_extraction', 'auto_comparison_results.json')
        
        if not os.path.exists(step1_file):
            return jsonify({"error": "Step 1 data not found"}), 404
            
        df_step1 = pd.read_csv(step1_file)
        # Replace NaN with None
        step1_data = df_step1.where(pd.notnull(df_step1), None).to_dict('records')
        
        step3_results = []
        if os.path.exists(step3_file):
            with open(step3_file, 'r', encoding='utf-8') as f:
                step3_results = json.load(f)
                
        step3_map = {}
        for item in step3_results:
            key = item.get('billing_document')
            if key:
                step3_map[str(key)] = item
                
        export_rows = []
        for row in step1_data:
            doc_id = str(row.get('Billing Document', '')).strip()
            if not doc_id: doc_id = str(row.get('Invoice No', '')).strip()
            
            match_data = step3_map.get(doc_id)
            
            # Map status to Korean for Excel
            final_judg = match_data['auto_comparison']['status'] if match_data else 'MISSING'
            final_judg_kr = {
                'complete_match': 'PASS',
                'partial_error': 'FAIL',
                'review_required': 'WARNING',
                'MISSING': '미수집'
            }.get(final_judg, final_judg)
            
            export_row = {
                '최종판단': final_judg_kr,
                '날짜_판정': '일치' if match_data and match_data['auto_comparison']['field_results']['date']['match'] else '불일치' if match_data else '-',
                '금액_판정': '일치' if match_data and match_data['auto_comparison']['field_results']['amount']['match'] else '불일치' if match_data else '-',
                '인코텀즈_판정': '일치' if match_data and match_data['auto_comparison']['field_results']['incoterms']['match'] else '불일치' if match_data else '-',
                '수량_판정': '일치' if match_data and match_data['auto_comparison']['field_results']['quantity']['match'] else '불일치' if match_data else '-',
                **row # Original Data
            }
            export_rows.append(export_row)
            
        # Create DataFrame
        df_export = pd.DataFrame(export_rows)
        
        # Reorder columns: Put judgment columns first
        cols = list(df_export.columns)
        priority_cols = ['최종판단', '날짜_판정', '금액_판정', '인코텀즈_판정', '수량_판정']
        other_cols = [c for c in cols if c not in priority_cols]
        new_order = priority_cols + other_cols
        df_export = df_export[new_order]
        
        # Save to temp file
        export_dir = os.path.join(project_path, 'exports')
        os.makedirs(export_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Reconciliation_Results_{timestamp}.xlsx"
        filepath = os.path.join(export_dir, filename)
        
        df_export.to_excel(filepath, index=False)
        
        return send_from_directory(export_dir, filename, as_attachment=True)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
        


@app.route('/api/projects/<project_id>/extraction-progress', methods=['GET'])
def get_extraction_progress(project_id):
    """
    Get the current progress of the extraction process
    """
    progress = extraction_progress.get(project_id)
    if not progress:
        return jsonify({
            "status": "idle",
            "current": 0,
            "total": 0,
            "message": "대기 중..."
        })
    return jsonify(progress)

if __name__ == '__main__':
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1, open_browser).start()
    app.run(debug=True, port=5000)
