# flock-client (Python)

Python SDK for all NVIDIA NIM free endpoints. Zero dependencies — uses only Python 3.11+ stdlib.

## Install

```bash
pip install flock-client
# or from source:
pip install -e .
```

## Usage

```python
from nim_client import Nim
import os

nim = Nim(os.environ["NVIDIA_API_KEY"])

# Chat
answer = nim.chat.ask("What is quantum computing?")

# Streaming
for token in nim.chat.stream("Tell me a joke:"):
    print(token, end="", flush=True)

# Vision
caption = nim.vision.caption("https://example.com/image.jpg")

# Embeddings
results = nim.embeddings.find_most_similar("search query", ["doc1", "doc2", "doc3"])

# Safety / PII
clean = nim.safety.detect_pii("Call John at 555-123-4567")["anonymized"]

# Protein folding
structure = nim.biology.fold_protein(amino_acid_sequence)

# Molecule generation
molecules = nim.biology.generate_molecules("CC(=O)Oc1ccccc1C(=O)O", num=5)
```

See the main [README.md](../README.md) for full documentation.
