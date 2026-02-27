<div align="center">
  <img src="docs/architecture.svg" alt="Symparse Architecture Graph" width="800">

  <h1><code>symparse</code></h1>
  
  <p><strong>The AI <code>jq</code> for unstructured text. From 100% LLM latency to 95% regex speeds in one run.</strong></p>

  <p>
    <a href="https://github.com/Aftermath-Technologies-Ltd/symparse/actions"><img src="https://img.shields.io/badge/build-passing-brightgreen?logo=github" alt="Build passing"></a>
    <a href="https://pypi.org/project/symparse/"><img src="https://img.shields.io/pypi/v/symparse?color=blue&logo=python&logoColor=white" alt="PyPI"></a>
    <a href="https://github.com/Aftermath-Technologies-Ltd/symparse/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-purple" alt="License: MIT"></a>
    <img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+">
  </p>
</div>

---

**Symparse** is a self-optimizing Unix pipeline tool that routes data between an **AI Path** (using local LLMs/Ollama) and a **Fast Path** (using cached `<re2>` regex blocks) with a strict neurosymbolic JSON validation gate.

You get the magical, unstructured data extraction of Large Language Models, with the raw performance and ReDoS-safety of compiled C++ regular expressions on 95% of subsequent matched traffic.

## 🚀 Installation

Install Symparse from PyPI:

```bash
pip install symparse
```

Or with optional but recommended Tier-2 Local Vector Embeddings (uses `sentence-transformers` for vastly superior cache hit-rates against polymorphic logs):

```bash
pip install symparse[embed]
```

Or from source:

```bash
git clone https://github.com/Aftermath-Technologies-Ltd/symparse.git
cd symparse
pip install -e .
```

## ⚡ Usage

Symparse is built for Unix pipes. You stream standard text into `stdin` and provide a JSON Schema describing your desired format. Symparse enforces that structure and outputs valid JSON objects to `stdout`.

### Basic Example

Parse a messy raw text log into a clean standard JSON string:

```bash
# We have a messy text input:
echo "User alice@example.com logged in from 192.168.1.50 at 10:45 AM" | \
symparse run --schema login_schema.json --compile
```

** `login_schema.json` **:
```json
{
  "type": "object",
  "properties": {
    "email": { "type": "string" },
    "ip_address": { "type": "string" }
  },
  "required": ["email", "ip_address"]
}
```

** Output (`stdout`) **:
```json
{
  "email": "alice@example.com",
  "ip_address": "192.168.1.50"
}
```

Because we passed `--compile`, Symparse will use the LLM (AI Path) on this first pass to deduce a standard Re2 regex schema. The next time a log matching this prototype is fired, Symparse will hit the **Fast Path Cache**, completely bypassing the LLM. 

### Live Verified Fallback (Graceful Degradation)

Symparse is built to natively handle imperfect LLM generation on the fly. In a live test using the lightweight local `gemma3:1b` model to parse messy logs, here is how the neurosymbolic loop behaved:

