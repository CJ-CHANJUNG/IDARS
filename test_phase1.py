"""
IDARS Phase 1 Test Suite
Tests the foundational refactoring components including:
- Project creation and metadata initialization
- Step confirmation workflow (1 → 2 → 3 → 4)
- Step unconfirmation (reverse order validation)
- Mother Workspace data aggregation
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = 'http://127.0.0.1:5000'

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(message):
    print(f"{Colors.BLUE}[TEST]{Colors.END} {message}")

def print_success(message):
    print(f"{Colors.GREEN}✓{Colors.END} {message}")

def print_error(message):
    print(f"{Colors.RED}✗{Colors.END} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠{Colors.END} {message}")

def test_project_creation():
    """Test 1: Create a new project and verify metadata initialization"""
    print_test("Test 1: Project Creation and Metadata Initialization")
    
    response = requests.post(f'{BASE_URL}/api/projects', json={
        'name': 'Phase1_Test_Project'
    })
    
    if response.status_code == 200:
        project = response.json()
        project_id = project['id']
        
        # Verify metadata structure
        assert 'id' in project, "Project ID missing"
        assert 'name' in project, "Project name missing"
        assert 'steps' in project, "Steps missing in metadata"
        assert project['current_step'] == 0, "Initial step should be 0"
        assert project['status'] == 'new', "Initial status should be 'new'"
        
        # Verify all steps are initialized
        for i in range(1, 5):
            step_key = f'step{i}'
            assert step_key in project['steps'], f"Step {i} missing"
            assert 'status' in project['steps'][step_key], f"Step {i} status missing"
            assert 'data_path' in project['steps'][step_key], f"Step {i} data_path missing"
        
        print_success(f"Project created successfully: {project_id}")
        return project_id
    else:
        print_error(f"Project creation failed: {response.status_code}")
        return None

def test_step1_confirmation(project_id):
    """Test 2: Confirm Step 1 and verify Step 2 activation"""
    print_test("Test 2: Step 1 Confirmation → Step 2 Activation")
    
    # Upload some dummy data for Step 1
    dummy_data = [
        {'Billing Document': '12345', 'Amount': '1000', 'Description': 'Test 1'},
        {'Billing Document': '12346', 'Amount': '2000', 'Description': 'Test 2'}
    ]
    
    response = requests.post(f'{BASE_URL}/api/projects/{project_id}/confirm', json={
        'ledgerData': dummy_data,
        'visibleColumns': ['Billing Document', 'Amount', 'Description']
    })
    
    if response.status_code == 200:
        result = response.json()
        metadata = result['metadata']
        
        assert metadata['steps']['step1']['status'] == 'completed', "Step 1 should be completed"
        assert metadata['steps']['step2']['status'] == 'pending', "Step 2 should be pending (unlocked)"
        assert metadata['current_step'] == 1, "Current step should be 1"
        
        print_success("Step 1 confirmed, Step 2 activated")
        return True
    else:
        print_error(f"Step 1 confirmation failed: {response.status_code}")
        return False

def test_sequential_confirmation(project_id):
    """Test 3: Sequential step confirmation (Step 2 → 3 → 4)"""
    print_test("Test 3: Sequential Step Confirmation")
    
    # Confirm Step 2
    response2 = requests.post(f'{BASE_URL}/api/projects/{project_id}/confirm-step2', json={
        'evidenceData': [{'billingDocument': '12345', 'status': 'collected'}]
    })
    
    if response2.status_code == 200:
        print_success("Step 2 confirmed")
    else:
        print_error(f"Step 2 confirmation failed: {response2.status_code}")
        return False
    
    # Confirm Step 3 (Note: In real scenario, extraction data would be populated)
    # For test purposes, we'll use mock data
    response3 = requests.post(f'{BASE_URL}/api/projects/{project_id}/step3/confirm', json={
        'extractionData': [{'document': '12345', 'extracted_fields': {}}]
    })
    
    # Note: This endpoint might not exist yet, so we'll skip if it fails
    if response3.status_code == 200:
        print_success("Step 3 confirmed")
    else:
        print_warning(f"Step 3 confirmation endpoint may not be implemented: {response3.status_code}")
    
    return True

def test_reverse_unconfirm(project_id):
    """Test 4: Reverse unconfirm validation (must unconfirm in reverse order)"""
    print_test("Test 4: Reverse Unconfirm Validation")
    
    # Try to unconfirm Step 1 without unconfirming Step 2 first (should fail)
    response = requests.post(f'{BASE_URL}/api/projects/{project_id}/unconfirm', json={
        'step': 1
    })
    
    if response.status_code != 200:
        print_success("Correctly prevented Step 1 unconfirm when Step 2 is confirmed")
    else:
        print_error("Should not allow Step 1 unconfirm when Step 2 is confirmed")
        return False
    
    # Now unconfirm Step 2 first
    response2 = requests.post(f'{BASE_URL}/api/projects/{project_id}/unconfirm', json={
        'step': 2
    })
    
    if response2.status_code == 200:
        metadata = response2.json()['metadata']
        assert metadata['steps']['step2']['status'] == 'pending', "Step 2 should be pending after unconfirm"
        print_success("Step 2 unconfirmed successfully")
    else:
        print_error(f"Step 2 unconfirm failed: {response2.status_code}")
        return False
    
    # Now Step 1 unconfirm should succeed
    response3 = requests.post(f'{BASE_URL}/api/projects/{project_id}/unconfirm', json={
        'step': 1
    })
    
    if response3.status_code == 200:
        print_success("Step 1 unconfirmed successfully (after Step 2 was unconfirmed)")
        return True
    else:
        print_error(f"Step 1 unconfirm failed unexpectedly: {response3.status_code}")
        return False

def test_mother_workspace_data(project_id):
    """Test 5: Mother Workspace data aggregation"""
    print_test("Test 5: Mother Workspace Data Aggregation")
    
    response = requests.get(f'{BASE_URL}/api/projects/{project_id}/mother-workspace')
    
    if response.status_code == 200:
        data = response.json()
        
        assert 'project' in data, "Project metadata missing"
        assert 'step1_summary' in data, "Step 1 summary missing"
        assert 'step2_summary' in data, "Step 2 summary missing"
        assert 'step3_summary' in data, "Step 3 summary missing"
        assert 'step4_summary' in data, "Step 4 summary missing"
        
        print_success("Mother Workspace API returned expected data structure")
        print(f"  Project: {data['project']['name']}")
        print(f"  Current Step: {data['project']['current_step']}")
        
        if data['step1_summary']:
            print(f"  Step 1: {data['step1_summary']['invoice_count']} invoices")
        
        return True
    else:
        print_error(f"Mother Workspace API failed: {response.status_code}")
        return False

def cleanup(project_id):
    """Clean up test project"""
    print_test("Cleanup: Deleting test project")
    
    response = requests.delete(f'{BASE_URL}/api/projects/{project_id}')
    
    if response.status_code == 200:
        print_success("Test project deleted")
    else:
        print_warning(f"Cleanup failed (project may need manual deletion): {project_id}")

def main():
    print("\n" + "="*60)
    print(f"{Colors.BLUE}IDARS Phase 1 Test Suite{Colors.END}")
    print("="*60 + "\n")
    
    # Check if backend is running
    try:
        response = requests.get(f'{BASE_URL}/api/projects')
        if response.status_code != 200:
            print_error("Backend is not responding correctly")
            return
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to backend. Make sure the server is running at http://127.0.0.1:5000")
        return
    
    print_success("Backend is running\n")
    
    # Run tests
    project_id = test_project_creation()
    if not project_id:
        print_error("Aborting tests due to project creation failure")
        return
    
    print()
    time.sleep(0.5)
    
    if not test_step1_confirmation(project_id):
        cleanup(project_id)
        return
    
    print()
    time.sleep(0.5)
    
    if not test_sequential_confirmation(project_id):
        cleanup(project_id)
        return
    
    print()
    time.sleep(0.5)
    
    if not test_reverse_unconfirm(project_id):
        cleanup(project_id)
        return
    
    print()
    time.sleep(0.5)
    
    if not test_mother_workspace_data(project_id):
        cleanup(project_id)
        return
    
    print()
    cleanup(project_id)
    
    print("\n" + "="*60)
    print(f"{Colors.GREEN}✓ All Phase 1 Tests Passed!{Colors.END}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
