import { FlockClient } from "../client.js";
import { Models } from "../models.js";

export interface DocumentParseOptions {
  model?: string;
  mode?: "basic" | "advanced";
}

export interface ParsedDocument {
  pages: Array<{
    page_number: number;
    text: string;
    tables: Array<{
      rows: string[][];
      headers?: string[];
    }>;
    images: Array<{
      caption?: string;
      bbox?: number[];
    }>;
  }>;
  full_text: string;
  metadata?: Record<string, unknown>;
}

export interface OCRResult {
  text: string;
  confidence?: number;
  blocks?: Array<{
    text: string;
    bbox: number[];
    confidence: number;
  }>;
}

export class DocumentEndpoint {
  constructor(private client: FlockClient) {}

  async parse(
    pdfBase64: string,
    options: DocumentParseOptions = {}
  ): Promise<ParsedDocument> {
    const response = await this.client.request<{
      content?: string;
      pages?: Array<{
        page_number: number;
        text: string;
        tables?: Array<{ rows: string[][] }>;
        images?: Array<{ caption?: string }>;
      }>;
    }>("/retrieval/nvidia/nemoretriever-parse/v1/infer", {
      method: "POST",
      body: JSON.stringify({
        messages: [
          {
            role: "user",
            content: [
              {
                type: "text",
                text: "Extract all text, tables, and image descriptions from this document.",
              },
              {
                type: "media_url",
                media_url: {
                  url: `data:application/pdf;base64,${pdfBase64}`,
                },
              },
            ],
          },
        ],
        model: options.model ?? Models.Document.NEMORETRIEVER_PARSE,
      }),
    });

    const pages = response.pages ?? [];
    const full_text = pages.map((p) => p.text).join("\n\n");

    return {
      pages: pages.map((p) => ({
        page_number: p.page_number,
        text: p.text,
        tables: (p.tables ?? []).map((t) => ({ rows: t.rows })),
        images: (p.images ?? []).map((img) => ({ caption: img.caption })),
      })),
      full_text: full_text || (response.content ?? ""),
    };
  }

  async ocr(
    imageBase64: string,
    mimeType = "image/jpeg"
  ): Promise<OCRResult> {
    const response = await this.client.chat({
      model: Models.Document.NEMOTRON_OCR,
      messages: [
        {
          role: "user",
          content: [
            {
              type: "image_url",
              image_url: {
                url: `data:${mimeType};base64,${imageBase64}`,
              },
            },
            {
              type: "text",
              text: "Extract all text from this image. Return only the text, preserving the original layout.",
            },
          ],
        },
      ],
      temperature: 0.0,
      max_tokens: 2048,
    });

    return {
      text: response.choices[0]?.message.content ?? "",
    };
  }

  async extractTable(
    imageBase64: string,
    mimeType = "image/jpeg"
  ): Promise<{ headers: string[]; rows: string[][] }> {
    const response = await this.client.chat({
      model: Models.Document.NEMOTRON_TABLE,
      messages: [
        {
          role: "user",
          content: [
            {
              type: "image_url",
              image_url: {
                url: `data:${mimeType};base64,${imageBase64}`,
              },
            },
            {
              type: "text",
              text: 'Extract the table from this image and return it as JSON with format: {"headers": [...], "rows": [[...]]}. Return only the JSON.',
            },
          ],
        },
      ],
      temperature: 0.0,
      max_tokens: 2048,
    });

    const raw = response.choices[0]?.message.content ?? "{}";
    const match = raw.match(/\{[\s\S]*\}/);
    try {
      return match
        ? (JSON.parse(match[0]) as { headers: string[]; rows: string[][] })
        : { headers: [], rows: [] };
    } catch {
      return { headers: [], rows: [] };
    }
  }

  async chartToData(imageBase64: string): Promise<string> {
    const response = await this.client.chat({
      model: Models.Document.DEPLOT,
      messages: [
        {
          role: "user",
          content: [
            {
              type: "image_url",
              image_url: { url: `data:image/jpeg;base64,${imageBase64}` },
            },
            {
              type: "text",
              text: "Generate underlying data table of the figure below:",
            },
          ],
        },
      ],
      temperature: 0.0,
      max_tokens: 1024,
    });

    return response.choices[0]?.message.content ?? "";
  }
}