1. **Log 1 (`Cold Start`)**: User logs in. LLM extracts correctly and creates a Fast Path Regex Cache.
2. **Log 2 (`Fast Path`)**: User logs out. Symparse attempts to use the Regex cache.
3. **Execution**: The Regex cache was slightly imprecise (a flaw in the 1B parameter model's generation), missing a field requirement.
4. **Graceful Self-Healing**: Symparse detected the strict `SchemaViolationError` mid-stream, safely purged the flawed Regex from its cache, seamlessly fell back to the local `gemma3:1b` AI Path, precisely extracted the exact JSON needed, and returned it to `stdout`—all without crashing the active Unix pipeline.

### Streaming Logs (`tail -f`)

Symparse excels at processing live unstructured data feeds. 
For example, attaching it directly to an Apache or Nginx log tail stream:

```bash
tail -f /var/log/nginx/access.log | symparse run --schema access_schema.json --compile >> parsed_logs.jsonl
```

### CLI Options

* `--schema <path>`: **Required**. Path to the local JSON schema file to enforce.
* `--compile`: Compiles a fast-path sandbox script on successful AI extraction.
* `--force-ai`: Bypasses the local fast-path cache entirely and routes all data to the AI.
* `--confidence <float>`: Overrides the average token logprob threshold for the AI egress gate (default: `-2.0`).
* `--embed`: Activates semantic Dense Vector tier-2 cache checks instead of simple Jaccard similarity (requires `symparse[embed]`).
* `--stats`: Prints the engine cache hit/miss ratio, latency averages, and stream velocity on exit.

## 🐳 Docker (Pre-Loaded Fast Start)

To completely eliminate the "Does it work on my machine?" factor and remove the need to configure a local Ollama daemon, you can run the pre-packaged Symparse container.

The standard image comes bundled with Ollama and `gemma3:1b` downloaded.

```bash
docker pull aftermath/symparse:latest
docker run -i --rm aftermath/symparse run --schema my_schema.json < logs.txt
```

## 🎬 Viral 60-Second Demo

We have provided an automated terminal typing simulation script perfect for recording marketing GIFs (e.g. via Asciinema or QuickTime).

```bash
python scripts/record_demo.py
```

## 🏎️ Benchmarks

How fast is the exact same Unix pipe once the AI successfully compiles the cache?

We ran `symparse run --stats` iteratively over batches of 1,000 dense synthetic lines down the warmed **Fast Path**. 

| Schema Type | Description | Avg Wall Time (1000 lines) | Throughput |
| --- | --- | --- | --- |
| **Apache Basic** | Flat regex string matching | `424.13ms ± 9.91ms` | `~2,357 ops/sec` |
| **Nginx Nested** | Nested dict-building (IP, Request obj, HTTP) | `1669.13ms ± 75.88ms` | `~599 ops/sec` |
| **Kubernetes Audit** | Deeply structured event parsing | `1771.30ms ± 79.56ms` | `~564 ops/sec` |
| **Invoices** | Heavy multiline text slicing/casting | `1703.53ms ± 106.56ms`| `~587 ops/sec` |
| **JSONL Polishing** | Plucking sparse target keys from giant files | `1757.71ms ± 75.51ms` | `~568 ops/sec` |

> [!NOTE]
> **Real-world Variance**: Throughput scales inversely with schema nesting depth, regex multiline complexity, and CPU hardware. The `2300+ ops/sec` figure assumes flat data on standard server hardware; extremely nested JSON builders pulling disjoint strings across megabytes of context will naturally trend toward `500-800 ops/sec`. However, this still represents a massive magnitude leap over performing 1000 synchronous 1-second native LLM iterations. Note: To guarantee rigorous reproducibility, `benchmarks/run_examples.py` strictly utilizes `random.seed(42)` on all generated text workloads.

See the `examples/` directory for the raw configurations.

## �🗄️ Cache Management

Symparse creates deterministic sandbox scripts under `$HOME` or a `.symparse_cache` folder. You can manage these cache rules out of the box.

```bash
symparse cache list    # List all cached schema signatures and their compiled RE2 Regexes
symparse cache clear   # Purge the local compilation directory
```

## 🐍 Python API

Symparse exposes a reliable internal Python API for direct application integrations.

### API Validation Router

Enforce strict schema properties manually via validation logic:

```python
from symparse.validator import enforce_schema, SchemaViolationError

schema = {"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}
data = {"status": "success"}

# Fast. Returns True or raises SchemaViolationError.
enforce_schema(data, schema)
```

### Pipeline Engine

Run the neurosymbolic system programmatically with graceful degradation.

```python
from symparse.engine import process_stream, GracefulDegradationMode

# Returns dict or raises EngineFailure.
result = process_stream(
    "unstructured data chunk from memory",
    schema,
    compile=True,
    max_retries=3,
    degradation_mode=GracefulDegradationMode.PASSTHROUGH
)
```

### Auto-Compiler & Cache System

Symparse builds secure, mathematically ReDoS-resistant extractions without invoking `eval()`. 

```python
from symparse.compiler import generate_script, execute_script
from symparse.cache_manager import CacheManager

manager = CacheManager()
manager.save_script(schema, "example text", "def extract(txt): ...") # Applies IPC/Unix Lock
manager.fetch_script(schema, "example text") # Uses Hybrid Two-Tier Collision Detection
manager.clear_cache()
```

## 🤝 Contributing & License

Pull requests are actively welcomed! Please read the tests architecture under `tests/` to run integration checks (`test_agent_skills.py` patterns).

Symparse is released under the MIT Open Source License. See the [LICENSE](LICENSE) file for more.

### ⚠️ Known Limitations
* **Operating System Constraints**: Symparse relies extensively on deep OS-level `fcntl` locks (`LOCK_EX` and `LOCK_SH`) to coordinate strictly serial atomic I/O cache writes across concurrent Unix pipes or `tail -f` streams. At this time, it is officially **Unix-only** (Linux & macOS). Windows compatibility may be shipped in future implementations using simulated portalocker bindings.

---
*Engineered by Aftermath Technologies Ltd. with human-in-the-loop AI assistance.*
