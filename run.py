import os
import sys
import importlib.util

# Ensure project root is first on sys.path to avoid package name conflicts
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Dynamically load server/main.py to avoid conflicts with third-party 'server'
main_path = os.path.join(ROOT, 'server', 'main.py')
spec = importlib.util.spec_from_file_location('local_server_main', main_path)
if spec is None or spec.loader is None:
    raise RuntimeError('Cannot load server/main.py')
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)  # type: ignore
app = getattr(_mod, 'app')