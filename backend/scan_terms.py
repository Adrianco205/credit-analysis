import pandas as pd
import requests
from io import BytesIO

url='https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/paginas/inddiarios_new.xls'
content=requests.get(url,timeout=60).content
wb=pd.read_excel(BytesIO(content),sheet_name=None,engine='xlrd',header=None)
terms=['uvr','unidad de valor real','ipc','indice de precios','inflacion']
for name,df in wb.items():
    text=' '.join(df.astype(str).fillna('').values.ravel().astype(str)).lower()
    hits=[t for t in terms if t in text]
    if hits:
        print(name,hits)
