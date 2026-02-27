# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-26
### Added
- **Multi-Model Support**: Native integration with `litellm` allows seamless drop-in of OpenAI, Anthropic, vLLM, and Ollama backends via the `--model` flag and `~/.symparserc` files.
- **Nested Schema Compilation**: The LLM compiler now dynamically writes sandboxed Python `def extract()` dict-builders instead of flat matching strings, expanding 95% execution coverage to deep nested JSON.
- **Semantic Tier-2 Caching**: Incorporated local Contrastive Collision checks using exact sentence transformer thresholding (enabled via `--embed` flag and `symparse[embed]`).
- **Telemetry & Streaming**: The `run` command now features true unbuffered `stdin` stream processing for commands like `tail -f`, alongside a robust `--stats` flag for cycle metrics and average latency tracking.
- **Packaged Viral Demo**: Exported `scripts/record_demo.py` into a core executable `symparse-demo` (via `symparse[demo]`) to allow seamless community benchmarking videos.
- **Expanded Benchmarking Suite**: `examples/` now contains exhaustive multi-format schemas (Nginx, JSONL, Invoices, Kubernetes) heavily tested for accuracy.
- CLI argument `--version`.

### Changed
- Replaced Unix-exclusive `fcntl` caching mechanism with cross-platform `portalocker` to enable seamless Windows compatibility.
- Transitioned cache lock modes from generic shared memory maps to strictly serialized JSON block definitions to avert concurrency overwrites.
- Re-architected README with comprehensive hardware context variance and security disclaimers (Nondeterminism + Stdin Injection).

### Security
- Cached compiled definitions now enforce strict `0700` user-only sandbox directory permissions for system egress safety.
- Fully pinned exact versions for `openai`, `google-re2`, `jsonschema`, `sentence-transformers`, and `torch` to completely mitigate transient dependency supply-chain drift.

## [0.1.1] - 2026-02-05
### Added
- Initial public release conceptualizing Two-Tier compiler flow (LLM caching down to Google Re2).
