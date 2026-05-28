from __future__ import annotations

import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ZIP_NAME = "Submission_RAG.zip"
ZIP_PATH = ROOT / ZIP_NAME

REQUIRED_FILES = [
    "app.py",
    "requirements.txt",
    "README.md",
    "Dockerfile",
    "docker-compose.yml",
    ".env.example",
    "package_submission.py",
]

REQUIRED_DIRECTORIES = [
    "src",
    "scripts",
    ".streamlit",
]

EXCLUDED_FILE_NAMES = {
    ".env",
    "apis.txt",
    "apiss.txt",
}

EXCLUDED_DIRECTORIES = {
    ".venv",
    "__pycache__",
    "data",
    ".git",
    ".pytest_cache",
}

EXCLUDED_SUFFIXES = {
    ".db",
    ".jsonl",
}


def must_exclude(path: Path) -> bool:
    """Return True for any file or path that must never enter the ZIP."""

    relative = path.relative_to(ROOT)
    parts = set(relative.parts)
    if parts.intersection(EXCLUDED_DIRECTORIES):
        return True
    if path.name in EXCLUDED_FILE_NAMES:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    return False


def validate_required_inputs() -> None:
    missing: list[str] = []
    for filename in REQUIRED_FILES:
        if not (ROOT / filename).is_file():
            missing.append(filename)
    for directory in REQUIRED_DIRECTORIES:
        if not (ROOT / directory).is_dir():
            missing.append(directory + "/")
    if missing:
        raise FileNotFoundError(f"Missing required submission inputs: {', '.join(missing)}")


def iter_submission_files() -> list[Path]:
    """Collect exactly the approved files and recursive directory contents."""

    files: list[Path] = []
    for filename in REQUIRED_FILES:
        path = ROOT / filename
        if not must_exclude(path):
            files.append(path)

    for directory in REQUIRED_DIRECTORIES:
        base = ROOT / directory
        for path in sorted(base.rglob("*")):
            if path.is_file() and not must_exclude(path):
                files.append(path)

    return sorted(set(files), key=lambda item: item.relative_to(ROOT).as_posix())


def validate_zip_contents(names: list[str]) -> None:
    """Fail the build if a fatal security exclusion appears in the archive."""

    forbidden: list[str] = []
    for name in names:
        path = Path(name)
        if path.name in EXCLUDED_FILE_NAMES:
            forbidden.append(name)
        if path.suffix.lower() in EXCLUDED_SUFFIXES:
            forbidden.append(name)
        if set(path.parts).intersection(EXCLUDED_DIRECTORIES):
            forbidden.append(name)

    if forbidden:
        raise RuntimeError("Forbidden files detected in ZIP: " + ", ".join(sorted(set(forbidden))))

    required_names = {Path(filename).as_posix() for filename in REQUIRED_FILES}
    missing = sorted(required_names.difference(names))
    if missing:
        raise RuntimeError("Required files missing from ZIP: " + ", ".join(missing))


def build_zip() -> None:
    validate_required_inputs()
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    files = iter_submission_files()
    with zipfile.ZipFile(ZIP_PATH, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in files:
            archive.write(file_path, file_path.relative_to(ROOT).as_posix())

    with zipfile.ZipFile(ZIP_PATH, mode="r") as archive:
        names = archive.namelist()
    validate_zip_contents(names)

    print(f"Created {ZIP_PATH}")
    print(f"Included files: {len(names)}")
    print(f"Archive size: {ZIP_PATH.stat().st_size} bytes")


if __name__ == "__main__":
    build_zip()
