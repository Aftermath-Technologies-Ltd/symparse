# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-26
### Added
- **Multi-Model Support**: Native integration with `litellm` allows seamless drop-in of OpenAI, Anthropic, vLLM, and Ollama backends via the `--model` flag and `~/.symparserc` config files.
- **Nested Schema Compilation**: The LLM compiler now dynamically writes sandboxed Python `def extract()` dict-builders instead of flat matching strings, expanding 95% execution coverage to deep nested JSON.
- **Semantic Tier-2 Caching**: Incorporated local Contrastive Collision checks using exact sentence transformer thresholding (enabled via `--embed` flag and `symparse[embed]`).
- **Telemetry & Streaming**: The `run` command now features true unbuffered `stdin` stream processing for commands like `tail -f`, alongside a robust `--stats` flag for cycle metrics and average latency tracking.
- **Packaged Demo**: `symparse-demo` entry point (via `symparse[demo]` extra) for recording terminal demos without a live LLM.
- **Expanded Benchmarking Suite**: `examples/` now contains exhaustive multi-format schemas (Nginx, JSONL, Invoices, Kubernetes) plus a 100-line real-world Nginx access log sample (`examples/sample_nginx.log`) for independent verification.
- CLI argument `--version` on the global parser.
- CLI argument `-v/--verbose` for debug logging.
- Full CLI help reference in README for `run`, `cache`, and global flags.
- `CHANGELOG.md` linked from contributing section.

### Changed
- Replaced Unix-exclusive `fcntl` caching mechanism with cross-platform `portalocker` (pinned to `==2.10.1`) to enable Windows compatibility.
- Removed residual `fcntl` imports from `test_cache_manager.py` and `test_e2e.py` to ensure all tests are cross-platform.
- Pinned all dependency versions exactly (`litellm==1.60.2`, `portalocker==2.10.1`, `openai==1.61.0`, `google-re2==1.0.0`, `jsonschema==4.23.0`, `sentence-transformers==3.4.1`, `torch==2.5.1`) to prevent supply-chain drift.
- Fixed README Fast Path description to accurately reflect sandboxed `re2`-based Python extraction scripts (not raw "regex blocks").
- Expanded Known Limitations with actionable mitigations for prompt injection, nondeterminism, embed size, and Windows compatibility.
- Updated demo script version references from `v0.1.1` to `v0.2.0`.
- Added `requires-python = ">=3.10"` and full Python version classifiers to `pyproject.toml`.

### Security
- Cached compiled definitions enforce strict `0o700` user-only sandbox directory permissions.
- Fully pinned exact dependency versions to mitigate transient supply-chain drift.
- Documented prompt injection surface with concrete mitigations (pre-filter input, compile-first workflow, Fast Path isolation).

## [0.1.1] - 2026-02-05
### Added
- Initial public release conceptualizing Two-Tier compiler flow (LLM caching down to Google Re2).
