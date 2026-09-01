# S01 Second-model reasoning replication

**Status: COMPLETE AND ANALYZED.**

Population: 1,000 frozen CAMS respondents. Model: `deepseek/deepseek-v4-flash-0731`. Final production provider: **OpenInference FP8**. Fallbacks were disabled, provider data collection was set to `deny`, and human truth was not loaded during generation.

Paired arms were `rich_off` and `rich_high`. The final production artifact contains 1,000 valid responses in each arm and is reused exactly by S03.

Primary rich high-minus-off results from the 10,000 paired bootstrap:

- individual Brier: **-0.01796**, 95% CI [-0.03101, -0.00490];
- probability-prevalence MAE: **-5.76 pp**, 95% CI [-8.31, -3.19];
- hard prevalence MAE: **-16.67 pp**, 95% CI [-18.17, -13.92];
- hard accuracy: **+4.37 pp**, 95% CI [+2.64, +6.13];
- log loss worsened because high reasoning created a larger tail of extreme wrong probabilities.

Production run: `33406819430`. Final S01 artifact: `9763493454`.

The AkashML endpoint used during engineering was abandoned before final production because it rate-limited concurrent DeepSeek requests. Provider selection was an operational pre-outcome change; the scientific arms and response schema were unchanged.
