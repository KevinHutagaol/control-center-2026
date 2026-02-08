import sys
from pathlib import Path


def resource_path(rel: str | Path) -> str:
    rel_path = Path(rel)

    # 0) Absolute path: just return it (don’t prepend bases)
    if rel_path.is_absolute():
        return str(rel_path)

    candidates: list[Path] = []

    # 1) PyInstaller onefile: temp unpack dir
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)
        candidates += [base / rel_path, base / "_internal" / rel_path]

    # 2) PyInstaller onedir: beside the executable
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        candidates += [exe_dir / rel_path, exe_dir / "_internal" / rel_path]

    # 3) Dev: walk upwards so root-level assets can be found from subpackages
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        candidates.append(parent / rel_path)
        candidates.append(parent / "_internal" / rel_path)

    # Pick the first existing candidate
    for c in candidates:
        if c.exists():
            return str(c)

    # Fallback: return the first candidate even if missing (caller can handle)
    return str(candidates[0])


def bundle_path() -> Path:
    """Path to the outer executable or script."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve()
    else:
        return Path(__file__).resolve()


def bundle_dir() -> Path:
    """Directory containing the real exe (not the _MEI temp)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    else:
        return Path(__file__).resolve().parent
