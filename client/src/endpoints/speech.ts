import { FlockClient } from "../client.js";
import { Models } from "../models.js";

const AUDIO_BASE_URL = "https://integrate.api.nvidia.com/v1";

export interface TranscribeOptions {
  model?: string;
  language?: string;
  task?: "transcribe" | "translate";
}

export interface TranscribeResult {
  text: string;
  segments?: Array<{ start: number; end: number; text: string }>;
  language?: string;
}

export interface TTSOptions {
  model?: string;
  voice?: string;
  language?: string;
  sample_rate?: number;
}

export class SpeechEndpoint {
  constructor(private client: FlockClient) {}

  async transcribe(
    audioData: Buffer | Blob | string,
    options: TranscribeOptions = {}
  ): Promise<TranscribeResult> {
    const formData = new FormData();

    if (typeof audioData === "string") {
      formData.append("file", audioData);
    } else if (Buffer.isBuffer(audioData)) {
      formData.append(
        "file",
        new Blob([audioData], { type: "audio/wav" }),
        "audio.wav"
      );
    } else {
      formData.append("file", audioData, "audio.wav");
    }

    formData.append("model", options.model ?? Models.Speech.PARAKEET_CTC);
    if (options.language) formData.append("language", options.language);
    if (options.task) formData.append("task", options.task);

    const response = await fetch(`${AUDIO_BASE_URL}/audio/transcriptions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.client.apiKey}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`ASR error ${response.status}: ${text}`);
    }

    return response.json() as Promise<TranscribeResult>;
  }

  async transcribeMultilingual(
    audioData: Buffer | Blob,
    options: TranscribeOptions = {}
  ): Promise<TranscribeResult> {
    return this.transcribe(audioData, {
      model: Models.Speech.CANARY_1B,
      ...options,
    });
  }

  async synthesize(
    text: string,
    options: TTSOptions = {}
  ): Promise<Buffer> {
    const response = await fetch(`${AUDIO_BASE_URL}/audio/speech`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.client.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: options.model ?? Models.Speech.MAGPIE_TTS,
        input: text,
        voice: options.voice ?? "default",
        response_format: "wav",
        sample_rate: options.sample_rate ?? 22050,
      }),
    });

    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(`TTS error ${response.status}: ${text}`);
    }

    const arrayBuffer = await response.arrayBuffer();
    return Buffer.from(arrayBuffer);
  }

  async zeroShotClone(
    text: string,
    referenceAudioUrl: string,
    options: TTSOptions = {}
  ): Promise<Buffer> {
    return this.synthesize(text, {
      model: Models.Speech.MAGPIE_TTS,
      voice: referenceAudioUrl,
      ...options,
    });
  }
}
