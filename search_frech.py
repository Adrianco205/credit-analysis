import os

def search_files(directory, query):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if not file.endswith('.py'):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if query in content:
                        print(f"Found in {path}")
            except Exception:
                pass

search_files('backend/app', 'La vigencia del FRECH no está confirmada')
