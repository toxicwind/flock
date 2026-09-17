import { Nim } from "../src/index.js";

const nim = new Nim(process.env.NVIDIA_API_KEY ?? "");

async function main() {
  console.log("=== Single Embedding ===");
  const vec = await nim.embeddings.embed("What is the speed of light?");
  console.log(`Embedding dimensions: ${vec.length}`);
  console.log(`First 5 values: ${vec.slice(0, 5).map((v) => v.toFixed(4)).join(", ")}`);

  console.log("\n=== Semantic Search ===");
  const query = "machine learning algorithms";
  const candidates = [
    "Deep learning is a subset of machine learning that uses neural networks.",
    "The recipe calls for two cups of flour and one egg.",
    "Gradient descent optimizes model parameters by minimizing loss.",
    "Paris is the capital of France.",
    "Support vector machines are supervised learning algorithms.",
  ];

  const results = await nim.embeddings.findMostSimilar(query, candidates);
  console.log(`Query: "${query}"`);
  console.log("Ranked results:");
  results.forEach((r, i) => {
    console.log(`  ${i + 1}. [${r.score.toFixed(4)}] ${r.text}`);
  });

  console.log("\n=== Reranking ===");
  const reranked = await nim.embeddings.rerank(
    "How do I reverse a string in Python?",
    [
      "Python strings can be reversed with slicing: s[::-1]",
      "JavaScript arrays have a built-in reverse() method.",
      "You can use reversed() and join() to reverse a string in Python.",
      "The weather today is sunny and warm.",
    ]
  );
  console.log("Reranked:");
  reranked.forEach((r, i) => {
    console.log(`  ${i + 1}. [${r.score.toFixed(4)}] ${r.text}`);
  });

  console.log("\n=== Cosine Similarity ===");
  const [vec1, vec2, vec3] = await Promise.all([
    nim.embeddings.embed("dog"),
    nim.embeddings.embed("puppy"),
    nim.embeddings.embed("automobile"),
  ]);
  console.log(
    `dog ↔ puppy:      ${nim.embeddings.cosineSimilarity(vec1, vec2).toFixed(4)}`
  );
  console.log(
    `dog ↔ automobile: ${nim.embeddings.cosineSimilarity(vec1, vec3).toFixed(4)}`
  );

  console.log("\n=== Code Embeddings ===");
  const codeVec = await nim.embeddings.embedCode(`
    function binarySearch(arr, target) {
      let left = 0, right = arr.length - 1;
      while (left <= right) {
        const mid = Math.floor((left + right) / 2);
        if (arr[mid] === target) return mid;
        if (arr[mid] < target) left = mid + 1;
        else right = mid - 1;
      }
      return -1;
    }
  `);
  console.log(`Code embedding dimensions: ${codeVec.length}`);
}

main().catch(console.error);
