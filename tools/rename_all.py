"""One-off helper for migrating legacy MemBrain/CSM text references."""

from __future__ import annotations

from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
RULES = (
    ("membrain", "brainmemory"),
    ("CSM_DEEPSEEK", "BRAINMEMORY_DEEPSEEK"),
    ("CSM_EMBEDDING", "BRAINMEMORY_EMBEDDING"),
    ("CSM_LLM", "BRAINMEMORY_LLM"),
    ("CSM_API_KEY", "BRAINMEMORY_API_KEY"),
    ("CSM_PROJECT_DIR", "BRAINMEMORY_PROJECT_DIR"),
    ("CSM_PYTHON", "BRAINMEMORY_PYTHON"),
    ("CSM_PORT", "BRAINMEMORY_PORT"),
    ("CSM_HOST", "BRAINMEMORY_HOST"),
    ("CSM_DB", "BRAINMEMORY_DB"),
)
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "models",
    ".pytest_cache",
    ".pytest_tmp",
    ".tmp",
    ".csm_eval",
}
SKIP_SUFFIXES = {".pyc", ".db", ".pdf", ".safetensors", ".bin", ".pth"}


def process_file(path: Path) -> bool:
    if path.suffix in SKIP_SUFFIXES or path.name.endswith((".db-wal", ".db-shm")):
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    modified = content
    for old, new in RULES:
        modified = modified.replace(old, new)
    if modified == content:
        return False
    path.write_text(modified, encoding="utf-8")
    return True


def main() -> None:
    count = 0
    for path in BASE.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if process_file(path):
            count += 1
            print(f"modified: {path.relative_to(BASE)}")
    print(f"{count} files modified")


if __name__ == "__main__":
    main()
