# Statistical Significance Tests

All tests use the Wilcoxon signed-rank test (non-parametric, paired on patient ID).
Effect size: r = Z / sqrt(N), where N = number of pairs.
p-values for strategy comparisons are Bonferroni-corrected (4 tests per model).

## 1. Strategy A vs Strategy C (within model, paired on patient)

| Model | W | p (uncorrected) | p (Bonferroni, k=4) | r | Interpretation |
|---|---|---|---|---|---|
| Phi-3.5-mini (3.8B) | 3143 | 2.6604e-02 | 1.0642e-01 ns | 0.197 | C > A |
| Mistral-7B | 948 | 4.3124e-11 | 1.7250e-10 *** | 0.617 | C > A |
| Llama-3.1-8B | 859 | 2.7806e-03 | 1.1123e-02 * | 0.345 | C > A |
| Llama-3.3-70B | 10 | 4.9587e-01 | 1.0000e+00 ns | 0.257 | A > C |

## 2. Cross-Model Comparisons on Strategy C (paired on patient)

| Comparison | W | p | r | Interpretation |
|---|---|---|---|---|
| Mistral-7B vs Llama-3.1-8B | 414 | 1.9461e-02 * | 0.327 | llama-3.1-8b > mistral-7b |
| Llama-3.1-8B vs Llama-3.3-70B | 22 | 1.5325e-04 *** | 0.757 | llama-3.3-70b > llama-3.1-8b |
| Mistral-7B vs BioMistral-7B (one-sided: Mistral > BioMistral) | 0 | 7.0665e-38 *** | 0.576 | mistral-7b > biomistral |

Significance codes: *** p<0.001, ** p<0.01, * p<0.05, ns not significant