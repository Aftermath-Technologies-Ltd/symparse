import time
import sys
import subprocess

def type_text(text, speed=0.03, newline=True):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    if newline:
        sys.stdout.write('\n')
        time.sleep(0.5)

def main():
    print("\033[2J\033[H", end="")  # Clear screen

    type_text("$ cat messy_log.txt", speed=0.05)
    time.sleep(0.5)
    print('User alice@example.com logged in from 192.168.1.50 at 10:45 AM')
    time.sleep(1)

    type_text("\n$ # COLD START: AI Path Compiles Regex", speed=0.05)
    cmd = "cat messy_log.txt | symparse run --schema login_schema.json --compile --stats"
    type_text(f"$ {cmd}", speed=0.04)

    print("...")
    time.sleep(2)  # fake LLM latency pause before it prints
    print('{"email": "alice@example.com", "ip_address": "192.168.1.50"}')
    print('''
--- Symparse Run Stats (v0.1.1) ---
Fast Path Hits: 0
AI Path Hits:   1
Average Latency: 2154.30ms
''')
    time.sleep(2)

    type_text("$ # WARM START: Re2 Fast Path Execution", speed=0.05)
    cmd = "tail -f access.log | symparse run --schema login_schema.json --stats"
    type_text(f"$ {cmd}", speed=0.04)
    time.sleep(0.5)

    # Simulate rapid output
    for i in range(50):
        print(f'{{"email": "user{i}@example.com", "ip_address": "10.0.0.{i}"}}')
        time.sleep(0.01)

    print("^C")
    print('''
--- Symparse Run Stats (v0.1.1) ---
Fast Path Hits: 50
AI Path Hits:   0
Average Latency: 0.42ms
''')
    time.sleep(2)
    type_text("$ # 100% Extract. 99.9% Faster.", speed=0.08)

if __name__ == "__main__":
    main()
