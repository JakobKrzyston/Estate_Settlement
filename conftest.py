"""Root conftest.py: add project root to sys.path so doc_parser is importable."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
