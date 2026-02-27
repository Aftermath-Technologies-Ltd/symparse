import time
import json
import random
import subprocess
from pathlib import Path

# Provide a sample schema for an Apache Access Log
SCHEMA = {
  "type": "object",
  "properties": {
    "ip": {"type": "string"},
    "user_id": {"type": "string"},
    "timestamp": {"type": "string"},
    "method": {"type": "string"},
    "path": {"type": "string"},
    "protocol": {"type": "string"},
    "status": {"type": "integer"},
    "bytes": {"type": "integer"}
  }
}

def generate_logs(count=1000):
    methods = ["GET", "POST", "PUT", "DELETE", "HEAD"]
    paths = ["/index.html", "/api/data", "/login", "/images/logo.png"]
    protocols = ["HTTP/1.1", "HTTP/2.0"]
    
    logs = []
    for i in range(count):
        ip = f"192.168.1.{random.randint(1, 255)}"
        user = f"user{random.randint(1, 100)}" if random.random() > 0.5 else "-"
        timestamp = "10/Oct/2000:13:55:36 -0700"
        method = random.choice(methods)
        path = random.choice(paths)
        protocol = random.choice(protocols)
        status = random.choice([200, 201, 301, 404, 500])
        byte_size = random.randint(100, 5000)
        
        logline = f'{ip} - {user} [{timestamp}] "{method} {path} {protocol}" {status} {byte_size}'
        logs.append(logline)
    return logs

def run_benchmark():
    print("Generating 1000 synthetic Apache logs...")
    logs = generate_logs(1000)
    
    schema_path = Path("apache_test_schema.json")
    schema_path.write_text(json.dumps(SCHEMA, indent=2))
    
    logs_str = "\n".join(logs) + "\n"
    
    import symparse.cache_manager
    cm = symparse.cache_manager.CacheManager()
    
    compiled_script = """import re2
def extract(text):
    m = re2.search(r'^(\\S+) \\S+ (\\S+) \\[(.*?)\\] "(\\S+) (\\S+) (\\S+)" (\\d+) (\\d+)', text)
    if m:
        return {
            "ip": m.group(1),
            "user_id": m.group(2) if m.group(2) != "-" else None,
            "timestamp": m.group(3),
            "method": m.group(4),
            "path": m.group(5),
            "protocol": m.group(6),
            "status": int(m.group(7)),
            "bytes": int(m.group(8))
        }
    return {}
"""
    
    times = []
    
    for run in range(1, 11):
        # Force a pre-populated cache for exactly 100% warm rate test
        cm.clear_cache()
        cm.save_script(SCHEMA, logs[0], compiled_script)
        
        overall_start = time.time()
        process = subprocess.Popen(
            ["symparse", "run", "--schema", "apache_test_schema.json", "--stats"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=logs_str)
        overall_time = (time.time() - overall_start) * 1000
        
        times.append(overall_time)
        print(f"Run {run}/10: {overall_time:.2f}ms")
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    variance = sum((x - avg_time) ** 2 for x in times) / len(times)
    import math
    std_dev = math.sqrt(variance)
    
    print("\n======== WARM CACHE BENCHMARK (1000 lines) ========")
    print(f"Average total wall time: {avg_time:.2f}ms ± {std_dev:.2f}ms")
    print(f"Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
    print(f"Lines processed per second: {1000 / (avg_time / 1000):.2f} ops/sec")
    print("===================================================")
    
    schema_path.unlink()

if __name__ == "__main__":
    run_benchmark()
