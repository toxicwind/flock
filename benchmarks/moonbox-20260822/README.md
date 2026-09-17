# nim-benchmark-2 — MOONBOX SUBMODULE
## Container: 320feec8 | Hash: 66f285d4ed69e70c
## Path: /mnt/agents/nim-benchmark-2

### .env.example
```
# Get your free API key at https://build.nvidia.com/explore/discover
NVIDIA_API_KEY=nvapi-YOUR_API_KEY_HERE

```

### .gitattributes
```
# Auto detect text files and perform LF normalization
* text=auto

```

### .gitfile
```
gitdir: _git

```

### .gitignore
```
# Environment files (contains API keys)
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Test/benchmark artifacts
Testing-NIM/
*.log

# Results (optional - uncomment if you don't want to commit results)
# results.json
# results_compact.json
```

### LICENSE
```
MIT License

Copyright (c) 2025 NIM LLM Speed Benchmark Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### README.md
```
# nim-benchmark-2

Created: 2026-08-22T18:10:29+00:00
Hash: 3c9bca5ff01cb5e5

## Files
-rw-r--r-- 1 root root   108 Aug 14 18:49 .env.example
-rw-r--r-- 1 root root    66 Aug 14 18:49 .gitattributes
-rw-r--r-- 1 root root    13 Aug 22 18:05 .gitfile
-rw-r--r-- 1 root root   351 Aug 14 18:49 .gitignore
-rw-r--r-- 1 root root  1092 Aug 14 18:49 LICENSE
-rw-r--r-- 1 root root    87 Aug 22 18:10 README.md
drwxr-xr-x 1 root root     0 Aug 22 18:05 _git
-rw-r--r-- 1 root root  4510 Aug 14 18:49 benchmark.py
-rw-r--r-- 1 root root  3440 Aug 14 18:49 models.json
-rw-r--r-- 1 root root    36 Aug 14 18:49 requirements.txt
-rw-r--r-- 1 root root  9725 Aug 14 18:49 results.json
-rw-r--r-- 1 root root 24471 Aug 14 18:49 visualize.html

```

### benchmark.py
```
import os
import json
import time
import sys
import argparse
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description="NVIDIA NIM LLM Speed Benchmark")
group = parser.add_mutually_exclusive_group()
group.add_argument("--resume", action="store_true", help="Continue from last completed model (default)")
group.add_argument("--restart", action="store_true", help="Delete results.json and start from scratch")
args = parser.parse_args()

API_KEY = os.getenv("NVIDIA_API_KEY")
BASE_URL = "https://integrate.api.nvidia.com/v1"
PROMPT = "What is the capital of India? Please answer in one sentence."
RESULTS_FILE = "results.json"
RATE_LIMIT_WAIT = 12  # seconds to wait on 429
REQUEST_TIMEOUT = 60  # seconds before giving up on a hung model

if not API_KEY:
    sys.exit(
        "Missing NVIDIA_API_KEY. Copy .env.example to .env and add your NVIDIA API key."
    )

if not os.path.exists("models.json"):
    sys.exit("Missing models.json. The benchmark cannot run without a model list.")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=REQUEST_TIMEOUT)

with open("models.json") as f:
    models = json.load(f)

# Load existing results so we can resume
if args.restart and os.path.exists(RESULTS_FILE):
    os.remove(RESULTS_FILE)
    print("🗑  Deleted results.json — starting fresh.")

try:
    with open(RESULTS_FILE) as f:
        results = json.load(f)
    done_ids = {r["id"] for r in results}
    print(f"Resuming — {len(done_ids)} models already done, {len(models) - len(done_ids)} remaining.")
except FileNotFoundError:
    results = []
    done_ids = set()
    print(f"Starting fresh — {len(models)} models to benchmark.")


def benchmark_model(model_id, label):
    print(f"\n→ {label} ({model_id})")
    try:
        start = time.perf_counter()
        token_count = 0
        first_token_time = None

        stream = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", 
