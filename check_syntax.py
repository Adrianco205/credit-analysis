import py_compile
import traceback
import sys

try:
    py_compile.compile('backend/app/services/uvr_projection_engine.py', doraise=True)
    py_compile.compile('backend/app/services/indicadores_service.py', doraise=True)
    print("No syntax errors!")
except Exception as e:
    print(e)
