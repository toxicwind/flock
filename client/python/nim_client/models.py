class Models:
    class Chat:
        NEMOTRON_ULTRA = "nvidia/nemotron-3-ultra-550b-a55b"
        NEMOTRON_SUPER = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
        NEMOTRON_NANO = "nvidia/llama-3.1-nemotron-nano-8b-v1"
        LLAMA_3_3_70B = "meta/llama-3.3-70b-instruct"
        LLAMA_3_1_70B = "meta/llama-3.1-70b-instruct"
        LLAMA_3_1_8B = "meta/llama-3.1-8b-instruct"
        LLAMA_3_1_405B = "meta/llama-3.1-405b-instruct"
        MISTRAL_LARGE = "mistralai/mistral-large-3-675b-instruct-2512"
        MISTRAL_7B = "mistralai/mistral-7b-instruct-v0.3"
        DEEPSEEK_V4_FLASH = "deepseek-ai/deepseek-v4-flash"
        QWEN3_CODER = "qwen/qwen3-coder-480b-a35b-instruct"
        QWEN2_5_72B = "qwen/qwen2.5-72b-instruct"
        PALMYRA_MED = "writer/palmyra-med-70b-32k"
        PALMYRA_FIN = "writer/palmyra-fin-70b-32k"
        CODESTRAL = "mistralai/codestral-22b-instruct-v0.1"

    class Vision:
        LLAMA_3_2_90B = "meta/llama-3.2-90b-vision-instruct"
        LLAMA_3_2_11B = "meta/llama-3.2-11b-vision-instruct"
        PALIGEMMA = "google/paligemma"

    class Embeddings:
        NV_EMBEDQA_E5 = "nvidia/nv-embedqa-e5-v5"
        NV_EMBED_CODE = "nvidia/nv-embedcode-7b-v1"
        LLAMA_NEMOTRON_EMBED = "nvidia/llama-nemotron-embed-1b-v2"
        BGE_M3 = "baai/bge-m3"

    class Rerank:
        RERANK_MISTRAL = "nvidia/rerank-qa-mistral-4b"
        NEMOTRON_RERANK = "nvidia/nemotron-rerank-1b-v2"

    class Safety:
        NEMOGUARD_CONTENT = "nvidia/llama-3.1-nemoguard-8b-content-safety"
        NEMOGUARD_TOPIC = "nvidia/llama-3.1-nemoguard-8b-topic-control"
        GLINER_PII = "nvidia/gliner-pii"
        NEMOJAIL = "nvidia/nemojail-jailbreak-detect"

    class Biology:
        ESMFOLD = "nvidia/esmfold"
        ESM2_650M = "nvidia/esm2-650m"
        GENMOL = "nvidia/genmol"
        MOLMIM = "nvidia/molmim"

    class Speech:
        PARAKEET_CTC = "nvidia/parakeet-ctc-1.1b-asr"
        CANARY_1B = "nvidia/canary-1b-asr"
        MAGPIE_TTS = "nvidia/magpie-tts-zeroshot"

    class Document:
        NEMORETRIEVER_PARSE = "nvidia/nemoretriever-parse"
        NEMOTRON_OCR = "nvidia/nemotron-ocr-v1"
        DEPLOT = "google/deplot"

    class Translation:
        RIVA_TRANSLATE = "nvidia/riva-translate-4b-instruct-v1.1"
