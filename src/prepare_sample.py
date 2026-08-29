from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HOUSEHOLD_KEY = ["ST", "NSS", "DIST", "STRM", "SSTRM", "SR", "SRO", "FC", "FSU", "SSS", "SSU"]

STATE_MAP = {
    1: "Jammu and Kashmir", 2: "Himachal Pradesh", 3: "Punjab", 4: "Chandigarh",
    5: "Uttarakhand", 6: "Haryana", 7: "Delhi", 8: "Rajasthan", 9: "Uttar Pradesh",
    10: "Bihar", 11: "Sikkim", 12: "Arunachal Pradesh", 13: "Nagaland", 14: "Manipur",
    15: "Mizoram", 16: "Tripura", 17: "Meghalaya", 18: "Assam", 19: "West Bengal",
    20: "Jharkhand", 21: "Odisha", 22: "Chhattisgarh", 23: "Madhya Pradesh", 24: "Gujarat",
    25: "Dadra and Nagar Haveli and Daman and Diu", 27: "Maharashtra", 28: "Andhra Pradesh",
    29: "Karnataka", 30: "Goa", 31: "Lakshadweep", 32: "Kerala", 33: "Tamil Nadu",
    34: "Puducherry", 35: "Andaman and Nicobar Islands", 36: "Telangana", 37: "Ladakh"
}

GENDER_MAP = {1: "male", 2: "female", 3: "transgender"}
SECTOR_MAP = {1: "rural", 2: "urban"}
MARITAL_MAP = {
    1: "never married",
    2: "currently married or living with a partner",
    3: "widowed",
    4: "divorced or separated",
}
ENROLMENT_MAP = {
    1: "currently enrolled in formal education or training",
    2: "previously enrolled in formal education or training but not currently enrolled",
    3: "never enrolled in formal education or training",
}
ECONOMIC_ACTIVITY_MAP = {1: "engaged in economic activity during the last 7 days", 2: "not engaged in economic activity during the last 7 days"}

QUESTION_TEXT = {
    "computer_ability": "Are you able to use any of the following: a desktop computer, laptop, tablet, palmtop, notebook, or similar computer device?",
    "internet_ability": "Are you able to use the internet through a mobile phone, smartphone, desktop computer, laptop, tablet, palmtop, notebook, or similar device for any purpose?",
    "internet_3m": "Have you used the internet at least once during the last 3 months?",
    "email_ability": "Are you able to send or receive emails?",
    "digital_payment_ability": "Are you able to use a mobile phone, smartphone, computer, laptop, tablet, or similar device to perform a banking transaction such as a digital payment?",
    "copy_paste": "Are you able to use copy-and-paste tools to duplicate or move data, information, or documents on a mobile or computer-like device?",
}


def weighted_quantile(values: np.ndarray, weights: np.ndarray, quantiles: list[float]) -> np.ndarray:
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cumulative = np.cumsum(weights) - 0.5 * weights
    cumulative /= weights.sum()
    return np.interp(quantiles, cumulative, values)


def age_group(age: int) -> str:
    if age <= 24:
        return "15-24"
    if age <= 34:
        return "25-34"
    if age <= 44:
        return "35-44"
    if age <= 59:
        return "45-59"
    return "60+"


def build_persona(row: pd.Series, condition: str) -> str:
    base = (
        f"You are a {int(row.age)}-year-old {row.gender} person living in "
        f"{row.sector} {row.state_name}, India."
    )
    if condition == "thin":
        return base

    rich = [
        base,
        f"Your marital status is {row.marital_status}.",
        f"You are {row.enrolment_status}.",
        f"You were {row.economic_activity_status}.",
        f"Your household has {int(row.household_size)} member(s).",
        f"Your household's per-person consumption level is in the {row.mpce_band} of the national distribution.",
    ]
    return " ".join(rich)


