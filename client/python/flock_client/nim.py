import math
from typing import Any, Generator, Iterator
from .client import FlockClient as _RawFlockClient
from .models import Models


class ChatAPI:
    def __init__(self, client: FlockClient):
        self._c = client

    def ask(
        self,
        prompt: str,
        model: str = Models.Chat.LLAMA_3_1_70B,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        system: str | None = None,
    ) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._c.chat(model, messages, temperature=temperature, max_tokens=max_tokens)
        return resp["choices"][0]["message"]["content"]

    def stream(
        self,
        prompt: str,
        model: str = Models.Chat.LLAMA_3_1_70B,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Generator[str, None, None]:
        messages = [{"role": "user", "content": prompt}]
        for chunk in self._c.chat_stream(model, messages, temperature=temperature, max_tokens=max_tokens):
            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
            if content:
                yield content

    def reason(self, prompt: str, **kwargs: Any) -> str:
        return self.ask(
            prompt,
            model=Models.Chat.NEMOTRON_ULTRA,
            temperature=0.6,
            max_tokens=4096,
            **kwargs,
        )

    def summarize(self, text: str, **kwargs: Any) -> str:
        return self.ask(
            f"Summarize the following content clearly and concisely:\n\n{text}",
            temperature=0.1,
            max_tokens=512,
            **kwargs,
        )

    def classify(self, text: str, labels: list[str], **kwargs: Any) -> str:
        prompt = f"Classify into exactly one of: {', '.join(labels)}.\nReturn only the label.\n\nText: {text}"
        return self.ask(prompt, model=Models.Chat.LLAMA_3_1_8B, temperature=0.1, max_tokens=50, **kwargs).strip()


class VisionAPI:
    def __init__(self, client: FlockClient):
        self._c = client

    def analyze(self, image_url: str, prompt: str, model: str = Models.Vision.LLAMA_3_2_90B) -> str:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        resp = self._c.chat(model, messages, max_tokens=1024)
        return resp["choices"][0]["message"]["content"]

    def caption(self, image_url: str) -> str:
        return self.analyze(image_url, "Describe this image in detail.")

    def ocr(self, image_url: str) -> str:
        return self.analyze(image_url, "Extract all text from this image. Return only the text.")

    def answer(self, image_url: str, question: str) -> str:
        return self.analyze(image_url, question)


class EmbeddingsAPI:
    def __init__(self, client: FlockClient):
        self._c = client

    def embed(self, text: str, model: str = Models.Embeddings.NV_EMBEDQA_E5) -> list[float]:
        resp = self._c.embed(model, text, input_type="query")
        return resp["data"][0]["embedding"]

    def embed_many(self, texts: list[str], model: str = Models.Embeddings.NV_EMBEDQA_E5) -> list[list[float]]:
        resp = self._c.embed(model, texts, input_type="passage")
        return [d["embedding"] for d in sorted(resp["data"], key=lambda x: x["index"])]

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        return dot / (norm_a * norm_b) if norm_a * norm_b != 0 else 0.0

    def rerank(self, query: str, passages: list[str], model: str = Models.Rerank.RERANK_MISTRAL) -> list[dict[str, Any]]:
        resp = self._c.rerank(model, query, passages)
        return [
            {"text": passages[r["index"]], "score": r["logit"], "index": r["index"]}
            for r in resp.get("rankings", [])
        ]

    def find_most_similar(self, query: str, candidates: list[str]) -> list[dict[str, Any]]:
        q_vec = self.embed(query)
        c_vecs = self.embed_many(candidates)
        results = [
            {"text": t, "score": self.cosine_similarity(q_vec, v), "index": i}
            for i, (t, v) in enumerate(zip(candidates, c_vecs))
        ]
        return sorted(results, key=lambda x: x["score"], reverse=True)


class SafetyAPI:
    def __init__(self, client: FlockClient):
        self._c = client

    def is_safe(self, text: str) -> bool:
        resp = self._c.chat(
            Models.Safety.NEMOGUARD_CONTENT,
            [{"role": "user", "content": text}],
            max_tokens=100,
            temperature=0.0,
        )
        raw = resp["choices"][0]["message"]["content"].lower()
        return "safe" in raw and "unsafe" not in raw

    def detect_pii(self, text: str) -> dict[str, Any]:
        resp = self._c.chat(
            Models.Safety.GLINER_PII,
            [{"role": "user", "content": text}],
            max_tokens=512,
            temperature=0.0,
        )
        import json, re
        raw = resp["choices"][0]["message"]["content"]
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        try:
            entities = json.loads(match.group()) if match else []
        except Exception:
            entities = []
        anonymized = text
        for e in sorted(entities, key=lambda x: x.get("start", 0), reverse=True):
            anonymized = anonymized[:e["start"]] + f"[{e['label']}]" + anonymized[e["end"]:]
        return {"entities": entities, "anonymized": anonymized, "has_pii": len(entities) > 0}


class BiologyAPI:
    BIOLOGY_URL = "https://health.api.nvidia.com/v1"

    def __init__(self, client: FlockClient):
        self._c = client

    def fold_protein(self, sequence: str) -> dict[str, Any]:
        resp = self._c.request(
            f"{self.BIOLOGY_URL}/biology/deepmind/esmfold",
            {"sequence": sequence},
        )
        return {"pdb": resp.get("pdbs", [""])[0], "mean_plddt": (resp.get("mean_plddt") or [None])[0]}

    def generate_molecules(self, smiles: str, num: int = 10, temperature: float = 1.0) -> list[dict[str, Any]]:
        resp = self._c.request(
            f"{self.BIOLOGY_URL}/biology/nvidia/genmol",
            {"smiles": smiles, "num_molecules": num, "temperature": temperature, "iterations": 20},
        )
        return resp.get("molecules", [])


class Flock:
    def __init__(self, api_key: str, **kwargs: Any):
        self._client = _RawFlockClient(api_key, **kwargs)
        self.chat = ChatAPI(self._client)
        self.vision = VisionAPI(self._client)
        self.embeddings = EmbeddingsAPI(self._client)
        self.safety = SafetyAPI(self._client)
        self.biology = BiologyAPI(self._client)


def create_flock_client(api_key: str, **kwargs: Any) -> Flock:
    return Flock(api_key, **kwargs)

# Deprecated alias kept for one release cycle after the rename.
Nim = Flock
