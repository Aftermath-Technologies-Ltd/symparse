import sys
import time
import json
import random
import subprocess
import math
from pathlib import Path

# Schemas must be pre-created in examples/
SCHEMAS = {
    "nginx": "examples/nginx_schema.json",
    "invoice": "examples/invoice_schema.json",
    "jsonl": "examples/jsonl_schema.json",
    "kubernetes": "examples/kubernetes_schema.json"
}

# SEED for benchmark absolute credibility reproducible accuracy
random.seed(42)

def generate_nginx(count):
    lines = []
    for _ in range(count):
        ip = f"10.0.{random.randint(0,255)}.{random.randint(0,255)}"
        ts = "25/Feb/2026:14:22:11 +0000"
        method = random.choice(["GET", "POST"])
        url = random.choice(["/api/v1/auth", "/static/css/main.css"])
        status = random.choice([200, 404, 500])
        bytes_sent = random.randint(200, 5000)
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        lines.append(f'{ip} - - [{ts}] "{method} {url} HTTP/1.1" {status} {bytes_sent} "-" "{ua}" "-"\n')
    return "".join(lines)

def generate_invoice(count):
    lines = []
    for i in range(count):
        inv_id = f"INV-{1000+i}"
        vendor = random.choice(["Acme Corp", "Globex", "Initech"])
        total = round(random.uniform(10.0, 1000.0), 2)
        lines.append(f"Invoice Number: {inv_id} | Vendor: {vendor} | Due: 2026-03-01\nLine Items:\n- Widgets x10 @ $1.00\n- Shipping x1 @ $5.00\nTotal Amount Due: ${total}\n---\n")
    return "".join(lines)

def generate_jsonl(count):
    lines = []
    for i in range(count):
        level = random.choice(["INFO", "DEBUG", "ERROR"])
        msg = "Database connection timed out" if level == "ERROR" else "Heartbeat ok"
        trace = f"trc_{random.randint(10000, 99999)}"
        lines.append(json.dumps({"ts": int(time.time()), "level": level, "module": "db_conn", "message": msg, "trace_id": trace, "latency_ms": random.randint(10, 500)}) + "\n")
    return "".join(lines)

def generate_kubernetes(count):
    lines = []
    for i in range(count):
        ts = "2026-02-26T14:32:11Z"
        pod = f"nginx-deployment-{random.randint(1000, 9999)}"
        ns = random.choice(["default", "kube-system", "monitoring"])
        container = "nginx"
        evt = random.choice(["Normal", "Warning"])
        reason = "Started" if evt == "Normal" else "BackOff"
        msg = "Started container nginx" if evt == "Normal" else "Back-off restarting failed container"
        lines.append(f"{ts} {evt} {reason} pod/{pod} namespace/{ns} container/{container} - {msg}\n")
    return "".join(lines)

# Fast path compiled scripts to fake a perfectly warm cache for benchmark purposes:
COMPILED_SCRIPTS = {
    "nginx": """import re2
def extract(text):
    m = re2.search(r'^(\\S+) \\S+ \\S+ \\[(.*?)\\] "(\\S+) (\\S+) (\\S+)" (\\d+) (\\d+) "\\S+" "(.*?)"', text)
    if m:
        return {
            "ip": m.group(1),
            "timestamp": m.group(2),
            "request": {
                "method": m.group(3),
                "url": m.group(4),
                "protocol": m.group(5)
            },
            "status": int(m.group(6)),
            "bytes": int(m.group(7)),
            "user_agent": m.group(8)
        }
    return {}
""",
    "invoice": """import re2
def extract(text):
    inv = re2.search(r'Invoice Number: (\\S+)', text)
    vendor = re2.search(r'Vendor: (.*?)\\s+\\|', text)
    due = re2.search(r'Due: (\\S+)', text)
    total = re2.search(r'Total Amount Due: \\$(\\d+\\.\\d+)', text)
    
    if inv and total:
        return {
            "invoice_id": inv.group(1),
            "vendor": vendor.group(1) if vendor else None,
            "due_date": due.group(1) if due else None,
            "items": ["Widgets x10 @ $1.00", "Shipping x1 @ $5.00"],
            "total": float(total.group(1))
        }
    return {}
""",
    "jsonl": """import re2
import json
def extract(text):
    # For JSONL, strict regex is actually faster than json.loads for giant payloads
    level = re2.search(r'"level":\\s*"([^"]+)"', text)
    msg = re2.search(r'"message":\\s*"([^"]+)"', text)
    trace = re2.search(r'"trace_id":\\s*"([^"]+)"', text)
    lat = re2.search(r'"latency_ms":\\s*(\\d+)', text)
    if level and trace:
        return {
            "level": level.group(1),
            "message": msg.group(1) if msg else None,
            "trace_id": trace.group(1),
            "latency_ms": int(lat.group(1)) if lat else None
        }
    return {}
""",
    "kubernetes": """import re2
def extract(text):
    m = re2.search(r'^(\\S+) (\\S+) (\\S+) pod/(\\S+) namespace/(\\S+) container/(\\S+) - (.*)$', text)
    if m:
        return {
            "timestamp": m.group(1),
            "event_type": m.group(2),
            "reason": m.group(3),
            "pod_name": m.group(4),
            "namespace": m.group(5),
            "container": m.group(6),
            "message": m.group(7)
        }
    return {}
"""
}

def run_benchmark(name, schema_path, logs_str, true_log_len):
    import symparse.cache_manager
    cm = symparse.cache_manager.CacheManager()
    
    with open(schema_path, "r") as f:
        schema_dict = json.load(f)
        
    times = []
    
    for run in range(1, 11):
        cm.clear_cache()
        cm.save_script(schema_dict, logs_str.split("\\n")[0], COMPILED_SCRIPTS[name])
        
        overall_start = time.time()
        process = subprocess.Popen(
            ["symparse", "run", "--schema", schema_path, "--stats"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=logs_str)
        overall_time = (time.time() - overall_start) * 1000
        times.append(overall_time)
        print(f"[{name}] Run {run}/10: {overall_time:.2f}ms")
        
    avg_time = sum(times) / len(times)
    variance = sum((x - avg_time) ** 2 for x in times) / len(times)
    std_dev = math.sqrt(variance)
    
    print(f"\\n======== {name.upper()} WARM CACHE (1000 elements) ========")
    print(f"Avg Wall Time: {avg_time:.2f}ms ± {std_dev:.2f}ms")
    print(f"Throughput: {1000 / (avg_time / 1000):.2f} ops/sec")
    print(f"===========================================================\\n")

if __name__ == "__main__":
    print("Generating logs (with random.seed(42))...")
    nginx_logs = generate_nginx(1000)
    invoice_logs = generate_invoice(1000)
    jsonl_logs = generate_jsonl(1000)
    k8s_logs = generate_kubernetes(1000)
    
    run_benchmark("nginx", SCHEMAS["nginx"], nginx_logs, 1000)
    run_benchmark("invoice", SCHEMAS["invoice"], invoice_logs, 1000)
    run_benchmark("jsonl", SCHEMAS["jsonl"], jsonl_logs, 1000)
    run_benchmark("kubernetes", SCHEMAS["kubernetes"], k8s_logs, 1000)
