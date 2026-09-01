from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

COMBINED_AAD = b"LLM_Persona_results_combined_v1"


def result_key(secret: str) -> bytes:
    return hashlib.sha256(("LLM_Persona_results_v1|" + secret).encode()).digest()


def decrypt_luna_combined(inp: Path, out: Path) -> None:
    secret = os.environ.get("OPENROUTER_API_KEY")
    if not secret:
        raise RuntimeError("OPENROUTER_API_KEY is required only as the historical encryption key")

    blob = base64.b64decode(inp.read_text(encoding="ascii"))
    if len(blob) <= 12:
        raise ValueError("Encrypted Luna result bundle is unexpectedly small")
    nonce, ciphertext = blob[:12], blob[12:]
    compressed = AESGCM(result_key(secret)).decrypt(nonce, ciphertext, COMBINED_AAD)
    plaintext = gzip.decompress(compressed)

    rows = [json.loads(line) for line in plaintext.decode("utf-8").splitlines() if line.strip()]
    successful = [row for row in rows if "error" not in row]
    pairs = {(str(row["anon_id"]), str(row["condition"])) for row in successful}
    respondents = {str(row["anon_id"]) for row in successful}
    conditions = {str(row["condition"]) for row in successful}

    if len(successful) != 2000 or len(pairs) != 2000 or len(respondents) != 1000:
        raise AssertionError(
            f"Expected 2,000 unique successful Luna respondent-condition rows over 1,000 respondents; "
            f"found rows={len(successful)}, pairs={len(pairs)}, respondents={len(respondents)}"
        )
    if conditions != {"thin", "rich"}:
        raise AssertionError(f"Unexpected Luna conditions: {sorted(conditions)}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(plaintext)
    print(json.dumps({
        "status": "LUNA_LEGACY_RECOVERY_PASS",
        "respondents": len(respondents),
        "successful_rows": len(successful),
        "conditions": sorted(conditions),
        "plaintext_sha256": hashlib.sha256(plaintext).hexdigest(),
        "note": "Plaintext is a transient CI input and must never be committed or uploaded as an artifact."
    }, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="Recover completed legacy LLM outputs for zero-inference harmonized analysis.")
    ap.add_argument("--luna-combined", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    decrypt_luna_combined(args.luna_combined, args.out)


if __name__ == "__main__":
    main()
