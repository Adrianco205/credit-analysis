import pandas as pd
import requests
from io import BytesIO
from datetime import datetime

url = "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_new.xls"
content = requests.get(url, timeout=60).content

print("=== header=None ===")
wb = pd.read_excel(BytesIO(content), sheet_name=None, engine="xlrd", header=None)
for sheet_name, df in wb.items():
    if "2025" not in str(sheet_name):
        continue
    print("sheet", sheet_name, "shape", df.shape)
    for idx, row in df.iterrows():
        row_text = " ".join(str(v).lower() for v in row.values[:8] if pd.notna(v))
        if "ipc" in row_text or "indice de precios" in row_text or "inflaci" in row_text:
            print("row", idx, row.values[:10])

print("\n=== header=0 ===")
wb2 = pd.read_excel(BytesIO(content), sheet_name=None, engine="xlrd")
for sheet_name, df in wb2.items():
    if "2025" not in str(sheet_name):
        continue
    print("sheet", sheet_name, "shape", df.shape)
    cols = [str(c).lower() for c in df.columns]
    for i, c in enumerate(cols):
        if "ipc" in c or "indice" in c or "inflaci" in c:
            print("candidate_col", i, df.columns[i])
    for idx, row in df.head(100).iterrows():
        row_text = " ".join(str(v).lower() for v in row.values[:8] if pd.notna(v))
        if "ipc" in row_text or "indice de precios" in row_text or "inflaci" in row_text:
            print("row", idx, row.values[:10])
