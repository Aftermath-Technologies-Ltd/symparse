"""Tests for symparse.utils – binary detection, token estimation, and gitignore parsing."""

from symparse.utils import (
    is_binary_content,
    is_binary_file,
    is_binary_line,
    estimate_tokens,
    token_budget_warning,
    parse_gitignore,
    should_ignore,
    BINARY_EXTENSIONS,
)


# --- Binary detection ---

def test_is_binary_content_with_null_byte():
    assert is_binary_content(b"hello\x00world") is True


def test_is_binary_content_clean_text():
    assert is_binary_content(b"just plain text\nwith newlines\n") is False


def test_is_binary_content_empty():
    assert is_binary_content(b"") is False


def test_is_binary_content_respects_sample_size():
    # Null byte beyond sample window should not trigger
    data = b"A" * 2048 + b"\x00"
    assert is_binary_content(data, sample_size=1024) is False


def test_is_binary_file_by_extension(tmp_path):
    pkl = tmp_path / "model.pkl"
    pkl.write_bytes(b"clean text")
    assert is_binary_file(pkl) is True


def test_is_binary_file_by_content(tmp_path):
    dat = tmp_path / "data.txt"
    dat.write_bytes(b"looks text\x00but has null")
    assert is_binary_file(dat) is True


def test_is_binary_file_clean(tmp_path):
    txt = tmp_path / "readme.txt"
    txt.write_text("hello world")
    assert is_binary_file(txt) is False


def test_is_binary_line_with_null():
    assert is_binary_line("foo\x00bar") is True


def test_is_binary_line_clean():
    assert is_binary_line("normal log line 2026-02-26") is False


def test_binary_extensions_comprehensive():
    """Ensure common problematic extensions are covered."""
    for ext in [".pickle", ".sqlite", ".gz", ".png", ".exe", ".pyc", ".wasm"]:
        assert ext in BINARY_EXTENSIONS, f"{ext} missing from BINARY_EXTENSIONS"


# --- Token estimation ---

def test_estimate_tokens_basic():
    # 350 chars / 3.5 chars per token = 100 tokens
    text = "a" * 350
    assert estimate_tokens(text) == 100


def test_estimate_tokens_minimum():
    assert estimate_tokens("hi") >= 1


def test_estimate_tokens_empty():
    # Even empty string should return at least 1
    assert estimate_tokens("") >= 1


def test_estimate_tokens_custom_ratio():
    text = "x" * 400
    # 400 / 4.0 = 100
    assert estimate_tokens(text, chars_per_token=4.0) == 100


def test_token_budget_warning_small_input():
    assert token_budget_warning("short text") is None


def test_token_budget_warning_large_input():
    big = "x" * 200_000
    warning = token_budget_warning(big)
    assert warning is not None
    assert "tokens" in warning


def test_token_budget_warning_model_specific():
    # gemma3:1b has 8192 context; 50% = 4096 tokens ≈ 14,336 chars
    text = "x" * 20_000
    warning = token_budget_warning(text, model="ollama/gemma3:1b")
    assert warning is not None
    assert "gemma3:1b" in warning


def test_token_budget_warning_model_within_budget():
    # Small input for a large-context model should be fine
    text = "x" * 100
    assert token_budget_warning(text, model="openai/gpt-4o") is None


# --- .gitignore parsing ---

def test_parse_gitignore_basic(tmp_path):
    gi = tmp_path / ".gitignore"
    gi.write_text("*.pyc\n__pycache__/\n# comment\n.env\n\n")
    patterns = parse_gitignore(tmp_path)
    assert "*.pyc" in patterns
    assert "__pycache__/" in patterns
    assert ".env" in patterns
    assert "# comment" not in patterns
    assert "" not in patterns


def test_parse_gitignore_missing(tmp_path):
    assert parse_gitignore(tmp_path) == []


def test_should_ignore_extension(tmp_path):
    patterns = ["*.pyc", "*.log"]
    assert should_ignore(tmp_path / "foo.pyc", patterns, root=tmp_path) is True
    assert should_ignore(tmp_path / "foo.py", patterns, root=tmp_path) is False


def test_should_ignore_directory(tmp_path):
    patterns = ["__pycache__/"]
    target = tmp_path / "__pycache__" / "module.cpython-312.pyc"
    assert should_ignore(target, patterns, root=tmp_path) is True


def test_should_ignore_plain_name(tmp_path):
    patterns = [".env"]
    assert should_ignore(tmp_path / ".env", patterns, root=tmp_path) is True
    assert should_ignore(tmp_path / "sub" / ".env", patterns, root=tmp_path) is True


def test_should_ignore_relative_path(tmp_path):
    patterns = ["build/output"]
    assert should_ignore(tmp_path / "build" / "output", patterns, root=tmp_path) is True
    assert should_ignore(tmp_path / "other" / "output", patterns, root=tmp_path) is False


def test_should_ignore_negation_skipped(tmp_path):
    """Negation patterns (!) are intentionally unsupported and should not match."""
    patterns = ["*.log", "!important.log"]
    assert should_ignore(tmp_path / "debug.log", patterns, root=tmp_path) is True
    # Negation is ignored, so important.log is still matched by *.log
    assert should_ignore(tmp_path / "important.log", patterns, root=tmp_path) is True
