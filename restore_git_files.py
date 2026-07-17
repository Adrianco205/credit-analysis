import subprocess
import os

def restore_file(filepath):
    # Find the last commit where the file was NOT empty
    cmd = f'git log --pretty=format:"%h" -- "{filepath}"'
    commits = subprocess.check_output(cmd, shell=True, text=True).strip().split('\n')
    
    for commit in commits:
        if not commit: continue
        # Check size of file in this commit
        size_cmd = f'git ls-tree -r -l {commit} "{filepath}"'
        out = subprocess.check_output(size_cmd, shell=True, text=True).strip()
        if out:
            # Output format: mode type hash size filepath
            parts = out.split()
            if len(parts) >= 4:
                size = int(parts[3])
                if size > 0:
                    print(f"Restoring {filepath} from commit {commit} (size: {size} bytes)")
                    subprocess.run(f'git checkout {commit} -- "{filepath}"', shell=True)
                    return True
    print(f"Could not find a non-empty version of {filepath}")
    return False

os.chdir(r"D:\Perfinanzas\credit-analysis")
restore_file("backend/alembic.ini")
restore_file("backend/alembic/env.py")
restore_file("backend/pyproject.toml")
