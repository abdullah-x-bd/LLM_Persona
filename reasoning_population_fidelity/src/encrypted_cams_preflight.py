from __future__ import annotations
import csv, io, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / "src"))
from production_runtime import decrypt_bundle, CODES_AAD, TRUTH_AAD

CODES = HERE / "data/encrypted/cams_codes_v2.x25519.aesgcm.gz.b64"
TRUTH = HERE / "data/encrypted/cams_truth_v2.x25519.aesgcm.gz.b64"

REQUIRED_PERSONA_RAW = {
    "anon_id", "ST", "SEC", "BL31C3", "BL31C4", "BL31C5", "BL31C6",
    "BL31C7", "BL31C8", "BL41I1", "BL41I2", "BL41I3", "BL41I4", "mpce_band"
}
CURRENT_TARGET_RAW = {"BL32C3", "BL32C4", "BL32C6", "BL32C7", "BL32C8", "BL33C3"}
CURRENT_TARGET_NAMES = {
    "mobile_ability", "mobile_3m", "computer_ability", "internet_ability",
    "internet_3m", "copy_paste"
}

def columns_and_rows(blob: bytes):
    text = blob.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    return set(reader.fieldnames or []), rows

def main():
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SystemExit("FAIL: OPENROUTER_API_KEY is required only as the existing decryption secret")
    code_cols, code_rows = columns_and_rows(decrypt_bundle(CODES, CODES_AAD))
    truth_cols, truth_rows = columns_and_rows(decrypt_bundle(TRUTH, TRUTH_AAD))
    if len(code_rows) != 1000 or len(truth_rows) != 1000:
        raise AssertionError((len(code_rows), len(truth_rows)))
    code_ids = {r["anon_id"] for r in code_rows}
    truth_ids = {r["anon_id"] for r in truth_rows}
    report = {
        "code_rows": len(code_rows),
        "truth_rows": len(truth_rows),
        "code_columns": sorted(code_cols),
        "truth_columns": sorted(truth_cols),
        "ids_unique_codes": len(code_ids) == len(code_rows),
        "ids_unique_truth": len(truth_ids) == len(truth_rows),
        "id_sets_match": code_ids == truth_ids,
        "persona_fields_complete": REQUIRED_PERSONA_RAW <= code_cols,
        "current_targets_available_as_raw_codes": CURRENT_TARGET_RAW <= truth_cols,
        "current_targets_available_as_names": CURRENT_TARGET_NAMES <= truth_cols,
        "missing_persona_fields": sorted(REQUIRED_PERSONA_RAW - code_cols),
        "missing_current_raw_targets": sorted(CURRENT_TARGET_RAW - truth_cols),
        "missing_current_named_targets": sorted(CURRENT_TARGET_NAMES - truth_cols),
        "plaintext_printed": False,
        "inference_endpoint_called": False,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    assert report["ids_unique_codes"] and report["ids_unique_truth"] and report["id_sets_match"]
    assert report["persona_fields_complete"], report

if __name__ == "__main__":
    main()
