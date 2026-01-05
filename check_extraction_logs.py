# -*- coding: utf-8 -*-
import json

# Load extraction results
with open(r'd:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\샘플2_20251231_072311\step3_data_extraction\invoice_extraction_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check specific slips
slips = ['94524511', '94533565', '94526996']

for slip_id in slips:
    slip = data.get(slip_id, {})
    print(f"\n{'='*60}")
    print(f"Slip: {slip_id}")
    print('='*60)

    print(f"\nQuantity: {slip.get('Quantity')}")
    print(f"Amount: {slip.get('Amount')}")

    print(f"\nNotes: {slip.get('notes', 'NO NOTES')}")

    print(f"\nEvidence:")
    for ev in slip.get('evidence', []):
        print(f"  Field: {ev.get('field')}")
        print(f"  Values: {ev.get('values')}")
        print(f"  Reason: {ev.get('reason')}")
        print()
