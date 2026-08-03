import subprocess

try:
    with open("git_history.txt", "w", encoding="utf-8") as f:
        # Get the commit hash for "V1 de Perfinanzas ya entregado"
        result = subprocess.run(["git", "log", "--grep=V1 de Perfinanzas ya entregado", "--format=%H"], capture_output=True, text=True)
        commit_hash = result.stdout.strip().split('\n')[0]
        f.write(f"Commit hash: {commit_hash}\n\n")
        
        # Show the calc_service.py at that commit
        if commit_hash:
            subprocess.run(["git", "show", f"{commit_hash}:backend/app/services/calc_service.py"], stdout=f, stderr=subprocess.STDOUT)
            f.write("\n\n" + "="*80 + "\n\n")
            subprocess.run(["git", "show", f"{commit_hash}:backend/app/services/analysis_service.py"], stdout=f, stderr=subprocess.STDOUT)
    print("Done")
except Exception as e:
    with open("git_history.txt", "w") as f:
        f.write(str(e))
