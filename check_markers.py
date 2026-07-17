import sys

for file_path in ['backend/app/services/uvr_projection_engine.py', 'backend/app/services/indicadores_service.py']:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if '<<<<<<<' in line or '=======' in line or '>>>>>>>' in line:
                print(f"{file_path} (Line {i+1}): {line.strip()}")
