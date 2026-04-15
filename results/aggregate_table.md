# Aggregate Results Table

| Model | Strategy | n | Mean F1 | Mean Prec | Mean Recall | Median F1 | Perfect | Zero F1 | Parse Failed |
|---|---|---|---|---|---|---|---|---|---|
| Phi-3.5-mini (3.8B) | A — Raw JSON | 200 | 0.6356 | 0.7296 | 0.5932 | 0.7596 | 75 | 45 | 33 |
| Phi-3.5-mini (3.8B) | B — Markdown Table | 200 | 0.6833 | 0.8111 | 0.6264 | 0.7500 | 64 | 25 | 16 |
| Phi-3.5-mini (3.8B) | C — Clinical Narrative | 200 | 0.7008 | 0.7616 | 0.6670 | 0.8000 | 66 | 28 | 7 |
| Phi-3.5-mini (3.8B) | D — Chrono. Timeline | 200 | 0.6443 | 0.7703 | 0.5902 | 0.6905 | 61 | 30 | 11 |
| Mistral-7B | A — Raw JSON | 200 | 0.7247 | 0.8886 | 0.6684 | 0.8889 | 87 | 20 | 11 |
| Mistral-7B | B — Markdown Table | 200 | 0.8753 | 0.9646 | 0.8344 | 1.0000 | 122 | 6 | 3 |
| Mistral-7B | C — Clinical Narrative | 200 | 0.9149 | 0.9319 | 0.9026 | 1.0000 | 153 | 10 | 5 |
| Mistral-7B | D — Chrono. Timeline | 200 | 0.8588 | 0.9611 | 0.8100 | 1.0000 | 112 | 6 | 3 |
| BioMistral-7B | A — Raw JSON | 200 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 200 | 198 |
| BioMistral-7B | B — Markdown Table | 200 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 200 | 197 |
| BioMistral-7B | C — Clinical Narrative | 200 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 200 | 198 |
| BioMistral-7B | D — Chrono. Timeline | 200 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 | 200 | 198 |
| Llama-3.1-8B | A — Raw JSON | 200 | 0.9180 | 0.9629 | 0.9052 | 1.0000 | 138 | 2 | 0 |
| Llama-3.1-8B | B — Markdown Table | 200 | 0.9250 | 0.9562 | 0.9182 | 1.0000 | 147 | 1 | 0 |
| Llama-3.1-8B | C — Clinical Narrative | 200 | 0.9471 | 0.9513 | 0.9448 | 1.0000 | 173 | 5 | 2 |
| Llama-3.1-8B | D — Chrono. Timeline | 200 | 0.9228 | 0.9724 | 0.8995 | 1.0000 | 144 | 2 | 1 |
| Llama-3.3-70B | A — Raw JSON | 200 | 0.9956 | 1.0000 | 0.9929 | 1.0000 | 196 | 0 | 0 |
| Llama-3.3-70B | B — Markdown Table | 200 | 0.9867 | 0.9900 | 0.9845 | 1.0000 | 194 | 2 | 2 |
| Llama-3.3-70B | C — Clinical Narrative | 200 | 0.9850 | 0.9850 | 0.9850 | 1.0000 | 197 | 3 | 3 |
| Llama-3.3-70B | D — Chrono. Timeline | 200 | 0.8742 | 0.8750 | 0.8736 | 1.0000 | 174 | 25 | 2 |