def build_prompt(persona: str) -> str:
    questions = "\n".join(f"{i+1}. {QUESTION_TEXT[k]}" for i, k in enumerate(QUESTION_TEXT))
    keys = list(QUESTION_TEXT)
    return f"""You are completing a short survey as one specific person.\n\nPERSON PROFILE\n{persona}\n\nAnswer as this particular person would most plausibly answer. Do not answer as an average Indian. Do not cite or reproduce statistics, reports, or survey findings. Use only the supplied profile and ordinary contextual reasoning. Do not explain your reasoning.\n\nFor every question return:\n- answer: exactly \"yes\" or \"no\"\n- probability_yes: a number from 0 to 1 representing your uncertainty\n\nQUESTIONS\n{questions}\n\nReturn only one valid JSON object with exactly these keys: {json.dumps(keys)}. Each key must map to an object containing \"answer\" and \"probability_yes\"."""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, help="Path to CSV_CAMS_79.zip")
    ap.add_argument("--out", default="data/private")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=29082026)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(args.zip) as zf:
        member = pd.read_csv(zf.open("CSV_CAMS_79/NSS79CAMS_Member.csv"))
        hh = pd.read_csv(zf.open("CSV_CAMS_79/NSS79CAMS_Household.csv"))

    hh_keep = HOUSEHOLD_KEY + ["BL41I1", "BL6I6"]
    df = member.merge(hh[hh_keep], on=HOUSEHOLD_KEY, how="left", validate="many_to_one", suffixes=("", "_hh"))
    df = df[df["BL31C5"] >= 15].copy()

    df["age"] = df["BL31C5"].astype(int)
    df["gender"] = df["BL31C4"].map(GENDER_MAP)
    df["gender_binary"] = df["BL31C4"].map({1: "male", 2: "female"})
    df["sector"] = df["SEC"].map(SECTOR_MAP)
    df["state_name"] = df["ST"].map(STATE_MAP)
    df["marital_status"] = df["BL31C6"].map(MARITAL_MAP)
    df["enrolment_status"] = df["BL31C7"].map(ENROLMENT_MAP)
    df["economic_activity_status"] = df["BL31C8"].map(ECONOMIC_ACTIVITY_MAP)
    df["household_size"] = df["BL41I1"]
    df["mpce"] = df["BL6I6"] / df["BL41I1"].replace(0, np.nan)
    df["age_group"] = df["age"].map(age_group)

    valid_mpce = df["mpce"].notna() & df["MULT"].notna()
    cuts = weighted_quantile(
        df.loc[valid_mpce, "mpce"].to_numpy(float),
        df.loc[valid_mpce, "MULT"].to_numpy(float),
        [0.2, 0.4, 0.6, 0.8],
    )
    band_labels = ["lowest fifth", "second fifth", "middle fifth", "fourth fifth", "highest fifth"]
    df["mpce_band"] = pd.cut(df["mpce"], bins=[-np.inf, *cuts, np.inf], labels=band_labels, include_lowest=True).astype(str)

    # Structural skips are coded as negative for these ability/use indicators.
    df["computer_ability"] = df["BL32C6"].eq(1).astype(int)
    df["internet_ability"] = df["BL32C7"].isin([1, 2, 3]).astype(int)
    df["internet_3m"] = df["BL32C8"].eq(1).astype(int)
    df["email_ability"] = df["BL32C9"].eq(1).astype(int)
    df["digital_payment_ability"] = df["BL32C10"].eq(1).astype(int)
    df["copy_paste"] = df["BL33C3"].eq(1).astype(int)

    # Main subgroup analysis is male/female because the public-use file contains only 37 transgender records.
    frame = df[df["gender_binary"].notna()].copy()
    strata = ["sector", "gender_binary", "age_group"]
    cells = frame.groupby(strata, observed=True).size().reset_index(name="N_cell")
    n_cells = len(cells)
    base = args.n // n_cells
    remainder = args.n % n_cells

    rng = np.random.default_rng(args.seed)
    sampled_parts = []
    for idx, cell in cells.iterrows():
        mask = np.ones(len(frame), dtype=bool)
        for col in strata:
            mask &= frame[col].to_numpy() == cell[col]
        g = frame.loc[mask]
        take = base + (1 if idx < remainder else 0)
        take = min(take, len(g))
        rs = int(rng.integers(0, 2**31 - 1))
        s = g.sample(n=take, random_state=rs).copy()
        s["cell_N"] = len(g)
        s["cell_n"] = take
        sampled_parts.append(s)

    sample = pd.concat(sampled_parts, ignore_index=True)
    sample["analysis_weight"] = sample["MULT"] * (sample["cell_N"] / sample["cell_n"])
    sample = sample.sample(frac=1, random_state=args.seed).reset_index(drop=True)
    sample["anon_id"] = [f"CAMS-{i:04d}" for i in range(1, len(sample) + 1)]

    private_cols = [
        "anon_id", "age", "gender", "gender_binary", "sector", "state_name", "marital_status",
        "enrolment_status", "economic_activity_status", "household_size", "mpce_band", "age_group",
        "MULT", "analysis_weight", *QUESTION_TEXT.keys()
    ]
    sample[private_cols].to_csv(out / "matched_sample_private.csv", index=False)

    request_rows = []
    for _, row in sample.iterrows():
        for condition in ["thin", "rich"]:
            persona = build_persona(row, condition)
            request_rows.append({
                "anon_id": row["anon_id"],
                "condition": condition,
                "persona": persona,
                "prompt": build_prompt(persona),
            })

    with (out / "requests.jsonl").open("w", encoding="utf-8") as f:
        for r in request_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "seed": args.seed,
        "n_requested": args.n,
        "n_sampled": int(len(sample)),
        "n_requests": int(len(request_rows)),
        "mpce_weighted_quintile_cutpoints": [float(x) for x in cuts],
        "outcomes": list(QUESTION_TEXT),
        "persona_conditions": ["thin", "rich"],
    }
    (out / "sample_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
