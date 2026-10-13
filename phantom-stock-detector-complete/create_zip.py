"""Create the distributable ZIP while excluding caches and generated outputs."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
ZIP_PATH = ROOT.parent / "phantom-stock-detector-backend.zip"
EXCLUDED_PARTS = {".venv", "venv", "__pycache__", ".pytest_cache"}
EXCLUDED_NAMES = {"phantom-stock-detector-backend.zip"}

def create_zip():
    """Package project source and documentation into a ZIP."""
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(ROOT)
            if any(part in EXCLUDED_PARTS for part in relative.parts) or path.name in EXCLUDED_NAMES:
                continue
            if relative.parts[0] == "output" and path.name not in {"README.md", ".gitkeep"}:
                continue
            if relative.parts[0] == "data" and path.name not in {"README.md", ".gitkeep"}:
                continue
            archive.write(path, Path(ROOT.name) / relative)
    print(f"Created ZIP: {ZIP_PATH}")

if __name__ == "__main__":
    create_zip()
