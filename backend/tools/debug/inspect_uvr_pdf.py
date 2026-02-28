import requests, re
from io import BytesIO
from pypdf import PdfReader

url='https://d1b4gd4m8561gs.cloudfront.net/sites/default/files/datos_estadisticos_uvr.pdf'
resp=requests.get(url,timeout=60)
print('status',resp.status_code,'ct',resp.headers.get('content-type'),'size',len(resp.content))
reader=PdfReader(BytesIO(resp.content))
text='\n'.join((p.extract_text() or '') for p in reader.pages[:3])
print(text[:2000])
print('has 2026?', '2026' in text)
