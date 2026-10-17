"""Root package alias forwarding to backend.app for seamless IDE and runner resolution."""
import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent / "backend"
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
