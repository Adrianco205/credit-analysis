import pandas as pd
import requests
from io import BytesIO

url = "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_new.xls"
content = requests.get(url, timeout=60).content
wb = pd.read_excel(BytesIO(content), sheet_name=None, engine="xlrd")
print("sheets:", list(wb.keys())[:10])
for name, df in list(wb.items())[:4]:
    print("---", name, df.shape)
    print(df.head(12).to_string())
