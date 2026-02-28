import pandas as pd, requests
from io import BytesIO
from datetime import datetime
url='https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_new.xls'
content=requests.get(url,timeout=60).content
wb=pd.read_excel(BytesIO(content),sheet_name=None,engine='xlrd')
key=[k for k in wb.keys() if '2026' in k][0]
df=wb[key]
print('sheet',key,'shape',df.shape)
for i,row in df.iterrows():
    probe=' '.join(str(v).lower() for v in row.values[:8] if v is not None)
    if 'indice de precios' in probe or 'ipc' in probe:
        print('row',i,probe)
        date_cols=[c for c in df.columns if isinstance(c,(pd.Timestamp,datetime))]
        print('date_cols',len(date_cols))
        vals=[(str(c)[:10],row.get(c)) for c in date_cols[:15]]
        print('sample',vals)
        break
