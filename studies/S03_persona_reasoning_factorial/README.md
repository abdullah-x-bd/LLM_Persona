# S03 Persona × reasoning factorial

**Status: COMPLETE AND ANALYZED.**

Population: the same 1,000 frozen CAMS respondents as S01. Model: `deepseek/deepseek-v4-flash-0731`. Final provider: **OpenInference FP8**, fallbacks disabled, provider data collection `deny`, no human truth during generation.

The complete 2 × 2 design is thin/off, thin/high, rich/off, and rich/high. S03 generated only the two thin cells; the rich cells are the exact S01 outputs.

All four cells contain 1,000 respondents. Key cell metrics:

| Cell | Brier | Hard accuracy | Probability MAE | Hard MAE |
|---|---:|---:|---:|---:|
| thin/off | 0.2239 | 71.28% | 14.07 pp | 21.37 pp |
| thin/high | 0.1885 | 76.42% | 6.22 pp | 9.34 pp |
| rich/off | 0.2049 | 73.32% | 12.75 pp | 20.27 pp |
| rich/high | 0.1869 | 77.69% | 6.99 pp | 3.60 pp |

The Brier persona × reasoning interaction is **+0.01743**, 95% CI [+0.00327, +0.03154]. The hard-prevalence interaction is approximately **-4.64 pp**, 95% CI [-6.32, -1.72]. Thus reasoning partly substitutes for persona information at the individual probabilistic level while complementing rich information for categorical population reconstruction.

Joint structure also changes strongly: rich/off has entropy 1.307 bits and TV distance 0.626 from the human distribution, while rich/high has entropy 2.298 bits and TV 0.190. Human entropy is 2.486 bits.

Production run: `33406819430`. Final S03 artifact: `9765135867`. Full results are documented in `docs/DEEPSEEK_S01_S03_FACTORIAL_RESULTS.md`.
