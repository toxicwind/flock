export { NimClient } from "./client.js";
export { Models } from "./models.js";
export type {
  ChatModel,
  VisionModel,
  EmbeddingModel,
  RerankModel,
  SpeechModel,
  SafetyModel,
  DocumentModel,
  BiologyModel,
} from "./models.js";

export { ChatEndpoint } from "./endpoints/chat.js";
export { VisionEndpoint } from "./endpoints/vision.js";
export { EmbeddingsEndpoint } from "./endpoints/embeddings.js";
export { SafetyEndpoint } from "./endpoints/safety.js";
export { BiologyEndpoint } from "./endpoints/biology.js";
export { SpeechEndpoint } from "./endpoints/speech.js";
export { DocumentEndpoint } from "./endpoints/document.js";
export { TranslationEndpoint, SUPPORTED_LANGUAGES } from "./endpoints/translation.js";

export type {
  NimClientConfig,
  ChatMessage,
  ChatCompletionRequest,
  ChatCompletionResponse,
  StreamChunk,
  EmbeddingRequest,
  EmbeddingResponse,
  RerankRequest,
  RerankResponse,
  NimError,
} from "./types.js";

export type { ChatOptions } from "./endpoints/chat.js";
export type { VisionOptions } from "./endpoints/vision.js";
export type { EmbedOptions, RerankOptions } from "./endpoints/embeddings.js";
export type {
  SafetyOptions,
  PIIEntity,
  PIIResult,
  SafetyResult,
  JailbreakResult,
} from "./endpoints/safety.js";
export type {
  ProteinFoldResult,
  MoleculeGenerationOptions,
  MoleculeResult,
} from "./endpoints/biology.js";
export type {
  TranscribeOptions,
  TranscribeResult,
  TTSOptions,
} from "./endpoints/speech.js";
export type { DocumentParseOptions, ParsedDocument, OCRResult } from "./endpoints/document.js";
export type { TranslateOptions, TranslateResult } from "./endpoints/translation.js";

import { NimClient } from "./client.js";
import { ChatEndpoint } from "./endpoints/chat.js";
import { VisionEndpoint } from "./endpoints/vision.js";
import { EmbeddingsEndpoint } from "./endpoints/embeddings.js";
import { SafetyEndpoint } from "./endpoints/safety.js";
import { BiologyEndpoint } from "./endpoints/biology.js";
import { SpeechEndpoint } from "./endpoints/speech.js";
import { DocumentEndpoint } from "./endpoints/document.js";
import { TranslationEndpoint } from "./endpoints/translation.js";
import type { NimClientConfig } from "./types.js";

export class Nim {
  readonly chat: ChatEndpoint;
  readonly vision: VisionEndpoint;
  readonly embeddings: EmbeddingsEndpoint;
  readonly safety: SafetyEndpoint;
  readonly biology: BiologyEndpoint;
  readonly speech: SpeechEndpoint;
  readonly document: DocumentEndpoint;
  readonly translation: TranslationEndpoint;

  private _client: NimClient;

  constructor(config: NimClientConfig | string) {
    const resolvedConfig: NimClientConfig =
      typeof config === "string" ? { apiKey: config } : config;

    this._client = new NimClient(resolvedConfig);

    this.chat = new ChatEndpoint(this._client);
    this.vision = new VisionEndpoint(this._client);
    this.embeddings = new EmbeddingsEndpoint(this._client);
    this.safety = new SafetyEndpoint(this._client);
    this.biology = new BiologyEndpoint(this._client);
    this.speech = new SpeechEndpoint(this._client);
    this.document = new DocumentEndpoint(this._client);
    this.translation = new TranslationEndpoint(this._client);
  }

  get client(): NimClient {
    return this._client;
  }
}

export function createNimClient(config: NimClientConfig | string): Nim {
  return new Nim(config);
}
