from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import os
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from prepare_sample import (
    ECON_MAP,
    ENROLMENT_MAP,
    GENDER_MAP,
    LANGUAGE_MAP,
    MARITAL_MAP,
    RELATION_MAP,
    RELIGION_MAP,
    SECTOR_MAP,
    SOCIAL_MAP,
    STATE_MAP,
    build_persona,
    build_prompt,
    response_schema,
)

BUNDLE_INFO = b"LLM_Persona_bundle_v2"
CODES_AAD = b"LLM_Persona_CAMS_codes_v2"
TRUTH_AAD = b"LLM_Persona_CAMS_truth_v2"


def secret() -> str:
    value = os.getenv("OPENROUTER_API_KEY")
    if not value:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    return value


def recipient_private_key(value: str) -> x25519.X25519PrivateKey:
    seed = hashlib.sha256(("LLM_Persona_bundle_v2|" + value).encode()).digest()
    return x25519.X25519PrivateKey.from_private_bytes(seed)


def decrypt_bundle(path: Path, aad: bytes) -> bytes:
    blob = base64.b64decode(path.read_text(encoding="ascii"))
    if len(blob) < 61:
        raise ValueError("Encrypted bundle is unexpectedly small")
    eph_pub, nonce, ciphertext = blob[:32], blob[32:44], blob[44:]
    private = recipient_private_key(secret())
    shared = private.exchange(x25519.X25519PublicKey.from_public_bytes(eph_pub))
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=BUNDLE_INFO).derive(shared)
    compressed = AESGCM(key).decrypt(nonce, ciphertext, aad)
    return gzip.decompress(compressed)


def decode_row(raw: dict[str, str]) -> SimpleNamespace:
    def integer(name: str) -> int:
        return int(float(raw[name]))

    return SimpleNamespace(
        age=integer("BL31C5"),
        gender=GENDER_MAP[integer("BL31C4")],
        sector=SECTOR_MAP[integer("SEC")],
        state_name=STATE_MAP[integer("ST")],
        relationship=RELATION_MAP[integer("BL31C3")],
        marital_status=MARITAL_MAP[integer("BL31C6")],
        enrolment_status=ENROLMENT_MAP[integer("BL31C7")],
        economic_activity_status=ECON_MAP[integer("BL31C8")],
        household_size=integer("BL41I1"),
        religion=RELIGION_MAP[integer("BL41I2")],
        social_group=SOCIAL_MAP[integer("BL41I3")],
        household_language=LANGUAGE_MAP[integer("BL41I4")],
        mpce_band=raw["mpce_band"],
    )


def make_requests(bundle: Path, out_requests: Path, out_schema: Path, chunk: int, chunk_size: int) -> None:
    text = decrypt_bundle(bundle, CODES_AAD).decode("utf-8")
    rows = list(csv.DictReader(StringIO(text)))
    if len(rows) != 1000:
        raise AssertionError(f"Expected 1000 persona-code rows, found {len(rows)}")
    if len({r['anon_id'] for r in rows}) != 1000:
        raise AssertionError("Persona-code bundle has duplicate anon_id values")

    requests = []
    for raw in rows:
        decoded = decode_row(raw)
        for condition in ("rich", "thin"):
            persona = build_persona(decoded, condition)
            requests.append({
                "anon_id": raw["anon_id"],
                "condition": condition,
                "persona": persona,
                "prompt": build_prompt(persona),
            })

    if len(requests) != 2000:
        raise AssertionError("Expected exactly 2000 production requests")
    pairs = {(r["anon_id"], r["condition"]) for r in requests}
    if len(pairs) != 2000:
        raise AssertionError("Duplicate respondent-condition pair")

    start = chunk * chunk_size
    selected = requests[start:start + chunk_size]
    if not selected:
        raise AssertionError(f"Chunk {chunk} is empty")
    if len(selected) != chunk_size:
        raise AssertionError(f"Chunk {chunk} contains {len(selected)}, expected {chunk_size}")

    out_requests.parent.mkdir(parents=True, exist_ok=True)
    with out_requests.open("w", encoding="utf-8") as f:
        for row in selected:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    out_schema.write_text(json.dumps(response_schema(), separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"chunk": chunk, "chunk_size": len(selected), "total_requests": len(requests)}))


def decrypt_truth(bundle: Path, out: Path) -> None:
    plaintext = decrypt_bundle(bundle, TRUTH_AAD)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(plaintext)
    line_count = max(0, len(plaintext.splitlines()) - 1)
    if line_count != 1000:
        raise AssertionError(f"Expected 1000 truth rows, found {line_count}")
    print(json.dumps({"truth_rows": line_count, "sha256": hashlib.sha256(plaintext).hexdigest()}))


