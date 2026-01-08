# -*- coding: utf-8 -*-
import json

# Load final results
with open(r'd:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\샘플2_20251231_072311\step3_data_extraction\final_results.json', 'r', encoding='utf-8') as f:
    final = json.load(f)

slips = ['94524511', '94533565', '94526996']

print('Step1 Expected Values from final_results.json:')
for slip_id in slips:
    if slip_id in final:
        step1 = final[slip_id].get('step1_data', {})
        print(f"\n{slip_id}:")
        print(f"  Amount: {step1.get('amount')}")
        print(f"  Quantity: {step1.get('quantity')}")
    else:
        print(f"\n{slip_id}: NOT FOUND")
