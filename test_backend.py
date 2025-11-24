import requests

# Test project creation
response = requests.post(
    'http://127.0.0.1:5000/api/projects',
    headers={'Content-Type': 'application/json'},
    json={'name': 'Test Debug Project'}
)

print("Project Creation Response:")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    project_id = response.json()['id']
    print(f"\nProject ID: {project_id}")
    
    # Test SAP download
    print("\n--- Testing SAP Download ---")
    sap_response = requests.post(
        'http://127.0.0.1:5000/api/sap/download',
        headers={'Content-Type': 'application/json'},
        json={
            'projectId': project_id,
            'dateFrom': '2025-11-01',
            'dateTo': '2025-11-30'
        }
    )
    print(f"SAP Status: {sap_response.status_code}")
    print(f"SAP Response: {sap_response.text[:500]}")
