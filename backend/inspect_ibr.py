import pandas as pd
import requests
from io import BytesIO

url='https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/IBR.xlsx'
content=requests.get(url,timeout=60).content
wb=pd.read_excel(BytesIO(content),sheet_name=None,engine='openpyxl',header=None)
print('sheets', list(wb.keys()))
df=list(wb.values())[0]
print('shape', df.shape)
print(df.head(30).to_string())
