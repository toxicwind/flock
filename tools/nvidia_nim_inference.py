#!/usr/bin/env python3
"""
NVIDIA NIM Free Endpoint Inference Examples
==========================================
All 41 preview models at https://build.nvidia.com/models?filters=nimType%3Anim_type_preview
use the OpenAI-compatible API at https://integrate.api.nvidia.com/v1

Requirements:
  pip install openai requests keyring

Usage:
  python nvidia_nim_inference.py [--demo <name>]

The API key is read from the system keyring (service="nvidia-nim", username="api-key").
To store your key:
  python -c "import keyring; keyring.set_password('nvidia-nim', 'api-key', 'nvapi-...')"

Get a free API key at: https://build.nvidia.com (click "Get API Key")
"""

import argparse
import json
import os
import sys
import keyring
from openai import OpenAI

BASE_URL = "https://integrate.api.nvidia.com/v1"

# All 41 free preview NIM endpoints (as of 2026-05)
ALL_MODELS = {
    # --- General-purpose LLMs ---
    "meta/llama-4-maverick-17b-128e-instruct": "General-purpose multimodal MoE, 128 experts, 17B params",
    "mistralai/mistral-large-3-675b-instruct-2512": "State-of-the-art MoE VLM for chat and agentic tasks",
    "mistralai/mistral-nemotron": "Agentic: coding, instruction following, function calling",
    "bytedance/seed-oss-36b-instruct": "Long-context, reasoning, agentic intelligence",
    "stepfun-ai/step-3.5-flash": "200B open-source reasoning engine, sparse MoE",
    "minimaxai/minimax-m2.7": "230B MoE, coding, reasoning, office tasks",
    "nvidia/nemotron-mini-4b-instruct": "Small on-device model, RAG, roleplay, function calling",
    "google/gemma-3n-e4b-it": "Edge model: text, audio, image input",
    "google/gemma-3n-e2b-it": "Lightweight edge model: text, audio, image input",
    "google/gemma-2-2b-it": "Compact generative model for edge applications",
    "abacusai/dracarys-llama-3.1-70b-instruct": "Fine-tuned Llama 3.1 70B for code and summarization",
    "upstage/solar-10.7b-instruct": "Instruction-following, reasoning, mathematics",

    # --- Coding ---
    "qwen/qwen3-coder-480b-a35b-instruct": "480B MoE coding model, agentic coding, 256K context",
    "nvidia/usdcode": "LLM for OpenUSD knowledge queries and USD-Python code",
    "nvidia/nv-embedcode-7b-v1": "Code embedding model for retrieval (7B Mistral-based)",

    # --- Reasoning ---
    "mistralai/magistral-small-2506": "Reasoning model optimized for efficiency (deprecated label)",

    # --- Safety & Moderation ---
    "nvidia/nemotron-3-content-safety": "Multilingual/multimodal unsafe/toxic content detection",
    "nvidia/nemotron-content-safety-reasoning-4b": "Context-aware safety with domain-specific policy reasoning",
    "nvidia/llama-3.1-nemotron-safety-guard-8b-v3": "Multilingual content safety for LLMs",
    "meta/llama-guard-4-12b": "Multimodal safety classification for prompts and responses",

    # --- PII Detection ---
    "nvidia/gliner-pii": "Detect Personally Identifiable Information in text (GLiNER)",

    # --- Translation ---
    "nvidia/riva-translate-4b-instruct-v1_1": "Translation in 12 languages with few-shot prompts",

    # --- Embeddings & Retrieval ---
    "nvidia/nv-embed-v1": "High-quality text embeddings (non-commercial)",
    "nvidia/rerank-qa-mistral-4b": "Reranking: probability that a passage answers a question",

    # --- Vision / Multimodal ---
    "google/paligemma": "Vision-language model: text + image understanding",
    "microsoft/phi-4-multimodal-instruct": "Multimodal reasoning from image and audio inputs",

    # --- Biology ---
    "meta/esm2-650m": "Protein embeddings from amino acid sequences",
    "meta/esmfold": "3D protein structure prediction from amino acid sequence",

    # --- Autonomous Vehicles ---
    "nvidia/sparsedrive": "End-to-end autonomous driving: perception + prediction + planning",
    "nvidia/bevformer": "Bird's-eye-view 3D perception for autonomous driving",
    "nvidia/streampetr": "3D object detection for autonomous driving",

    # --- Synthetic Data / Video ---
    "nvidia/cosmos-predict1-5b": "Physics-aware future-frame generation from image/video",
    "nvidia/cosmos-transfer1-7b": "Physics-aware video world states from text + spatial controls",
    "nvidia/cosmos-transfer2.5-2b": "Video world states from text + real-world/simulation data",
    "nvidia/synthetic-video-detector": "Detect AI-generated (synthetic) videos",

    # --- Speech / Audio ---
    "nvidia/nemotron-voicechat": "Voice chat in English",
    "nvidia/magpie-tts-zeroshot": "Zero-shot expressive TTS from a short audio sample",
    "nvidia/studiovoice": "Low-quality mic → studio-quality speech enhancement",

    # --- Active Speaker Detection ---
    "nvidia/active-speaker-detection": "Detect and track speakers across video frames",

    # --- Digital Twin ---
    "nvidia/usdvalidate": "OpenUSD asset validation with RTX render and rule-based checks",
}


