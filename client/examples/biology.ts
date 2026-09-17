import { Flock } from "../src/index.js";

const nim = new Flock(process.env.NVIDIA_API_KEY ?? "");

async function main() {
  console.log("=== Protein Structure Prediction (ESMFold) ===");
  const sequence = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGDEDRLELEWHQALLRGEMPQTIGGGIGQSRLTMLLLQLPHIGQVQAGVWPAAVRESVPSLL";

  const result = await nim.biology.foldProtein(sequence.slice(0, 100));
  console.log(`PDB output length: ${result.pdb.length} chars`);
  if (result.mean_plddt) {
    console.log(`Mean pLDDT score: ${result.mean_plddt.toFixed(2)}`);
  }
  console.log("PDB preview:", result.pdb.slice(0, 200) + "...");

  console.log("\n=== Protein Embedding (ESM2) ===");
  const embedding = await nim.biology.getProteinEmbedding(sequence.slice(0, 50));
  console.log(`Protein embedding dimensions: ${embedding.length}`);

  console.log("\n=== Molecule Generation (GenMol) ===");
  const aspirin = "CC(=O)Oc1ccccc1C(=O)O";
  const newMolecules = await nim.biology.generateMolecules(aspirin, {
    numMolecules: 5,
    temperature: 1.0,
  });
  console.log(`Generated ${newMolecules.length} molecules from aspirin scaffold:`);
  newMolecules.forEach((mol, i) => {
    console.log(`  ${i + 1}. ${mol.smiles}${mol.score ? ` (score: ${mol.score.toFixed(3)})` : ""}`);
  });

  console.log("\n=== Molecule Optimization (MolMIM) ===");
  const caffeine = "Cn1cnc2c1c(=O)n(c(=O)n2C)C";
  const optimized = await nim.biology.optimizeMolecule(caffeine, "qed", {
    numMolecules: 5,
    iterations: 50,
  });
  console.log("QED-optimized variants of caffeine:");
  optimized.forEach((mol, i) => {
    console.log(`  ${i + 1}. ${mol.smiles}`);
    if (mol.properties?.qed) {
      console.log(`     QED: ${mol.properties.qed.toFixed(3)}`);
    }
  });
}

main().catch(console.error);
