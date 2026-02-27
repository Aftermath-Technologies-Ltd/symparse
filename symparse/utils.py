"""Shared utilities for binary detection, token estimation, and .gitignore-aware filtering."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# --- Binary Detection ---

# Common binary file extensions to reject outright without content sniffing
BINARY_EXTENSIONS = frozenset({
    ".pickle", ".pkl", ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe",
    ".bin", ".dat", ".db", ".sqlite", ".sqlite3",
    ".gz", ".bz2", ".xz", ".zst", ".zip", ".tar", ".rar", ".7z",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv", ".flac",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".class", ".jar", ".war", ".o", ".a", ".lib",
    ".wasm", ".parquet", ".arrow", ".avro", ".protobuf",
})


def is_binary_content(data: bytes, sample_size: int = 1024) -> bool:
    """Detect binary content by checking for null bytes in the first *sample_size* bytes.

    This is the standard heuristic used by Git, file(1), and most editors.
    A single ``\\x00`` in the leading chunk is a reliable binary indicator.
    """
    chunk = data[:sample_size]
    return b"\x00" in chunk


def is_binary_file(path: Path) -> bool:
    """Return True if *path* looks like a binary file (extension or content sniff)."""
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(path, "rb") as f:
            return is_binary_content(f.read(1024))
    except (OSError, PermissionError):
        return True  # Treat unreadable files as binary


def is_binary_line(line: str) -> bool:
    """Quick check on a single stdin line for embedded binary/null-byte artifacts."""
    return "\x00" in line


# --- Lightweight Token Estimation ---

# Approximate BPE token ratios calibrated against tiktoken cl100k_base (GPT-4/Claude):
#   English prose:   ~4.0 chars/token
#   Python code:     ~3.5 chars/token
#   JSON/structured: ~3.0 chars/token
#   Mixed/average:   ~3.5 chars/token
_DEFAULT_CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str, chars_per_token: float = _DEFAULT_CHARS_PER_TOKEN) -> int:
    """Estimate the number of BPE tokens for *text* without importing a tokenizer.

    Uses a conservative 3.5 chars/token ratio calibrated against ``tiktoken``
    cl100k_base (the encoding used by GPT-4o and Claude).  This is intentionally
    an *overestimate* so that context-window budget warnings err on the safe side.
    """
    return max(1, int(len(text) / chars_per_token))


# Well-known context window sizes for popular models
MODEL_CONTEXT_WINDOWS = {
    "gpt-4o": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-haiku": 200_000,
    "gemma3:1b": 8_192,
    "llama3": 8_192,
}


def token_budget_warning(text: str, model: str = None) -> str | None:
    """Return a human-readable warning if *text* is likely to exceed 50% of the model context, else None."""
    estimated = estimate_tokens(text)
    if model:
        # Strip provider prefix (e.g. "ollama/gemma3:1b" -> "gemma3:1b")
        short_model = model.split("/", 1)[-1] if "/" in model else model
        window = MODEL_CONTEXT_WINDOWS.get(short_model)
        if window and estimated > window * 0.5:
            return (
                f"Estimated {estimated:,} tokens (~{len(text):,} chars) exceeds 50% of "
                f"{short_model} context window ({window:,} tokens). "
                f"Consider splitting input or using a larger model."
            )
    # Generic warning for very large inputs (> ~30k tokens)
    if estimated > 30_000:
        return f"Estimated {estimated:,} tokens (~{len(text):,} chars). Large inputs may degrade extraction quality or hit token limits."
    return None


# --- .gitignore-aware Smart Ignore ---

def parse_gitignore(root: Path) -> list[str]:
    """Parse a .gitignore at *root* and return a list of non-comment, non-empty patterns."""
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    patterns = []
    try:
        for raw_line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    except OSError:
        pass
    return patterns


def should_ignore(path: Path, patterns: list[str], root: Path | None = None) -> bool:
    """Return True if *path* matches any gitignore-style *patterns*.

    Supports basic gitignore semantics:
    - ``*.ext`` matches any file with that extension
    - ``dirname/`` matches directories by name
    - ``path/to/thing`` matches relative paths
    - Negation (``!pattern``) is **not** supported for simplicity
    """
    # Normalise to forward-slash relative path for matching
    try:
        rel = path.relative_to(root).as_posix() if root else path.as_posix()
    except ValueError:
        rel = path.as_posix()

    name = path.name

    for pattern in patterns:
        if pattern.startswith("!"):
            continue  # Negation not supported

        # Directory pattern (e.g. __pycache__/)
        if pattern.endswith("/"):
            dir_name = pattern.rstrip("/")
            if dir_name in rel.split("/"):
                return True
            continue

        # Exact relative path match
        if "/" in pattern:
            if rel == pattern or rel.startswith(pattern + "/"):
                return True
            continue

        # Wildcard extension match (e.g. *.pyc)
        if pattern.startswith("*."):
            ext = pattern[1:]  # e.g. ".pyc"
            if name.endswith(ext):
                return True
            continue

        # Plain name match (matches anywhere in the tree)
        if name == pattern:
            return True

    return False
