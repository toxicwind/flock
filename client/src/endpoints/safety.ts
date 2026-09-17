import { FlockClient } from "../client.js";
import { Models } from "../models.js";
import type { ChatMessage } from "../types.js";

export interface SafetyOptions {
  model?: string;
  threshold?: number;
}

export interface PIIEntity {
  text: string;
  label: string;
  start: number;
  end: number;
  score: number;
}

export interface PIIResult {
  entities: PIIEntity[];
  anonymized: string;
  hasPII: boolean;
}

export interface SafetyResult {
  safe: boolean;
  violated: string[];
  scores: Record<string, number>;
  explanation?: string;
}

export interface JailbreakResult {
  isJailbreak: boolean;
  confidence: number;
  explanation?: string;
}

export class SafetyEndpoint {
  constructor(private client: FlockClient) {}

  async checkContent(
    text: string,
    options: SafetyOptions = {}
  ): Promise<SafetyResult> {
    const response = await this.client.chat({
      model: options.model ?? Models.Safety.NEMOGUARD_CONTENT,
      messages: [{ role: "user", content: text }],
      max_tokens: 200,
      temperature: 0.1,
    });

    const raw = response.choices[0]?.message.content ?? "";
    const safe = raw.toLowerCase().includes("safe") && !raw.toLowerCase().includes("unsafe");

    return {
      safe,
      violated: safe ? [] : ["content_policy"],
      scores: { safety: safe ? 1 : 0 },
      explanation: raw,
    };
  }

  async checkMessages(
    messages: ChatMessage[],
    options: SafetyOptions = {}
  ): Promise<SafetyResult> {
    const last = messages[messages.length - 1]?.content;
    const text = typeof last === "string" ? last : JSON.stringify(last);
    return this.checkContent(text, options);
  }

  async detectPII(
    text: string,
    options: SafetyOptions = {}
  ): Promise<PIIResult> {
    const response = await this.client.request<{ predictions: PIIEntity[][] }>(
      "/chat/completions",
      {
        method: "POST",
        body: JSON.stringify({
          model: options.model ?? Models.Safety.GLINER_PII,
          messages: [{ role: "user", content: text }],
          max_tokens: 512,
          temperature: 0.0,
        }),
      }
    );

    const raw = (response as { choices?: Array<{ message: { content: string } }> })
      ?.choices?.[0]?.message.content ?? "[]";

    let entities: PIIEntity[] = [];
    try {
      entities = JSON.parse(raw) as PIIEntity[];
    } catch {
      entities = [];
    }

    let anonymized = text;
    for (const entity of [...entities].sort((a, b) => b.start - a.start)) {
      anonymized =
        anonymized.slice(0, entity.start) +
        `[${entity.label}]` +
        anonymized.slice(entity.end);
    }

    return { entities, anonymized, hasPII: entities.length > 0 };
  }

  async anonymize(text: string): Promise<string> {
    const result = await this.detectPII(text);
    return result.anonymized;
  }

  async detectJailbreak(
    prompt: string,
    options: SafetyOptions = {}
  ): Promise<JailbreakResult> {
    const response = await this.client.chat({
      model: options.model ?? Models.Safety.NEMOJAIL,
      messages: [{ role: "user", content: prompt }],
      max_tokens: 200,
      temperature: 0.0,
    });

    const raw = response.choices[0]?.message.content?.toLowerCase() ?? "";
    const isJailbreak = raw.includes("jailbreak") || raw.includes("injection");

    return {
      isJailbreak,
      confidence: isJailbreak ? 0.9 : 0.1,
      explanation: response.choices[0]?.message.content,
    };
  }

  async enforceTopicPolicy(
    message: string,
    allowedTopics: string[],
    options: SafetyOptions = {}
  ): Promise<{ allowed: boolean; reason?: string }> {
    const system = `You are a topic guard. Only allow messages related to: ${allowedTopics.join(", ")}. Respond with JSON: {"allowed": boolean, "reason": string}`;
    const response = await this.client.chat({
      model: options.model ?? Models.Safety.NEMOGUARD_TOPIC,
      messages: [
        { role: "system", content: system },
        { role: "user", content: message },
      ],
      max_tokens: 100,
      temperature: 0.0,
    });

    try {
      const raw = response.choices[0]?.message.content ?? "{}";
      const jsonMatch = raw.match(/\{[\s\S]*\}/);
      return jsonMatch
        ? (JSON.parse(jsonMatch[0]) as { allowed: boolean; reason?: string })
        : { allowed: false, reason: "Could not parse policy response" };
    } catch {
      return { allowed: false, reason: "Policy check failed" };
    }
  }

  async isSafe(text: string): Promise<boolean> {
    const result = await this.checkContent(text);
    return result.safe;
  }
}
