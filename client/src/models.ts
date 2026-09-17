export const Models = {
  Chat: {
    NEMOTRON_ULTRA: "nvidia/nemotron-3-ultra-550b-a55b",
    NEMOTRON_SUPER: "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    NEMOTRON_NANO: "nvidia/llama-3.1-nemotron-nano-8b-v1",
    NEMOTRON_NANO_OMNI: "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    LLAMA_3_3_70B: "meta/llama-3.3-70b-instruct",
    LLAMA_3_1_70B: "meta/llama-3.1-70b-instruct",
    LLAMA_3_1_8B: "meta/llama-3.1-8b-instruct",
    LLAMA_3_1_405B: "meta/llama-3.1-405b-instruct",
    MISTRAL_LARGE: "mistralai/mistral-large-3-675b-instruct-2512",
    MISTRAL_7B: "mistralai/mistral-7b-instruct-v0.3",
    MIXTRAL_8X7B: "mistralai/mixtral-8x7b-instruct-v0.1",
    MIXTRAL_8X22B: "mistralai/mixtral-8x22b-instruct-v0.1",
    DEEPSEEK_V4_FLASH: "deepseek-ai/deepseek-v4-flash",
    QWEN3_CODER: "qwen/qwen3-coder-480b-a35b-instruct",
    QWEN2_5_72B: "qwen/qwen2.5-72b-instruct",
    PHI_4: "microsoft/phi-4-multimodal-instruct",
    GEMMA_2_27B: "google/gemma-2-27b-it",
    PALMYRA_MED: "writer/palmyra-med-70b-32k",
    PALMYRA_FIN: "writer/palmyra-fin-70b-32k",
    CODESTRAL: "mistralai/codestral-22b-instruct-v0.1",
  },

  Vision: {
    LLAMA_3_2_90B: "meta/llama-3.2-90b-vision-instruct",
    LLAMA_3_2_11B: "meta/llama-3.2-11b-vision-instruct",
    PALIGEMMA: "google/paligemma",
    PHI_4_MULTIMODAL: "microsoft/phi-4-multimodal-instruct",
    NEMOTRON_NANO_VL: "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
    COSMOS_REASON: "nvidia/cosmos-reason2-8b",
  },

  Embeddings: {
    NV_EMBEDQA_E5: "nvidia/nv-embedqa-e5-v5",
    NV_EMBEDQA_MISTRAL: "nvidia/nv-embedqa-mistral-7b-v2",
    NV_EMBED_CODE: "nvidia/nv-embedcode-7b-v1",
    LLAMA_NEMOTRON_EMBED: "nvidia/llama-nemotron-embed-1b-v2",
    LLAMA_NEMOTRON_EMBED_VL: "nvidia/llama-nemotron-embed-vl-1b-v2",
    BGE_M3: "baai/bge-m3",
    E5_LARGE: "intfloat/multilingual-e5-large-instruct",
  },

  Rerank: {
    RERANK_MISTRAL: "nvidia/rerank-qa-mistral-4b",
    NEMOTRON_RERANK: "nvidia/nemotron-rerank-1b-v2",
  },

  Speech: {
    PARAKEET_CTC: "nvidia/parakeet-ctc-1.1b-asr",
    PARAKEET_TDT: "nvidia/parakeet-tdt-1.1b-asr",
    CANARY_1B: "nvidia/canary-1b-asr",
    MAGPIE_TTS: "nvidia/magpie-tts-zeroshot",
    FASTPITCH_HIFIGAN: "nvidia/fastpitch-hifigan-tts",
  },

  Safety: {
    NEMOGUARD_CONTENT: "nvidia/llama-3.1-nemoguard-8b-content-safety",
    NEMOGUARD_TOPIC: "nvidia/llama-3.1-nemoguard-8b-topic-control",
    NEMOTRON_CONTENT_SAFETY: "nvidia/nemotron-3.5-content-safety",
    NEMOTRON_CONTENT_SAFETY_REASONING: "nvidia/nemotron-content-safety-reasoning-4b",
    GLINER_PII: "nvidia/gliner-pii",
    NEMOJAIL: "nvidia/nemojail-jailbreak-detect",
    AEGIS: "nvidia/llama-3.1-aegis-defense-v1.0",
  },

  Document: {
    NEMORETRIEVER_PARSE: "nvidia/nemoretriever-parse",
    NEMOTRON_OCR: "nvidia/nemotron-ocr-v1",
    NEMOTRON_TABLE: "nvidia/nemotron-table-structure-v1",
    NEMOTRON_PAGE_ELEMENTS: "nvidia/nemotron-page-elements-v3",
    NEMOTRON_GRAPHIC: "nvidia/nemotron-graphic-elements-v1",
    PADDLE_OCR: "nvidia/paddleocr",
    DEPLOT: "google/deplot",
  },

  Biology: {
    ESMFOLD: "nvidia/esmfold",
    ESM2_650M: "nvidia/esm2-650m",
    MSA_SEARCH: "nvidia/msa-search",
    GENMOL: "nvidia/genmol",
    MOLMIM: "nvidia/molmim",
    RFDIFFUSION: "nvidia/rfdiffusion",
    BOLTZ2: "nvidia/Boltz-2",
  },

  Video: {
    COSMOS3_NANO: "nvidia/cosmos3-nano",
    COSMOS_TRANSFER: "nvidia/cosmos-transfer1-7b",
    COSMOS_PREDICT: "nvidia/cosmos-predict1-5b",
    COSMOS_TRANSFER2: "nvidia/cosmos-transfer2.5-2b",
    SYNTHETIC_VIDEO_DETECTOR: "nvidia/ai-synthetic-video-detector",
  },

  Weather: {
    FOURCASTNET: "nvidia/fourcastnet",
  },

  Translation: {
    RIVA_TRANSLATE: "nvidia/riva-translate-4b-instruct-v1.1",
  },

  Audio: {
    BACKGROUND_NOISE_REMOVAL: "nvidia/noise-cancellation",
    STUDIO_VOICE: "nvidia/studio-voice",
    ACTIVE_SPEAKER_DETECTION: "nvidia/active-speaker-detection",
  },

  Code: {
    QWEN3_CODER: "qwen/qwen3-coder-480b-a35b-instruct",
    NV_EMBED_CODE: "nvidia/nv-embedcode-7b-v1",
    CODESTRAL: "mistralai/codestral-22b-instruct-v0.1",
    DEEPSEEK_V4_FLASH: "deepseek-ai/deepseek-v4-flash",
  },
} as const;

export type ChatModel = (typeof Models.Chat)[keyof typeof Models.Chat];
export type VisionModel = (typeof Models.Vision)[keyof typeof Models.Vision];
export type EmbeddingModel = (typeof Models.Embeddings)[keyof typeof Models.Embeddings];
export type RerankModel = (typeof Models.Rerank)[keyof typeof Models.Rerank];
export type SpeechModel = (typeof Models.Speech)[keyof typeof Models.Speech];
export type SafetyModel = (typeof Models.Safety)[keyof typeof Models.Safety];
export type DocumentModel = (typeof Models.Document)[keyof typeof Models.Document];
export type BiologyModel = (typeof Models.Biology)[keyof typeof Models.Biology];
