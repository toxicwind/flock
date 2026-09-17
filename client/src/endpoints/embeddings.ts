import { FlockClient } from "../client.js";
import { Models } from "../models.js";
import type { EmbeddingResponse, RerankResponse } from "../types.js";

export interface EmbedOptions {
  model?: string;
  input_type?: "query" | "passage";
  truncate?: "NONE" | "START" | "END";
}

export interface RerankOptions {
  model?: string;
  truncate?: "NONE" | "END";
}

export class EmbeddingsEndpoint {
  constructor(private client: FlockClient) {}

  async embed(text: string, options: EmbedOptions = {}): Promise<number[]> {
    const response = await this.client.embed({
      model: options.model ?? Models.Embeddings.NV_EMBEDQA_E5,
      input: text,
      input_type: options.input_type ?? "query",
      truncate: options.truncate ?? "END",
    });
    return response.data[0]?.embedding ?? [];
  }

  async embedMany(
    texts: string[],
    options: EmbedOptions = {}
  ): Promise<number[][]> {
    const response = await this.client.embed({
      model: options.model ?? Models.Embeddings.NV_EMBEDQA_E5,
      input: texts,
      input_type: options.input_type ?? "passage",
      truncate: options.truncate ?? "END",
    });
    return response.data
      .sort((a, b) => a.index - b.index)
      .map((d) => d.embedding);
  }

  async embedCode(code: string, options: EmbedOptions = {}): Promise<number[]> {
    return this.embed(code, {
      model: Models.Embeddings.NV_EMBED_CODE,
      input_type: "passage",
      ...options,
    });
  }

  async embedQuery(query: string, options: EmbedOptions = {}): Promise<number[]> {
    return this.embed(query, {
      input_type: "query",
      ...options,
    });
  }

  async rerank(
    query: string,
    passages: string[],
    options: RerankOptions = {}
  ): Promise<Array<{ text: string; score: number; index: number }>> {
    const response = await this.client.rerank({
      model: options.model ?? Models.Rerank.RERANK_MISTRAL,
      query,
      passages: passages.map((text) => ({ text })),
      truncate: options.truncate ?? "END",
    });

    return response.rankings.map((r) => ({
      text: passages[r.index] ?? "",
      score: r.logit,
      index: r.index,
    }));
  }

  cosineSimilarity(a: number[], b: number[]): number {
    if (a.length !== b.length) throw new Error("Vectors must have equal length");
    let dot = 0, normA = 0, normB = 0;
    for (let i = 0; i < a.length; i++) {
      dot += a[i]! * b[i]!;
      normA += a[i]! * a[i]!;
      normB += b[i]! * b[i]!;
    }
    const denom = Math.sqrt(normA) * Math.sqrt(normB);
    return denom === 0 ? 0 : dot / denom;
  }

  async findMostSimilar(
    query: string,
    candidates: string[],
    options: EmbedOptions = {}
  ): Promise<{ text: string; score: number; index: number }[]> {
    const [queryVec, candidateVecs] = await Promise.all([
      this.embedQuery(query, options),
      this.embedMany(candidates, { ...options, input_type: "passage" }),
    ]);

    return candidates
      .map((text, i) => ({
        text,
        score: this.cosineSimilarity(queryVec, candidateVecs[i]!),
        index: i,
      }))
      .sort((a, b) => b.score - a.score);
  }
}
