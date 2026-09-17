import { FlockClient } from "../client.js";
import { Models } from "../models.js";
import type { ChatMessage, ChatCompletionResponse, StreamChunk } from "../types.js";

export interface ChatOptions {
  model?: string;
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  stop?: string | string[];
  seed?: number;
  system?: string;
}

export interface AskOptions extends ChatOptions {
  stream?: false;
}

export class ChatEndpoint {
  constructor(private client: FlockClient) {}

  async complete(
    messages: ChatMessage[],
    options: ChatOptions = {}
  ): Promise<ChatCompletionResponse> {
    const { system, ...rest } = options;
    const allMessages: ChatMessage[] = system
      ? [{ role: "system", content: system }, ...messages]
      : messages;

    return this.client.chat({
      model: rest.model ?? Models.Chat.LLAMA_3_1_70B,
      messages: allMessages,
      temperature: rest.temperature ?? 0.2,
      top_p: rest.top_p ?? 0.7,
      max_tokens: rest.max_tokens ?? 1024,
      stop: rest.stop,
      seed: rest.seed,
    });
  }

  async ask(prompt: string, options: ChatOptions = {}): Promise<string> {
    const response = await this.complete(
      [{ role: "user", content: prompt }],
      options
    );
    return response.choices[0]?.message.content ?? "";
  }

  async *stream(
    messages: ChatMessage[],
    options: ChatOptions = {}
  ): AsyncGenerator<StreamChunk> {
    const { system, ...rest } = options;
    const allMessages: ChatMessage[] = system
      ? [{ role: "system", content: system }, ...messages]
      : messages;

    yield* this.client.chatStream({
      model: rest.model ?? Models.Chat.LLAMA_3_1_70B,
      messages: allMessages,
      temperature: rest.temperature ?? 0.2,
      top_p: rest.top_p ?? 0.7,
      max_tokens: rest.max_tokens ?? 1024,
      stop: rest.stop,
      seed: rest.seed,
    });
  }

  async *streamText(
    prompt: string,
    options: ChatOptions = {}
  ): AsyncGenerator<string> {
    for await (const chunk of this.stream(
      [{ role: "user", content: prompt }],
      options
    )) {
      const content = chunk.choices[0]?.delta?.content;
      if (content) yield content;
    }
  }

  async reason(prompt: string, options: ChatOptions = {}): Promise<string> {
    return this.ask(prompt, {
      model: Models.Chat.NEMOTRON_ULTRA,
      temperature: 0.6,
      top_p: 0.95,
      max_tokens: 4096,
      ...options,
    });
  }

  async summarize(text: string, options: ChatOptions = {}): Promise<string> {
    return this.ask(
      `Summarize the following content clearly and concisely:\n\n${text}`,
      {
        model: Models.Chat.LLAMA_3_1_70B,
        temperature: 0.1,
        max_tokens: 512,
        ...options,
      }
    );
  }

  async extract<T = Record<string, unknown>>(
    text: string,
    schema: string,
    options: ChatOptions = {}
  ): Promise<T> {
    const prompt = `Extract the following fields from the text and return as valid JSON only (no markdown, no explanation):\n\nSchema: ${schema}\n\nText:\n${text}`;
    const raw = await this.ask(prompt, {
      model: Models.Chat.LLAMA_3_1_70B,
      temperature: 0.1,
      max_tokens: 1024,
      ...options,
    });
    const jsonMatch = raw.match(/\{[\s\S]*\}/);
    if (!jsonMatch) throw new Error("Model did not return valid JSON");
    return JSON.parse(jsonMatch[0]) as T;
  }

  async classify(
    text: string,
    labels: string[],
    options: ChatOptions = {}
  ): Promise<string> {
    const prompt = `Classify the following text into exactly one of these categories: ${labels.join(", ")}.\nReturn only the category name, nothing else.\n\nText: ${text}`;
    const result = await this.ask(prompt, {
      model: Models.Chat.LLAMA_3_1_8B,
      temperature: 0.1,
      max_tokens: 50,
      ...options,
    });
    return result.trim();
  }

  async translate(text: string, targetLanguage: string, options: ChatOptions = {}): Promise<string> {
    return this.ask(
      `Translate the following text to ${targetLanguage}. Return only the translation, no explanation:\n\n${text}`,
      { model: Models.Chat.MISTRAL_7B, temperature: 0.1, max_tokens: 2048, ...options }
    );
  }
}
