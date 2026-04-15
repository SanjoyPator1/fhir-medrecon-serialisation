# Hard Patient Analysis

Patients with mean F1 < 0.5 averaged across all 4 main models and all 4 strategies.

Found 4 universally hard patient(s).

| Patient ID (prefix) | Mean F1 | GT Count | History Span (yrs) |
|---|---|---|---|
| 7323b20b | 0.3429 | 11 | 30 |
| e15ab14b | 0.3958 | 4 | 29 |
| 6c6acf0d | 0.4215 | 12 | 25 |
| bb88b4a2 | 0.4625 | 2 | 26 |

## Per-Model Per-Strategy F1 for Hard Patients

### Patient `7323b20b` (full: `7323b20b-743d-7c48-cd98-975a97865957`)

| Model | Strat A | Strat B | Strat C | Strat D |
|---|---|---|---|---|
| Phi-3.5-mini (3.8B) | 0.0000 | 0.0000 | 0.6250 | 0.3750 |
| Mistral-7B | 0.9524 | 0.0000 | 0.0000 | 0.0000 |
| Llama-3.1-8B | 1.0000 | 0.6250 | 0.0000 | 0.9091 |
| Llama-3.3-70B | 1.0000 | 0.0000 | 0.0000 | 0.0000 |

### Patient `e15ab14b` (full: `e15ab14b-22c7-3c59-1d8e-fba4bed48af1`)

| Model | Strat A | Strat B | Strat C | Strat D |
|---|---|---|---|---|
| Phi-3.5-mini (3.8B) | 0.0000 | 0.6667 | 0.0000 | 1.0000 |
| Mistral-7B | 1.0000 | 0.0000 | 0.0000 | 0.0000 |
| Llama-3.1-8B | 1.0000 | 0.6667 | 0.0000 | 1.0000 |
| Llama-3.3-70B | 1.0000 | 0.0000 | 0.0000 | 0.0000 |

### Patient `6c6acf0d` (full: `6c6acf0d-3295-986e-fbc9-57e7189fbc2e`)

| Model | Strat A | Strat B | Strat C | Strat D |
|---|---|---|---|---|
| Phi-3.5-mini (3.8B) | 0.0000 | 0.5556 | 0.8333 | 0.5556 |
| Mistral-7B | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Llama-3.1-8B | 1.0000 | 0.5000 | 0.8000 | 0.5000 |
| Llama-3.3-70B | 1.0000 | 1.0000 | 0.0000 | 0.0000 |

### Patient `bb88b4a2` (full: `bb88b4a2-77be-6165-d15b-e788caf14a25`)

| Model | Strat A | Strat B | Strat C | Strat D |
|---|---|---|---|---|
| Phi-3.5-mini (3.8B) | 0.4000 | 0.5000 | 0.5000 | 0.0000 |
| Mistral-7B | 0.0000 | 0.0000 | 0.5000 | 0.0000 |
| Llama-3.1-8B | 0.5000 | 0.5000 | 0.5000 | 1.0000 |
| Llama-3.3-70B | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
