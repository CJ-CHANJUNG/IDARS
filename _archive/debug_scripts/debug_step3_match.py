import os
import csv
import json

project_id = "D조건_251001~251231_20260105_110824"
project_path = fr"d:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\{project_id}"

print(f"Checking project: {project_path}")

# 1. Load CSV
step1_path = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')
print(f"Step 1 CSV path: {step1_path}")

if not os.path.exists(step1_path):
    print("❌ Step 1 CSV not found!")
else:
    try:
        sap_map = {}
        with open(step1_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            print(f"Columns: {fieldnames}")
            
            rows = list(reader)
            print(f"✅ Loaded CSV with {len(rows)} rows.")
            
            for row in rows:
                # Try multiple possible column names
                sid = row.get('Billing Document') or row.get('전표번호') or row.get('Billing Document') 
                if not sid:
                    continue
                sap_map[str(sid)] = True
            
        print(f"✅ Created SAP Map with {len(sap_map)} keys.")
        print("Sample keys:", list(sap_map.keys())[:5])
        
        # 2. Check Files
        evidence_dir = os.path.join(project_path, 'step2_evidence_collection', 'dterm_downloads')
        print(f"Evidence Dir: {evidence_dir}")
        
        if os.path.exists(evidence_dir):
            files = os.listdir(evidence_dir)
            print(f"Found {len(files)} files.")
            
            matches = 0
            for f in files:
                if not f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    continue
                    
                matched_sid = None
                for sid in sap_map.keys():
                    if sid in f:
                        matched_sid = sid
                        break
                
                if matched_sid:
                    matches += 1
                else:
                    print(f"❌ No match for file: {f}")
            
            print(f"Total Matches: {matches}")
        else:
            print("❌ Evidence dir not found")
            
    except Exception as e:
        print(f"Error loading CSV: {e}")
