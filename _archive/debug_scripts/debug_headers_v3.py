import csv
import sys

path = r"d:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\D조건_251001~251231_20260105_110824\step1_invoice_confirmation\confirmed_invoices.csv"
try:
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        print("Headers:", headers)
except Exception as e:
    print(e)
