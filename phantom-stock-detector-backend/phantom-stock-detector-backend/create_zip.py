"""Create the requested distributable ZIP archive."""
from pathlib import Path
import zipfile

def main():
    project_dir = Path(__file__).resolve().parent
    zip_path = project_dir.parent / "phantom-stock-detector-backend.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(project_dir.rglob("*")):
            if path.is_file() and not any(part in {".venv", "__pycache__", ".pytest_cache"} for part in path.parts):
                archive.write(path, path.relative_to(project_dir.parent))
    print(f"Created: {zip_path}")

if __name__ == "__main__":
    main()
