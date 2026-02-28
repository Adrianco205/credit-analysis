import pandas as pd
import requests
from io import BytesIO
from datetime import datetime

url = "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_new.xls"
content = requests.get(url, timeout=60).content
wb = pd.read_excel(BytesIO(content), sheet_name=None, engine="xlrd")
print('total sheets', len(wb))
for name in list(wb.keys())[-8:]:
    df = wb[name]
    cols = list(df.columns)
    date_cols=0
    for c in cols:
        try:
            if isinstance(c, (pd.Timestamp, datetime)):
                date_cols += 1
            else:
                datetime.fromisoformat(str(c).replace('Z','+00:00'))
                date_cols += 1
        except Exception:
            pass
    has_uvr = False
    probe = df.astype(str).head(40).to_string().lower()
    if 'uvr' in probe:
        has_uvr=True
    print(name, 'shape', df.shape, 'date_cols', date_cols, 'has_uvr', has_uvr)
