import { Nim } from "../src/index.js";

const nim = new Nim(process.env.NVIDIA_API_KEY ?? "");

const SAMPLE_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png";
const CHART_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/Percent-of-Americans-who-can-name-these-five-rights_2015_survey.svg/1200px-Percent-of-Americans-who-can-name-these-five-rights_2015_survey.svg.png";

async function main() {
  console.log("=== Image Caption ===");
  const caption = await nim.vision.caption(SAMPLE_IMAGE);
  console.log("Caption:", caption);

  console.log("\n=== Ask a Question About an Image ===");
  const answer = await nim.vision.answer(
    SAMPLE_IMAGE,
    "What colors are prominently featured in this image?"
  );
  console.log("Answer:", answer);

  console.log("\n=== Object Detection ===");
  const objects = await nim.vision.detectObjects(SAMPLE_IMAGE);
  console.log("Objects:", objects);

  console.log("\n=== Chart to Data (DePlot) ===");
  const chartData = await nim.vision.readChart(CHART_IMAGE);
  console.log("Chart data:", chartData);

  console.log("\n=== Analyze with Custom Prompt ===");
  const analysis = await nim.vision.analyze(
    SAMPLE_IMAGE,
    "Describe the artistic style and technique used in this image."
  );
  console.log("Analysis:", analysis);
}

main().catch(console.error);
