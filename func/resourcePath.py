import inspect
from pathlib import Path
import sys

def resource_path(rel: str) -> str:
    rel_path = Path(rel)
    caller_frame = inspect.stack()[1]
    caller_file = Path(caller_frame.filename).resolve().parent  # directory of the caller

    candidates = []

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        candidates += [base / rel_path, base / "_internal" / rel_path]

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates += [exe_dir / rel_path, exe_dir / "_internal" / rel_path]

    candidates.append(caller_file / rel_path)

    for c in candidates:
        if c.exists():
            return str(c)
    return str(candidates[0])
