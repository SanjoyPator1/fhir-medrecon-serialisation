export const MODEL_LABELS: Record<string, string> = {
  "phi-3.5-mini": "Phi-3.5-mini (3.8B)",
  "mistral-7b": "Mistral 7B v0.3",
  biomistral: "BioMistral 7B",
  "llama-3.1-8b": "Llama 3.1 8B",
  "llama-3.3-70b": "Llama 3.3 70B",
}

/** Canonical model order: smallest → largest by parameter count */
export const MODEL_SIZE_ORDER: string[] = [
  "phi-3.5-mini",  // 3.8B
  "mistral-7b",    // 7B
  "biomistral",    // 7B (domain-specific)
  "llama-3.1-8b",  // 8B
  "llama-3.3-70b", // 70B
]

export function sortModelsBySize(models: string[]): string[] {
  return [...models].sort((a, b) => {
    const ai = MODEL_SIZE_ORDER.indexOf(a)
    const bi = MODEL_SIZE_ORDER.indexOf(b)
    // unknown models go to the end, preserving their relative order
    if (ai === -1 && bi === -1) return 0
    if (ai === -1) return 1
    if (bi === -1) return -1
    return ai - bi
  })
}

export const STRATEGY_LABELS: Record<string, string> = {
  strategy_a: "Strategy A — Raw FHIR JSON",
  strategy_b: "Strategy B — Markdown Table",
  strategy_c: "Strategy C — Clinical Narrative",
  strategy_d: "Strategy D — Timeline",
}

export const STRATEGY_SHORT: Record<string, string> = {
  strategy_a: "Raw JSON",
  strategy_b: "Table",
  strategy_c: "Narrative",
  strategy_d: "Timeline",
}

export const MODEL_SHORT: Record<string, string> = {
  "phi-3.5-mini": "Phi-3.5",
  "mistral-7b": "Mistral",
  biomistral: "BioMistral",
  "llama-3.1-8b": "Llama 8B",
  "llama-3.3-70b": "Llama 70B",
}