KEYRING_SERVICE = "nvidia-nim"
KEYRING_USERNAME = "api-key"


def get_api_key(override: str | None = None) -> str:
    if override:
        return override
    key = keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    if key:
        return key
    # Fall back to environment variable
    key = os.environ.get("NVIDIA_API_KEY")
    if key:
        return key
    sys.exit(
        "NVIDIA API key not found.\n"
        "Store it with:\n"
        f"  python -c \"import keyring; keyring.set_password('{KEYRING_SERVICE}', '{KEYRING_USERNAME}', 'nvapi-...')\"\n"
        "Get a free key at https://build.nvidia.com"
    )


def get_client(api_key: str | None = None) -> OpenAI:
    return OpenAI(base_url=BASE_URL, api_key=get_api_key(api_key))


# ---------------------------------------------------------------------------
# Demo 1: Basic chat completion (streaming)
# ---------------------------------------------------------------------------
def demo_chat(client: OpenAI, model: str = "meta/llama-4-maverick-17b-128e-instruct",
              prompt: str = "Explain gradient descent in 3 sentences.") -> str:
    print(f"\n[Chat] model={model}")
    print(f"Prompt: {prompt}\n")
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=512,
        stream=True,
    )
    result = []
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            print(text, end="", flush=True)
            result.append(text)
    print()
    return "".join(result)


# ---------------------------------------------------------------------------
# Demo 2: Coding assistant
# ---------------------------------------------------------------------------
def demo_coding(client: OpenAI, prompt: str = "Write a Python function to compute Fibonacci numbers iteratively.") -> str:
    return demo_chat(client, model="qwen/qwen3-coder-480b-a35b-instruct", prompt=prompt)


# ---------------------------------------------------------------------------
# Demo 3: PII detection (gliner-pii)
# ---------------------------------------------------------------------------
def demo_pii(client: OpenAI, text: str | None = None) -> dict:
    text = text or (
        "Dr. Jane Smith lives at 123 Main St, New York, NY 10001. "
        "Her SSN is 123-45-6789 and email is jane@example.com."
    )
    print(f"\n[PII Detection] model=nvidia/gliner-pii")
    print(f"Input: {text}\n")
    completion = client.chat.completions.create(
        model="nvidia/gliner-pii",
        messages=[{"role": "user", "content": text}],
        extra_body={
            "labels": [
                "first_name", "last_name", "street_address", "city", "state",
                "postcode", "email", "phone_number", "ssn",
            ],
            "threshold": 0.4,
            "chunk_length": 384,
            "overlap": 128,
            "flat_ner": False,
        },
    )
    result = json.loads(completion.choices[0].message.content or "{}")
    print(f"Found {result['total_entities']} entities:")
    for entity in result.get("entities", []):
        print(f"  [{entity['label']}] \"{entity['text']}\"  confidence={entity['score']:.2f}")
    print(f"\nTagged: {result.get('tagged_text', '')}")
    return result


# ---------------------------------------------------------------------------
# Demo 4: Content safety check
# ---------------------------------------------------------------------------
def demo_safety(client: OpenAI, text: str | None = None) -> str:
    text = text or "How do I bake a chocolate cake?"
    print(f"\n[Safety Check] model=nvidia/nemotron-3-content-safety")
    print(f"Input: {text}\n")
    response = client.chat.completions.create(
        model="nvidia/nemotron-3-content-safety",
        messages=[{"role": "user", "content": text}],
        max_tokens=512,
        temperature=0.2,
        top_p=0.7,
    )
    verdict = response.choices[0].message.content or ""
    print(f"Verdict: {verdict}")
    return verdict


# ---------------------------------------------------------------------------
# Demo 5: Text embeddings
# ---------------------------------------------------------------------------
def demo_embeddings(client: OpenAI, texts: list[str] | None = None) -> list[list[float]]:
    texts = texts or ["The quick brown fox", "A fast auburn canine"]
    print(f"\n[Embeddings] model=nvidia/nv-embed-v1")
    print(f"Inputs: {texts}\n")
    response = client.embeddings.create(
        model="nvidia/nv-embed-v1",
        input=texts,
        encoding_format="float",
    )
    vectors = [item.embedding for item in response.data]
    # Cosine similarity
    import math
    def dot(a, b): return sum(x*y for x, y in zip(a, b))
    def norm(v): return math.sqrt(sum(x*x for x in v))
    sim = dot(vectors[0], vectors[1]) / (norm(vectors[0]) * norm(vectors[1]))
    print(f"Embedding dimension: {len(vectors[0])}")
    print(f"Cosine similarity between texts: {sim:.4f}")
    return vectors


