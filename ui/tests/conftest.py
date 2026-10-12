import sys
from pathlib import Path

# The UI modules import each other as top-level modules (as `streamlit run ui/app.py` does).
UI_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(UI_DIR))
