from flask import Blueprint, request, jsonify
import os
import json
import asyncio
from backend.logic.step_manager import run_step3_extraction, get_step3_extraction_data

step3_bp = Blueprint('step3', __name__)

@step3_bp.route('/api/extraction-config', methods=['GET'])
def get_extraction_config():
    """
    추출 설정(extraction_config.json) 반환
    """
    try:
        # 프로젝트 루트 계산
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        config_path = os.path.join(project_root, 'Config', 'extraction_config.json')
        
        if not os.path.exists(config_path):
            return jsonify({"error": "설정 파일을 찾을 수 없습니다"}), 404
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        return jsonify(config)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@step3_bp.route('/api/projects/<project_id>/extract-evidence', methods=['POST'])
def extract_evidence(project_id):
    """
    Step 3: 증빙 데이터 추출 실행 (비동기 트리거)
    """
    try:
        # 선택된 필드 (옵션)
        data = request.get_json() or {}
        selected_fields = data.get('selected_fields', [])
        
        # 비동기 작업 시작 (Fire and Forget 또는 백그라운드 작업)
        # 실제 운영 환경에서는 Celery 등을 권장하지만, 여기서는 asyncio.create_task 사용
        # Flask는 기본적으로 동기식이므로, 별도의 스레드나 프로세스에서 실행해야 함
        # 여기서는 step_manager에서 처리하도록 위임
        
        task_id = run_step3_extraction(project_id, selected_fields)
        
        return jsonify({
            "message": "추출 작업이 시작되었습니다",
            "project_id": project_id,
            "task_id": task_id
        }), 202
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@step3_bp.route('/api/projects/<project_id>/step3/load', methods=['GET'])
def load_step3_data(project_id):
    """
    Step 3: 추출된 데이터 로드
    """
    try:
        data = get_step3_extraction_data(project_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