```

### models.json
```
[
  { "id": "sarvamai/sarvam-m", "label": "Sarvam M", "type": "chat" },
  { "id": "mistralai/mistral-small-4-119b-2603", "label": "Mistral Small 4 119B 2603", "type": "chat" },
  { "id": "mistralai/ministral-14b-instruct-2512", "label": "Ministral 14B Instruct 2512", "type": "chat" },
  { "id": "mistralai/mistral-medium-3.5-128b", "label": "Mistral Medium 3.5 128B", "type": "chat" },
  { "id": "mistralai/mistral-nemotron", "label": "Mistral Nemotron", "type": "chat" },
  { "id": "google/gemma-2-2b-it", "label": "Gemma 2 2B IT", "type": "chat" },
  { "id": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1", "label": "Llama 3.1 Nemotron Nano VL 8B v1", "type": "vision" },
  { "id": "mistralai/mistral-large-3-675b-instruct-2512", "label": "Mistral Large 3 675B Instruct 2512", "type": "chat" },
  { "id": "nvidia/nemotron-3-nano-30b-a3b", "label": "Nemotron 3 Nano 30B A3B", "type": "chat" },
  { "id": "nvidia/nemotron-nano-12b-v2-vl", "label": "Nemotron Nano 12B V2 VL", "type": "vision" },
  { "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning", "label": "Nemotron 3 Nano Omni 30B A3B Reasoning", "type": "chat" },
  { "id": "meta/llama-3.2-11b-vision-instruct", "label": "Llama 3.2 11B Vision Instruct", "type": "vision" },
  { "id": "nvidia/nemotron-3.5-content-safety", "label": "Nemotron 3.5 Content Safety", "type": "safety" },
  { "id": "stockmark/stockmark-2-100b-instruct", "label": "Stockmark 2 100B Instruct", "type": "chat" },
  { "id": "nvidia/nemotron-3-super-120b-a12b", "label": "Nemotron 3 Super 120B A12B", "type": "chat" },
  { "id": "nvidia/nemotron-3-content-safety", "label": "Nemotron 3 Content Safety", "type": "safety" },
  { "id": "openai/gpt-oss-20b", "label": "GPT OSS 20B", "type": "chat" },
  { "id": "nvidia/nemotron-mini-4b-instruct", "label": "Nemotron Mini 4B Instruct", "type": "chat" },
  { "id": "minimaxai/minimax-m2.7", "label": "MiniMax M2.7", "type": "chat" },
  { "id": "openai/gpt-oss-120b", "label": "GPT OSS 120B", "type": "chat" },
  { "id": "meta/lla
```

### requirements.txt
```
openai>=1.100.0
python-dotenv>=1.0.1
```

### results.json
```
[
  {
    "id": "sarvamai/sarvam-m",
    "label": "Sarvam M",
    "status": "ok",
    "total_time_s": 3.84,
    "tokens": 95,
    "tokens_per_second": 24.74,
    "ttft_s": 0.851,
    "response_preview": "Okay, the user is asking for the capital of India. Let me recall that. I think it's New Delhi. Wait, sometimes people co"
  },
  {
    "id": "mistralai/mistral-small-4-119b-2603",
    "label": "Mistral Small 4 119B 2603",
    "status": "ok",
    "total_time_s": 0.46,
    "tokens": 8,
    "tokens_per_second": 17.4,
    "ttft_s": 0.427,
    "response_preview": "The capital of India is New Delhi."
  },
  {
    "id": "mistralai/ministral-14b-instruct-2512",
    "label": "Ministral 14B Instruct 2512",
    "status": "ok",
    "total_time_s": 0.422,
    "tokens": 9,
    "tokens_per_second": 21.31,
    "ttft_s": 0.311,
    "response_preview": "The capital of India is **New Delhi**."
  },
  {
    "id": "mistralai/mistral-medium-3.5-128b",
    "label": "Mistral Medium 3.5 128B",
    "status": "ok",
    "total_time_s": 0.503,
    "tokens": 9,
    "tokens_per_second": 17.88,
    "ttft_s": 0.345,
    "response_preview": "The capital of India is **New Delhi**."
  },
  {
    "id": "mistralai/mistral-nemotron",
    "label": "Mistral Nemotron",
    "status": "ok",
    "total_time_s": 0.482,
    "tokens": 8,
    "tokens_per_second": 16.59,
    "ttft_s": 0.343,
    "response_preview": "The capital of India is New Delhi."
  },
  {
    "id": "google/gemma-2-2b-it",
    "label": "Gemma 2 2B IT",
    "status": "ok",
    "total_time_s": 7.083,
    "tokens": 8,
    "tokens_per_second": 1.13,
    "ttft_s": 7.064,
    "response_preview": "The capital of India is New Delhi."
  },
  {
    "id": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
    "label": "Llama 3.1 Nemotron Nano VL 8B v1",
    "status": "ok",
    "total_time_s": 0.502,
    "tokens": 8,
    "tokens_per_second": 15.92,
    "ttft_s": 0.309,
    "response_preview": "New Delhi is the capital of India."
  },
  {
    "id": "mistralai/mistr
```
