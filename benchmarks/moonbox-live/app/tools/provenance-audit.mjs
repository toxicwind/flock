import fs from "fs";
import path from "path";

const base = "src/content/archives/collectables/designer-toys/pop-mart/the-monsters";
const productsDir = path.join(base, "products");
const provDir = path.join(base, "provenance");

for (const file of fs
  .readdirSync(productsDir)
  .filter((f) => f.endsWith(".json"))) {
  const data = JSON.parse(
    fs.readFileSync(path.join(productsDir, file), "utf8"),
  );
  const provPath = path.join(provDir, `${data.product_id}.jsonl`);
  if (!fs.existsSync(provPath)) {
    console.error(`Missing provenance for ${data.product_id}`);
    process.exitCode = 1;
    continue;
  }
  const lines = fs
    .readFileSync(provPath, "utf8")
    .trim()
    .split("\n")
    .filter(Boolean);
  if (lines.length === 0) {
    console.error(`Empty provenance for ${data.product_id}`);
    process.exitCode = 1;
  }
}
