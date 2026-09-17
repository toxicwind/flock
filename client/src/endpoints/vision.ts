import { FlockClient } from "../client.js";
import { Models } from "../models.js";
import type { ChatMessage } from "../types.js";

export interface VisionOptions {
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

function toDataUrl(imageBuffer: Buffer, mimeType = "image/jpeg"): string {
  return `data:${mimeType};base64,${imageBuffer.toString("base64")}`;
}

export class VisionEndpoint {
  constructor(private client: FlockClient) {}

  async analyze(
    imageUrl: string,
    prompt: string,
    options: VisionOptions = {}
  ): Promise<string> {
    const messages: ChatMessage[] = [
      {
        role: "user",
        content: [
          { type: "image_url", image_url: { url: imageUrl } },
          { type: "text", text: prompt },
        ],
      },
    ];

    const response = await this.client.chat({
      model: options.model ?? Models.Vision.LLAMA_3_2_90B,
      messages,
      temperature: options.temperature ?? 0.2,
      max_tokens: options.max_tokens ?? 1024,
    });

    return response.choices[0]?.message.content ?? "";
  }

  async analyzeBuffer(
    imageBuffer: Buffer,
    prompt: string,
    options: VisionOptions & { mimeType?: string } = {}
  ): Promise<string> {
    const dataUrl = toDataUrl(imageBuffer, options.mimeType ?? "image/jpeg");
    return this.analyze(dataUrl, prompt, options);
  }

  async caption(imageUrl: string, options: VisionOptions = {}): Promise<string> {
    return this.analyze(
      imageUrl,
      "Describe this image in detail. What do you see?",
      options
    );
  }

  async ocr(imageUrl: string, options: VisionOptions = {}): Promise<string> {
    return this.analyze(
      imageUrl,
      "Extract all text visible in this image. Return only the extracted text, preserving layout where possible.",
      options
    );
  }

  async readChart(imageUrl: string, options: VisionOptions = {}): Promise<string> {
    return this.analyze(
      imageUrl,
      "This is a chart or graph. Extract all data points, labels, axis values, and describe the trend or insight the chart shows. Return as structured text.",
      { model: Models.Document.DEPLOT, ...options }
    );
  }

  async detectObjects(imageUrl: string, options: VisionOptions = {}): Promise<string> {
    return this.analyze(
      imageUrl,
      "List all objects, people, and elements visible in this image with their approximate positions.",
      options
    );
  }

  async answer(
    imageUrl: string,
    question: string,
    options: VisionOptions = {}
  ): Promise<string> {
    return this.analyze(imageUrl, question, options);
  }

  async compareImages(
    imageUrl1: string,
    imageUrl2: string,
    prompt = "Compare these two images and describe the differences.",
    options: VisionOptions = {}
  ): Promise<string> {
    const messages: ChatMessage[] = [
      {
        role: "user",
        content: [
          { type: "image_url", image_url: { url: imageUrl1 } },
          { type: "image_url", image_url: { url: imageUrl2 } },
          { type: "text", text: prompt },
        ],
      },
    ];

    const response = await this.client.chat({
      model: options.model ?? Models.Vision.LLAMA_3_2_90B,
      messages,
      temperature: options.temperature ?? 0.2,
      max_tokens: options.max_tokens ?? 1024,
    });

    return response.choices[0]?.message.content ?? "";
  }
}
