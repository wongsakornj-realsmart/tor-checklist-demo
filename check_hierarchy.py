import pandas as pd
df = pd.read_excel(r'D:\CBD\TORChecklist\OutputTORChecklist\Attach_TOR_1.xlsx')
for idx, row in df.iterrows():
    if row['ลำดับ'] == '1.':
        print(f"Row {idx+2}: ลำดับ = {row['ลำดับ']}, หมวดหมู่หลัก = {row['หมวดหมู่หลัก']}")
