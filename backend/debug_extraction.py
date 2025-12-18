import sys
import os
import asyncio
import json

# Setup paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR) # IDARS PJT
MODULES_DIR = os.path.join(BASE_DIR, 'Modules')
PARSER_DIR = os.path.join(MODULES_DIR, 'Parser')

sys.path.append(PARSER_DIR)

try:
    from smart_extraction_engine import SmartExtractionEngine
except ImportError as e:
    print(f"Failed to import SmartExtractionEngine from {PARSER_DIR}")
    print(f"Error details: {e}")
    sys.exit(1)

async def run_debug():
    project_id = "test_251215_v2_20251215_105525"
    target_id = "94520767"
    
    projects_dir = os.path.join(BASE_DIR, 'Data', 'projects')
    project_path = os.path.join(projects_dir, project_id)
    split_dir = os.path.join(project_path, 'step2_evidence_collection', 'split_documents')
    
    print(f"Debug extraction for {target_id} in {project_id}")
    print(f"Split dir: {split_dir}")
    
    engine = SmartExtractionEngine()
    
    # Mock progress callback
    def progress_callback(current, total, doc_number, message):
        print(f"[PROGRESS] {current}/{total} - {doc_number}: {message}")

    try:
        results = await engine.process_project_pdfs_async(
            project_id=project_id,
            split_dir=split_dir,
            extraction_mode="detailed", # Try detailed mode
            target_ids=[target_id],
            progress_callback=progress_callback
        )
        
        with open('debug_result.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print("Results saved to debug_result.json")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_debug())
