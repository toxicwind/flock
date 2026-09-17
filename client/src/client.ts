import type {
  NimClientConfig,
  NimError,
  ChatCompletionRequest,
  ChatCompletionResponse,
  StreamChunk,
  EmbeddingRequest,
  EmbeddingResponse,
  RerankRequest,
  RerankResponse,
} from "./types.js";

const DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1";
const DEFAULT_TIMEOUT = 60_000;
const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_RETRY_DELAY = 1_000;

const RETRYABLE_STATUS_CODES = new Set([429, 500, 502, 503, 504]);

export class NimClient {
  readonly apiKey: string;
  readonly baseURL: string;
  readonly timeout: number;
  readonly maxRetries: number;
  readonly retryDelay: number;

  constructor(config: NimClientConfig) {
    if (!config.apiKey) {
      throw new Error(
        "NimClient requires an apiKey. Get yours free at https://build.nvidia.com"
      );
    }
    this.apiKey = config.apiKey;
    this.baseURL = (config.baseURL ?? DEFAULT_BASE_URL).replace(/\/$/, "");
    this.timeout = config.timeout ?? DEFAULT_TIMEOUT;
    this.maxRetries = config.maxRetries ?? DEFAULT_MAX_RETRIES;
    this.retryDelay = config.retryDelay ?? DEFAULT_RETRY_DELAY;
  }

  async request<T>(
    path: string,
    options: RequestInit & { timeout?: number } = {}
  ): Promise<T> {
    const url = path.startsWith("http") ? path : `${this.baseURL}${path}`;
    const { timeout = this.timeout, ...fetchOptions } = options;

    let lastError: NimError | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      if (attempt > 0) {
        const delay = this.retryDelay * Math.pow(2, attempt - 1);
        await sleep(delay);
      }

      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);

      try {
        const response = await fetch(url, {
          ...fetchOptions,
          headers: {
            Authorization: `Bearer ${this.apiKey}`,
            "Content-Type": "application/json",
            Accept: "application/json",
            ...fetchOptions.headers,
          },
          signal: fetchOptions.signal ?? controller.signal,
        });

        clearTimeout(timer);

        if (!response.ok) {
          const body = await response.text().catch(() => "");
          const error = createError(
            `NIM API error ${response.status}: ${body}`,
            response.status,
            RETRYABLE_STATUS_CODES.has(response.status)
          );

          if (error.retryable && attempt < this.maxRetries) {
            lastError = error;
            continue;
          }
          throw error;
        }

        return response.json() as Promise<T>;
      } catch (err) {
        clearTimeout(timer);

        if (err instanceof Error && err.name === "AbortError") {
          throw createError(`Request timed out after ${timeout}ms`, 408, true);
        }

        const nimErr = err as NimError;
        if (nimErr.retryable && attempt < this.maxRetries) {
          lastError = nimErr;
          continue;
        }
        throw err;
      }
    }

    throw lastError ?? createError("Max retries exceeded", 0, false);
  }

  async *stream(
    path: string,
    body: Record<string, unknown>
  ): AsyncGenerator<StreamChunk> {
    const url = `${this.baseURL}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ ...body, stream: true }),
      signal: controller.signal,
    });

    clearTimeout(timer);

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw createError(`NIM API error ${response.status}: ${text}`, response.status, false);
    }

    if (!response.body) throw createError("No response body for streaming", 0, false);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed === "data: [DONE]") continue;
          if (trimmed.startsWith("data: ")) {
            try {
              yield JSON.parse(trimmed.slice(6)) as StreamChunk;
            } catch {
              // skip malformed chunk
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  async chat(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    return this.request<ChatCompletionResponse>("/chat/completions", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  async *chatStream(
    request: Omit<ChatCompletionRequest, "stream">
  ): AsyncGenerator<StreamChunk> {
    yield* this.stream("/chat/completions", request as Record<string, unknown>);
  }

  async embed(request: EmbeddingRequest): Promise<EmbeddingResponse> {
    return this.request<EmbeddingResponse>("/embeddings", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  async rerank(request: RerankRequest): Promise<RerankResponse> {
    return this.request<RerankResponse>("/ranking", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }
}

function createError(message: string, status: number, retryable: boolean): NimError {
  const err = new Error(message) as NimError;
  err.status = status;
  err.retryable = retryable;
  return err;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
