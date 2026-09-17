import { NimClient } from "../client.js";
import { Models } from "../models.js";

export interface TranslateOptions {
  model?: string;
  source_language?: string;
}

export interface TranslateResult {
  translated_text: string;
  source_language?: string;
  target_language: string;
  model: string;
}

export const SUPPORTED_LANGUAGES = {
  ENGLISH: "en",
  SPANISH: "es",
  FRENCH: "fr",
  GERMAN: "de",
  ITALIAN: "it",
  PORTUGUESE: "pt",
  RUSSIAN: "ru",
  CHINESE: "zh",
  JAPANESE: "ja",
  KOREAN: "ko",
  ARABIC: "ar",
  HINDI: "hi",
  DUTCH: "nl",
  POLISH: "pl",
  TURKISH: "tr",
  VIETNAMESE: "vi",
  INDONESIAN: "id",
  THAI: "th",
  SWEDISH: "sv",
  NORWEGIAN: "no",
} as const;

export class TranslationEndpoint {
  constructor(private client: NimClient) {}

  async translate(
    text: string,
    targetLanguage: string,
    options: TranslateOptions = {}
  ): Promise<TranslateResult> {
    const sourceHint = options.source_language
      ? ` from ${options.source_language}`
      : "";
    const prompt = `Translate the following text${sourceHint} to ${targetLanguage}. Return only the translated text with no explanation:\n\n${text}`;

    const response = await this.client.chat({
      model: options.model ?? Models.Translation.RIVA_TRANSLATE,
      messages: [{ role: "user", content: prompt }],
      temperature: 0.1,
      max_tokens: text.length * 3,
    });

    return {
      translated_text: response.choices[0]?.message.content ?? "",
      source_language: options.source_language,
      target_language: targetLanguage,
      model: options.model ?? Models.Translation.RIVA_TRANSLATE,
    };
  }

  async translateBatch(
    texts: string[],
    targetLanguage: string,
    options: TranslateOptions = {}
  ): Promise<TranslateResult[]> {
    return Promise.all(texts.map((t) => this.translate(t, targetLanguage, options)));
  }

  async detectLanguage(text: string): Promise<string> {
    const response = await this.client.chat({
      model: Models.Chat.LLAMA_3_1_8B,
      messages: [
        {
          role: "user",
          content: `Detect the language of this text. Return only the ISO 639-1 language code (e.g., "en", "es", "fr") with no other output:\n\n${text}`,
        },
      ],
      temperature: 0.0,
      max_tokens: 10,
    });
    return response.choices[0]?.message.content?.trim() ?? "unknown";
  }

  async translateToMany(
    text: string,
    targetLanguages: string[],
    options: TranslateOptions = {}
  ): Promise<Record<string, string>> {
    const results = await Promise.all(
      targetLanguages.map(async (lang) => {
        const result = await this.translate(text, lang, options);
        return [lang, result.translated_text] as const;
      })
    );
    return Object.fromEntries(results);
  }
}
