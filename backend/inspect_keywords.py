import pandas as pd
import requests
from io import BytesIO

urls = [
 "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_new.xls",
 "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_3s_new.xls",
 "https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/IBR.xlsx",
]
for url in urls:
    print('\nURL', url)
    content = requests.get(url, timeout=60).content
    engine = 'openpyxl' if url.endswith('.xlsx') else 'xlrd'
    wb = pd.read_excel(BytesIO(content), sheet_name=None, engine=engine)
    found = {'uvr':0,'dtf':0,'ipc':0,'ibr':0}
    for name, df in wb.items():
        text = ' '.join(df.astype(str).fillna('').head(200).to_string().lower().split())
        for k in found:
            if k in text:
                found[k]+=1
    print('sheets', len(wb), 'matches', found)
