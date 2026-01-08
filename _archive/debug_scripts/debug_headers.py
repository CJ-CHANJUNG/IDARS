import os
import csv

project_id = "D조건_251001~251231_20260105_110824"
project_path = fr"d:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\{project_id}"
step1_path = os.path.join(project_path, 'step1_invoice_confirmation', 'confirmed_invoices.csv')

if os.path.exists(step1_path):
    print(f"Reading: {step1_path}")
    with open(step1_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        headers = next(reader)
        print("HEADERS FOUND:")
        for h in headers:
            print(f"[{h}]")
else:
    print("File not found")