def result_key(value: str) -> bytes:
    return hashlib.sha256(("LLM_Persona_results_v1|" + value).encode()).digest()


def encrypt_results(inp: Path, out: Path, chunk: int) -> None:
    plaintext = inp.read_bytes() if inp.exists() else b""
    compressed = gzip.compress(plaintext, compresslevel=9)
    nonce = os.urandom(12)
    aad = f"LLM_Persona_results_chunk_{chunk:03d}".encode()
    blob = nonce + AESGCM(result_key(secret())).encrypt(nonce, compressed, aad)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(base64.b64encode(blob).decode(), encoding="ascii")
    lines = [x for x in plaintext.splitlines() if x.strip()]
    successes = failures = 0
    for line in lines:
        row = json.loads(line)
        if "error" in row:
            failures += 1
        else:
            successes += 1
    print(json.dumps({"chunk": chunk, "saved_rows": len(lines), "successes": successes, "failures": failures}))


def decrypt_result_file(path: Path, chunk: int) -> bytes:
    blob = base64.b64decode(path.read_text(encoding="ascii"))
    nonce, ciphertext = blob[:12], blob[12:]
    aad = f"LLM_Persona_results_chunk_{chunk:03d}".encode()
    compressed = AESGCM(result_key(secret())).decrypt(nonce, ciphertext, aad)
    return gzip.decompress(compressed)


def combine_results(root: Path, out: Path, manifest_out: Path) -> None:
    successful: dict[tuple[str, str], dict] = {}
    latest_errors: dict[tuple[str, str], dict] = {}
    artifact_files = sorted(root.rglob("chunk-*.results.enc.b64"))
    for path in artifact_files:
        chunk = int(path.name.split("-")[1].split(".")[0])
        plaintext = decrypt_result_file(path, chunk)
        for line in plaintext.decode("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            key = (row["anon_id"], row["condition"])
            if "error" in row:
                if key not in successful:
                    latest_errors[key] = row
            else:
                successful[key] = row
                latest_errors.pop(key, None)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for key in sorted(successful):
            f.write(json.dumps(successful[key], ensure_ascii=False) + "\n")

    prompt_tokens = sum(int(r.get("prompt_tokens") or 0) for r in successful.values())
    completion_tokens = sum(int(r.get("completion_tokens") or 0) for r in successful.values())
    manifest = {
        "artifact_files": len(artifact_files),
        "successful_unique_requests": len(successful),
        "remaining_failed_requests": len(latest_errors),
        "complete": len(successful) == 2000,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }
    manifest_out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


def encrypt_combined(inp: Path, out: Path) -> None:
    plaintext = inp.read_bytes()
    compressed = gzip.compress(plaintext, compresslevel=9)
    nonce = os.urandom(12)
    aad = b"LLM_Persona_results_combined_v1"
    blob = nonce + AESGCM(result_key(secret())).encrypt(nonce, compressed, aad)
    out.write_text(base64.b64encode(blob).decode(), encoding="ascii")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("requests")
    p.add_argument("--bundle", required=True)
    p.add_argument("--out-requests", required=True)
    p.add_argument("--out-schema", required=True)
    p.add_argument("--chunk", type=int, required=True)
    p.add_argument("--chunk-size", type=int, default=25)

    p = sub.add_parser("truth")
    p.add_argument("--bundle", required=True)
    p.add_argument("--out", required=True)

    p = sub.add_parser("encrypt-results")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--chunk", type=int, required=True)

    p = sub.add_parser("combine")
    p.add_argument("--root", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--manifest", required=True)

    p = sub.add_parser("encrypt-combined")
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", required=True)

    args = ap.parse_args()
    if args.cmd == "requests":
        make_requests(Path(args.bundle), Path(args.out_requests), Path(args.out_schema), args.chunk, args.chunk_size)
    elif args.cmd == "truth":
        decrypt_truth(Path(args.bundle), Path(args.out))
    elif args.cmd == "encrypt-results":
        encrypt_results(Path(args.inp), Path(args.out), args.chunk)
    elif args.cmd == "combine":
        combine_results(Path(args.root), Path(args.out), Path(args.manifest))
    elif args.cmd == "encrypt-combined":
        encrypt_combined(Path(args.inp), Path(args.out))


if __name__ == "__main__":
    main()
