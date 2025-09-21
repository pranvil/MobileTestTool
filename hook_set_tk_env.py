import os,sys
from pathlib import Path
base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
os.environ.setdefault("TCL_LIBRARY", str(base / "lib" / "tcl8.6"))
os.environ.setdefault("TK_LIBRARY",  str(base / "lib" / "tk8.6"))
