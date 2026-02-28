import pandas as pd
import requests
from io import BytesIO

url = "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_new.xls"
content = requests.get(url, timeout=60).content

for sheet in ["Español-2024", "Español-2025", "Español-2026"]:
    try:
        df = pd.read_excel(BytesIO(content), sheet_name=sheet, engine="xlrd", header=None)
    except Exception as exc:
        print(sheet, "error", exc)
        continue
    print("\n===", sheet, "===")
    for i, row in df.iterrows():
        text = " ".join(str(v).lower() for v in row.values[:8] if pd.notna(v))
        if "inflaci" in text or "ipc" in text:
            print(i, text)
