import { Flock, Models } from "../src/index.js";

const nim = new Flock(process.env.NVIDIA_API_KEY ?? "");

async function main() {
  console.log("=== Basic Chat ===");
  const answer = await nim.chat.ask("What is quantum entanglement in one sentence?");
  console.log("Answer:", answer);

  console.log("\n=== Streaming Chat ===");
  process.stdout.write("Streaming: ");
  for await (const token of nim.chat.streamText(
    "Tell me 3 fun facts about the ocean.",
    { max_tokens: 300 }
  )) {
    process.stdout.write(token);
  }
  console.log("\n");

  console.log("=== Deep Reasoning with Nemotron-Ultra ===");
  const reasoning = await nim.chat.reason(
    "A farmer has 17 sheep. All but 9 run away. How many sheep does the farmer have?",
  );
  console.log("Reasoning:", reasoning);

  console.log("\n=== Summarization ===");
  const summary = await nim.chat.summarize(
    `The James Webb Space Telescope (JWST) is a space telescope designed to conduct 
     infrared astronomy. Its high-resolution and high-sensitivity instruments allow it 
     to view objects too old, distant, or faint for the Hubble Space Telescope. It 
     enables investigations across many fields of astronomy and cosmology, such as 
     observation of the first stars and the formation of the first galaxies, and 
     detailed atmospheric characterization of potentially habitable exoplanets.`
  );
  console.log("Summary:", summary);

  console.log("\n=== JSON Extraction ===");
  const extracted = await nim.chat.extract(
    "John Smith, age 34, works at Acme Corp as a software engineer since 2019.",
    '{"name": "string", "age": "number", "company": "string", "role": "string", "start_year": "number"}'
  );
  console.log("Extracted:", extracted);

  console.log("\n=== Classification ===");
  const category = await nim.chat.classify(
    "My order never arrived and I want a refund immediately!",
    ["complaint", "question", "compliment", "feedback"]
  );
  console.log("Category:", category);

  console.log("\n=== Medical LLM (Palmyra-Med) ===");
  const medAnswer = await nim.chat.ask(
    "What are the first-line treatments for type 2 diabetes?",
    { model: Models.Chat.PALMYRA_MED, max_tokens: 300 }
  );
  console.log("Medical answer:", medAnswer);

  console.log("\n=== Financial LLM (Palmyra-Fin) ===");
  const finAnswer = await nim.chat.ask(
    "Explain the difference between a forward contract and a futures contract.",
    { model: Models.Chat.PALMYRA_FIN, max_tokens: 300 }
  );
  console.log("Financial answer:", finAnswer);

  console.log("\n=== Code Generation ===");
  const code = await nim.chat.ask(
    "Write a TypeScript function that debounces another function.",
    { model: Models.Chat.QWEN3_CODER, max_tokens: 400 }
  );
  console.log("Generated code:", code);
}

main().catch(console.error);
