# 🚀 nim-client

[![Build Status](https://img.shields.io/github/actions/workflow/status/HayreBuilds/nim-client/ci.yml?branch=main)](https://github.com/HayreBuilds/nim-client/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![NVIDIA NIM](https://img.shields.io/badge/NVIDIA-NIM-76B900?logo=nvidia&logoColor=white)](https://build.nvidia.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/HayreBuilds/nim-client/pulls)
[![Star History](https://img.shields.io/github/stars/HayreBuilds/nim-client?style=social)](https://github.com/HayreBuilds/nim-client/stargazers)

**The unified SDK for all 77 NVIDIA NIM free endpoints. TypeScript and Python. One install. Every model.**

> Stop juggling multiple APIs. **nim-client** provides a type-safe, high-performance interface to every NVIDIA NIM model—from Chat and Vision to Biology and Speech.

---

## 🚀 Quick Start

```bash
npm install nim-client
```

```typescript
import { NimClient } from 'nim-client';

const nim = new NimClient('nvapi-...');

// Chat with Nemotron-Ultra
const response = await nim.chat.ask('What is protein folding?', { 
  model: 'nemotron-ultra' 
});

console.log(response.text);
```

---

## ✨ Key Features

- **🛡️ 100% Type-Safe**: Full TypeScript definitions for every endpoint and model ID.
- **🌐 Multi-Platform**: First-class support for both TypeScript/JavaScript and Python.
- **🧬 Domain Specialized**: Dedicated modules for Biology (protein folding), Vision (OCR/Captioning), and Speech (ASR/TTS).
- **🔄 Auto-Retry & Streaming**: Built-in resilience and support for real-time streaming responses.
- **📦 Zero Dependency (Python)**: The Python client uses only standard libraries for maximum compatibility.

---

## 📂 SDK Structure

The SDK is modularized for ease of use:

- **`chat`**: Ask, stream, summarize, extract, classify.
- **`vision`**: Caption, OCR, detect objects, compare images.
- **`embeddings`**: Embed, rerank, cosine similarity.
- **`safety`**: Content checking, PII detection, anonymization.
- **`biology`**: Protein folding, molecule generation.
- **`speech`**: Transcription, synthesis, zero-shot cloning.

---

## 🛠️ Usage Examples

### Vision: Image Captioning
```typescript
const caption = await nim.vision.caption('./image.jpg');
```

### Biology: Protein Folding
```typescript
const protein = await nim.biology.foldProtein('MAH...ZZ');
```

### Safety: PII Detection
```typescript
const check = await nim.safety.detectPII('My email is alice@example.com');
```

---

## 💻 Installation

### TypeScript
```bash
npm install nim-client
```

### Python
```bash
pip install nim-client
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 🛡️ Badge

Add this to your own project's README to show you use **nim-client**:

[![nim-client](https://img.shields.io/badge/Powered--by-nim--client-green)](https://github.com/HayreBuilds/nim-client)

```md
[![nim-client](https://img.shields.io/badge/Powered--by-nim--client-green)](https://github.com/HayreBuilds/nim-client)
```
