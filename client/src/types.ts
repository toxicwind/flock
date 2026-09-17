export interface FlockClientConfig {
  apiKey: string;
  /** Additional keys; apiKey may also be comma-separated. Enables rotation. */
  apiKeys?: string[];
  baseURL?: string;
  timeout?: number;
  maxRetries?: number;
  retryDelay?: number;
}

export interface RequestOptions {
  signal?: AbortSignal;
  stream?: boolean;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string | ContentPart[];
}

export type ContentPart = TextPart | ImageUrlPart;

export interface TextPart {
  type: "text";
  text: string;
}

export interface ImageUrlPart {
  type: "image_url";
  image_url: { url: string };
}

export interface ChatCompletionRequest {
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  stream?: boolean;
  stop?: string | string[];
  seed?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

export interface ChatChoice {
  index: number;
  message: { role: string; content: string };
  finish_reason: string | null;
  delta?: { content?: string };
}

export interface ChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: ChatChoice[];
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface StreamChunk {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Array<{
    index: number;
    delta: { role?: string; content?: string };
    finish_reason: string | null;
  }>;
}

export interface EmbeddingRequest {
  model: string;
  input: string | string[];
  input_type?: "query" | "passage";
  encoding_format?: "float" | "base64";
  truncate?: "NONE" | "START" | "END";
}

export interface EmbeddingData {
  object: "embedding";
  index: number;
  embedding: number[];
}

export interface EmbeddingResponse {
  object: "list";
  data: EmbeddingData[];
  model: string;
  usage: { prompt_tokens: number; total_tokens: number };
}

export interface RerankRequest {
  model: string;
  query: string;
  passages: Array<{ text: string }>;
  truncate?: "NONE" | "END";
}

export interface RerankResult {
  index: number;
  logit: number;
  text?: string;
}

export interface RerankResponse {
  rankings: RerankResult[];
  usage: { prompt_tokens: number; total_tokens: number };
}

export interface NimError extends Error {
  status?: number;
  code?: string;
  retryable?: boolean;
}

export interface ASRRequest {
  model?: string;
  audio: Blob | Buffer | string;
  language?: string;
  task?: "transcribe" | "translate";
}

export interface ASRResponse {
  text: string;
  segments?: Array<{
    start: number;
    end: number;
    text: string;
  }>;
}

export interface TTSRequest {
  model?: string;
  input: string;
  voice?: string;
  language?: string;
  sample_rate?: number;
  audio_prompt_voice?: string;
}

export interface PIIEntity {
  text: string;
  label: string;
  start: number;
  end: number;
  score: number;
}

export interface PIIResponse {
  entities: PIIEntity[];
  anonymized_text?: string;
}

export interface SafetyCheckRequest {
  model?: string;
  messages: ChatMessage[];
  threshold?: number;
}

export interface SafetyCheckResponse {
  safe: boolean;
  categories?: Record<string, number>;
  flagged_categories?: string[];
}

export interface ProteinFoldRequest {
  sequence: string;
}

export interface ProteinFoldResponse {
  pdb: string;
  mean_plddt?: number;
}

export interface MoleculeRequest {
  smiles?: string;
  num_molecules?: number;
  temperature?: number;
  iterations?: number;
}

export interface MoleculeResponse {
  molecules: Array<{
    smiles: string;
    score?: number;
  }>;
}

export interface TranslationRequest {
  model?: string;
  text: string;
  source_language?: string;
  target_language: string;
}

export interface TranslationResponse {
  translated_text: string;
  source_language?: string;
  target_language: string;
}
