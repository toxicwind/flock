import { Flock } from "../src/index.js";

const nim = new Flock(process.env.NVIDIA_API_KEY ?? "");

async function main() {
  console.log("=== Content Safety Check ===");
  const safe = await nim.safety.isSafe("What is the capital of France?");
  console.log(`"What is the capital of France?" → safe: ${safe}`);

  console.log("\n=== PII Detection ===");
  const piiResult = await nim.safety.detectPII(
    "Please contact John Smith at john.smith@email.com or call 555-123-4567. His SSN is 123-45-6789."
  );
  console.log("PII Entities found:", piiResult.entities.length);
  piiResult.entities.forEach((e) => {
    console.log(`  [${e.label}] "${e.text}" (score: ${e.score.toFixed(2)})`);
  });
  console.log("Anonymized:", piiResult.anonymized);

  console.log("\n=== Topic Policy Enforcement ===");
  const customerSupport = await nim.safety.enforceTopicPolicy(
    "What are your shipping rates?",
    ["shipping", "returns", "orders", "products", "billing"]
  );
  console.log("Customer support query:", customerSupport);

  const offTopic = await nim.safety.enforceTopicPolicy(
    "What do you think about the upcoming election?",
    ["shipping", "returns", "orders", "products", "billing"]
  );
  console.log("Off-topic query:", offTopic);

  console.log("\n=== Full Safety Pipeline ===");
  const messages = [
    "Please help me with my order #12345",
    "My credit card number is 4111-1111-1111-1111",
    "I hate everyone",
  ];

  for (const msg of messages) {
    const [safety, pii, jailbreak] = await Promise.all([
      nim.safety.checkContent(msg),
      nim.safety.detectPII(msg),
      nim.safety.detectJailbreak(msg),
    ]);
    console.log(`\nMessage: "${msg}"`);
    console.log(`  Safe: ${safety.safe}`);
    console.log(`  Has PII: ${pii.hasPII}`);
    console.log(`  Jailbreak: ${jailbreak.isJailbreak}`);
    if (pii.hasPII) console.log(`  Anonymized: "${pii.anonymized}"`);
  }
}

main().catch(console.error);
