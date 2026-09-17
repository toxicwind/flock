# NVIDIA NIM Free Inference Endpoints

NVIDIA hosts 40+ AI models as free-tier inference endpoints at [build.nvidia.com](https://build.nvidia.com/models?filters=nimType%3Anim_type_preview). All of them share a single OpenAI-compatible API.

## Quick start

```bash
# Run a demo
python nvidia_nim_inference.py --demo chat --prompt "Explain transformers in 2 sentences."
```

## API basics

**Base URL:** `https://integrate.api.nvidia.com/v1`  
**Auth:** Bearer token — `Authorization: Bearer $NVIDIA_API_KEY`  
**Protocol:** OpenAI-compatible (`/v1/chat/completions`, `/v1/embeddings`)

Every model — including specialized ones like PII detection — is accessed through the same base URL and the same OpenAI client. Special capabilities are passed via `extra_body`.

### Minimal example

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="nvapi-...",
)

response = client.chat.completions.create(
    model="meta/llama-4-maverick-17b-128e-instruct",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=256,
)
print(response.choices[0].message.content)
```

### Streaming

All chat models support streaming:

```python
stream = client.chat.completions.create(
    model="meta/llama-4-maverick-17b-128e-instruct",
    messages=[{"role": "user", "content": "Write a haiku about GPUs."}],
    stream=True,
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

## Authentication

The script reads the API key in this priority order:

1. `--api-key` CLI flag
2. System keyring (`service="nvidia-nim"`, `username="api-key"`)
3. `NVIDIA_API_KEY` environment variable

**Store in keyring (recommended):**
```bash
python -c "import keyring; keyring.set_password('nvidia-nim', 'api-key', 'nvapi-...')"
```

**Retrieve:**
```python
import keyring
key = keyring.get_password("nvidia-nim", "api-key")
```

## Model categories

### Chat / instruction LLMs

All use `client.chat.completions.create(model=..., messages=...)`.

| Model | Notes |
|---|---|
| `meta/llama-4-maverick-17b-128e-instruct` | General-purpose multimodal MoE, 128 experts |
| `mistralai/mistral-large-3-675b-instruct-2512` | MoE VLM for chat and agentic tasks |
| `mistralai/mistral-nemotron` | Agentic: coding, function calling |
| `bytedance/seed-oss-36b-instruct` | Long-context, reasoning |
| `stepfun-ai/step-3.5-flash` | 200B sparse MoE reasoning engine |
| `minimaxai/minimax-m2.7` | 230B MoE, coding and office tasks |
| `nvidia/nemotron-mini-4b-instruct` | Small model for RAG and function calling |
| `google/gemma-3n-e4b-it` | Edge model, accepts text/audio/image |
| `google/gemma-3n-e2b-it` | Lightweight edge model |
| `google/gemma-2-2b-it` | Compact model for edge |
| `abacusai/dracarys-llama-3.1-70b-instruct` | Llama 3.1 70B fine-tuned for code |
| `upstage/solar-10.7b-instruct` | Strong at reasoning and math |

### Coding

```python
response = client.chat.completions.create(
    model="qwen/qwen3-coder-480b-a35b-instruct",
    messages=[{"role": "user", "content": "Write a binary search in Python."}],
    temperature=0.7,
    top_p=0.8,
    max_tokens=4096,
    stream=True,
)
```

| Model | Notes |
|---|---|
| `qwen/qwen3-coder-480b-a35b-instruct` | 480B MoE, agentic coding, 256K context |
| `nvidia/usdcode` | OpenUSD queries and USD-Python generation |
| `mistralai/magistral-small-2506` | Reasoning model optimized for efficiency |

### Safety & content moderation

These return a plain text verdict via chat completions.

```python
response = client.chat.completions.create(
    model="nvidia/nemotron-3-content-safety",
    messages=[{"role": "user", "content": "Is this text safe?"}],
    max_tokens=512,
    temperature=0.2,
    top_p=0.7,
)
print(response.choices[0].message.content)
# → "User Safety: safe"  or  "User Safety: unsafe"
```

| Model | Notes |
|---|---|
| `nvidia/nemotron-3-content-safety` | Multilingual/multimodal toxicity detection |
| `nvidia/nemotron-content-safety-reasoning-4b` | Reasoning-based, domain-specific policies |
| `nvidia/llama-3.1-nemotron-safety-guard-8b-v3` | Multilingual safety for LLM pipelines |
| `meta/llama-guard-4-12b` | Multimodal safety classification |

### PII detection

`nvidia/gliner-pii` uses the chat completions endpoint but takes extra parameters in `extra_body`. The response content is JSON.

```python
completion = client.chat.completions.create(
    model="nvidia/gliner-pii",
    messages=[{"role": "user", "content": "Jane Smith, SSN 123-45-6789, lives at 42 Main St."}],
    extra_body={
        "labels": ["first_name", "last_name", "ssn", "street_address", "email", "phone_number"],
        "threshold": 0.4,      # minimum confidence score (0–1)
        "chunk_length": 384,   # tokens per processing chunk
        "overlap": 128,        # overlap between chunks
        "flat_ner": False,     # allow nested entities
    },
)

import json
result = json.loads(completion.choices[0].message.content)
# result keys: total_entities, entities, tagged_text
for entity in result["entities"]:
    print(entity["label"], entity["text"], entity["score"])
# → first_name Jane 1.0
# → last_name Smith 1.0
# → ssn 123-45-6789 1.0

print(result["tagged_text"])
# → <first_name>Jane</first_name> <last_name>Smith</last_name>, SSN <ssn>123-45-6789</ssn>, ...
```

Supported entity labels (pass any subset):
`first_name`, `last_name`, `street_address`, `city`, `state`, `postcode`,
`email`, `phone_number`, `ssn`, `account_number`, `swift_bic`, `time`, `occupation`.

### Text embeddings

```python
response = client.embeddings.create(
    model="nvidia/nv-embed-v1",
    input=["The quick brown fox", "A fast auburn canine"],
    encoding_format="float",
)
vectors = [item.embedding for item in response.data]
# vectors[i] is a list of 4096 floats
```

| Model | Notes |
|---|---|
| `nvidia/nv-embed-v1` | 4096-dim text embeddings (non-commercial) |
| `nvidia/nv-embedcode-7b-v1` | Code + text retrieval embeddings |

### Translation

```python
response = client.chat.completions.create(
    model="nvidia/riva-translate-4b-instruct-v1_1",
    messages=[{"role": "user", "content": "Translate to French: Hello, how are you?"}],
    max_tokens=256,
)
print(response.choices[0].message.content)
```

Supports 12 languages with few-shot example prompts.

### Vision / multimodal

```python
import base64

with open("image.jpg", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="google/paligemma",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What is in this image?"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ],
    }],
    max_tokens=512,
)
print(response.choices[0].message.content)
```

| Model | Notes |
|---|---|
| `google/paligemma` | Vision-language model |
| `microsoft/phi-4-multimodal-instruct` | Multimodal: image + audio reasoning |
| `meta/llama-4-maverick-17b-128e-instruct` | Multimodal MoE (text + image) |

### Biology / protein

```python
# Protein sequence embeddings
response = client.embeddings.create(
    model="meta/esm2-650m",
    input="MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ...",  # amino acid sequence
    encoding_format="float",
)
embedding = response.data[0].embedding  # list of floats

# 3D structure prediction — uses chat completions, returns PDB format
response = client.chat.completions.create(
    model="meta/esmfold",
    messages=[{"role": "user", "content": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ..."}],
    max_tokens=4096,
)
pdb_structure = response.choices[0].message.content
```

### Autonomous driving

Computer vision models for perception and planning.

| Model | Use case |
|---|---|
| `nvidia/bevformer` | Bird's-eye-view 3D object detection |
| `nvidia/streampetr` | Temporal 3D object detection |
| `nvidia/sparsedrive` | End-to-end perception + prediction + planning |

### Video / synthetic data

| Model | Use case |
|---|---|
| `nvidia/cosmos-predict1-5b` | Physics-aware future-frame video generation |
| `nvidia/cosmos-transfer1-7b` | Video world states from text + spatial controls |
| `nvidia/cosmos-transfer2.5-2b` | Video world states from real-world or simulation data |
| `nvidia/synthetic-video-detector` | Detect AI-generated videos |

### Speech & audio

| Model | Use case |
|---|---|
| `nvidia/magpie-tts-zeroshot` | Zero-shot TTS from a short audio sample |
| `nvidia/studiovoice` | Low-quality mic → studio-quality speech enhancement |
| `nvidia/nemotron-voicechat` | Voice chat (English) |
| `nvidia/active-speaker-detection` | Track speaker identities across video frames |

### Digital twin / OpenUSD

| Model | Use case |
|---|---|
| `nvidia/usdcode` | OpenUSD knowledge queries and USD-Python generation |
| `nvidia/usdvalidate` | Validate USD assets with RTX render + rule checks |

## CLI reference (`nvidia_nim_inference.py`)

```
python nvidia_nim_inference.py [--demo DEMO] [--model MODEL] [--prompt PROMPT] [--api-key KEY]

--demo    chat        Streaming chat (default model: llama-4-maverick)
          coding      Code generation (model: qwen3-coder-480b)
          pii         PII entity detection (model: gliner-pii)
          safety      Content safety verdict (model: nemotron-3-content-safety)
          embeddings  Text embeddings + cosine similarity (model: nv-embed-v1)
          rerank      LLM-based passage reranking
          protein     Protein sequence embedding (model: esm2-650m)
          all         Run all demos
          list        Print all 40 models and descriptions
```

Examples:

```bash
# Chat with a specific model
python nvidia_nim_inference.py --demo chat \
  --model mistralai/mistral-large-3-675b-instruct-2512 \
  --prompt "Summarize the transformer architecture."

# PII detection on custom text
python nvidia_nim_inference.py --demo pii \
  --prompt "Call John at 555-1234 or email john@acme.com."

# Safety check
python nvidia_nim_inference.py --demo safety \
  --prompt "How do I pick a lock?"

# List all available models
python nvidia_nim_inference.py --demo list
```

## Common parameters

| Parameter | Typical range | Notes |
|---|---|---|
| `temperature` | 0.0 – 1.0 | 0 = deterministic, higher = more creative |
| `top_p` | 0.7 – 1.0 | Nucleus sampling threshold |
| `max_tokens` | 64 – 128000 | Varies per model |
| `stream` | `True` / `False` | All chat models support streaming |

## Rate limits and quotas

Free-tier endpoints impose per-minute and monthly token limits that vary by model. Requests exceeding the limit receive HTTP 429. There is no published SLA for the free tier.

## Notes

- **`nvidia/rerank-qa-mistral-4b`** appears in the catalog but its dedicated reranking endpoint is not accessible on the free tier. Passage reranking can be approximated via an LLM prompt.
- **`nvidia/nv-embed-v1`** is marked non-commercial use only.
- **`upstage/solar-10.7b-instruct`** is also marked non-commercial use only.
- Model IDs follow the pattern `publisher/model-slug`, matching the URL path on `build.nvidia.com`.
