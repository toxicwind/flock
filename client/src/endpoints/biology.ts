import { NimClient } from "../client.js";

const BIOLOGY_BASE_URL = "https://health.api.nvidia.com/v1";

export interface ProteinFoldResult {
  pdb: string;
  mean_plddt?: number;
  model: string;
}

export interface MoleculeGenerationOptions {
  numMolecules?: number;
  temperature?: number;
  iterations?: number;
  property?: "qed" | "sa" | "logp";
}

export interface MoleculeResult {
  smiles: string;
  score?: number;
  properties?: {
    qed?: number;
    sa?: number;
    logp?: number;
    mw?: number;
  };
}

export interface MSAResult {
  alignment: string;
  sequences: string[];
}

export class BiologyEndpoint {
  private bioUrl: string;

  constructor(private client: NimClient) {
    this.bioUrl = BIOLOGY_BASE_URL;
  }

  async foldProtein(sequence: string): Promise<ProteinFoldResult> {
    const response = await this.client.request<{
      pdbs: string[];
      mean_plddt?: number[];
    }>(`${this.bioUrl}/biology/deepmind/esmfold`, {
      method: "POST",
      body: JSON.stringify({ sequence }),
    });

    return {
      pdb: response.pdbs?.[0] ?? "",
      mean_plddt: response.mean_plddt?.[0],
      model: "esmfold",
    };
  }

  async getProteinEmbedding(sequence: string): Promise<number[]> {
    const response = await this.client.request<{
      mean_representations: Record<string, number[]>;
    }>(`${this.bioUrl}/biology/nvidia/esm2-650m`, {
      method: "POST",
      body: JSON.stringify({ sequence }),
    });

    const layers = Object.values(response.mean_representations ?? {});
    return layers[layers.length - 1] ?? [];
  }

  async generateMolecules(
    smiles: string,
    options: MoleculeGenerationOptions = {}
  ): Promise<MoleculeResult[]> {
    const response = await this.client.request<{
      molecules: Array<{ smiles: string; score?: number }>;
    }>(`${this.bioUrl}/biology/nvidia/genmol`, {
      method: "POST",
      body: JSON.stringify({
        smiles,
        num_molecules: options.numMolecules ?? 10,
        temperature: options.temperature ?? 1.0,
        iterations: options.iterations ?? 20,
      }),
    });

    return (response.molecules ?? []).map((m) => ({
      smiles: m.smiles,
      score: m.score,
    }));
  }

  async optimizeMolecule(
    smiles: string,
    targetProperty: "qed" | "sa" | "logp" = "qed",
    options: MoleculeGenerationOptions = {}
  ): Promise<MoleculeResult[]> {
    const response = await this.client.request<{
      optimized_molecules: Array<{ smiles: string; [key: string]: unknown }>;
    }>(`${this.bioUrl}/biology/nvidia/molmim`, {
      method: "POST",
      body: JSON.stringify({
        smiles,
        property: targetProperty,
        num_molecules: options.numMolecules ?? 10,
        iterations: options.iterations ?? 100,
        temperature: options.temperature ?? 0.5,
      }),
    });

    return (response.optimized_molecules ?? []).map((m) => ({
      smiles: m.smiles,
      properties: {
        qed: m.qed as number | undefined,
        sa: m.sa as number | undefined,
        logp: m.logp as number | undefined,
        mw: m.mw as number | undefined,
      },
    }));
  }

  async runMSA(sequence: string): Promise<MSAResult> {
    const response = await this.client.request<{
      alignment: string;
      sequences?: string[];
    }>(`${this.bioUrl}/biology/nvidia/msa-search`, {
      method: "POST",
      body: JSON.stringify({ sequence }),
    });

    return {
      alignment: response.alignment ?? "",
      sequences: response.sequences ?? [],
    };
  }
}
