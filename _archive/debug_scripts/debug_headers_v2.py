import pandas as pd
import os

path = r"d:\CJ\Project Manager\IDARS\IDARS PJT\Data\projects\D조건_251001~251231_20260105_110824\step1_invoice_confirmation\confirmed_invoices.csv"
try:
    df = pd.read_csv(path)
    print("Columns:", df.columns.tolist())
    print("First row:", df.iloc[0].to_dict())
except Exception as e:
    print(e)
