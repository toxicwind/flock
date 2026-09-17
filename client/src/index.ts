export { FlockClient } from "./client.js";
export { FlockKeyPool, parseRetryAfterMs, splitKeys } from "./keypool.js";
export type { FlockKeyStats } from "./keypool.js";
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
  FlockClientConfig,
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

import { FlockClient } from "./client.js";
import { ChatEndpoint } from "./endpoints/chat.js";
import { VisionEndpoint } from "./endpoints/vision.js";
import { EmbeddingsEndpoint } from "./endpoints/embeddings.js";
import { SafetyEndpoint } from "./endpoints/safety.js";
import { BiologyEndpoint } from "./endpoints/biology.js";
import { SpeechEndpoint } from "./endpoints/speech.js";
import { DocumentEndpoint } from "./endpoints/document.js";
import { TranslationEndpoint } from "./endpoints/translation.js";
import type { FlockClientConfig } from "./types.js";

export class Flock {
  readonly chat: ChatEndpoint;
  readonly vision: VisionEndpoint;
  readonly embeddings: EmbeddingsEndpoint;
  readonly safety: SafetyEndpoint;
  readonly biology: BiologyEndpoint;
  readonly speech: SpeechEndpoint;
  readonly document: DocumentEndpoint;
  readonly translation: TranslationEndpoint;

  private _client: FlockClient;

  constructor(config: FlockClientConfig | string) {
    const resolvedConfig: FlockClientConfig =
      typeof config === "string" ? { apiKey: config } : config;

    this._client = new FlockClient(resolvedConfig);

    this.chat = new ChatEndpoint(this._client);
    this.vision = new VisionEndpoint(this._client);
    this.embeddings = new EmbeddingsEndpoint(this._client);
    this.safety = new SafetyEndpoint(this._client);
    this.biology = new BiologyEndpoint(this._client);
    this.speech = new SpeechEndpoint(this._client);
    this.document = new DocumentEndpoint(this._client);
    this.translation = new TranslationEndpoint(this._client);
  }

  get client(): FlockClient {
    return this._client;
  }
}

export function createFlockClient(config: FlockClientConfig | string): Flock {
  return new Flock(config);
}

// Deprecated aliases kept for one release cycle after the nim-client -> flock-client rename.
/** @deprecated Use Flock instead. */
export const Nim = Flock;
/** @deprecated Use FlockClient instead. */
export const NimClient = FlockClient;
/** @deprecated Use createFlockClient instead. */
export const createNimClient = createFlockClient;
