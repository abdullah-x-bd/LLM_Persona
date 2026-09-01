# Release checklist

Target tag: `v1.0.0`

Recommended release title: **v1.0.0 — Frozen synthetic-population fidelity research artifact**

## Before creating the tag

- Confirm `main` contains the final public-facing README and `CITATION.cff`.
- Confirm `analysis_final/results/MANIFEST.json` and `analysis_final/figures/MANIFEST.json` are present.
- Run or confirm the final repository QA workflow is green on the release commit.
- Confirm no respondent-level plaintext, raw result JSONL, API secret, or decrypted historical artifact has entered the durable publication directories.
- Confirm the frozen study registry still marks S01 and S03 complete, S02 and S05 archived unrun, and S04 scientifically blocked.
- Decide and add an explicit reuse license before publishing the release. Do not infer a license merely from public repository visibility.

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

## Licensing decision still required

No explicit repository license has been selected in the current tree. This is intentionally left for the repository owner because selecting a license changes legal reuse rights.

A common research-code arrangement is a permissive software license for code and a separate content license for original documentation/figures, but the exact choice should be made deliberately before release.
