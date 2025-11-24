import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def make_request(endpoint, method='GET', data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    if data:
        data_bytes = json.dumps(data).encode('utf-8')
    else:
        data_bytes = None
        
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode('utf-8')
            return json.loads(response_body)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_create_project():
    print("Testing Create Project...")
    data = make_request("/api/projects", method='POST', data={"name": "RefactorTest"})
    
    if not data:
        print("FAILED: Create Project")
        return None
    
    project_id = data['id']
    print(f"SUCCESS: Project created with ID {project_id}")
    
    if 'steps' not in data:
        print("FAILED: Metadata does not contain 'steps'")
    else:
        print("SUCCESS: Metadata schema looks correct")
        
    return project_id

def test_save_project(project_id):
    print("\nTesting Save Project (Step 1 Draft)...")
    ledger_data = [{"col1": "val1", "col2": "val2"}]
    data = make_request(f"/api/projects/{project_id}/save", method='POST', data={
        "ledgerData": ledger_data,
        "visibleColumns": ["col1", "col2"]
    })
    
    if not data:
        print("FAILED: Save Project")
        return False
        
    print("SUCCESS: Project saved")
    return True

def test_confirm_project(project_id):
    print("\nTesting Confirm Project (Step 1)...")
    ledger_data = [{"col1": "val1", "col2": "val2"}]
    data = make_request(f"/api/projects/{project_id}/confirm", method='POST', data={
        "ledgerData": ledger_data,
        "visibleColumns": ["col1", "col2"]
    })
    
    if not data:
        print("FAILED: Confirm Project")
        return False
        
    metadata = data.get('metadata', {})
    if metadata.get('steps', {}).get('step1', {}).get('status') != 'completed':
        print(f"FAILED: Step 1 status is not completed. Got: {metadata}")
        return False
        
    if metadata.get('steps', {}).get('step2', {}).get('status') != 'pending':
        print(f"FAILED: Step 2 status is not pending. Got: {metadata}")
        return False
        
    print("SUCCESS: Project confirmed and Step 2 unlocked")
    return True

def test_load_project(project_id):
    print("\nTesting Load Project...")
    data = make_request(f"/api/projects/{project_id}/load", method='GET')
    
    if not data:
        print("FAILED: Load Project")
        return False
        
    if len(data.get('confirmedData', [])) != 1:
        print("FAILED: Confirmed data mismatch")
        return False
        
    print("SUCCESS: Project loaded correctly")
    return True

def test_mother_workspace(project_id):
    print("\nTesting Mother Workspace API...")
    data = make_request(f"/api/projects/{project_id}/mother-workspace", method='GET')
    
    if not data:
        print("FAILED: Mother Workspace")
        return False
        
    if not data.get('step1_summary'):
        print("FAILED: Step 1 summary missing")
        return False
        
    print("SUCCESS: Mother workspace data retrieved")
    return True

if __name__ == "__main__":
    try:
        project_id = test_create_project()
        if project_id:
            if test_save_project(project_id):
                if test_confirm_project(project_id):
                    test_load_project(project_id)
                    test_mother_workspace(project_id)
    except Exception as e:
        print(f"An error occurred: {e}")
