import subprocess
import os

try:
    with open("git_log.txt", "w", encoding="utf-8") as f:
        subprocess.run(["git", "log", "--grep=V1 de Perfinanzas ya entregado", "-p"], stdout=f, stderr=subprocess.STDOUT)
    print("Success")
except Exception as e:
    with open("git_log_error.txt", "w") as f:
        f.write(str(e))
