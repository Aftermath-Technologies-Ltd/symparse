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
- CLI argument `--log-level {DEBUG,INFO,WARNING,ERROR}` for granular logging control.
- CLI argument `--sanitize` to strip control characters from stdin before the AI Path (prompt injection mitigation).
- CLI argument `--max-tokens` (default: 4000) to cap LLM token spend per request and prevent accidental API bill spikes.
- Full CLI help reference in README for `run`, `cache`, and global flags.
- `CHANGELOG.md` linked from contributing section.

### Changed
- Replaced Unix-exclusive `fcntl` caching mechanism with cross-platform `portalocker` (pinned to `==2.10.1`) to enable Windows compatibility.
- Removed residual `fcntl` imports from `test_cache_manager.py` and `test_e2e.py` to ensure all tests are cross-platform.
- Pinned all dependency versions exactly (`litellm==1.60.2`, `portalocker==2.10.1`, `openai==1.61.0`, `google-re2==1.0.0`, `jsonschema==4.23.0`, `sentence-transformers==3.4.1`, `torch==2.5.1`) to prevent supply-chain drift.
- Fixed all README copy to accurately describe the Fast Path as "sandboxed Python scripts wrapping `re2`" — removed all legacy "compiled C++ regular expressions" claims.
- Expanded Known Limitations with actionable mitigations for prompt injection (`--sanitize`), nondeterminism, embed size, AI Path rate-limiting, and Windows compatibility.
- Fixed mojibake characters in Cache Management section header.
- Updated demo script version references from `v0.1.1` to `v0.2.0`.
- Added `requires-python = ">=3.10"` and full Python version classifiers to `pyproject.toml`.

### Security
- Added `--sanitize` flag to strip control characters from stdin before LLM prompt injection surface.
- Added `--max-tokens 4000` guard to cap per-request token spend and prevent runaway API costs on cache-miss loops.
- Cached compiled definitions enforce strict `0o700` user-only sandbox directory permissions.
- Hardcoded `temperature=0.0` in all LLM calls to minimize nondeterminism.
- Fully pinned exact dependency versions to mitigate transient supply-chain drift.
- Documented prompt injection surface with concrete mitigations (sanitize, pre-filter input, compile-first workflow, Fast Path isolation).

## [0.1.1] - 2026-02-05
### Added
- Initial public release conceptualizing Two-Tier compiler flow (LLM caching down to Google Re2).