# ---------------------------------------------------------------------------
# Demo 6: Reranking passages
# ---------------------------------------------------------------------------
def demo_rerank(api_key: str | None = None) -> None:
    # nvidia/rerank-qa-mistral-4b is listed in the catalog but the dedicated
    # /v1/reranking endpoint is not available on the free trial tier.
    # Use the chat completions endpoint to simulate reranking via prompting.
    client = OpenAI(base_url=BASE_URL, api_key=get_api_key(api_key))
    query = "What is the boiling point of water?"
    passages = [
        "Water boils at 100°C (212°F) at sea level.",
        "The Eiffel Tower is 330 meters tall.",
        "H2O freezes at 0°C under standard pressure.",
    ]
    prompt = (
        f"Rank these passages by relevance to the query. "
        f"Reply with a JSON list of indices from most to least relevant.\n\n"
        f"Query: {query}\n\n"
        + "\n".join(f"[{i}] {p}" for i, p in enumerate(passages))
    )
    print(f"\n[Rerank via LLM] query: {query}")
    print(f"Passages: {passages}\n")
    response = client.chat.completions.create(
        model="meta/llama-4-maverick-17b-128e-instruct",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=64,
        temperature=0,
    )
    print(f"Ranking: {response.choices[0].message.content}")


# ---------------------------------------------------------------------------
# Demo 7: Protein embedding (ESM2)
# ---------------------------------------------------------------------------
def demo_protein_embedding(client: OpenAI, sequence: str | None = None) -> list[float]:
    sequence = sequence or "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGEDEDTLDEMARHQSAQEGAVDGADLSKLAFTDYTPQVWGMAKAIEELRQADGEQLPQATLAQPSLE"
    print(f"\n[Protein Embedding] model=meta/esm2-650m")
    print(f"Sequence length: {len(sequence)} amino acids\n")
    response = client.embeddings.create(
        model="meta/esm2-650m",
        input=sequence,
        encoding_format="float",
    )
    vec = response.data[0].embedding
    print(f"Embedding dimension: {len(vec)}")
    print(f"First 5 values: {vec[:5]}")
    return vec


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
DEMOS = {
    "chat": demo_chat,
    "coding": demo_coding,
    "pii": demo_pii,
    "safety": demo_safety,
    "embeddings": demo_embeddings,
    "rerank": demo_rerank,
    "protein": demo_protein_embedding,
}


def main():
    parser = argparse.ArgumentParser(description="NVIDIA NIM free endpoint inference demos")
    parser.add_argument("--api-key", help="NVIDIA API key (or set NVIDIA_API_KEY env var)")
    parser.add_argument("--demo", choices=list(DEMOS.keys()) + ["all", "list"],
                        default="all", help="Which demo to run (default: all)")
    parser.add_argument("--model", help="Override model for --demo chat")
    parser.add_argument("--prompt", help="Override prompt for --demo chat or coding")
    args = parser.parse_args()

    if args.demo == "list":
        print(f"\n{len(ALL_MODELS)} NVIDIA NIM Free Endpoint Preview Models:\n")
        for model_id, desc in ALL_MODELS.items():
            print(f"  {model_id}")
            print(f"    {desc}\n")
        return

    client = get_client(args.api_key)

    if args.demo == "all":
        demo_chat(client, **({"model": args.model} if args.model else {}),
                  **({"prompt": args.prompt} if args.prompt else {}))
        demo_coding(client)
        demo_pii(client)
        demo_safety(client)
        demo_embeddings(client)
        demo_rerank(args.api_key)
    elif args.demo == "chat":
        kwargs = {}
        if args.model:
            kwargs["model"] = args.model
        if args.prompt:
            kwargs["prompt"] = args.prompt
        demo_chat(client, **kwargs)
    elif args.demo == "coding":
        demo_coding(client, **({"prompt": args.prompt} if args.prompt else {}))
    elif args.demo == "pii":
        demo_pii(client, **({"text": args.prompt} if args.prompt else {}))
    elif args.demo == "safety":
        demo_safety(client, **({"text": args.prompt} if args.prompt else {}))
    elif args.demo == "embeddings":
        demo_embeddings(client)
    elif args.demo == "rerank":
        demo_rerank(args.api_key)
    elif args.demo == "protein":
        demo_protein_embedding(client)


if __name__ == "__main__":
    main()
