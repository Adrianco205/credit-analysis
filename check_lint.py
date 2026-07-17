import subprocess
import os

with open("lint_out.txt", "w", encoding="utf-8") as f:
    r = subprocess.run(
        ["python", "-m", "flake8", "backend/app/services/uvr_projection_engine.py", "backend/app/services/indicadores_service.py"],
        capture_output=True, text=True
    )
    f.write(r.stdout)
    f.write(r.stderr)
