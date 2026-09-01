# Release checklist

Target tag: `v1.0.0`

Recommended release title: **v1.0.0 — Frozen synthetic-population fidelity research artifact**

## Before creating the tag

- Confirm `main` contains the final public-facing README and `CITATION.cff`.
- Confirm `LICENSE` contains the MIT License for software code.
- Confirm `LICENSE-CONTENT.md` applies CC BY 4.0 to original documentation, figures, and aggregate publication outputs while excluding third-party and restricted material.
- Confirm `analysis_final/results/MANIFEST.json` and `analysis_final/figures/MANIFEST.json` are present.
- Run or confirm the final repository QA workflow is green on the release commit.
- Confirm no respondent-level plaintext, raw result JSONL, API secret, or decrypted historical artifact has entered the durable publication directories.
- Confirm the frozen study registry still marks S01 and S03 complete, S02 and S05 archived unrun, and S04 scientifically blocked.

## Recommended GitHub “About” metadata

Repository description:

> Multi-model audit of LLM synthetic-population fidelity against Government of India CAMS survey respondents.

Recommended topics:

- `large-language-models`
- `synthetic-respondents`
- `synthetic-populations`
- `computational-social-science`
- `survey-methodology`
- `ai-evaluation`
- `reproducibility`

Leave the project website blank until there is a stable article, DOI, or project page worth linking.

## Create the GitHub release

1. Open **Releases → Draft a new release**.
2. Create tag `v1.0.0` from the final `main` commit.
3. Use release title: `v1.0.0 — Frozen synthetic-population fidelity research artifact`.
4. Paste the contents of `docs/RELEASE_NOTES_v1.0.0.md` into the release description.
5. Do not attach encrypted respondent-level artifacts or any transient analysis plaintext.
6. The automatically generated GitHub source archives are sufficient unless a separate publication-safe bundle is intentionally prepared.
7. Publish the release only after the final QA status on the tagged commit is green.

## After release

- Record the release tag and commit SHA in `docs/FINAL_PROVENANCE.md` in a later metadata-only update if desired.
- If the release is archived with Zenodo or another DOI provider, add the DOI to `CITATION.cff` and the README.
- When the companion article receives a final DOI, add it as the preferred citation without altering the frozen `v1.0.0` evidence package.
- Any later scientific extension should receive a new version and its own provenance record rather than silently changing the meaning of `v1.0.0`.

## Licensing

The licensing decision is complete:

- software code is licensed under the MIT License in `LICENSE`;
- original documentation, publication figures, aggregate publication result tables, and derived aggregate summaries are licensed under CC BY 4.0 in `LICENSE-CONTENT.md`;
- Government of India CAMS microdata, encrypted respondent-level artifacts, model-provider outputs, and third-party/restricted material are explicitly excluded from those grants.
