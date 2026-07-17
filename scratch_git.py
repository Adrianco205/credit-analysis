import subprocess
import os

print(os.getcwd())
res = subprocess.run(["git", "status"], capture_output=True, text=True)
print(res.stdout)
