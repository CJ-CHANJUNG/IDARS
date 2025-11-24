import urllib.request
import urllib.error
import json
import os
import pandas as pd
import time

BASE_URL = "http://127.0.0.1:5000"
TEST_FILE = "test.csv"

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

def print_step(step_name):
    print(f"\n{'='*50}")
    print(f"STEP: {step_name}")
    print(f"{'='*50}")

def run_debug_walkthrough():
    print("Starting Debug Walkthrough with 'test.csv'...")
    
    # 1. Create Project
    print_step("1. Create Project")
    project_name = f"Debug_Project_{int(time.time())}"
    response = make_request("/api/projects", method='POST', data={"name": project_name})
    
    if not response:
        print("❌ Failed to create project")
        return
        
    project_id = response['id']
    print(f"✅ Project Created: {project_name} (ID: {project_id})")
    print(f"   Metadata Status: {response['status']}")
    print(f"   Current Step: {response['current_step']}")
    
    # 2. Simulate File Upload (Read local file)
    print_step("2. Read Sample File (Simulating Upload)")
    if not os.path.exists(TEST_FILE):
        print(f"❌ Test file '{TEST_FILE}' not found!")
        return
        
    try:
        df = pd.read_csv(TEST_FILE)
        df = df.fillna('')
        ledger_data = df.to_dict(orient='records')
        print(f"✅ Read '{TEST_FILE}' successfully.")
        print(f"   Rows: {len(ledger_data)}")
        print(f"   Columns: {list(ledger_data[0].keys())}")
    except Exception as e:
        print(f"❌ Failed to read test file: {e}")
        return

    # 3. Save Project (Step 1 Draft)
    print_step("3. Save Project (Step 1 Draft)")
    response = make_request(f"/api/projects/{project_id}/save", method='POST', data={
        "ledgerData": ledger_data,
        "visibleColumns": list(ledger_data[0].keys())
    })
    
    if not response:
        print("❌ Failed to save project")
        return
        
    print("✅ Project Saved")
    print(f"   Message: {response.get('message')}")
    
    # Verify file existence
    project_path = os.path.join("Data", "projects", project_id)
    draft_path = os.path.join(project_path, "step1_invoice_confirmation", "ledger.csv")
    if os.path.exists(draft_path):
        print(f"   [File Check] Draft file exists: {draft_path}")
    else:
        print(f"   [File Check] ❌ Draft file MISSING: {draft_path}")

    # 4. Confirm Project (Step 1)
    print_step("4. Confirm Project (Step 1)")
    response = make_request(f"/api/projects/{project_id}/confirm", method='POST', data={
        "ledgerData": ledger_data,
        "visibleColumns": list(ledger_data[0].keys())
    })
    
    if not response:
        print("❌ Failed to confirm project")
        return
        
    print("✅ Project Confirmed")
    metadata = response.get('metadata', {})
    step1_status = metadata.get('steps', {}).get('step1', {}).get('status')
    step2_status = metadata.get('steps', {}).get('step2', {}).get('status')
    
    print(f"   Step 1 Status: {step1_status}")
    print(f"   Step 2 Status: {step2_status}")
    
    # Verify file existence
    confirmed_path = os.path.join(project_path, "step1_invoice_confirmation", "confirmed_invoices.csv")
    if os.path.exists(confirmed_path):
        print(f"   [File Check] Confirmed file exists: {confirmed_path}")
    else:
        print(f"   [File Check] ❌ Confirmed file MISSING: {confirmed_path}")

    # 5. Load Project (Verify Data)
    print_step("5. Load Project (Verify Data)")
    response = make_request(f"/api/projects/{project_id}/load", method='GET')
    
    if not response:
        print("❌ Failed to load project")
        return
        
    loaded_confirmed = response.get('confirmedData', [])
    print(f"✅ Project Loaded")
    print(f"   Confirmed Rows: {len(loaded_confirmed)}")
    
    if len(loaded_confirmed) == len(ledger_data):
        print("   [Data Check] Row count matches!")
    else:
        print(f"   [Data Check] ❌ Row count mismatch! Expected {len(ledger_data)}, got {len(loaded_confirmed)}")

    print("\n🎉 Debug Walkthrough Completed Successfully!")

if __name__ == "__main__":
    run_debug_walkthrough()
